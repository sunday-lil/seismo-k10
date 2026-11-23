/**
 * ==================================================================
 *  震感捕手 · UNIHIKER K10 振动采集终端（Arduino C++）  v2.0
 *  科学教育“做中学”案例 · 地球奥秘方向
 * ------------------------------------------------------------------
 *  开发环境：Arduino IDE（安装 UNIHIKER K10 BSP）
 *            或 PlatformIO（platform = DFRobot/platform-unihiker）
 *  依赖库  ：unihiker_k10.h（BSP 自带，无需另外安装）
 *
 *  功能：
 *    1) 实时监测：三轴波形 + 当前峰值 + 震动等级（RGB 灯）
 *    2) 事件记录：A 键启动，自动等待触发，记录“触发前 1 s + 触发后 4 s”
 *    3) 数据存盘：优先写 TF 卡 CSV；失败则从 USB 串口整块输出
 *    4) 现场读数：PGA、主振方向、主频估计、持续时长
 *
 *  用法：
 *    1) 改下面“实验参数”里的 EXP_ID / DIST_M / TRIAL_NO / NOTE_TXT
 *    2) 编译上传，按 RST 运行
 *    3) A 键 = 记录一次，B 键 = 取消 / 返回
 *    4) 实验结束取 TF 卡，或运行 02_代码/分析端/serial_capture.py 从串口抓数据
 * ==================================================================
 */
#include "unihiker_k10.h"
#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

UNIHIKER_K10 k10;

/* ================= 实验参数（学生只改这里） ================= */
#define EXP_ID      "E1"      // E1 距离衰减 / E2 方向 / E3 建筑 / TEST 试测
#define DIST_M      0.60f     // 测点到震源的距离（m），卷尺量到 0.01 m
#define TRIAL_NO    1         // 第几次重复
#define NOTE_TXT    "wood"    // 备注：wood / tile / carpet ...
#define SCREEN_DIR  2         // 屏幕方向 0~3

#define FS_HZ       200       // 采样率（Hz）
#define PRE_S       1.0f      // 预触发时长（s）
#define POST_S      4.0f      // 触发后记录时长（s）
#define TRIG_G      0.05f     // 触发阈值（g）
#define TRIG_HOLD   3         // 连续超过阈值多少个样本才触发
#define ALARM_G     0.25f     // 报警阈值（g）
#define WAIT_MS     20000UL   // 等待触发超时（ms）

/* 库返回的单位是 mg（1000 = 1 g）。
 * 如果你的 BSP 版本返回 m/s²，把这里改成 (1.0f / 9.80665f)。 */
#define ACC_TO_G    0.001f


/* ================= 界面语言 =================
 * 1 = 中文，0 = 英文。
 * 如果屏幕上中文变成方块/乱码，说明固件字库不是 UTF-8，把它改成 0 即可。
 */
#define UI_CN 1

#if UI_CN
  #define T_TITLE   "震感捕手"
  #define T_MONITOR "监测中"
  #define T_CALIB   "校准中"
  #define T_WAIT    "等待触发"
  #define T_CANCEL  "已取消"
  #define T_TIMEOUT "等待超时"
  #define T_BOOT    "启动中"
  #define T_DONE    "记录完成"
  #define T_PGA     "峰值 %.3f g"
  #define T_REC     "A:记录 B:取消"
  #define T_BACK    "B:返回"
  #define T_AXIS    "方向 %c"
  #define T_FREQ    "主频 %.1f Hz"
  #define T_DUR     "时长 %.0f ms"
  #define T_SAVED   "已存卡"
  #define T_SERIAL  "仅串口"
#else
  #define T_TITLE   "SEISMO K10"
  #define T_MONITOR "MONITOR"
  #define T_CALIB   "CALIB"
  #define T_WAIT    "WAIT"
  #define T_CANCEL  "CANCEL"
  #define T_TIMEOUT "TIMEOUT"
  #define T_BOOT    "BOOT"
  #define T_DONE    "DONE"
  #define T_PGA     "PGA %.3f g"
  #define T_REC     "A:REC B:CANC"
  #define T_BACK    "B:BACK"
  #define T_AXIS    "AXIS %c"
  #define T_FREQ    "FREQ %.1f Hz"
  #define T_DUR     "DUR %.0f ms"
  #define T_SAVED   "SAVED"
  #define T_SERIAL  "SERIAL"
#endif

/* ================= 屏幕与配色 ================= */
#define SCR_W       240
#define SCR_H       320
#define WAVE_TOP    175
#define WAVE_H      142   /* 175+142=317，别超出 320 */

#define C_BG        0x0B1220u
#define C_TEXT      0xE5E7EBu
#define C_DIM       0x7C8AA0u
#define C_CYAN      0x22D3EEu
#define C_AMBER     0xF59E0Bu
#define C_VIOLET    0xA78BFAu
#define C_GREEN     0x34D399u
#define C_RED       0xEF4444u
#define C_GRID      0x1E2A3Au

/* ================= 数据结构 ================= */
struct Sample {
  int16_t x, y, z;      // mg
};

static const int PRE_N  = (int)(FS_HZ * PRE_S);              // 200
static const int POST_N = (int)(FS_HZ * POST_S);             // 800
static const int BUF_N  = PRE_N + POST_N;                    // 1000

static Sample ringBuf[PRE_N];        // 环形缓冲：最近 1 s
static int    ringHead  = 0;
static int    ringCount = 0;
static Sample burst[BUF_N + 16];     // 一次事件的完整数据

static uint32_t g_nextUs   = 0;      // 采样节拍
static uint32_t g_periodUs = 0;
static char     g_filePath[64] = "SERIAL";

/* 静止基线（mg）。开机/每次记录前重新测一次。
 * 不假设“Z 一定是 +1000”，这样板子倒放、倾斜、Z 轴朝下都不会算错。 */
static float g_bx = 0, g_by = 0, g_bz = 1000.0f;

/* ================= 小工具 ================= */
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

/* 按固定周期等待，保证采样率稳定 */
static inline void waitNextSample() {
  g_nextUs += g_periodUs;
  int32_t d = (int32_t)(g_nextUs - micros());
  if (d > 0) {
    delayMicroseconds((uint32_t)d);
  } else {
    g_nextUs = micros();          // 落后太多就重新对齐
  }
}

static void setRgb(uint32_t c) {
  uint8_t r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, b = c & 0xFF;
  k10.rgb->write(0, r, g, b);
  k10.rgb->write(1, r, g, b);
  k10.rgb->write(2, r, g, b);
}

static void rgbOff() {
  k10.rgb->write(0, 0, 0, 0);
  k10.rgb->write(1, 0, 0, 0);
  k10.rgb->write(2, 0, 0, 0);
}

static inline void textRow(uint8_t row, const char *s, uint32_t color) {
  k10.canvas->canvasText(s, row, color);
}

/* ================= 波形区 ================= */
static void drawWave(const Sample *buf, int n) {
  /* 只清波形区，避免整屏重绘闪烁 */
  k10.canvas->canvasRectangle(0, WAVE_TOP, SCR_W, WAVE_H, C_BG, C_BG, true);

  const uint32_t cols[3] = {C_CYAN, C_AMBER, C_VIOLET};
  const int laneY[3] = {195, 235, 275};
  const int halfH = 16;
  const float bx = g_bx * ACC_TO_G, by = g_by * ACC_TO_G, bz = g_bz * ACC_TO_G;

  k10.canvas->canvasSetLineWidth(1);
  for (int k = 0; k < 3; k++) {
    k10.canvas->canvasLine(0, laneY[k], SCR_W - 1, laneY[k], C_GRID);
  }
  if (!buf || n < 2) return;

  int step = n / 60;
  if (step < 1) step = 1;

  for (int k = 0; k < 3; k++) {
    int16_t prevX = 0, prevY = laneY[k];
    bool first = true;
    for (int i = 0; i < n; i += step) {
      int16_t raw = (k == 0) ? buf[i].x : (k == 1 ? buf[i].y : buf[i].z);
      float g = raw * ACC_TO_G - (k == 0 ? bx : (k == 1 ? by : bz));
      int y = laneY[k] - (int)(g * 30.0f);
      if (y < laneY[k] - halfH) y = laneY[k] - halfH;
      if (y > laneY[k] + halfH) y = laneY[k] + halfH;
      int x = (int)((long)i * (SCR_W - 1) / (n - 1));
      if (!first) k10.canvas->canvasLine(prevX, prevY, x, y, cols[k]);
      prevX = x; prevY = y; first = false;
    }
  }
}

static void drawRaw(const Sample *s) {
  char line[24];
  snprintf(line, sizeof(line), "x%d y%d", s->x, s->y);
  textRow(5, line, C_DIM);
  snprintf(line, sizeof(line), "z%d b%d", s->z, (int)g_bz);
  textRow(6, line, C_DIM);
}

static void drawPga(float pga) {
  char line[32];
  snprintf(line, sizeof(line), T_PGA, pga);
  uint32_t c = (pga >= ALARM_G) ? C_RED : (pga >= 0.03f ? C_AMBER : C_GREEN);
  textRow(3, line, c);              // 定宽格式，直接覆盖即可
}

/* 整页重绘：只在进入新页面时调用 */
static void drawPage(const char *state, float pga, const Sample *buf, int n) {
  k10.setScreenBackground(C_BG);

  textRow(1, T_TITLE, C_TEXT);
  textRow(2, state, C_CYAN);

  char line[40];
  snprintf(line, sizeof(line), "%s %.2fm #%d", EXP_ID, DIST_M, TRIAL_NO);
  textRow(4, line, C_DIM);

  drawPga(pga);
  drawWave(buf, n);

  if (buf && n > 0) {
    snprintf(line, sizeof(line), "x%d y%d", buf[n - 1].x, buf[n - 1].y);
    textRow(5, line, C_DIM);
    snprintf(line, sizeof(line), "z%d b%d", buf[n - 1].z, (int)g_bz);
    textRow(6, line, C_DIM);
  } else {
    textRow(5, "x--- y---", C_DIM);
    textRow(6, "z--- b---", C_DIM);
  }
  textRow(7, T_REC, C_DIM);

  k10.canvas->updateCanvas();
}

/* 测 0.5 s 的静止基线。必须在板子放稳、手离开桌子时调用。 */
static void calibrateBaseline() {
  drawPage(T_CALIB, 0, nullptr, 0);
  double sx = 0, sy = 0, sz = 0;
  int n = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < 500) {
    int16_t x, y, z;
    readAcc(x, y, z);
    sx += x; sy += y; sz += z; n++;
    delay(5);
  }
  if (n > 0) {
    g_bx = sx / n; g_by = sy / n; g_bz = sz / n;
  }
  Serial.printf("# baseline mg: %.0f %.0f %.0f\n", g_bx, g_by, g_bz);
}

static void drawResult(float pga, char axis, float fHz, float durMs, bool saved) {
  k10.setScreenBackground(C_BG);
  textRow(1, T_DONE, C_GREEN);

  char line[40];
  snprintf(line, sizeof(line), T_PGA, pga);
  textRow(2, line, C_AMBER);

  snprintf(line, sizeof(line), T_AXIS, axis);
  textRow(3, line, C_TEXT);
  snprintf(line, sizeof(line), T_FREQ, fHz);
  textRow(4, line, C_TEXT);
  snprintf(line, sizeof(line), T_DUR, durMs);
  textRow(5, line, C_TEXT);

  textRow(6, saved ? T_SAVED : T_SERIAL, C_DIM);
  textRow(7, T_BACK, C_DIM);
  k10.canvas->updateCanvas();
}

/* ================= 存盘 ================= */
static bool writeCsvFile(const char *path, const Sample *buf, int n,
                         int trigIdx, float pga, float fHz, float durMs) {
  FILE *fp = fopen(path, "w");
  if (!fp) return false;

  fprintf(fp, "# device=UNIHIKER K10\n");
  fprintf(fp, "# exp=%s\n", EXP_ID);
  fprintf(fp, "# dist_m=%.3f\n", DIST_M);
  fprintf(fp, "# trial=%d\n", TRIAL_NO);
  fprintf(fp, "# note=%s\n", NOTE_TXT);
  fprintf(fp, "# fs=%.1f\n", (double)FS_HZ);
  fprintf(fp, "# unit=mg\n");
  fprintf(fp, "# trig_idx=%d\n", trigIdx);
  fprintf(fp, "# pga_g=%.4f\n", pga);
  fprintf(fp, "# f_hz=%.2f\n", fHz);
  fprintf(fp, "# dur_ms=%.1f\n", durMs);
  fprintf(fp, "t_ms,ax,ay,az\n");

  for (int i = 0; i < n; i++) {
    float t = (i - trigIdx) * 1000.0f / FS_HZ;
    fprintf(fp, "%.1f,%d,%d,%d\n", t, buf[i].x, buf[i].y, buf[i].z);
  }
  fclose(fp);
  return true;
}

static bool saveToTfCard(const Sample *buf, int n, int trigIdx,
                         float pga, float fHz, float durMs) {
  const char *dirs[] = {"S:/", "/sdcard/", "/sd/", "/"};
  char path[72];
  for (int i = 0; i < 4; i++) {
    snprintf(path, sizeof(path), "%s%s_d%03d_t%d.csv", dirs[i], EXP_ID,
             (int)(DIST_M * 100), TRIAL_NO);
    if (writeCsvFile(path, buf, n, trigIdx, pga, fHz, durMs)) {
      strncpy(g_filePath, path, sizeof(g_filePath) - 1);
      g_filePath[sizeof(g_filePath) - 1] = 0;
      return true;
    }
  }
  strncpy(g_filePath, "SERIAL ONLY", sizeof(g_filePath) - 1);
  return false;
}

/* 串口整块输出：PC 端 serial_capture.py 负责存成 CSV */
static void dumpToSerial(const Sample *buf, int n, int trigIdx,
                         float pga, float fHz, float durMs) {
  Serial.println("###BEGIN");
  Serial.printf("# device=UNIHIKER K10\n# exp=%s\n# dist_m=%.3f\n# trial=%d\n",
                EXP_ID, (double)DIST_M, TRIAL_NO);
  Serial.printf("# note=%s\n# fs=%.1f\n# unit=mg\n# trig_idx=%d\n", NOTE_TXT, (double)FS_HZ, trigIdx);
  Serial.printf("# pga_g=%.4f\n# f_hz=%.2f\n# dur_ms=%.1f\n", pga, fHz, durMs);
  Serial.println("t_ms,ax,ay,az");
  for (int i = 0; i < n; i++) {
    float t = (i - trigIdx) * 1000.0f / FS_HZ;
    Serial.printf("%.1f,%d,%d,%d\n", t, buf[i].x, buf[i].y, buf[i].z);
  }
  Serial.println("###END");
}

/* ================= 现场分析 ================= */
static void analyse(const Sample *buf, int n, int trigIdx,
                    float &pga, char &axis, float &fHz, float &durMs) {
  int baseN = (trigIdx > 20) ? trigIdx / 2 : 1;
  if (baseN > n) baseN = n;

  float bx = 0, by = 0, bz = 0;
  for (int i = 0; i < baseN; i++) {
    bx += buf[i].x; by += buf[i].y; bz += buf[i].z;
  }
  bx /= baseN; by /= baseN; bz /= baseN;

  /* 峰值窗口：从触发点前 5 个样本开始。
   * 触发条件是“连续 3 个样本超阈值”，冲击峰值通常就在触发点前后几毫秒；
   * 之前从 +50 ms 开始，会系统性漏掉峰值。 */
  int i0 = trigIdx - 5;
  int i1 = trigIdx + (int)(FS_HZ * 1.5f);
  if (i0 < 0) i0 = 0;
  if (i1 > n) i1 = n;
  if (i1 <= i0 + 10) { i0 = 0; i1 = n; }
  /* 频率/时长用触发后的窗口，避免把触发前噪声算进去 */
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

  /* 主频：主振轴零交叉计数 */
  int cross = 0;
  float mean = (axis == 'X') ? bx : (axis == 'Y' ? by : bz);
  float prev = 0;
  for (int i = f0; i < i1; i++) {
    float v = ((axis == 'X') ? buf[i].x : (axis == 'Y' ? buf[i].y : buf[i].z)) - mean;
    if (i > f0 && ((prev < 0 && v >= 0) || (prev > 0 && v <= 0))) cross++;
    prev = v;
  }
  float span = (i1 - f0) / (float)FS_HZ;
  fHz = (span > 0) ? (cross / (2.0f * span)) : 0;

  /* 持续时间：包络超过峰值 10% 的时间跨度 */
  float thr = pga * 0.10f;
  int first = -1, last = -1;
  for (int i = i0; i < i1; i++) {
    float v = fabsf(((axis == 'X') ? buf[i].x : (axis == 'Y' ? buf[i].y : buf[i].z)) - mean) * ACC_TO_G;
    if (v > thr) {
      if (first < 0) first = i;
      last = i;
    }
  }
  durMs = (first >= 0) ? (last - first) * 1000.0f / FS_HZ : 0;
}

/* ================= 记录流程 ================= */
static void pushRing(const Sample &s) {
  ringBuf[ringHead] = s;
  ringHead = (ringHead + 1) % PRE_N;
  if (ringCount < PRE_N) ringCount++;
}

static void copyRingToBurst() {
  int start = (ringHead - ringCount + PRE_N) % PRE_N;
  for (int i = 0; i < ringCount; i++) {
    burst[i] = ringBuf[(start + i) % PRE_N];
  }
}

static void waitButtonB() {
  /* 最多等 15 s：B 键没反应时自动回待机，避免整机看起来死机 */
  uint32_t t0 = millis();
  while (!k10.buttonB->isPressed()) {
    if (millis() - t0 > 15000UL) return;
    delay(20);
  }
  delay(250);
}

static void runRecord() {
  ringHead = 0;
  ringCount = 0;

  calibrateBaseline();
  drawPage(T_WAIT, 0, nullptr, 0);
  setRgb(C_CYAN);

  uint32_t tStart = millis();
  bool triggered = false;
  int  over = 0;
  int  n = 0;
  int  trigIdx = 0;

  g_periodUs = 1000000UL / FS_HZ;
  g_nextUs = micros();

  while (true) {
    if (!triggered && k10.buttonB->isPressed()) {      // 取消
      rgbOff();
      drawPage(T_CANCEL, 0, nullptr, 0);
      delay(600);
      return;
    }

    Sample s;
    readAcc(s.x, s.y, s.z);

    if (!triggered) {
      pushRing(s);
      float dx = (s.x - g_bx) * ACC_TO_G;
      float dy = (s.y - g_by) * ACC_TO_G;
      float dz = (s.z - g_bz) * ACC_TO_G;
      float dev = sqrtf(dx * dx + dy * dy + dz * dz);
      over = (dev > TRIG_G) ? over + 1 : 0;

      if (over >= TRIG_HOLD) {
        triggered = true;
        trigIdx = ringCount - 1;
        copyRingToBurst();
        n = ringCount;
        setRgb(C_RED);
        // 注意：这里不要在采样循环里重绘屏幕。
        // 一次全屏刷新约几十毫秒，会在触发瞬间丢掉十几个样本。
        // 记录过程中的反馈交给 RGB 红灯，屏幕等记录结束再刷新。
      } else if (millis() - tStart > WAIT_MS) {
        rgbOff();
        drawPage(T_TIMEOUT, 0, nullptr, 0);
        delay(800);
        return;
      }
    } else if (n < BUF_N) {
      burst[n++] = s;
    }

    if (triggered && n >= BUF_N) break;
    waitNextSample();
  }

  float pga, fHz, durMs; char axis;
  analyse(burst, n, trigIdx, pga, axis, fHz, durMs);

  bool saved = saveToTfCard(burst, n, trigIdx, pga, fHz, durMs);
  drawResult(pga, axis, fHz, durMs, saved);
  if (pga >= ALARM_G) setRgb(C_RED); else setRgb(C_GREEN);

  if (!saved) {
    dumpToSerial(burst, n, trigIdx, pga, fHz, durMs);   // 卡片不可写时走串口
  } else {
    Serial.printf("# saved %s pga=%.4f f=%.2f dur=%.1f\n", g_filePath, pga, fHz, durMs);
  }

  waitButtonB();
  rgbOff();
}

/* ================= 待机监测 ================= */
static void runMonitor() {
  static Sample win[240];
  int wn = 0;
  float pga = 0;
  uint32_t tUi = 0;

  calibrateBaseline();
  drawPage(T_MONITOR, 0, nullptr, 0);

  g_periodUs = 1000000UL / FS_HZ;
  g_nextUs = micros();

  while (true) {
    if (k10.buttonA->isPressed()) { delay(250); return; }

    Sample s;
    readAcc(s.x, s.y, s.z);

    if (wn < 240) {
      win[wn++] = s;
    } else {
      memmove(win, win + 1, sizeof(Sample) * 239);
      win[239] = s;
    }

    if (millis() - tUi > 60) {
      tUi = millis();
      float mx = 0;
      /* 只取最近 0.3 s（60 个样本）做“实时值”。
       * 之前取的是整个 240 样本窗口（1.2 s）的最大值，敲一下桌子数字会挂 1 秒多，
       * 看起来像在“累加”。波形仍然显示 1.2 s，两条时间尺度分开。 */
      int from = (wn > 60) ? (wn - 60) : 0;
      for (int i = from; i < wn; i++) {
        float ax = fabsf((win[i].x - g_bx) * ACC_TO_G);
        float ay = fabsf((win[i].y - g_by) * ACC_TO_G);
        float az = fabsf((win[i].z - g_bz) * ACC_TO_G);
        if (ax > mx) mx = ax;
        if (ay > mx) mx = ay;
        if (az > mx) mx = az;
      }
      pga = mx;
      uint32_t c = (pga < 0.03f) ? 0 : (pga < ALARM_G ? C_AMBER : C_RED);
      setRgb(c);

      drawWave(win, wn);       // 局部刷新，避免闪烁
      drawPga(pga);
      drawRaw(&win[wn - 1]);
      k10.canvas->updateCanvas();
    }
    waitNextSample();
  }
}

/* ================= 入口 ================= */
void setup() {
  Serial.begin(115200);
  k10.begin();
  k10.initScreen(SCREEN_DIR);
  k10.creatCanvas();
  k10.setScreenBackground(C_BG);
  k10.initSDFile();          // 挂载 TF 卡；没有卡也不影响串口输出
  k10.rgb->brightness(6);

  drawPage(T_BOOT, 0, nullptr, 0);
  delay(800);
}

void loop() {
  runMonitor();
  runRecord();
}
