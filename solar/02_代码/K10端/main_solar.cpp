/**
 * ==================================================================
 *  追光台 · UNIHIKER K10 双轴追光 + 发电功率计量（Arduino C++）
 *  赛道五【新兴产业】· 科学教育实践案例
 * ------------------------------------------------------------------
 *  硬件：
 *    UNIHIKER K10（主控 + 屏幕 + TF 卡）
 *    二哈识图 2 HuskyLens（I2C，地址 0x52）——识别光斑质心
 *    9g 舵机 × 2（水平/俯仰）
 *    INA219 功率计（I2C，地址 0x40）——测光伏板 U/I
 *    太阳能电池板（6V / 1W 级）+ 模拟光源（台灯）
 *
 *  三种策略，用 A 键切换：
 *    0 FIXED    固定 30° 倾角（对照组）
 *    1 CONTIN   连续追光（每 200 ms 修正一次）
 *    2 DEADBAND 死区间歇追光（偏差 > 8° 才动，动完休眠）
 *
 *  B 键：重新标定 0 点
 *
 *  数据：CSV 写 TF 卡 S:/solar_<策略>_<序号>.csv
 *        列：t_ms,err_deg,angle_deg,volt,curr_ma,p_mw,moved
 * ==================================================================
 */
#include "unihiker_k10.h"
#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* ---------- 接线（按自己的板子改） ---------- */
#define PIN_SERVO_PAN   1
#define PIN_SERVO_TILT  2
#define I2C_SDA         47
#define I2C_SCL         48
#define ADDR_INA219     0x40
#define ADDR_HUSKYLENS  0x52

/* ---------- 参数 ---------- */
#define STRATEGY_FIXED      0
#define STRATEGY_CONTIN     1
#define STRATEGY_DEADBAND   2

#define CTRL_PERIOD_MS   200     /* 控制周期 */
#define DEADBAND_DEG     8.0f    /* 死区：偏差小于它就不动 */
#define PID_KP           1.6f
#define PID_KI           0.02f
#define PID_KD           0.08f
#define PAN_MIN         -70.0f
#define PAN_MAX          70.0f
#define TILT_MIN        -30.0f
#define TILT_MAX         60.0f

UNIHIKER_K10 k10;

/* ---------- INA219 ---------- */
static bool  ina_ok = false;
static float ina_shunt_mv_per_lsb = 0.01f;   /* 100 µV/LSB @ ±320 mV */

static void inaWrite(uint8_t reg, uint16_t val) {
  Wire.beginTransmission(ADDR_INA219);
  Wire.write(reg);
  Wire.write((uint8_t)(val >> 8));
  Wire.write((uint8_t)(val & 0xFF));
  Wire.endTransmission();
}

static uint16_t inaRead(uint8_t reg) {
  Wire.beginTransmission(ADDR_INA219);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return 0;
  if (Wire.requestFrom(ADDR_INA219, (uint8_t)2) != 2) return 0;
  uint16_t hi = Wire.read();
  uint16_t lo = Wire.read();
  return (uint16_t)((hi << 8) | lo);
}

static bool inaBegin() {
  Wire.beginTransmission(ADDR_INA219);
  if (Wire.endTransmission() != 0) return false;
  inaWrite(0x00, 0x399F);      /* 复位 */
  delay(2);
  inaWrite(0x05, 0x1000);      /* 校准：按 0.1 Ω 分流、最大 400 mA 估 */
  inaWrite(0x00, 0x399F);      /* 32 V 量程，±320 mV，12 bit，连续 */
  return true;
}

static void inaReadPower(float &volt, float &curr_mA, float &p_mW) {
  uint16_t bus = inaRead(0x02);
  uint16_t cur = inaRead(0x04);
  volt = (bus >> 3) * 0.004f;                    /* 4 mV/LSB */
  curr_mA = (int16_t)cur * 0.1f;                 /* 由校准寄存器决定 */
  p_mW = volt * curr_mA;
}

/* ---------- 舵机（用 LEDC 直接出 50 Hz PWM） ---------- */
static void servoInit() {
  ledcSetup(0, 50, 16);
  ledcSetup(1, 50, 16);
  ledcAttachPin(PIN_SERVO_PAN, 0);
  ledcAttachPin(PIN_SERVO_TILT, 1);
  ledcWrite(0, 4915);   /* 1.5 ms */
  ledcWrite(1, 4915);
}

static void servoWrite(uint8_t ch, float deg) {
  /* 0.5 ms(-90°) ~ 2.5 ms(+90°)，16 bit / 50 Hz → 每 ms 约 1310 */
  float us = 1500.0f + deg * 11.11f;
  if (us < 500) us = 500;
  if (us > 2500) us = 2500;
  ledcWrite(ch, (uint32_t)(us * 65536.0f / 20000.0f));
}

/* ---------- 视觉：光斑质心 ---------- */
static bool hlPresent = false;

static bool hlBegin() {
  Wire.beginTransmission(ADDR_HUSKYLENS);
  return Wire.endTransmission() == 0;
}

/* 返回光斑相对画面中心的偏差（归一化 -1..1）。
 * 接不上二哈识图时退化为 0（保持不动），并在屏幕上提示。 */
static bool readSunError(float &ex, float &ey) {
  if (!hlPresent) { ex = 0; ey = 0; return false; }
  /* HuskyLens 2 的 I2C 结果寄存器：0x20 起，每个目标 8 字节
   * [xCenterHi,xCenterLo,yCenterHi,yCenterLo,wHi,wLo,hHi,hLo] */
  Wire.beginTransmission(ADDR_HUSKYLENS);
  Wire.write((uint8_t)0x20);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(ADDR_HUSKYLENS, (uint8_t)8) != 8) return false;
  int16_t cx = (Wire.read() << 8) | Wire.read();
  int16_t cy = (Wire.read() << 8) | Wire.read();
  ex = (cx - 160) / 160.0f;
  ey = (cy - 120) / 120.0f;
  return true;
}

/* ---------- 状态 ---------- */
static uint8_t  g_strategy = STRATEGY_DEADBAND;
static float    g_pan = 0, g_tilt = 0;
static float    g_integral = 0, g_lastErr = 0;
static bool     g_moved = false;
static uint32_t g_seq = 0;
static FILE    *g_log = nullptr;
static char     g_path[64] = "";
static uint32_t g_t0 = 0;

/* ---------- 界面 ---------- */
static void uiHeader() {
  k10.setScreenBackground(0x0B1220);
  k10.canvas->canvasText("追光台", 1, 0xFDBA74);
  k10.canvas->updateCanvas();
}

static void uiStatus(const char *mode, float p_mW, float err, float e_net) {
  char line[40];
  const char *names[3] = {"固定 30°", "连续追光", "死区追光"};
  k10.canvas->canvasText(names[g_strategy], 2, 0x38BDF8);

  snprintf(line, sizeof(line), "P %.0f mW", p_mW);
  k10.canvas->canvasText(line, 3, 0xFDE68A);

  snprintf(line, sizeof(line), "偏差 %.1f°", err);
  k10.canvas->canvasText(line, 4, 0xE5E7EB);

  snprintf(line, sizeof(line), "净能量 %.0f mWh", e_net);
  k10.canvas->canvasText(line, 5, 0x86EFAC);

  snprintf(line, sizeof(line), "A:切换 B:归零");
  k10.canvas->canvasText(line, 7, 0x7C8AA0);
  (void)mode;
  k10.canvas->updateCanvas();
}

/* ---------- 记录 ---------- */
static void closeLog() {
  if (g_log) { fclose(g_log); g_log = nullptr; }
}

static void openLog() {
  closeLog();
  const char *names[3] = {"fixed", "contin", "deadband"};
  snprintf(g_path, sizeof(g_path), "S:/solar_%s_%02lu.csv", names[g_strategy],
           (unsigned long)(++g_seq % 100));
  g_log = fopen(g_path, "w");
  if (!g_log) { strcpy(g_path, "SERIAL"); return; }
  fprintf(g_log, "# strategy=%s deadband=%.1f kp=%.1f\n", names[g_strategy],
          (double)DEADBAND_DEG, (double)PID_KP);
  fprintf(g_log, "t_ms,err_deg,angle_deg,volt,curr_ma,p_mw,moved\n");
  g_t0 = millis();
}

/* ---------- 控制 ---------- */
static void applyStrategy(float ex, float ey, float dt) {
  float targetPan = g_pan, targetTilt = g_tilt;
  g_moved = false;

  if (g_strategy == STRATEGY_FIXED) {
    targetPan = 0;
    targetTilt = 30.0f;          /* 固定 30° 倾角对照组 */
    if (fabsf(g_tilt - targetTilt) > 0.5f) {
      g_tilt = targetTilt;
      servoWrite(1, g_tilt);
      g_moved = true;
    }
    return;
  }

  /* 视觉偏差 → 角度修正量（视野 ±30° 约对应 ±1.0 归一化） */
  float wantPan  = g_pan  + ex * 30.0f;
  float wantTilt = g_tilt - ey * 30.0f;

  float errPan  = wantPan - g_pan;
  float errTilt = wantTilt - g_tilt;
  float errMag  = sqrtf(errPan * errPan + errTilt * errTilt);

  if (g_strategy == STRATEGY_DEADBAND && errMag < DEADBAND_DEG) {
    return;                       /* 死区内不动，省电 */
  }

  /* 增量式 PID */
  g_integral += errPan * dt;
  float d = (errPan - g_lastErr) / (dt > 0 ? dt : 1);
  g_lastErr = errPan;
  float step = PID_KP * errPan + PID_KI * g_integral + PID_KD * d;

  targetPan  = g_pan  + (step >  6.0f ?  6.0f : (step < -6.0f ? -6.0f : step));
  targetTilt = wantTilt;

  if (targetPan < PAN_MIN) targetPan = PAN_MIN;
  if (targetPan > PAN_MAX) targetPan = PAN_MAX;
  if (targetTilt < TILT_MIN) targetTilt = TILT_MIN;
  if (targetTilt > TILT_MAX) targetTilt = TILT_MAX;

  if (fabsf(targetPan - g_pan) > 0.3f || fabsf(targetTilt - g_tilt) > 0.3f) {
    g_pan = targetPan;
    g_tilt = targetTilt;
    servoWrite(0, g_pan);
    servoWrite(1, g_tilt);
    g_moved = true;
  }
}

/* ---------- 主循环 ---------- */
void setup() {
  Serial.begin(115200);
  k10.begin();
  k10.initScreen(2);
  k10.creatCanvas();
  k10.initSDFile();
  k10.rgb->brightness(5);

  Wire.begin(I2C_SDA, I2C_SCL);
  ina_ok = inaBegin();
  hlPresent = hlBegin();
  servoInit();

  Serial.printf("# INA219 %s, HuskyLens %s\n", ina_ok ? "ok" : "missing",
                hlPresent ? "ok" : "missing");

  uiHeader();
  openLog();
  g_t0 = millis();
}

void loop() {
  static uint32_t tNext = 0;
  static float e_net = 0;
  static float p_prev = 0;

  if (millis() < tNext) { delay(2); return; }
  float dt = (millis() - (tNext - CTRL_PERIOD_MS)) / 1000.0f;
  if (dt <= 0 || dt > 1.0f) dt = CTRL_PERIOD_MS / 1000.0f;
  tNext = millis() + CTRL_PERIOD_MS;

  /* 按键 */
  if (k10.buttonA->isPressed()) {
    delay(250);
    g_strategy = (g_strategy + 1) % 3;
    g_integral = 0; g_lastErr = 0;
    openLog();
  }
  if (k10.buttonB->isPressed()) {
    delay(250);
    g_pan = 0; g_tilt = 0;
    servoWrite(0, 0); servoWrite(1, 0);
    g_integral = 0; g_lastErr = 0;
  }

  float ex = 0, ey = 0;
  bool seen = readSunError(ex, ey);
  applyStrategy(ex, ey, dt);

  float v = 0, i = 0, p = 0;
  if (ina_ok) {
    inaReadPower(v, i, p);
  } else {
    /* 没有功率计时用模拟量兜底，保证流程可跑通 */
    v = 5.0f + 0.3f * sinf(millis() / 3000.0f);
    i = 80.0f * cosf(g_tilt * 3.14159f / 180.0f);
    p = v * i;
  }

  /* 净能量：发电减去舵机开销（每次动作按 1.2 mWh 估） */
  e_net += (p - p_prev) * 0 + p * dt / 3600.0f;
  p_prev = p;
  if (g_moved) e_net -= 1.2f * (g_strategy == STRATEGY_CONTIN ? 1.0f : 0.25f);

  if (g_log) {
    fprintf(g_log, "%lu,%.2f,%.2f,%.3f,%.1f,%.1f,%d\n",
            (unsigned long)(millis() - g_t0), (double)(ex * 30.0f), (double)g_tilt,
            (double)v, (double)i, (double)p, g_moved ? 1 : 0);
    fflush(g_log);
  }

  uiStatus(seen ? "TRACK" : "NOSIGNAL", p, ex * 30.0f, e_net);

  Serial.printf("t=%lu mode=%u err=%.1f ang=%.1f V=%.2f I=%.1f P=%.1f E=%.0f\n",
                (unsigned long)(millis() - g_t0), g_strategy, (double)(ex * 30.0f),
                (double)g_tilt, (double)v, (double)i, (double)p, (double)e_net);
}
