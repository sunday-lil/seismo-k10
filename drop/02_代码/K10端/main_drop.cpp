/**
 * =====================================================================
 *  闪传节点 —— 跨系统浏览器文件互传（行空板 K10）
 *
 *  一块 K10 开热点，Windows / macOS / 安卓 / iOS 用浏览器打开同一个地址，
 *  就能互相传文件，不需要装任何 App，也不需要路由器。
 *
 *  接口：
 *    GET  /                 网页（拖拽上传 + 文件列表）
 *    GET  /list             文件列表 JSON
 *    GET  /dl?f=xxx         下载
 *    POST /up               multipart 上传（字段名 file）
 *    GET  /rm?f=xxx         删除
 *
 *  存储：TF 卡根目录（S:/）
 * =====================================================================
 */
#include "unihiker_k10.h"
#include <WiFi.h>
#include <WebServer.h>
#include <dirent.h>
#include <sys/stat.h>

UNIHIKER_K10 k10;
WebServer server(80);

static const char *AP_SSID = "K10-Drop";
static const char *AP_PASS = "12345678";     /* 空字符串 = 开放网络 */
static const char *ROOT = "S:/";

static FILE *uploadFile = nullptr;

/* ---------------- 屏幕 ---------------- */
static void drawStatus(const char *line1, const char *line2) {
  k10.setScreenBackground(0x05070F);
  k10.canvas->canvasText("闪传节点", 1, 0x22D3EE);
  k10.canvas->canvasText(line1, 3, 0xE6EDF7);
  k10.canvas->canvasText(line2, 4, 0x7C8AA0);
  k10.canvas->canvasText("浏览器打开", 6, 0x7C8AA0);
  k10.canvas->canvasText("无需安装", 7, 0x7C8AA0);
  k10.canvas->updateCanvas();
}

/* ---------------- 工具 ---------------- */
static String safeName(const String &raw) {
  String s = raw;
  int slash = s.lastIndexOf('/');
  if (slash >= 0) s = s.substring(slash + 1);
  int bslash = s.lastIndexOf('\\');
  if (bslash >= 0) s = s.substring(bslash + 1);
  String out;
  for (int i = 0; i < (int)s.length() && out.length() < 60; i++) {
    char c = s[i];
    if ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
        c == '.' || c == '-' || c == '_') out += c;
    else if (c == ' ') out += '_';
  }
  if (out.length() == 0) out = "file";
  return out;
}

static void urlEncodeJson(String &out, const String &s) {
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else out += c;
  }
}

/* ---------------- 页面 ---------------- */
static const char PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>闪传节点</title>
<style>
:root{--bg:#0b1220;--card:#111c2e;--line:#22303f;--fg:#e6edf7;--dim:#7c8aa0;--acc:#22d3ee}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:20px}
h1{font-size:20px;margin:0 0 4px;color:var(--acc)}
.sub{color:var(--dim);font-size:13px;margin-bottom:16px}
#drop{border:2px dashed var(--line);border-radius:14px;padding:28px;text-align:center;color:var(--dim);
      transition:.15s;cursor:pointer}
#drop.on{border-color:var(--acc);color:var(--acc);background:#0e2230}
#bar{height:6px;background:#16233a;border-radius:3px;margin-top:12px;overflow:hidden;display:none}
#bar>i{display:block;height:100%;width:0;background:var(--acc);transition:width .1s}
ul{list-style:none;padding:0;margin:18px 0 0}
li{display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--card);border:1px solid var(--line);
   border-radius:10px;margin-bottom:8px}
li .n{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
li .s{color:var(--dim);font-size:12px}
a{color:var(--acc);text-decoration:none}
button{background:none;border:1px solid var(--line);color:var(--dim);border-radius:8px;padding:6px 10px;cursor:pointer}
.foot{margin-top:18px;color:var(--dim);font-size:12px}
</style></head><body><div class="wrap">
<h1>闪传节点</h1>
<div class="sub">拖文件到这里，或用「选择文件」。同一个 WiFi 下的手机、平板、电脑都能下载。</div>
<div id="drop">松手即传 · 点击选择文件<input id="f" type="file" multiple hidden></div>
<div id="bar"><i></i></div>
<ul id="list"></ul>
<div class="foot" id="foot"></div>
</div>
<script>
const drop=document.getElementById('drop'),fi=document.getElementById('f'),
      bar=document.getElementById('bar'),bari=bar.querySelector('i'),
      list=document.getElementById('list'),foot=document.getElementById('foot');
drop.onclick=()=>fi.click();
fi.onchange=()=>{upload([...fi.files]);fi.value='';};
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('on');}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('on');}));
drop.addEventListener('drop',ev=>{upload([...ev.dataTransfer.files]);});
function fmt(n){return n<1024?n+' B':n<1048576?(n/1024).toFixed(1)+' KB':(n/1048576).toFixed(1)+' MB';}
async function upload(files){
  if(!files.length)return;
  for(const f of files){
    bar.style.display='block';bari.style.width='0';
    await new Promise(res=>{
      const fd=new FormData();fd.append('file',f,f.name);
      const xhr=new XMLHttpRequest();
      xhr.open('POST','/up');
      xhr.upload.onprogress=e=>{if(e.lengthComputable)bari.style.width=(e.loaded/e.total*100)+'%';};
      xhr.onload=()=>{res();};
      xhr.onerror=()=>{res();};
      xhr.send(fd);
    });
  }
  bar.style.display='none';
  refresh();
}
async function refresh(){
  const r=await fetch('/list');const j=await r.json();
  list.innerHTML='';
  let total=0;
  for(const f of j.files){
    total+=f.size;
    const li=document.createElement('li');
    li.innerHTML='<span class="n">'+f.name.replace(/[<>&]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))+
      '</span><span class="s">'+fmt(f.size)+'</span>'+
      '<a href="/dl?f='+encodeURIComponent(f.name)+'">下载</a>'+
      '<button data-n="'+encodeURIComponent(f.name)+'">删</button>';
    li.querySelector('button').onclick=async()=>{
      if(confirm('删除 '+f.name+' ?')){await fetch('/rm?f='+encodeURIComponent(f.name));refresh();}
    };
    list.appendChild(li);
  }
  foot.textContent='共 '+j.files.length+' 个文件 · '+fmt(total);
}
refresh();
</script></body></html>)HTML";

/* ---------------- 路由 ---------------- */
static void handleRoot() {
  server.send_P(200, "text/html; charset=utf-8", PAGE);
}

static void handleList() {
  String out = "{\"files\":[";
  bool first = true;
  unsigned long long total = 0;
  DIR *d = opendir(ROOT);
  if (d) {
    struct dirent *e;
    while ((e = readdir(d)) != nullptr) {
      if (e->d_name[0] == '.') continue;
      String path = String(ROOT) + e->d_name;
      struct stat st;
      if (stat(path.c_str(), &st) != 0 || !S_ISREG(st.st_mode)) continue;
      total += st.st_size;
      if (!first) out += ",";
      first = false;
      out += "{\"name\":\"";
      urlEncodeJson(out, e->d_name);
      out += "\",\"size\":";
      out += String((unsigned long)st.st_size);
      out += "}";
    }
    closedir(d);
  }
  out += "],\"free\":0}";
  server.send(200, "application/json", out);
}

static void handleDownload() {
  if (!server.hasArg("f")) { server.send(400, "text/plain", "missing f"); return; }
  String name = safeName(server.arg("f"));
  String path = String(ROOT) + name;
  FILE *f = fopen(path.c_str(), "rb");
  if (!f) { server.send(404, "text/plain", "not found"); return; }
  server.sendHeader("Content-Disposition", "attachment; filename=\"" + name + "\"");
  server.setContentLength((size_t)ftell(f));
  server.send(200, "application/octet-stream", "");
  uint8_t buf[1024];
  size_t n;
  while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
    server.sendContent((const char *)buf, n);
  }
  fclose(f);
}

static void handleDelete() {
  if (!server.hasArg("f")) { server.send(400, "text/plain", "missing f"); return; }
  String name = safeName(server.arg("f"));
  String path = String(ROOT) + name;
  bool ok = (remove(path.c_str()) == 0);
  server.send(200, "application/json", ok ? "{\"ok\":1}" : "{\"ok\":0}");
}

static void handleUploadDone() {
  server.send(200, "application/json", "{\"ok\":1}");
}

static void handleUploadChunk() {
  HTTPUpload &u = server.upload();
  if (u.status == UPLOAD_FILE_START) {
    String name = safeName(u.filename);
    if (name.length() == 0) name = "file";
    String path = String(ROOT) + name;
    uploadFile = fopen(path.c_str(), "wb");
    Serial.printf("# upload start %s\n", name.c_str());
  } else if (u.status == UPLOAD_FILE_WRITE) {
    if (uploadFile) fwrite(u.buf, 1, u.currentSize, uploadFile);
  } else if (u.status == UPLOAD_FILE_END) {
    if (uploadFile) {
      fclose(uploadFile);
      uploadFile = nullptr;
      Serial.printf("# upload end %u bytes\n", (unsigned)u.totalSize);
    }
  }
}

/* ---------------- 入口 ---------------- */
void setup() {
  Serial.begin(115200);
  delay(600);
  k10.begin();
  k10.initScreen(2);
  k10.creatCanvas();

  if (!k10.initSDFile()) {
    Serial.println("# TF 卡挂载失败");
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  IPAddress ip = WiFi.softAPIP();
  Serial.printf("# AP %s  http://%s/\n", AP_SSID, ip.toString().c_str());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/list", HTTP_GET, handleList);
  server.on("/dl", HTTP_GET, handleDownload);
  server.on("/rm", HTTP_GET, handleDelete);
  server.on("/up", HTTP_POST, handleUploadDone, handleUploadChunk);
  server.begin();

  drawStatus("WiFi: K10-Drop", ip.toString().c_str());
}

void loop() {
  server.handleClient();
  delay(2);
}
