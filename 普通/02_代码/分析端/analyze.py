# -*- coding: utf-8 -*-
"""
震感捕手 · 数据分析脚本
------------------------------------------------------------------
输入：03_数据/实测/ 或 03_数据/示例数据/ 下的 K10 CSV
输出：03_数据/分析结果/metrics.json + 04_图片/fig1~fig5

用法：
    python analyze.py                # 自动选择：有实测数据就用实测
    python analyze.py --dir ../../03_数据/实测
"""
import os
import sys

# 控制台编码兜底：Windows 中文终端下避免 UnicodeEncodeError 中断整个流程
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import glob
import argparse

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import hilbert, butter, filtfilt

# ------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(ROOT, "..", ".."))
DATA_REAL = os.path.join(PROJ, "03_数据", "实测")
DATA_DEMO = os.path.join(PROJ, "03_数据", "示例数据")
DATA_DIR = DATA_DEMO
OUT_METRICS = os.path.join(PROJ, "03_数据", "分析结果")
IMG = os.path.join(PROJ, "04_图片")
G = 9.80665

INK = "#0F2A44"
TEAL = "#1B998B"
CORAL = "#E76F51"
AMBER = "#F4A259"
BLUE = "#2E6F95"
GREY = "#8A97A8"

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DengXian"],
    "axes.unicode_minus": False,
    "figure.dpi": 110,
    "savefig.dpi": 320,
    "axes.edgecolor": "#C9D2DE",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": "#5B6B7F",
    "ytick.color": "#5B6B7F",
    "axes.titlesize": 11,
    "axes.labelsize": 9.5,
    "font.size": 9,
})


# ------------------------------------------------------------------
# 读取
# ------------------------------------------------------------------
def read_csv(path):
    meta = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("#"):
                break
            body = line[1:].strip()
            if "=" in body:
                k, v = body.split("=", 1)
                meta[k.strip()] = v.strip()
    df = pd.read_csv(path, comment="#", encoding="utf-8")
    return meta, df


def load_all(folder):
    items = []
    for p in sorted(glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True)):
        if os.path.basename(p) == "blind_truth.csv":
            continue
        try:
            meta, df = read_csv(p)
        except Exception as e:
            print("  跳过", p, e)
            continue
        if len(df) < 50:
            continue
        meta["file"] = os.path.basename(p)
        meta.setdefault("exp", "E1")
        meta["dist_m"] = float(meta.get("dist_m", 0) or 0)
        meta["trial"] = int(float(meta.get("trial", 1) or 1))
        meta["fs"] = float(meta.get("fs", 200) or 200)
        items.append((meta, df))
    return items


def ac(df, pre_s=0.5, fs=200.0, unit="m/s2"):
    """去掉重力与零点，统一换算成 g。返回 (t_ms, ax, ay, az)。

    K10 的 C++ 程序输出 mg（1000 = 1 g）；早期的 Python 示例数据是 m/s²。
    单位由 CSV 表头的 unit 字段决定，缺省按 m/s² 处理。
    """
    n0 = max(5, int(pre_s * fs))
    if unit == "mg":
        scale = 0.001
    elif unit == "g":
        scale = 1.0
    else:
        scale = 1.0 / G
    out = {}
    for c in ("ax", "ay", "az"):
        v = df[c].to_numpy(dtype=float)
        out[c] = (v - np.mean(v[:n0])) * scale
    return df["t_ms"].to_numpy(dtype=float), out["ax"], out["ay"], out["az"]


def pga_of(df, fs, pre_s=0.5, unit="m/s2"):
    t, ax, ay, az = ac(df, pre_s, fs, unit)
    mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
    n0 = max(5, int(pre_s * fs))
    # 触发前的噪声有效值（三轴合成），用来算信噪比
    noise = float(np.sqrt(np.mean(ax[:n0] ** 2 + ay[:n0] ** 2 + az[:n0] ** 2)))
    pga = float(mag.max())
    return {
        "pga_g": pga,
        "pga_x": float(np.abs(ax).max()),
        "pga_y": float(np.abs(ay).max()),
        "pga_z": float(np.abs(az).max()),
        "t_peak_ms": float(t[int(np.argmax(mag))]),
        "noise_g": noise,
        "snr": (pga / noise) if noise > 0 else 99.0,
    }


# ------------------------------------------------------------------
# 实验一：距离衰减
# ------------------------------------------------------------------
def analyse_e1(items, min_snr=0.0):
    rows = []
    skipped = 0
    for meta, df in items:
        if meta["exp"] != "E1":
            continue
        r = pga_of(df, meta["fs"], unit=meta.get("unit", "m/s2"))
        r.update(dist=meta["dist_m"], trial=meta["trial"], file=meta["file"])
        if min_snr > 0 and r["snr"] < min_snr:
            skipped += 1
            continue
        rows.append(r)
    if not rows:
        return None
    tb = pd.DataFrame(rows)
    grp = tb.groupby("dist")["pga_g"].agg(["mean", "std", "count"]).reset_index()
    grp["sd"] = grp["std"].fillna(0)

    # 幂律拟合 A = A0 * r^(-n)
    x = np.log(grp["dist"].to_numpy())
    y = np.log(grp["mean"].to_numpy())
    slope, logA0 = np.polyfit(x, y, 1)
    n = -slope          # A = A0 * r^(-n)，n 为正的衰减指数
    pred = logA0 - n * x
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    A0 = float(np.exp(logA0))

    # 用每次重复做留一交叉验证，看看模型预测能力
    loo = []
    for i in range(len(grp)):
        mask = np.ones(len(grp), dtype=bool)
        mask[i] = False
        s_i, a_i = np.polyfit(x[mask], y[mask], 1)
        pred_i = float(np.exp(a_i + s_i * x[i]))
        loo.append((pred_i - grp["mean"].iloc[i]) / grp["mean"].iloc[i] * 100)

    return {
        "n_points": len(grp),
        "n_trials": int(grp["count"].sum()),
        "n_rejected": skipped,
        "min_snr": min_snr,
        "snr_median": float(np.median(tb["snr"])) if len(tb) else 0.0,
        "table": [{
            "dist": float(r["dist"]), "mean": float(r["mean"]), "sd": float(r["sd"]),
            "n": int(r["count"]), "cv": float(r["sd"] / r["mean"] * 100) if r["mean"] else 0,
        } for _, r in grp.iterrows()],
        "fit": {"A0": A0, "n": float(n), "r2": float(r2)},
        "loo_err_pct": [float(v) for v in loo],
        "raw": tb.to_dict(orient="records"),
    }


# ------------------------------------------------------------------
# 实验一·盲测
# ------------------------------------------------------------------
def analyse_blind(items, fit):
    rows = []
    for meta, df in items:
        if meta["exp"] != "E1B":
            continue
        r = pga_of(df, meta["fs"], unit=meta.get("unit", "m/s2"))
        case = meta["file"].split("_")[1]
        r.update(case=case, file=meta["file"])
        rows.append(r)
    if not rows or not fit:
        return None
    tb = pd.DataFrame(rows)
    grp = tb.groupby("case")["pga_g"].mean().reset_index()
    truth = {}
    tp = os.path.join(DATA_DIR, "blind_truth.csv")
    if os.path.exists(tp):
        tt = pd.read_csv(tp, encoding="utf-8")
        truth = dict(zip(tt["case"], tt["true_dist_m"]))
    out = []
    for _, r in grp.iterrows():
        a = r["pga_g"]
        est = (fit["A0"] / a) ** (1.0 / fit["n"]) if a > 0 else float("nan")
        tv = truth.get(r["case"], float("nan"))
        out.append({
            "case": r["case"], "pga_g": float(a), "pred_m": float(est),
            "true_m": float(tv),
            "err_pct": float((est - tv) / tv * 100) if tv == tv else float("nan"),
        })
    return {"cases": out,
            "mape": float(np.mean([abs(o["err_pct"]) for o in out if o["err_pct"] == o["err_pct"]]))}


# ------------------------------------------------------------------
# 实验二：振动方向
# ------------------------------------------------------------------
def analyse_e2(items):
    rows = []
    for meta, df in items:
        if meta["exp"] != "E2":
            continue
        r = pga_of(df, meta["fs"], unit=meta.get("unit", "m/s2"))
        key = meta["file"].split("_")[1]
        r.update(case=key, file=meta["file"])
        rows.append(r)
    if not rows:
        return None
    tb = pd.DataFrame(rows)
    grp = tb.groupby("case").agg(
        px=("pga_x", "mean"), py=("pga_y", "mean"), pz=("pga_z", "mean"),
        n=("pga_x", "count")).reset_index()
    out = []
    for _, r in grp.iterrows():
        horiz = float(np.hypot(r["px"], r["py"]))
        out.append({
            "case": r["case"], "px": float(r["px"]), "py": float(r["py"]),
            "pz": float(r["pz"]), "horiz": horiz,
            "ratio": float(r["pz"] / horiz) if horiz > 0 else 0,
            "angle_deg": float(np.degrees(np.arctan2(r["pz"], horiz))),
            "n": int(r["n"]),
        })
    return {"cases": out}


# ------------------------------------------------------------------
# 实验三：建筑模型
# ------------------------------------------------------------------
def analyse_e3(items):
    rows = []
    spectra = {}
    for meta, df in items:
        if meta["exp"] != "E3":
            continue
        fs = meta["fs"]
        t, ax, ay, az = ac(df, 0.5, fs, meta.get("unit", "m/s2"))
        h = ax if np.var(ax) >= np.var(ay) else ay   # 主导水平轴（避免取模后倍频）
        h_mag = np.sqrt(ax ** 2 + ay ** 2)
        key = meta["file"].split("_")[1]

        # 频谱
        seg = h[int(0.2 * fs):int(min(len(h), 3.2 * fs))]
        seg = seg - seg.mean()
        win = np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg * win, n=8192))
        freqs = np.fft.rfftfreq(8192, 1.0 / fs)
        band = (freqs > 1.0) & (freqs < 15.0)
        fpk = float(freqs[band][int(np.argmax(spec[band]))])
        # 抛物线插值细化
        idx = int(np.argmax(spec[band]))
        fb = freqs[band]
        if 0 < idx < len(spec[band]) - 1:
            y0, y1, y2 = spec[band][idx - 1], spec[band][idx], spec[band][idx + 1]
            d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) != 0 else 0
            fpk = float(fb[idx] + d * (fb[1] - fb[0]))
        spectra.setdefault(key, spec[band] / spec[band].max())
        spectra["_freqs"] = fb

        # 阻尼比：Hilbert 包络对数斜率
        b, a = butter(2, [max(1.0, fpk - 1.5), min(fs / 2 - 1, fpk + 1.5)],
                      btype="band", fs=fs)
        yf = filtfilt(b, a, seg)
        env = np.abs(hilbert(yf))
        tt = np.arange(len(env)) / fs
        i_pk = int(np.argmax(env))
        m = (tt >= tt[i_pk]) & (env > env[i_pk] * 0.15) & (env < env[i_pk] * 0.95)
        if m.sum() > 20:
            slope = np.polyfit(tt[m], np.log(env[m]), 1)[0]
            zeta = float(-slope / (2 * np.pi * fpk))
        else:
            zeta = float("nan")

        rows.append({
            "case": key, "file": meta["file"], "f0": fpk, "zeta": zeta,
            "pga_g": float(np.abs(h_mag).max()),
        })
    if not rows:
        return None
    tb = pd.DataFrame(rows)
    grp = tb.groupby("case").agg(
        f0=("f0", "mean"), zeta=("zeta", "mean"),
        pga=("pga_g", "mean"), n=("f0", "count")).reset_index()
    return {
        "cases": [{
            "case": r["case"], "f0": float(r["f0"]), "zeta": float(r["zeta"]),
            "pga_g": float(r["pga"]), "n": int(r["n"]),
        } for _, r in grp.iterrows()],
        "spectra": {k: (v.tolist() if k != "_freqs" else v.tolist()) for k, v in spectra.items()},
    }


# ------------------------------------------------------------------
# 画图
# ------------------------------------------------------------------
def style(ax, grid_axis="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, axis=grid_axis, color="#E8EDF3", lw=0.8)
    ax.set_axisbelow(True)


def fig_wave(items):
    pick = None
    for meta, df in items:
        if meta["exp"] == "E1" and abs(meta["dist_m"] - 0.4) < 1e-6 and meta["trial"] == 1:
            pick = (meta, df)
            break
    if pick is None and items:
        pick = items[0]
    if not pick:
        return None
    meta, df = pick
    t, ax, ay, az = ac(df, 0.5, meta["fs"])
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.4), sharex=True,
                             gridspec_kw={"height_ratios": [1.35, 1]})
    for v, c, n in ((ax, TEAL, "X"), (ay, AMBER, "Y"), (az, CORAL, "Z")):
        axes[0].plot(t, v, lw=0.8, color=c, label=n + " 轴")
    axes[0].set_ylabel("加速度 (g)")
    axes[0].legend(loc="upper right", frameon=False, ncol=3, fontsize=8)
    axes[0].set_title("单次落球事件的原始波形（距离 %.2f m）" % meta["dist_m"], loc="left")
    i = int(np.argmax(np.abs(az)))
    mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
    axes[1].plot(t, mag, lw=0.8, color=INK)
    axes[1].fill_between(t, 0, mag, color=TEAL, alpha=0.15)
    axes[1].set_ylabel("合加速度 (g)")
    axes[1].set_xlabel("时间 (ms)")
    axes[1].set_xlim(max(0, t[0]), min(t[-1], 2200))
    style(axes[0]); style(axes[1])
    fig.tight_layout()
    p = os.path.join(IMG, "fig1_波形.png")
    fig.savefig(p); plt.close(fig)
    return p


def fig_atten(e1):
    if not e1:
        return None
    d = np.array([r["dist"] for r in e1["table"]])
    m = np.array([r["mean"] for r in e1["table"]])
    s = np.array([r["sd"] for r in e1["table"]])
    fit = e1["fit"]
    rr = np.linspace(d.min() * 0.9, d.max() * 1.05, 200)
    aa = fit["A0"] * rr ** (-fit["n"])

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.5))
    axes[0].errorbar(d, m, yerr=s, fmt="o", ms=4, color=TEAL, ecolor="#B9C6D4",
                     capsize=2, lw=0.8, label="实测均值 ± 标准差")
    axes[0].plot(rr, aa, color=CORAL, lw=1.4, label="拟合 A=%.3f·r$^{-%.2f}$" % (fit["A0"], fit["n"]))
    axes[0].set_xlabel("震源距 r (m)"); axes[0].set_ylabel("峰值加速度 PGA (g)")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("振幅随距离衰减", loc="left")
    style(axes[0])

    axes[1].loglog(d, m, "o", ms=4, color=TEAL)
    axes[1].loglog(rr, aa, color=CORAL, lw=1.4)
    from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter
    axes[1].xaxis.set_major_locator(FixedLocator([0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0]))
    axes[1].xaxis.set_major_formatter(FuncFormatter(lambda v, _: ("%g" % v)))
    axes[1].xaxis.set_minor_locator(NullLocator())
    axes[1].yaxis.set_major_locator(FixedLocator([0.1, 0.2, 0.3, 0.5]))
    axes[1].yaxis.set_major_formatter(FuncFormatter(lambda v, _: ("%g" % v)))
    axes[1].yaxis.set_minor_locator(NullLocator())
    axes[1].set_xlabel("震源距 r (m)"); axes[1].set_ylabel("PGA (g)")
    axes[1].set_title("双对数坐标：斜率 = -%.2f   R²=%.3f" % (fit["n"], fit["r2"]), loc="left")
    style(axes[1], "both")
    fig.tight_layout()
    p = os.path.join(IMG, "fig2_距离衰减.png")
    fig.savefig(p); plt.close(fig)
    return p


def fig_polar(e2):
    if not e2:
        return None
    names = {"V": "垂直落球", "H": "水平敲击", "D": "45°斜击"}
    cs = e2["cases"]
    x = np.arange(len(cs))
    w = 0.26
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw={"width_ratios": [1.5, 1]})
    axes[0].bar(x - w, [c["px"] for c in cs], w, color=TEAL, label="X 轴")
    axes[0].bar(x, [c["py"] for c in cs], w, color=AMBER, label="Y 轴")
    axes[0].bar(x + w, [c["pz"] for c in cs], w, color=CORAL, label="Z 轴")
    axes[0].set_xticks(x, [names.get(c["case"], c["case"]) for c in cs])
    axes[0].set_ylabel("各轴 PGA (g)")
    axes[0].legend(frameon=False, fontsize=8, ncol=3)
    axes[0].set_title("不同敲击方向下的三轴分量", loc="left")
    style(axes[0])
    axes[1].bar(x, [c["angle_deg"] for c in cs], 0.5, color=[TEAL, AMBER, CORAL])
    axes[1].axhline(45, ls="--", lw=0.8, color=GREY)
    axes[1].set_xticks(x, [names.get(c["case"], c["case"]) for c in cs])
    axes[1].set_ylabel("振动方向角 θ (°)")
    axes[1].set_ylim(0, 95)
    axes[1].set_title("θ=arctan(Z/水平)", loc="left")
    style(axes[1])
    fig.tight_layout()
    p = os.path.join(IMG, "fig3_振动方向.png")
    fig.savefig(p); plt.close(fig)
    return p


def fig_res(e3):
    if not e3:
        return None
    names = {"A": "A 无斜撑", "B": "B X形斜撑", "C": "C 斜撑+配重"}
    cols = {"A": CORAL, "B": TEAL, "C": BLUE}
    sp = e3["spectra"]
    f = np.array(sp["_freqs"])
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw={"width_ratios": [1.6, 1]})
    for k in ("A", "B", "C"):
        if k in sp:
            axes[0].plot(f, sp[k], color=cols[k], lw=1.2, label=names[k])
    axes[0].set_xlim(1, 12)
    axes[0].set_xlabel("频率 (Hz)"); axes[0].set_ylabel("归一化幅值")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("自由衰减频谱：峰值即固有频率", loc="left")
    style(axes[0])
    cs = e3["cases"]
    x = np.arange(len(cs))
    axes[1].bar(x, [c["f0"] for c in cs], 0.5, color=[cols.get(c["case"], TEAL) for c in cs])
    for i, c in enumerate(cs):
        axes[1].text(i, c["f0"] + 0.1, "%.1f Hz" % c["f0"], ha="center", fontsize=8)
    axes[1].set_xticks(x, [names.get(c["case"], c["case"]) for c in cs])
    axes[1].set_ylabel("固有频率 f0 (Hz)")
    axes[1].set_title("三种结构的 f0 对比", loc="left")
    style(axes[1])
    fig.tight_layout()
    p = os.path.join(IMG, "fig4_建筑共振.png")
    fig.savefig(p); plt.close(fig)
    return p


def fig_blind(bl):
    if not bl:
        return None
    cs = bl["cases"]
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    lim = [0.3, 2.0]
    ax.plot(lim, lim, ls="--", lw=1, color=GREY, label="理想预测")
    ax.scatter([c["true_m"] for c in cs], [c["pred_m"] for c in cs], s=55,
               color=TEAL, zorder=3, label="盲测点")
    for c in cs:
        ax.annotate("%.0f%%" % c["err_pct"], (c["true_m"], c["pred_m"]),
                    textcoords="offset points", xytext=(6, -10), fontsize=8, color=CORAL)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("真实距离 (m)"); ax.set_ylabel("模型预测距离 (m)")
    ax.set_title("盲测检验：平均绝对误差 %.1f%%" % bl["mape"], loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    style(ax, "both")
    fig.tight_layout()
    p = os.path.join(IMG, "fig5_盲测.png")
    fig.savefig(p); plt.close(fig)
    return p


# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--min-snr", type=float, default=0.0,
                    help="只保留信噪比不低于该值的记录，默认 0（不过滤）")
    args = ap.parse_args()
    global DATA_DIR
    if args.dir:
        DATA_DIR = os.path.abspath(args.dir)
    else:
        has_real = os.path.isdir(DATA_REAL) and any(
            f.endswith(".csv") for _, _, fs in os.walk(DATA_REAL) for f in fs)
        DATA_DIR = DATA_REAL if has_real else DATA_DEMO

    os.makedirs(OUT_METRICS, exist_ok=True)
    os.makedirs(IMG, exist_ok=True)
    print("数据目录：", DATA_DIR)
    items = load_all(DATA_DIR)
    print("读取到 %d 个数据文件" % len(items))

    e1 = analyse_e1(items, min_snr=args.min_snr)
    bl = analyse_blind(items, e1["fit"] if e1 else None)
    e2 = analyse_e2(items)
    e3 = analyse_e3(items)

    figs = {
        "wave": fig_wave(items),
        "atten": fig_atten(e1),
        "polar": fig_polar(e2),
        "resonance": fig_res(e3),
        "blind": fig_blind(bl),
    }
    metrics = {
        "source": "实测" if DATA_DIR == DATA_REAL else "示例（仿真）",
        "data_dir": DATA_DIR,
        "n_files": len(items),
        "E1": e1, "E1B": bl, "E2": e2, "E3": e3,
        "figures": figs,
    }
    with open(os.path.join(OUT_METRICS, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)

    print("分析完成 →", os.path.join(OUT_METRICS, "metrics.json"))
    if e1:
        print("  衰减拟合：A0=%.3f g, n=%.3f, R²=%.3f" % (e1["fit"]["A0"], e1["fit"]["n"], e1["fit"]["r2"]))
    if bl:
        print("  盲测平均误差：%.1f%%" % bl["mape"])
    if e3:
        for c in e3["cases"]:
            print("  %s: f0=%.2f Hz, ζ=%.3f, PGA=%.3f g" % (c["case"], c["f0"], c["zeta"], c["pga_g"]))


if __name__ == "__main__":
    main()
