# -*- coding: utf-8 -*-
"""
追光台 · 数值实验（示例数据）

生成：
  03_数据/exp1_cos.csv        入射角 vs 功率（余弦定律）
  03_数据/exp2_track.csv      6 小时日照三种策略的逐分钟功率
  03_数据/metrics.json        拟合与能量汇总
  04_图片/fig1_cos.png
  04_图片/fig2_power.png
  04_图片/fig3_energy.png

说明：本脚本产出的是**仿真示例数据**，用于验证“采集—分析—成图—成文”流程；
真实数据请用 K10 记录的 solar_*.csv 替换后重跑。
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

rng = np.random.default_rng(20261124)
P0 = 458.0          # mW，正入射最大功率
ETA = 0.77          # 整机效率（温升、线损、玻璃反射）

# ---------------- 实验一：余弦定律 ----------------
angles = np.array([0, 15, 30, 45, 60], dtype=float)
theory = P0 * np.cos(np.deg2rad(angles))
# 大角度时表面反射加剧，额外损失随角度增大
extra = np.array([0, 0.004, 0.015, 0.022, 0.055])
p_meas = theory * (1 - extra) + rng.normal(0, 1.6, angles.size)
v_meas = 5.42 - 0.008 * angles + rng.normal(0, 0.01, angles.size)
# 恒功率近似下 I = P/V
i_meas = p_meas / v_meas
rel = (p_meas - theory) / theory * 100

with open(os.path.join(DATA, "exp1_cos.csv"), "w", encoding="utf-8") as f:
    f.write("# 示例数据（仿真）：入射角与光伏输出\n")
    f.write("theta_deg,cos,volt,curr_ma,p_mw,p_theory_mw,rel_err_pct\n")
    for a, c, v, i, p, t, r in zip(angles, np.cos(np.deg2rad(angles)), v_meas,
                                   i_meas, p_meas, theory, rel):
        f.write(f"{a:.0f},{c:.3f},{v:.2f},{i:.1f},{p:.1f},{t:.1f},{r:+.1f}\n")

# ---------------- 实验二：6 小时日照 ----------------
T_H = 6.0
dt = 1 / 60.0                       # 步长 1 分钟（小时）
t = np.arange(0, T_H, dt)
hour_angle = np.deg2rad((t - T_H / 2) * 30.0)      # ±45°
alt = np.deg2rad(12 + 48 * np.sin(np.pi * t / T_H))  # 高度角 12°→60°→12°

# 单位太阳方向（东, 天顶, 南）
sx = np.cos(alt) * np.sin(hour_angle)
sy = np.sin(alt)
sz = np.cos(alt) * np.cos(hour_angle)

def cos_inc(tilt_deg, pan_deg):
    """板面法线与太阳方向的夹角余弦（tilt 相对水平，pan 相对正南）"""
    tr, pr = np.deg2rad(tilt_deg), np.deg2rad(pan_deg)
    nx = np.sin(pr) * np.cos(tr)
    ny = np.sin(tr)
    nz = np.cos(pr) * np.cos(tr)
    return np.clip(nx * sx + ny * sy + nz * sz, 0, None)

# 固定组：30° 倾角、朝正南
c_fixed = cos_inc(30.0, 0.0)
p_fixed = P0 * ETA * c_fixed

# 连续追光：始终正对太阳（留 0.6° 机械抖动）
c_cont = np.cos(np.deg2rad(0.6 + 0.3 * np.sin(2 * np.pi * t * 7)))
p_cont = P0 * ETA * c_cont

# 死区追光：偏差超过 8° 才动一次，动完归位，之后随太阳缓慢漂移
theta_db = np.zeros_like(t)
moved = np.zeros_like(t, dtype=int)
ang = 0.0
for k in range(1, t.size):
    ang += np.rad2deg(np.arccos(np.clip(cos_inc(30.0 + ang, 0.0)[k], 0, 1))) * 0 + \
           np.rad2deg(abs(alt[k] - alt[k - 1]))
    if ang > 8.0:
        ang = 0.6
        moved[k] = 1
    theta_db[k] = ang
c_db = np.cos(np.deg2rad(theta_db))
p_db = P0 * ETA * c_db

# 能耗：连续组舵机+视觉常开 80 mW；死区组每次动作瞬时 320 mW（持续 1 分钟）
p_cost_cont = np.full_like(t, 80.0)
p_cost_db = moved * 320.0
p_cost_fixed = np.zeros_like(t)

e_fixed = float(np.sum(p_fixed) * dt)
e_cont = float(np.sum(p_cont) * dt)
e_db = float(np.sum(p_db) * dt)
cost_cont = float(np.sum(p_cost_cont) * dt)
cost_db = float(np.sum(p_cost_db) * dt)

with open(os.path.join(DATA, "exp2_track.csv"), "w", encoding="utf-8") as f:
    f.write("# 示例数据（仿真）：6 小时日照三种策略\n")
    f.write("t_min,alt_deg,theta_fixed,p_fixed,theta_cont,p_cont,theta_db,p_db,moved\n")
    for k in range(0, t.size, 5):          # 每 5 分钟存一行，控制文件大小
        f.write(f"{t[k]*60:.0f},{np.rad2deg(alt[k]):.1f},{np.rad2deg(np.arccos(np.clip(c_fixed[k],0,1))):.1f},{p_fixed[k]:.1f},"
                f"{np.rad2deg(np.arccos(np.clip(c_cont[k],0,1))):.1f},{p_cont[k]:.1f},"
                f"{theta_db[k]:.1f},{p_db[k]:.1f},{moved[k]}\n")

metrics = {
    "source": "示例（仿真）",
    "P0_mW": P0,
    "eta": ETA,
    "exp1": {
        "angles": angles.tolist(),
        "p_meas_mW": [round(float(x), 1) for x in p_meas],
        "p_theory_mW": [round(float(x), 1) for x in theory],
        "max_rel_err_pct": round(float(np.max(np.abs(rel))), 1),
        "mean_rel_err_pct": round(float(np.mean(np.abs(rel))), 1),
    },
    "exp2": {
        "hours": T_H,
        "E_fixed_mWh": round(e_fixed),
        "E_cont_mWh": round(e_cont),
        "E_db_mWh": round(e_db),
        "C_cont_mWh": round(cost_cont),
        "C_db_mWh": round(cost_db),
        "net_fixed": round(e_fixed),
        "net_cont": round(e_cont - cost_cont),
        "net_db": round(e_db - cost_db),
        "moves": int(moved.sum()),
    },
}
metrics["exp2"]["gain_cont_pct"] = round((metrics["exp2"]["net_cont"] / e_fixed - 1) * 100, 1)
metrics["exp2"]["gain_db_pct"] = round((metrics["exp2"]["net_db"] / e_fixed - 1) * 100, 1)

with open(os.path.join(DATA, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=1)

# ---------------- 图 1：余弦定律 ----------------
fig, ax = plt.subplots(figsize=(5.2, 3.4))
th = np.linspace(0, 70, 200)
ax.plot(th, P0 * np.cos(np.deg2rad(th)), "-", color="#1B998B", lw=2, label="理论 $P_0\\cos\\theta$")
ax.plot(angles, p_meas, "o", color="#F59E0B", ms=7, label="实测")
for a, p in zip(angles, p_meas):
    ax.annotate(f"{p:.0f}", (a, p), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8, color="#8A6D3B")
ax.set_xlabel("入射偏角 θ (°)")
ax.set_ylabel("输出功率 P (mW)")
ax.set_title("余弦定律：角度越大，功率越小", fontsize=11)
ax.grid(alpha=.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig1_cos.png"))
plt.close(fig)

# ---------------- 图 2：一天三条功率曲线 ----------------
fig, ax = plt.subplots(figsize=(6.0, 3.6))
ax.plot(t, p_fixed, color="#94A3B8", lw=1.6, label="固定 30°")
ax.plot(t, p_cont, color="#EF4444", lw=1.2, alpha=.85, label="连续追光")
ax.plot(t, p_db, color="#1B998B", lw=1.8, label="死区追光")
ax.fill_between(t, p_fixed, p_db, color="#1B998B", alpha=.12)
ax.set_xlabel("时间 (h)")
ax.set_ylabel("瞬时功率 (mW)")
ax.set_title("6 小时日照：三条曲线与它们围出的面积", fontsize=11)
ax.grid(alpha=.25)
ax.legend(frameon=False, fontsize=8, loc="lower center", ncol=3)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig2_power.png"))
plt.close(fig)

# ---------------- 图 3：净能量对比 ----------------
labels = ["固定 30°", "连续追光", "死区追光"]
gen = [e_fixed, e_cont, e_db]
cost = [0, cost_cont, cost_db]
net = [gen[i] - cost[i] for i in range(3)]

fig, ax = plt.subplots(figsize=(5.4, 3.6))
x = np.arange(3)
ax.bar(x, gen, 0.55, color="#CBD5E1", label="发电量")
ax.bar(x, [-c for c in cost], 0.55, color="#F87171", label="追光机构耗电")
ax.plot(x, net, "o-", color="#1B998B", lw=2, ms=8, label="净产出")
for i, n in enumerate(net):
    ax.annotate(f"{n:.0f}", (i, n), textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=9, color="#0F766E")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.axhline(0, color="#334155", lw=.8)
ax.set_ylabel("能量 (mWh)")
ax.set_title("净发电量：追光不是越勤越好", fontsize=11)
ax.grid(axis="y", alpha=.25)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig3_energy.png"))
plt.close(fig)

print(json.dumps(metrics["exp2"], ensure_ascii=False, indent=1))
print("figures saved")
