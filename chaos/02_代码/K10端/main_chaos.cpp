/**
 * ==================================================================
 *  双摆混沌 · UNIHIKER K10 实时相图与李雅普诺夫指数
 * ------------------------------------------------------------------
 *  做什么：
 *    同一块板子上同时积分两个双摆，初值只差 1e-6 rad。
 *    实时画相图（θ₁–ω₁），屏幕右侧显示两条轨迹的距离 δ
 *    和由 δ 的指数增长估出的李雅普诺夫指数 λ。
 *
 *  按键：
 *    A = 重置（同一初值）
 *    B = 改变初值差（1e-6 → 1e-3 → 1e-1 循环）
 *
 *  数据：CSV 写 TF 卡 S:/chaos_<Δ>.csv
 *        t,th1a,w1a,th2a,w2a,th1b,w1b,th2b,w2b,sep
 *
 *  为什么在单片机上做：
 *    双摆没有解析解，只能数值积分。K10 用 RK4 以 200 Hz 实时积分，
 *    学生能亲眼看到“两条几乎相同的曲线”在几秒内分开——
 *    这比看视频有说服力。
 * ==================================================================
 */
#include "unihiker_k10.h"
#include <Arduino.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

UNIHIKER_K10 k10;

/* ---------- 物理参数（与分析端一致） ---------- */
#define G_ACC   9.80665f
#define L1      0.30f
#define L2      0.30f
#define M1      0.050f
#define M2      0.050f

/* ---------- 运行参数 ---------- */
#define RATE_HZ     200
#define PLOT_EVERY  3          /* 每 3 个样本画一段线，够顺滑也够快 */
#define WINDOW_S    20.0f      /* 一次实验时长 */
#define TH1_0       2.0944f    /* 120° */
#define TH2_0       1.5708f    /* 90°  */

/* ---------- 配色 ---------- */
#define C_BG     0x0B1220u
#define C_TEXT   0xE5E7EBu
#define C_DIM    0x7C8AA0u
#define C_A      0x1B998Bu
#define C_B      0xF59E0Bu
#define C_WARN   0xEF4444u

/* ---------- 状态 ---------- */
struct State { float th1, w1, th2, w2; };

static State sA, sB;
static float g_delta = 1e-6f;
static uint32_t g_step = 0;
static uint32_t g_nextUs = 0;
static uint32_t g_periodUs = 1000000UL / RATE_HZ;

static FILE *g_log = nullptr;
static char  g_path[48] = "";

/* λ 估计：对 ln δ 做滑动直线拟合 */
#define FIT_N 40
static float fitT[FIT_N], fitY[FIT_N];
static int   fitCount = 0, fitHead = 0;
static float g_lambda = 0;

/* 绘图 */
#define PX0 10
#define PX1 230
#define PY0 96
#define PY1 250
static int16_t lastAx = 0, lastAy = 0, lastBx = 0, lastBy = 0;
static bool  hasLast = false;

/* ---------------- 物理 ---------------- */
static void derivs(const State &s, float out[4]) {
  float d = s.th2 - s.th1;
  float den = 2 * M1 + M2 - M2 * cosf(2 * d);
  float a1 = (-G_ACC * (2 * M1 + M2) * sinf(s.th1)
              - M2 * G_ACC * sinf(s.th1 - 2 * s.th2)
              - 2 * sinf(d) * M2 * (s.w2 * s.w2 * L2 + s.w1 * s.w1 * L1 * cosf(d)))
             / (L1 * den);
  float a2 = (2 * sinf(d) * (s.w1 * s.w1 * L1 * (M1 + M2)
              + G_ACC * (M1 + M2) * cosf(s.th1)
              + s.w2 * s.w2 * L2 * M2 * cosf(d)))
             / (L2 * den);
  out[0] = s.w1; out[1] = a1; out[2] = s.w2; out[3] = a2;
}

static void rk4(State &s, float dt) {
  float k1[4], k2[4], k3[4], k4[4];
  State t;
  derivs(s, k1);
  t = {s.th1 + 0.5f * dt * k1[0], s.w1 + 0.5f * dt * k1[1],
       s.th2 + 0.5f * dt * k1[2], s.w2 + 0.5f * dt * k1[3]};
  derivs(t, k2);
  t = {s.th1 + 0.5f * dt * k2[0], s.w1 + 0.5f * dt * k2[1],
       s.th2 + 0.5f * dt * k2[2], s.w2 + 0.5f * dt * k2[3]};
  derivs(t, k3);
  t = {s.th1 + dt * k3[0], s.w1 + dt * k3[1],
       s.th2 + dt * k3[2], s.w2 + dt * k3[3]};
  derivs(t, k4);
  s.th1 += dt / 6.0f * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]);
  s.w1  += dt / 6.0f * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]);
  s.th2 += dt / 6.0f * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]);
  s.w2  += dt / 6.0f * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]);
}

static float separation(const State &a, const State &b) {
  float d1 = a.th1 - b.th1, d2 = a.w1 - b.w1, d3 = a.th2 - b.th2, d4 = a.w2 - b.w2;
  return sqrtf(d1 * d1 + d2 * d2 + d3 * d3 + d4 * d4);
}

/* ---------------- 界面 ---------------- */
static int mapX(float th) {
  float v = (th + 3.1416f) / (2 * 3.1416f);
  if (v < 0) v = 0;
  if (v > 1) v = 1;
  return PX0 + (int)(v * (PX1 - PX0));
}
static int mapY(float w) {
  float v = (w + 8.0f) / 16.0f;
  if (v < 0) v = 0;
  if (v > 1) v = 1;
  return PY1 - (int)(v * (PY1 - PY0));
}

static void drawFrame() {
  k10.setScreenBackground(C_BG);
  k10.canvas->canvasText("双摆混沌", 1, C_TEXT);
  k10.canvas->canvasRectangle(PX0, PY0, PX1 - PX0, PY1 - PY0, C_BG, 0x1E2A3Au, true);
  k10.canvas->canvasText("θ1", 12, C_DIM);
  k10.canvas->updateCanvas();
}

static void drawHud(float t, float sep) {
  char line[40];
  snprintf(line, sizeof(line), "λ %.2f /s", (double)g_lambda);
  k10.canvas->canvasText(line, 2, C_A);
  snprintf(line, sizeof(line), "δ %.1e", (double)sep);
  k10.canvas->canvasText(line, 3, sep > 0.1f ? C_WARN : C_TEXT);
  snprintf(line, sizeof(line), "t %.1f s", (double)t);
  k10.canvas->canvasText(line, 4, C_DIM);
  snprintf(line, sizeof(line), "Δ0 %.0e  A:重置 B:改Δ", (double)g_delta);
  k10.canvas->canvasText(line, 12, C_DIM);
}

/* ---------------- 拟合 ---------------- */
static void pushFit(float t, float sep) {
  float y = logf(sep > 1e-9f ? sep : 1e-9f);
  fitT[fitHead] = t; fitY[fitHead] = y;
  fitHead = (fitHead + 1) % FIT_N;
  if (fitCount < FIT_N) fitCount++;
  if (fitCount < 8) return;
  /* 最小二乘 */
  float sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (int i = 0; i < fitCount; i++) {
    sx += fitT[i]; sy += fitY[i];
    sxx += fitT[i] * fitT[i]; sxy += fitT[i] * fitY[i];
  }
  float den = fitCount * sxx - sx * sx;
  if (fabsf(den) > 1e-6f) g_lambda = (fitCount * sxy - sx * sy) / den;
}

/* ---------------- 记录 ---------------- */
static void closeLog() { if (g_log) { fclose(g_log); g_log = nullptr; } }

static void openLog() {
  closeLog();
  snprintf(g_path, sizeof(g_path), "S:/chaos_d%03d.csv", (int)(g_delta * 1e6f));
  g_log = fopen(g_path, "w");
  if (!g_log) { strcpy(g_path, "SERIAL"); return; }
  fprintf(g_log, "# double pendulum, delta0=%.1e, L=%.2f, M=%.3f\n", (double)g_delta, (double)L1, (double)M1);
  fprintf(g_log, "t,th1a,w1a,th2a,w2a,th1b,w1b,th2b,w2b,sep\n");
}

/* ---------------- 初始化 ---------------- */
static void resetRun() {
  sA = {TH1_0, 0, TH2_0, 0};
  sB = {TH1_0 + g_delta, 0, TH2_0, 0};
  g_step = 0; fitCount = 0; fitHead = 0; g_lambda = 0;
  hasLast = false;
  g_nextUs = micros();
  drawFrame();
  openLog();
}

void setup() {
  Serial.begin(115200);
  k10.begin();
  k10.initScreen(2);
  k10.creatCanvas();
  k10.initSDFile();
  k10.rgb->brightness(4);
  resetRun();
}

void loop() {
  if (k10.buttonA->isPressed()) { delay(250); resetRun(); return; }
  if (k10.buttonB->isPressed()) {
    delay(250);
    g_delta = (g_delta < 1e-5f) ? 1e-3f : (g_delta < 1e-2f ? 1e-1f : 1e-6f);
    resetRun();
    return;
  }

  float dt = 1.0f / RATE_HZ;
  rk4(sA, dt);
  rk4(sB, dt);
  g_step++;

  float t = g_step * dt;
  float sep = separation(sA, sB);

  if (g_step % PLOT_EVERY == 0) {
    int ax = mapX(sA.th1), ay = mapY(sA.w1);
    int bx = mapX(sB.th1), by = mapY(sB.w1);
    if (hasLast) {
      k10.canvas->canvasLine(lastAx, lastAy, ax, ay, C_A);
      k10.canvas->canvasLine(lastBx, lastBy, bx, by, C_B);
    }
    lastAx = ax; lastAy = ay; lastBx = bx; lastBy = by; hasLast = true;
    drawHud(t, sep);
    k10.canvas->updateCanvas();
  }

  if (g_step % (RATE_HZ / 20) == 0) pushFit(t, sep);   /* 每 50 ms 采一个点 */

  if (g_log && g_step % 5 == 0) {
    fprintf(g_log, "%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.3e\n",
            (double)t, (double)sA.th1, (double)sA.w1, (double)sA.th2, (double)sA.w2,
            (double)sB.th1, (double)sB.w1, (double)sB.th2, (double)sB.w2, (double)sep);
  }

  if (t > WINDOW_S) {
    if (g_log) { fclose(g_log); g_log = nullptr; }
    k10.canvas->canvasText("完成 B:重来", 10, C_A);
    k10.canvas->updateCanvas();
    while (!k10.buttonB->isPressed()) delay(20);
    delay(250);
    resetRun();
    return;
  }

  g_nextUs += g_periodUs;
  int32_t wait = (int32_t)(g_nextUs - micros());
  if (wait > 0) delayMicroseconds(wait); else g_nextUs = micros();
}
