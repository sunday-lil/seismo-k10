/**
 * ==================================================================
 *  震感捕手 · 遥测版（K10 + WiFi + Web 服务器）
 *  在 main.cpp 的基础上增加：
 *    - 配网（Preferences 保存 SSID，失败回落 AP 热点）
 *    - HTTP 接口：/api/now、/api/wave、/api/record、/api/last
 *    - 手机/电脑浏览器直接看实时波形（无需装 App）
 *    - mDNS：http://seismo.local
 *
 *  设计原则：遥测只在“监测”时跑，正式记录时以采样精度优先，
 *  HTTP 每 50 ms 服务一次，且用绝对时间戳补偿，不改变 200 Hz 采样节拍。
 * ==================================================================
 */
#include "unihiker_k10.h"
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ESPmDNS.h>
#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

UNIHIKER_K10 k10;
WebServer server(80);
Preferences prefs;

/* ================= 实验参数 ================= */
#define EXP_ID      "E1"
#define DIST_M      0.60f
#define TRIAL_NO    1
#define NOTE_TXT    "wood"
#define SCREEN_DIR  2

#define FS_HZ       200
#define PRE_S       1.0f
#define POST_S      4.0f
#define TRIG_G      0.05f
#define TRIG_HOLD   3
#define ALARM_G     0.25f
#define WAIT_MS     20000UL

#define ACC_TO_G    0.001f

/* ================= 屏幕 ================= */
#define C_BG     0x0B1220u
#define C_TEXT   0xE5E7EBu
#define C_DIM    0x7C8AA0u
#define C_CYAN   0x22D3EEu
#define C_AMBER  0xF59E0Bu
#define C_VIOLET 0xA78BFAu
#define C_GREEN  0x34D399u
#define C_RED    0xEF4444u

/* ================= 状态 ================= */
struct Sample { int16_t x, y, z; };

static const int PRE_N  = (int)(FS_HZ * PRE_S);
static const int POST_N = (int)(FS_HZ * POST_S);
static const int BUF_N  = PRE_N + POST_N;

static Sample ringBuf[PRE_N];
static int    ringHead = 0, ringCount = 0;
static Sample burst[BUF_N + 16];
static Sample waveWin[240];
static int    waveN = 0;
static uint32_t waveSeq = 0;

static float g_bx = 0, g_by = 0, g_bz = 1000.0f;
static uint32_t g_nextUs = 0, g_periodUs = 0;
static char g_filePath[64] = "SERIAL";

static volatile int  g_state = 0;          // 0 监测 / 1 记录 / 2 完成
static volatile bool g_reqRecord = false;  // 网页点“记录”
static volatile float g_pga = 0;

struct LastEvent {
  bool valid = false;
  float pga = 0, f = 0, dur = 0;
  char axis = 'Z';
  uint32_t ms = 0;
  char file[48] = "";
};
static LastEvent g_last;

static bool networkReady = false;
static String deviceIP = "";
static bool needApConfig = false;

/* ================= 基础 ================= */
static inline int16_t clamp16(int v) {
  if (v > 32767) return 32767;
  if (v < -32768) return -32768;
  return (int16_t)v;
}
static inline void readAcc(int16_t &x, int16_t &y, int16_t &z) {
  x = clamp16(k10.getAccelerometerX());
  y = clamp16(k10.getAccelerometerY());
  z = clamp16(k10.getAccelerometerZ());
}
static inline void waitNextSample() {
  g_nextUs += g_periodUs;
  int32_t d = (int32_t)(g_nextUs - micros());
  if (d > 0) delayMicroseconds((uint32_t)d);
  else g_nextUs = micros();
}
static void setRgb(uint32_t c) {
  uint8_t r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, b = c & 0xFF;
  for (int i = 0; i < 3; i++) k10.rgb->write(i, r, g, b);
}
static inline void textRow(uint8_t row, const char *s, uint32_t color) {
  k10.canvas->canvasText(s, row, color);
}

/* ================= 屏幕 ================= */
static void drawScreen(const char *state, float pga) {
  k10.setScreenBackground(C_BG);
  textRow(1, "震感捕手 遥测版", C_TEXT);
  textRow(2, state, C_CYAN);
  char line[32];
  snprintf(line, sizeof(line), "峰值 %.3f g", pga);
  textRow(3, line, pga >= ALARM_G ? C_RED : (pga >= 0.03f ? C_AMBER : C_GREEN));
  textRow(5, deviceIP.length() ? deviceIP.c_str() : "192.168.4.1", C_DIM);
  textRow(6, "seismo.local", C_DIM);
  textRow(8, "A:记录  B:重连", C_DIM);
  k10.canvas->updateCanvas();
}

static void calibrateBaseline() {
  drawScreen("校准中", 0);
  double sx = 0, sy = 0, sz = 0;
  int n = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < 400) {
    int16_t x, y, z;
    readAcc(x, y, z);
    sx += x; sy += y; sz += z; n++;
    delay(5);
  }
  if (n > 0) { g_bx = sx / n; g_by = sy / n; g_bz = sz / n; }
  Serial.printf("# baseline %.0f %.0f %.0f\n", g_bx, g_by, g_bz);
}

/* ================= 数据快照（给 HTTP） ================= */
static void pushWave(const Sample &s) {
  if (waveN < 240) waveWin[waveN++] = s;
  else { memmove(waveWin, waveWin + 1, sizeof(Sample) * 239); waveWin[239] = s; }
  waveSeq++;
}

/* ================= HTTP ================= */
static void handleDashboard() {
  String html = R"HTML(<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>震感捕手 遥测</title><style>
body{margin:0;background:#0B1220;color:#E5E7EB;font-family:system-ui,"Microsoft YaHei",sans-serif}
.wrap{padding:14px 16px}
.hd{display:flex;justify-content:space-between;align-items:baseline}
.t{font-size:15px;color:#7C8AA0}.s{font-size:13px;color:#22D3EE}
.pga{font-size:44px;font-weight:700;margin:6px 0 0}
.u{font-size:14px;color:#7C8AA0;margin-left:4px}
canvas{width:100%;height:220px;display:block;background:#0F1726;border-radius:10px;margin-top:10px}
.row{display:flex;gap:8px;margin-top:12px}
button{flex:1;padding:13px;border:0;border-radius:10px;font-size:15px;background:#1B998B;color:#fff}
button.ghost{background:#1C2A3A;color:#9FB3C8}
.meta{margin-top:12px;font-size:12px;color:#7C8AA0;line-height:1.7}
</style></head><body><div class="wrap">
<div class="hd"><span class="t">震感捕手 · K10</span><span class="s" id="st">连接中…</span></div>
<div><span class="pga" id="pga">0.000</span><span class="u">g</span></div>
<canvas id="cv"></canvas>
<div class="row"><button onclick="rec()">记录一次</button><button class="ghost" onclick="rst()">重新校准</button></div>
<div class="meta" id="meta"></div>
</div><script>
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let W=0,H=0,data=[];
function fit(){const r=cv.getBoundingClientRect();W=cv.width=r.width*devicePixelRatio;H=cv.height=r.height*devicePixelRatio;}
addEventListener('resize',fit);fit();
function draw(){
  ctx.clearRect(0,0,W,H);
  const lanes=[0.2,0.5,0.8],cols=['#22D3EE','#F59E0B','#A78BFA'];
  ctx.lineWidth=devicePixelRatio;
  lanes.forEach((p,i)=>{
    const y=H*p;ctx.strokeStyle='#1E2A3A';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();
    if(data.length<2)return;
    ctx.strokeStyle=cols[i];ctx.beginPath();
    const n=data.length,step=Math.max(1,Math.floor(n/200));
    for(let j=0,k=0;j<n;j+=step,k++){
      const v=data[j][i],x=k*(W/(n/step-1)),yy=y-v*H*0.14;
      j===0?ctx.moveTo(x,yy):ctx.lineTo(x,yy);
    }
    ctx.stroke();
  });
}
async function tick(){
  try{
    const w=await (await fetch('/api/wave')).json();
    data=w.data||[];
    const n=await (await fetch('/api/now')).json();
    document.getElementById('pga').textContent=(n.pga||0).toFixed(3);
    document.getElementById('st').textContent=n.state;
    document.getElementById('meta').innerHTML='实验 '+n.exp+' · '+n.dist+' m · 第 '+n.trial+' 次<br>采样 '+n.fs+' Hz · 基线 '+n.base+' mg';
    document.getElementById('pga').style.color=n.pga>0.25?'#EF4444':(n.pga>0.03?'#F59E0B':'#34D399');
  }catch(e){document.getElementById('st').textContent='已断开';}
  draw();
}
setInterval(tick,200);tick();
async function rec(){await fetch('/api/record');}
async function rst(){await fetch('/api/calib');}
</script></body></html>)HTML";
  server.send(200, "text/html; charset=utf-8", html);
}

static void handleNow() {
  char buf[260];
  const char *st = g_state == 0 ? "MONITOR" : (g_state == 1 ? "RECORDING" : "DONE");
  snprintf(buf, sizeof(buf),
           "{\"state\":\"%s\",\"pga\":%.4f,\"exp\":\"%s\",\"dist\":%.2f,\"trial\":%d,"
           "\"fs\":%d,\"base\":%d,\"seq\":%lu}",
           st, (double)g_pga, EXP_ID, (double)DIST_M, TRIAL_NO, FS_HZ, (int)g_bz,
           (unsigned long)waveSeq);
  server.send(200, "application/json", buf);
}

static void handleWave() {
  String out;
  out.reserve(240 * 18 + 40);
  out += "{\"seq\":";
  out += String((unsigned long)waveSeq);
  out += ",\"data\":[";
  int n = waveN;
  int step = n > 120 ? n / 120 : 1;
  bool first = true;
  for (int i = 0; i < n; i += step) {
    if (!first) out += ",";
    first = false;
    char b[40];
    snprintf(b, sizeof(b), "[%.3f,%.3f,%.3f]",
             (waveWin[i].x - g_bx) * ACC_TO_G,
             (waveWin[i].y - g_by) * ACC_TO_G,
             (waveWin[i].z - g_bz) * ACC_TO_G);
    out += b;
  }
  out += "]}";
  server.send(200, "application/json", out);
}

static void handleRecordReq() {
  g_reqRecord = true;
  server.send(200, "application/json", "{\"ok\":1}");
}

static void handleLast() {
  char buf[220];
  if (!g_last.valid) {
    server.send(200, "application/json", "{\"ok\":0}");
    return;
  }
  snprintf(buf, sizeof(buf),
           "{\"ok\":1,\"pga\":%.4f,\"f\":%.2f,\"dur\":%.0f,\"axis\":\"%c\",\"ms\":%lu,\"file\":\"%s\"}",
           (double)g_last.pga, (double)g_last.f, (double)g_last.dur, g_last.axis,
           (unsigned long)g_last.ms, g_last.file);
  server.send(200, "application/json", buf);
}

/* ================= 配网 ================= */
static void handleConfigPage() {
  String html = R"HTML(<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>震感捕手 配网</title>
<style>body{font-family:system-ui,"Microsoft YaHei";background:#0B1220;color:#E5E7EB;padding:24px}
input,button{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:1px solid #2A3A4E;background:#111C2E;color:#E5E7EB}
button{background:#1B998B;border:0;font-size:16px}</style>
<h2>震感捕手 · 配网</h2><p style="color:#7C8AA0">输入 2.4G WiFi，设备重启后自动连接</p>
<form method="post" action="/save">
<input name="ssid" placeholder="WiFi 名称" required>
<input name="pass" type="password" placeholder="密码">
<button type="submit">保存并重启</button></form></body></html>)HTML";
  server.send(200, "text/html; charset=utf-8", html);
}

static void handleSaveWifi() {
  prefs.begin("seismo", false);
  prefs.putString("ssid", server.arg("ssid"));
  prefs.putString("pass", server.arg("pass"));
  prefs.end();
  server.send(200, "text/html; charset=utf-8",
              "<meta charset='utf-8'><body style='background:#0B1220;color:#fff;font-family:sans-serif;padding:24px'>"
              "<h2>已保存，正在重启…</h2></body>");
  delay(800);
  ESP.restart();
}

static void handleReset() {
  prefs.begin("seismo", false);
  prefs.clear();
  prefs.end();
  server.send(200, "text/html; charset=utf-8",
              "<meta charset='utf-8'><body style='background:#0B1220;color:#fff;font-family:sans-serif;padding:24px'>"
              "<h2>已清除配网，重启后进入热点模式</h2></body>");
  delay(800);
  ESP.restart();
}

static void setupNetwork() {
  prefs.begin("seismo", true);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  prefs.end();

  if (ssid.length()) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());
    for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
    if (WiFi.status() == WL_CONNECTED) {
      networkReady = true;
      deviceIP = WiFi.localIP().toString();
      MDNS.begin("seismo");
      MDNS.addService("http", "tcp", 80);
      Serial.println("# STA IP " + deviceIP);
    }
  }
  if (!networkReady) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP("K10-Seismo-Setup");
    deviceIP = WiFi.softAPIP().toString();
    needApConfig = true;
    Serial.println("# AP 192.168.4.1");
  }

  if (needApConfig) {
    server.on("/", handleConfigPage);
    server.on("/save", HTTP_POST, handleSaveWifi);
  } else {
    server.on("/", handleDashboard);
    server.on("/api/now", handleNow);
    server.on("/api/wave", handleWave);
    server.on("/api/record", handleRecordReq);
    server.on("/api/last", handleLast);
    server.on("/api/calib", []() { calibrateBaseline(); server.send(200, "application/json", "{\"ok\":1}"); });
  }
  server.on("/reset", handleReset);
  server.begin();
}

/* ================= 记录 ================= */
static void pushRing(const Sample &s) {
  ringBuf[ringHead] = s;
  ringHead = (ringHead + 1) % PRE_N;
  if (ringCount < PRE_N) ringCount++;
}
static void copyRingToBurst() {
  int start = (ringHead - ringCount + PRE_N) % PRE_N;
  for (int i = 0; i < ringCount; i++) burst[i] = ringBuf[(start + i) % PRE_N];
}

static void analyse(const Sample *buf, int n, int trigIdx,
                    float &pga, char &axis, float &fHz, float &durMs) {
  int baseN = (trigIdx > 20) ? trigIdx / 2 : 1;
  if (baseN > n) baseN = n;
  float bx = 0, by = 0, bz = 0;
  for (int i = 0; i < baseN; i++) { bx += buf[i].x; by += buf[i].y; bz += buf[i].z; }
  bx /= baseN; by /= baseN; bz /= baseN;

  /* 峰值窗口要从触发点前几个样本开始，否则会漏掉冲击峰值 */
  int i0 = trigIdx - 5;
  int i1 = trigIdx + (int)(FS_HZ * 1.5f);
  if (i0 < 0) i0 = 0;
  if (i1 > n) i1 = n;
  if (i1 <= i0 + 10) { i0 = 0; i1 = n; }
  int f0 = trigIdx;
  if (f0 < i0) f0 = i0;
  if (f0 > i1 - 10) f0 = i0;

  float mx = 0, my = 0, mz = 0;
  for (int i = i0; i < i1; i++) {
    float ax = fabsf((buf[i].x - bx) * ACC_TO_G);
    float ay = fabsf((buf[i].y - by) * ACC_TO_G);
    float az = fabsf((buf[i].z - bz) * ACC_TO_G);
    if (ax > mx) mx = ax;
    if (ay > my) my = ay;
    if (az > mz) mz = az;
  }
  pga = mx; axis = 'X';
  if (my > pga) { pga = my; axis = 'Y'; }
  if (mz > pga) { pga = mz; axis = 'Z'; }

  float mean = (axis == 'X') ? bx : (axis == 'Y' ? by : bz);
  int cross = 0; float prev = 0;
  for (int i = f0; i < i1; i++) {
    float v = ((axis == 'X') ? buf[i].x : (axis == 'Y' ? buf[i].y : buf[i].z)) - mean;
    if (i > f0 && ((prev < 0 && v >= 0) || (prev > 0 && v <= 0))) cross++;
    prev = v;
  }
  float span = (i1 - f0) / (float)FS_HZ;
  fHz = span > 0 ? cross / (2.0f * span) : 0;

  float thr = pga * 0.10f;
  int first = -1, last = -1;
  for (int i = i0; i < i1; i++) {
    float v = fabsf(((axis == 'X') ? buf[i].x : (axis == 'Y' ? buf[i].y : buf[i].z)) - mean) * ACC_TO_G;
    if (v > thr) { if (first < 0) first = i; last = i; }
  }
  durMs = first >= 0 ? (last - first) * 1000.0f / FS_HZ : 0;
}

static bool writeCsv(const char *path, const Sample *buf, int n, int trigIdx,
                     float pga, float fHz, float durMs) {
  FILE *fp = fopen(path, "w");
  if (!fp) return false;
  fprintf(fp, "# device=UNIHIKER K10\n# exp=%s\n# dist_m=%.3f\n# trial=%d\n",
          EXP_ID, (double)DIST_M, TRIAL_NO);
  fprintf(fp, "# note=%s\n# fs=%.1f\n# unit=mg\n# trig_idx=%d\n",
          NOTE_TXT, (double)FS_HZ, trigIdx);
  fprintf(fp, "# pga_g=%.4f\n# f_hz=%.2f\n# dur_ms=%.1f\n", pga, fHz, durMs);
  fprintf(fp, "t_ms,ax,ay,az\n");
  for (int i = 0; i < n; i++)
    fprintf(fp, "%.1f,%d,%d,%d\n", (i - trigIdx) * 1000.0f / FS_HZ, buf[i].x, buf[i].y, buf[i].z);
  fclose(fp);
  return true;
}

static void runRecord() {
  g_state = 1;
  ringHead = ringCount = 0;
  calibrateBaseline();
  drawScreen("等待触发", 0);
  setRgb(C_CYAN);

  uint32_t tStart = millis();
  bool triggered = false;
  int over = 0, n = 0, trigIdx = 0;
  uint32_t tHttp = millis();

  g_periodUs = 1000000UL / FS_HZ;
  g_nextUs = micros();

  while (true) {
    if (!triggered && k10.buttonB->isPressed()) { g_state = 0; setRgb(0); return; }

    Sample s;
    readAcc(s.x, s.y, s.z);

    if (!triggered) {
      pushRing(s);
      float dx = (s.x - g_bx) * ACC_TO_G, dy = (s.y - g_by) * ACC_TO_G, dz = (s.z - g_bz) * ACC_TO_G;
      float dev = sqrtf(dx * dx + dy * dy + dz * dz);
      over = (dev > TRIG_G) ? over + 1 : 0;
      if (over >= TRIG_HOLD) {
        triggered = true;
        trigIdx = ringCount - 1;
        copyRingToBurst();
        n = ringCount;
        setRgb(C_RED);
      } else if (millis() - tStart > WAIT_MS) {
        g_state = 0; setRgb(0); drawScreen("超时", 0); delay(600); return;
      }
    } else if (n < BUF_N) {
      burst[n++] = s;
    }
    if (triggered && n >= BUF_N) break;

    if (millis() - tHttp > 50) { server.handleClient(); tHttp = millis(); }
    waitNextSample();
  }

  float pga, fHz, durMs; char axis;
  analyse(burst, n, trigIdx, pga, axis, fHz, durMs);

  g_filePath[0] = 0;
  const char *dirs[] = {"S:/", "/sdcard/", "/sd/", "/"};
  for (int i = 0; i < 4; i++) {
    char p[72];
    snprintf(p, sizeof(p), "%s%s_d%03d_t%d.csv", dirs[i], EXP_ID, (int)(DIST_M * 100), TRIAL_NO);
    if (writeCsv(p, burst, n, trigIdx, pga, fHz, durMs)) { strncpy(g_filePath, p, sizeof(g_filePath) - 1); break; }
  }

  g_last.valid = true;
  g_last.pga = pga; g_last.f = fHz; g_last.dur = durMs; g_last.axis = axis;
  g_last.ms = millis();
  strncpy(g_last.file, g_filePath[0] ? g_filePath : "SERIAL", sizeof(g_last.file) - 1);

  g_state = 2;
  g_pga = pga;
  drawScreen("记录完成", pga);
  setRgb(pga >= ALARM_G ? C_RED : C_GREEN);
  server.handleClient();
  delay(1200);
  setRgb(0);
  g_state = 0;
}

/* ================= 监测 ================= */
static void runMonitor() {
  waveN = 0;
  float pga = 0;
  uint32_t tUi = 0, tHttp = 0;
  g_periodUs = 1000000UL / FS_HZ;
  g_nextUs = micros();

  while (true) {
    if (k10.buttonA->isPressed() || g_reqRecord) {
      g_reqRecord = false;
      delay(150);
      return;
    }
    Sample s;
    readAcc(s.x, s.y, s.z);
    pushWave(s);

    if (millis() - tUi > 100) {
      tUi = millis();
      float mx = 0;
      int from = waveN > 60 ? waveN - 60 : 0;
      for (int i = from; i < waveN; i++) {
        float ax = fabsf((waveWin[i].x - g_bx) * ACC_TO_G);
        float ay = fabsf((waveWin[i].y - g_by) * ACC_TO_G);
        float az = fabsf((waveWin[i].z - g_bz) * ACC_TO_G);
        if (ax > mx) mx = ax;
        if (ay > mx) mx = ay;
        if (az > mx) mx = az;
      }
      pga = mx; g_pga = pga;
      setRgb(pga < 0.03f ? 0 : (pga < ALARM_G ? C_AMBER : C_RED));
      drawScreen("监测中", pga);
    }
    if (millis() - tHttp > 20) { server.handleClient(); tHttp = millis(); }
    waitNextSample();
  }
}

/* ================= 入口 ================= */
void setup() {
  Serial.begin(115200);
  k10.begin();
  k10.initScreen(SCREEN_DIR);
  k10.creatCanvas();
  k10.initSDFile();
  k10.rgb->brightness(6);

  drawScreen("启动中", 0);
  setupNetwork();
  calibrateBaseline();
}

void loop() {
  runMonitor();
  runRecord();
}
