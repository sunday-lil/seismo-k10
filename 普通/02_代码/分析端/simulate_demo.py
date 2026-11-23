# -*- coding: utf-8 -*-
"""
生成"示例数据"（仿真），仅用于：
  1) 验证分析脚本与图表流程是否跑得通；
  2) 让作品文档在实测之前也能展示图表版式。

注意：这些 CSV 是物理模型仿真的数据，不是真实实验结果。
      真正投稿前，请用 K10 实测的 CSV 替换 03_数据/实测/ 下的文件，
      再运行 analyze.py 与 build_doc.py，全文图表与数字会自动更新。
"""
import os
import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, "..", "..", "03_数据", "示例数据"))
FS = 200.0
G = 9.80665
rng = np.random.default_rng(20261107)


def header(exp, dist, trial, note, fs=FS):
    lines = [
        "# device=UNIHIKER K10",
        "# exp=%s" % exp,
        "# dist_m=%.3f" % dist,
        "# trial=%d" % trial,
        "# note=%s" % note,
        "# fs=%.1f" % fs,
        "# data_kind=simulated",
    ]
    return "\n".join(lines) + "\n"


def save(path, t, ax, ay, az, meta):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header(**meta))
        f.write("t_ms,ax,ay,az\n")
        for i in range(len(t)):
            f.write("%.1f,%.4f,%.4f,%.4f\n" % (t[i], ax[i], ay[i], az[i]))


def impact_response(n, fs, trig_s, pga_g, dir_vec, f1=45.0, f2=78.0, tau=0.22):
    """模拟一次落球冲击的台面响应。dir_vec 为三轴投影系数（单位向量）。"""
    t = np.arange(n) / fs * 1000.0   # ms
    tau_t = t / 1000.0 - trig_s - 0.004
    tau_t = np.where(tau_t > 0, tau_t, 0.0)
    env = np.exp(-tau_t / tau)
    # 尖锐初动 + 两个台面模态
    s = (0.85 * np.exp(-tau_t / 0.010) * np.sin(2 * np.pi * 28 * tau_t)
         + 0.45 * env * np.sin(2 * np.pi * f1 * tau_t)
         + 0.25 * env * np.sin(2 * np.pi * f2 * tau_t + 0.6))
    s = s / (np.max(np.abs(s)) + 1e-9) * pga_g * G
    s = np.where(t / 1000.0 >= trig_s, s, 0.0)   # 触发前必须为 0
    out = []
    for k in range(3):
        noise = rng.normal(0, 0.0022, n)
        out.append(s * dir_vec[k] + noise)
    out[2] += G  # 重力（m/s²）
    return t, out[0], out[1], out[2]


def exp1(n_trials=5):
    """距离衰减：0.20 ~ 2.00 m，每档 5 次。"""
    d = os.path.join(OUT, "E1")
    os.makedirs(d, exist_ok=True)
    A0 = 0.58
    n_exp = 0.55
    att = 0.20
    for r in np.arange(0.20, 2.01, 0.20):
        for k in range(1, n_trials + 1):
            # 真实位置有 ±6 mm 的摆放误差，表头记录的仍是卷尺读数
            r_true = r + rng.normal(0, 0.006)
            base = A0 * (0.20 / r_true) ** n_exp * np.exp(-att * (r_true - 0.20))
            pga = base * rng.normal(1.0, 0.08)
            t, ax, ay, az = impact_response(int(5 * FS), FS, 1.0, pga,
                                            (0.22, 0.10, 0.97))
            save(os.path.join(d, "E1_d%03d_t%d.csv" % (int(round(r * 100)), k)),
                 t, ax, ay, az,
                 dict(exp="E1", dist=r, trial=k, note="木桌-落球"))


def exp2(n_trials=5):
    """振动方向：垂直 / 水平 / 45°斜击，距离 0.60 m。"""
    d = os.path.join(OUT, "E2")
    os.makedirs(d, exist_ok=True)
    cases = {
        "V": ((0.06, 0.04, 0.998), 0.42, "垂直落球"),
        "H": ((0.97, 0.16, 0.18), 0.30, "水平敲击"),
        "D": ((0.68, 0.14, 0.72), 0.36, "45°斜击"),
    }
    for key, (vec, pga, note) in cases.items():
        for k in range(1, n_trials + 1):
            t, ax, ay, az = impact_response(int(5 * FS), FS, 1.0,
                                            pga * rng.normal(1.0, 0.06), vec)
            save(os.path.join(d, "E2_%s_t%d.csv" % (key, k)), t, ax, ay, az,
                 dict(exp="E2", dist=0.60, trial=k, note=note))


def free_decay(n, fs, f0, zeta, amp, trig_s=1.0):
    t = np.arange(n) / fs * 1000.0   # ms
    tau_t = np.clip(t / 1000.0 - trig_s, 0, None)
    w0 = 2 * np.pi * f0
    wd = w0 * np.sqrt(1 - zeta ** 2)
    s = amp * np.exp(-zeta * w0 * tau_t) * np.sin(wd * tau_t)
    # 敲击瞬间的宽带成分
    s += 0.25 * amp * np.exp(-tau_t / 0.012) * np.sin(2 * np.pi * 90 * tau_t)
    noise = rng.normal(0, 0.0020, n)
    # K10 平放在楼顶：水平晃动由 X/Y 轴记录，Z 轴主要是重力
    ax = s + noise
    ay = 0.16 * s + noise
    az = G + 0.06 * s + noise
    return t, ax, ay, az


def exp3(n_trials=5):
    """建筑模型：A 无斜撑 / B X 形斜撑 / C 斜撑+顶部配重（阻尼）。"""
    d = os.path.join(OUT, "E3")
    os.makedirs(d, exist_ok=True)
    # (固有频率 Hz, 阻尼比, 顶部峰值加速度 g, 说明)
    cases = {
        "A": (3.1, 0.035, 0.36, "四层无斜撑"),
        "B": (5.8, 0.060, 0.15, "四层X形斜撑"),
        "C": (4.3, 0.115, 0.21, "斜撑+顶部配重"),
    }
    for key, (f0, zeta, amp, note) in cases.items():
        for k in range(1, n_trials + 1):
            t, ax, ay, az = free_decay(int(4 * FS), FS, f0 * rng.normal(1.0, 0.01),
                                       zeta * rng.normal(1.0, 0.05),
                                       amp * G * rng.normal(1.0, 0.07))
            save(os.path.join(d, "E3_%s_t%d.csv" % (key, k)), t, ax, ay, az,
                 dict(exp="E3", dist=0.0, trial=k, note=note))


def exp1_blind(n_trials=3):
    """盲测：真实距离写入 blind_truth.csv，CSV 表头里不写，逼着用模型去猜。"""
    d = os.path.join(OUT, "E1B")
    os.makedirs(d, exist_ok=True)
    truth = [0.65, 1.15, 1.70]
    with open(os.path.join(OUT, "blind_truth.csv"), "w", encoding="utf-8") as f:
        f.write("case,true_dist_m\n")
        for i, r in enumerate(truth, 1):
            f.write("u%d,%.2f\n" % (i, r))
    A0 = 0.58
    n_exp = 0.55
    att = 0.20
    for i, r in enumerate(truth, 1):
        for k in range(1, n_trials + 1):
            r_true = r + rng.normal(0, 0.006)
            base = A0 * (0.20 / r_true) ** n_exp * np.exp(-att * (r_true - 0.20))
            pga = base * rng.normal(1.0, 0.08)
            t, ax, ay, az = impact_response(int(5 * FS), FS, 1.0, pga,
                                            (0.22, 0.10, 0.97))
            save(os.path.join(d, "E1B_u%d_t%d.csv" % (i, k)), t, ax, ay, az,
                 dict(exp="E1B", dist=0.0, trial=k, note="盲测"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    exp1()
    exp2()
    exp3()
    exp1_blind()
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("示例数据已生成：", OUT, "文件数", n)
