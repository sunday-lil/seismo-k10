/**
 * ==================================================================
 *  教室混响 T60 · UNIHIKER K10 现场测量
 * ------------------------------------------------------------------
 *  做法：
 *    1) 按 A 键开始，屏幕提示“拍手”
 *    2) 采集 2.5 s 麦克风数据，按 10 ms 一帧算 RMS
 *    3) 反向积分得到能量衰减曲线（Schroeder）
 *    4) 在 −5 ~ −25 dB 区间线性拟合，外推到 −60 dB 得 T60
 *    5) 屏幕显示 T60，CSV 写 TF 卡
 *
 *  数据：S:/rt60_<序号>.csv
 *        frame,ms,rms_db,edc_db
 *
 *  注意：没有声级计就用“相对值”，本实验只关心衰减斜率，
 *        不依赖绝对声压校准。
 * ==================================================================
 */
#include "unihiker_k10.h"
#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

UNIHIKER_K10 k10;

#define CAP_MS      2500        /* 采集时长 */
#define FRAME_MS    10          /* 每帧 10 ms */
#define MAX_FRAMES  (CAP_MS / FRAME_MS)

static float g_rms[MAX_FRAMES];
static float g_edc[MAX_FRAMES];
static int   g_frames = 0;
static float g_fs = 16000;      /* 实测后会被覆盖 */
static float g_t60 = 0;
static uint32_t g_seq = 0;

/* ---------- 启动时估采样率 ---------- */
static void estimateFs() {
  uint32_t t0 = micros();
  uint32_t n = 0;
  while (micros() - t0 < 200000UL) {   /* 采 0.2 s */
    k10.getMicrophoneData();
    n++;
  }
  float fs = n / 0.2f;
  if (fs > 4000 && fs < 60000) g_fs = fs;
}

/* ---------- 采集 ---------- */
static void capture() {
  g_frames = 0;
  for (int f = 0; f < MAX_FRAMES; f++) {
    uint32_t t0 = micros();
    double acc = 0;
    uint32_t n = 0;
    while (micros() - t0 < (uint32_t)FRAME_MS * 1000UL) {
      int v = k10.getMicrophoneData();
      acc += (double)v * v;
      n++;
      if (n > 200000) break;
    }
    g_rms[f] = (n > 0) ? sqrtf((float)(acc / n)) : 0;
    g_frames++;
  }
}

/* ---------- Schroeder 反向积分 ---------- */
static void computeEdc() {
  double sum = 0;
  for (int i = 0; i < g_frames; i++) sum += (double)g_rms[i] * g_rms[i];
  if (sum <= 0) { for (int i = 0; i < g_frames; i++) g_edc[i] = -99; return; }
  double acc = 0;
  for (int i = g_frames - 1; i >= 0; i--) {
    acc += (double)g_rms[i] * g_rms[i];
    g_edc[i] = 10.0f * log10f((float)(acc / sum));
  }
}

/* ---------- 线性拟合求 T60 ---------- */
static float fitT60() {
  /* 找 −5 dB 与 −25 dB 的位置 */
  int i5 = -1, i25 = -1;
  for (int i = 0; i < g_frames; i++) {
    if (i5 < 0 && g_edc[i] <= -5.0f) i5 = i;
    if (i25 < 0 && g_edc[i] <= -25.0f) { i25 = i; break; }
  }
  if (i5 < 0 || i25 <= i5 + 3) return 0;

  double sx = 0, sy = 0, sxx = 0, sxy = 0;
  int n = 0;
  for (int i = i5; i <= i25; i++) {
    double x = i * FRAME_MS / 1000.0;      /* 秒 */
    double y = g_edc[i];
    sx += x; sy += y; sxx += x * x; sxy += x * y; n++;
  }
  double den = n * sxx - sx * sx;
  if (fabs(den) < 1e-9) return 0;
  double slope = (n * sxy - sx * sy) / den;
  if (slope >= 0) return 0;
  return (float)(-60.0 / slope);
}

/* ---------- 存盘 ---------- */
static void saveCsv() {
  char path[48];
  snprintf(path, sizeof(path), "S:/rt60_%02lu.csv", (unsigned long)(++g_seq % 100));
  FILE *fp = fopen(path, "w");
  if (!fp) { Serial.println("# 无 TF 卡，改为串口输出"); return; }
  fprintf(fp, "# fs=%.0f frame_ms=%d t60=%.2f\n", (double)g_fs, FRAME_MS, (double)g_t60);
  fprintf(fp, "frame,ms,rms_db,edc_db\n");
  for (int i = 0; i < g_frames; i++) {
    float db = 20.0f * log10f(g_rms[i] > 1e-6f ? g_rms[i] : 1e-6f);
    fprintf(fp, "%d,%d,%.2f,%.2f\n", i, i * FRAME_MS, (double)db, (double)g_edc[i]);
  }
  fclose(fp);
}

/* ---------- 界面 ---------- */
static void show(const char *l1, const char *l2, const char *l3) {
  k10.setScreenBackground(0x0B1220);
  k10.canvas->canvasText("混响测量", 1, 0xE5E7EB);
  k10.canvas->canvasText(l1, 3, 0x38BDF8);
  k10.canvas->canvasText(l2, 5, 0xFDE68A);
  k10.canvas->canvasText(l3, 7, 0x7C8AA0);
  k10.canvas->updateCanvas();
}

void setup() {
  Serial.begin(115200);
  k10.begin();
  k10.initScreen(2);
  k10.creatCanvas();
  k10.initSDFile();
  k10.rgb->brightness(4);
  estimateFs();
  Serial.printf("# fs≈%.0f Hz\n", (double)g_fs);
  show("按 A 开始", "拍一次手", "静音 2.5 s");
}

void loop() {
  if (!k10.buttonA->isPressed()) { delay(20); return; }
  delay(250);

  show("3…2…1", "准备拍手", "");
  delay(1200);
  show("采集中", "现在拍！", "");
  k10.rgb->write(0, 255, 0, 0);
  k10.rgb->write(1, 255, 0, 0);
  k10.rgb->write(2, 255, 0, 0);

  capture();
  computeEdc();
  g_t60 = fitT60();
  saveCsv();

  k10.rgb->write(0, 0, 0, 0);
  k10.rgb->write(1, 0, 0, 0);
  k10.rgb->write(2, 0, 0, 0);

  char a[32], b[32];
  snprintf(a, sizeof(a), "T60 %.2f s", (double)g_t60);
  snprintf(b, sizeof(b), "%d 帧 · %.0f Hz", g_frames, (double)g_fs);
  show(g_t60 > 0 ? a : "拟合失败", b, "A:再测");

  Serial.printf("# T60=%.2f s  frames=%d  fs=%.0f\n", (double)g_t60, g_frames, (double)g_fs);
  for (int i = 0; i < g_frames; i += 5)
    Serial.printf("%d,%d,%.2f\n", i, i * FRAME_MS, (double)g_edc[i]);
}
