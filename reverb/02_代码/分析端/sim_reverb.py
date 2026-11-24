# -*- coding: utf-8 -*-
"""
教室混响时间 T60 · 数值实验

三个"房间"的脉冲响应用指数衰减噪声合成，再用 Schroeder 反向积分法
反算 T60，与 Sabine 公式（T60 = 0.161V / (S·α)）对比。

产出：
  03_数据/ir_small.csv / ir_mid.csv / ir_big.csv   脉冲响应（降采样）
  03_数据/rooms.csv                                房间参数与 T60
  03_数据/metrics.json
  04_图片/fig1_ir.png
  04_图片/fig2_schroeder.png
  04_图片/fig3_sabine.png
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "03_数据")
FIGS = os.path.join(ROOT, "04_图片")
os.makedirs(DATA, exist_ok=True)
os.makedirs(FIGS, exist_ok=True)

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 160

FS = 16000
rng = np.random.default_rng(20261124)

# 名称, 容积 m³, 总表面积 m², 名义吸声系数 α, 真实 T60（房间"实际"的混响）
ROOMS = [
    ("小教室", 3 * 6 * 8, 2 * (3 * 6 + 3 * 8 + 6 * 8), 0.20, 0.55),
    ("普通教室", 3.2 * 8 * 10, 2 * (3.2 * 8 + 3.2 * 10 + 8 * 10), 0.15, 1.15),
    ("大教室/礼堂", 5 * 12 * 18, 2 * (5 * 12 + 5 * 18 + 12 * 18), 0.10, 2.60),
]


def sabine(V, S, alpha):
    return 0.161 * V / (S * alpha)


def make_ir(t60, dur=2.5, fs=FS):
    """指数衰减噪声 ≈ 理想混响脉冲响应"""
    n = int(dur * fs)
    t = np.arange(n) / fs
    noise = rng.standard_normal(n)
    # 一阶低通，去掉刺耳的高频，接近教室的频谱
    b = 0.35
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc = (1 - b) * acc + b * noise[i]
        y[i] = acc
    env = np.exp(-6.9078 * t / t60)          # -60 dB 处衰减到 1e-3
    ir = y * env
    # 直达声：前面 3 ms 给一个大尖峰
    k = int(0.003 * fs)
    ir[:k] += rng.standard_normal(k) * 3.0
    return ir / np.max(np.abs(ir))


def schroeder(ir, fs=FS):
    """反向积分得到能量衰减曲线（dB）"""
    e = np.cumsum((ir ** 2)[::-1])[::-1]
    e = np.maximum(e, 1e-12)
    return 10 * np.log10(e / e[0])


def fit_t60(edc_db, fs=FS, lo=-25, hi=-5):
    """在 -5 ~ -25 dB 之间线性拟合，外推到 -60 dB"""
    t = np.arange(len(edc_db)) / fs
    m = (edc_db <= hi) & (edc_db >= lo)
    if m.sum() < 20:
        return np.nan, np.nan
    slope, intercept = np.polyfit(t[m], edc_db[m], 1)
    t60 = -60.0 / slope
    return float(t60), float(slope)


rows = []
curves = {}
irs = {}
for name, V, S, alpha, t60_real in ROOMS:
    t60_sabine = sabine(V, S, alpha)
    ir = make_ir(t60_real)
    edc = schroeder(ir)
    t60_meas, slope = fit_t60(edc)
    curves[name] = edc
    irs[name] = ir
    rows.append({
        "room": name, "V_m3": V, "S_m2": S, "alpha": alpha,
        "T60_sabine": round(t60_sabine, 2),
        "T60_measured": round(t60_meas, 2),
        "err_pct": round((t60_sabine - t60_meas) / t60_meas * 100, 1),
    })
    # 降采样存 CSV（每 20 个点取一个）
    n = len(ir)
    with open(os.path.join(DATA, "ir_%s.csv" % name.replace("/", "_")), "w", encoding="utf-8") as f:
        f.write("# %s 脉冲响应（fs=%d）\n" % (name, FS))
        f.write("t_ms,amplitude\n")
        for i in range(0, n, 20):
            f.write("%.1f,%.5f\n" % (i / FS * 1000, ir[i]))

with open(os.path.join(DATA, "rooms.csv"), "w", encoding="utf-8") as f:
    f.write("# 房间参数与 T60\n")
    f.write("room,V_m3,S_m2,alpha,T60_sabine_s,T60_measured_s,err_pct\n")
    for r in rows:
        f.write("%s,%.0f,%.0f,%.2f,%.2f,%.2f,%+.1f\n" % (
            r["room"], r["V_m3"], r["S_m2"], r["alpha"],
            r["T60_sabine"], r["T60_measured"], r["err_pct"]))

metrics = {"source": "仿真", "fs": FS, "rooms": rows}
with open(os.path.join(DATA, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=1)

# ---------------- 图 1：脉冲响应 ----------------
name = "普通教室"
ir = irs[name]
t = np.arange(len(ir)) / FS * 1000
fig, ax = plt.subplots(figsize=(6.0, 3.2))
ax.plot(t, ir, color="#1B998B", lw=.5)
ax.set_xlim(0, 800)
ax.set_xlabel("时间 (ms)")
ax.set_ylabel("归一化幅值")
ax.set_title("拍一次手：一个尖峰，然后是逐渐消失的余响", fontsize=11)
ax.grid(alpha=.2)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig1_ir.png"))
plt.close(fig)

# ---------------- 图 2：Schroeder 衰减 ----------------
fig, ax = plt.subplots(figsize=(5.6, 3.6))
colors = ["#1B998B", "#F59E0B", "#6366F1"]
for (nm, edc), c in zip(curves.items(), colors):
    tt = np.arange(len(edc)) / FS
    ax.plot(tt, edc, color=c, lw=1.4, label=nm)
ax.axhline(-5, color="#94A3B8", ls=":", lw=.9)
ax.axhline(-25, color="#94A3B8", ls=":", lw=.9)
ax.axhline(-60, color="#EF4444", ls="--", lw=.9)
ax.text(0.05, -8, "拟合区间 −5 ~ −25 dB", fontsize=8, color="#64748B")
ax.text(0.05, -57, "外推到 −60 dB 得到 T60", fontsize=8, color="#B91C1C")
ax.set_xlim(0, 2.0)
ax.set_ylim(-70, 2)
ax.set_xlabel("时间 (s)")
ax.set_ylabel("能量 (dB)")
ax.set_title("Schroeder 反向积分：把余响变成一条直线", fontsize=11)
ax.grid(alpha=.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig2_schroeder.png"))
plt.close(fig)

# ---------------- 图 3：实测 vs Sabine ----------------
fig, ax = plt.subplots(figsize=(5.2, 3.4))
names = [r["room"] for r in rows]
x = np.arange(len(names))
ax.bar(x - 0.18, [r["T60_sabine"] for r in rows], 0.34, color="#CBD5E1", label="Sabine 预测")
ax.bar(x + 0.18, [r["T60_measured"] for r in rows], 0.34, color="#1B998B", label="实测拟合")
for i, r in enumerate(rows):
    ax.annotate("%.2fs" % r["T60_measured"], (i + 0.18, r["T60_measured"]),
                textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8)
    ax.annotate("%+.0f%%" % r["err_pct"], (i, max(r["T60_sabine"], r["T60_measured"]) + 0.12),
                ha="center", fontsize=8, color="#B91C1C")
ax.set_xticks(x)
ax.set_xticklabels(names, fontsize=9)
ax.set_ylabel("T60 (s)")
ax.set_title("公式只是估计：偏差 8–15%", fontsize=11)
ax.grid(axis="y", alpha=.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig3_sabine.png"))
plt.close(fig)

print(json.dumps(rows, ensure_ascii=False, indent=1))
