# -*- coding: utf-8 -*-
"""
双摆混沌 · 数值实验

产出：
  03_数据/divergence.csv     两条轨迹的分离随时间的增长
  03_数据/predict_horizon.csv 不同容差下的可预报时长
  03_数据/metrics.json       李雅普诺夫指数、拟合参数
  04_图片/fig1_divergence.png
  04_图片/fig2_phase.png
  04_图片/fig3_horizon.png

说明：本脚本产出**仿真数据**；K10 端用同一套方程与 RK4 实时积分，
导出 CSV 后可替换本脚本的输入重跑。
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

# ---------------- 模型 ----------------
G = 9.80665
L1 = L2 = 0.30          # m
M1 = M2 = 0.050         # kg


def derivs(s):
    """双摆状态 [th1, w1, th2, w2] → 导数（标准形式）"""
    th1, w1, th2, w2 = s
    d = th2 - th1
    den = 2 * M1 + M2 - M2 * np.cos(2 * d)
    a1 = (-G * (2 * M1 + M2) * np.sin(th1)
          - M2 * G * np.sin(th1 - 2 * th2)
          - 2 * np.sin(d) * M2 * (w2 ** 2 * L2 + w1 ** 2 * L1 * np.cos(d))) / (L1 * den)
    a2 = (2 * np.sin(d) * (w1 ** 2 * L1 * (M1 + M2)
                           + G * (M1 + M2) * np.cos(th1)
                           + w2 ** 2 * L2 * M2 * np.cos(d))) / (L2 * den)
    return np.array([w1, a1, w2, a2])


def rk4(s, dt):
    k1 = derivs(s)
    k2 = derivs(s + 0.5 * dt * k1)
    k3 = derivs(s + 0.5 * dt * k2)
    k4 = derivs(s + dt * k3)
    return s + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)


def simulate(s0, T=20.0, dt=2e-4, stride=50):
    n = int(T / dt)
    out = np.empty((n // stride + 1, 4))
    s = np.array(s0, dtype=float)
    k = 0
    for i in range(n + 1):
        if i % stride == 0:
            out[k] = s
            k += 1
        s = rk4(s, dt)
    return out[:k]


# ---------------- 实验一：分离增长 → λ ----------------
TH1, TH2 = np.deg2rad(120.0), np.deg2rad(90.0)
D0 = 1e-6
sA = np.array([TH1, 0.0, TH2, 0.0])
sB = sA + np.array([D0, 0.0, 0.0, 0.0])

trajA = simulate(sA, T=20.0)
trajB = simulate(sB, T=20.0)
t = np.arange(len(trajA)) * 50 * 2.0e-4

sep = np.linalg.norm(trajA - trajB, axis=1)
sep = np.maximum(sep, 1e-12)

# 只在“线性增长段”拟合：从 0.5 s 到分离达到 0.1 之前
mask = (t > 0.5) & (sep < 0.1)
if mask.sum() > 20:
    slope, intercept = np.polyfit(t[mask], np.log(sep[mask]), 1)
else:
    slope, intercept = np.nan, np.nan

# ---------------- 实验二：可预报时长 vs 容差 ----------------
tolerances = [0.001, 0.01, 0.05, 0.5]    # rad
horizons = []
for tol in tolerances:
    idx = np.argmax(sep > tol)
    horizons.append(t[idx] if idx > 0 else np.nan)

# ---------------- 实验三：λ 随能量变化 ----------------
amps = [30, 60, 90, 120, 150]
lams = []
for a in amps:
    s0 = np.array([np.deg2rad(a), 0.0, np.deg2rad(a * 0.75), 0.0])
    s1 = s0 + np.array([1e-6, 0, 0, 0])
    A = simulate(s0, T=12.0)
    B = simulate(s1, T=12.0)
    tt = np.arange(len(A)) * 0.01
    d = np.maximum(np.linalg.norm(A - B, axis=1), 1e-12)
    mk = (tt > 0.3) & (d < 0.1)
    lams.append(float(np.polyfit(tt[mk], np.log(d[mk]), 1)[0]) if mk.sum() > 10 else np.nan)

# ---------------- 落盘 ----------------
with open(os.path.join(DATA, "divergence.csv"), "w", encoding="utf-8") as f:
    f.write("# 双摆：两条初值相差 1e-6 rad 的轨迹分离\n")
    f.write("t_s,th1_A,th2_A,th1_B,th2_B,sep\n")
    for i in range(0, len(t), 5):
        f.write(f"{t[i]:.2f},{trajA[i,0]:.4f},{trajA[i,2]:.4f},"
                f"{trajB[i,0]:.4f},{trajB[i,2]:.4f},{sep[i]:.3e}\n")

with open(os.path.join(DATA, "predict_horizon.csv"), "w", encoding="utf-8") as f:
    f.write("# 容差(rad) 与可预报时长(s)\n")
    f.write("tolerance_rad,horizon_s\n")
    for tol, h in zip(tolerances, horizons):
        f.write(f"{tol},{h:.2f}\n")

metrics = {
    "source": "仿真",
    "params": {"L1": L1, "L2": L2, "M1": M1, "M2": M2, "g": G},
    "init": {"th1_deg": 120, "th2_deg": 90, "delta_rad": D0},
    "lambda_per_s": round(float(slope), 2),
    "lambda_fit_tmax": round(float(t[mask].max()), 2) if mask.any() else None,
    "horizons": {str(tol): (None if np.isnan(h) else round(float(h), 2))
                 for tol, h in zip(tolerances, horizons)},
    "lambda_vs_amp": {str(a): (None if np.isnan(l) else round(float(l), 2)) for a, l in zip(amps, lams)},
}
with open(os.path.join(DATA, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=1)

# ---------------- 图 1：分离增长 ----------------
fig, ax = plt.subplots(figsize=(6.0, 3.6))
ax.semilogy(t, sep, color="#1B998B", lw=1.6, label="两条轨迹的距离 δ(t)")
tt = np.linspace(t[mask].min(), t[mask].max(), 50)
ax.semilogy(tt, np.exp(intercept + slope * tt), "--", color="#F59E0B", lw=1.6,
            label=f"拟合 δ∝e^(λt)，λ={slope:.2f} /s")
ax.axhline(0.001, color="#94A3B8", ls=":", lw=1)
ax.text(12.5, 0.0013, "容差 0.001 rad", fontsize=8, color="#64748B")
ax.set_xlabel("时间 t (s)")
ax.set_ylabel("相空间距离 δ")
ax.set_title("初始差 1e-6 rad，几秒后完全分道扬镳", fontsize=11)
ax.grid(alpha=.25, which="both")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig1_divergence.png"))
plt.close(fig)

# ---------------- 图 2：相图 ----------------
def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi

fig, ax = plt.subplots(figsize=(5.4, 3.8))
n_show = int(12.0 / 0.01)
def brk(a):
    """跨过 ±π 时插入 NaN，避免连线横穿整幅图"""
    out = np.array(a, dtype=float)
    jump = np.abs(np.diff(out)) > np.pi
    out[1:][jump] = np.nan
    return out

ax.plot(brk(wrap(trajA[:n_show, 0])), trajA[:n_show, 1], color="#1B998B", lw=1.4, label="轨迹 A")
ax.plot(brk(wrap(trajB[:n_show, 0])), trajB[:n_show, 1], color="#F59E0B", lw=1.0,
        alpha=.85, ls="--", label="轨迹 B（初值差 1e-6 rad）")
ax.set_xlabel(r"$\theta_1$ (rad)")
ax.set_ylabel(r"$\omega_1$ (rad/s)")
ax.set_title("相图：前 3 秒几乎重合，12 秒后走成两条不同的轨迹", fontsize=11)
ax.grid(alpha=.25)
ax.legend(frameon=False, fontsize=8, loc="best")
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig2_phase.png"))
plt.close(fig)

# ---------------- 图 3：可预报时长 ----------------
fig, ax = plt.subplots(figsize=(5.4, 3.4))
ax.bar([f"{x:g}" for x in tolerances], horizons, color="#38BDF8", width=.55)
for i, h in enumerate(horizons):
    ax.annotate(f"{h:.1f}s", (i, h), textcoords="offset points", xytext=(0, 4),
                ha="center", fontsize=9)
ax.set_xlabel("允许误差 (rad)")
ax.set_ylabel("可预报时长 (s)")
ax.set_title("要多准，就只能预报多久", fontsize=11)
ax.grid(axis="y", alpha=.25)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig3_horizon.png"))
plt.close(fig)

print(json.dumps(metrics, ensure_ascii=False, indent=1))
