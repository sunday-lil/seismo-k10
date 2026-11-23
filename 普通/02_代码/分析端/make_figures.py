# -*- coding: utf-8 -*-
"""
震感捕手 · 配图生成
生成：封面、装置示意图、科学原理图、连线图、屏幕界面、探究流程图
所有图为矢量绘制的 PNG（320 dpi），可直接放进作品文档与帖子。
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon, FancyArrowPatch
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.abspath(os.path.join(ROOT, "..", "..", "04_图片"))
os.makedirs(IMG, exist_ok=True)

INK = "#12263A"
MUTED = "#5B6B7F"
TEAL = "#1B998B"
AMBER = "#F4A259"
CORAL = "#E76F51"
BLUE = "#2E6F95"
PAPER = "#FFFFFF"
LINE = "#C9D2DE"
WOOD = "#D9B382"
WOOD_D = "#A9825C"

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "axes.unicode_minus": False,
    "savefig.dpi": 320,
    "figure.facecolor": PAPER,
    "savefig.facecolor": PAPER,
})


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.subplots_adjust(0, 0, 1, 1)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.set_facecolor(PAPER)
    return fig, ax


def box(ax, x, y, w, h, fc="#FFFFFF", ec=INK, lw=1.2, r=0.08, z=3, alpha=1.0):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=%s" % r,
                       fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha)
    ax.add_patch(p)
    return p


def arrow(ax, x0, y0, x1, y1, color=INK, lw=1.2, style="-|>", ms=10, z=4, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=ms, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0, zorder=z, linestyle=ls))


# ==================================================================
# 封面
# ==================================================================
def cover():
    W, H = 12.8, 7.2
    fig, ax = canvas(W, H)
    ax.set_facecolor(INK)
    fig.patch.set_facecolor(INK)
    # 渐变底
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    ax.imshow(grad, extent=(0, W, 0, H), origin="lower", aspect="auto",
              cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
                  "c", ["#08131F", "#12263A", "#1C3A52"]), zorder=0)

    # 地震波
    x = np.linspace(0, W, 1200)
    for i, (amp, freq, y0, a, lw) in enumerate([
            (1.05, 2.2, 2.25, 0.16, 1.1), (0.72, 3.4, 2.25, 0.22, 1.0),
            (0.42, 5.2, 2.25, 0.30, 0.9)]):
        env = np.exp(-((x - 8.6) ** 2) / 7.0)
        y = y0 + amp * env * np.sin(freq * x * 2.4 + i)
        ax.plot(x, y, color=TEAL, lw=lw, alpha=a, zorder=2)
    # 主波形
    env = np.exp(-np.clip(x - 8.0, 0, None) / 1.6) * (x > 8.0)
    ax.plot(x, 2.25 + 1.5 * env * np.sin(6.0 * (x - 8.0)), color=TEAL, lw=2.2, alpha=0.95, zorder=2)

    ax.text(0.75, 6.35, "DF创客社区 · 做中学·探未来", color="#8FB3C7", fontsize=12, zorder=5)
    ax.text(0.72, 4.85, "震感捕手", color="#FFFFFF", fontsize=54, fontweight="bold", zorder=5)
    ax.text(0.78, 4.22, "用一块行空板 K10，把“看不见的震动”变成可读的数据", color="#DCE7EF",
            fontsize=16, zorder=5)
    ax.plot([0.78, 4.6], [3.86, 3.86], color=AMBER, lw=2.0, zorder=5)
    ax.text(0.78, 3.35, "模拟地震波传播 · 振动方向识别 · 建筑共振 · 盲测定位",
            color="#9FC3D8", fontsize=13, zorder=5)
    ax.text(0.78, 0.72, "科学教育实践案例  |  地球奥秘  |  初中", color="#6F93A8", fontsize=11, zorder=5)
    fig.savefig(os.path.join(IMG, "fig0_封面.png"), facecolor=INK)
    plt.close(fig)



def banner():
    W, H = 12.8, 4.6
    fig, ax = canvas(W, H)
    ax.set_facecolor(INK)
    fig.patch.set_facecolor(INK)
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    ax.imshow(grad, extent=(0, W, 0, H), origin="lower", aspect="auto",
              cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
                  "c", ["#08131F", "#12263A", "#1C3A52"]), zorder=0)
    x = np.linspace(0, W, 1200)
    for i, (amp, freq, a, lw) in enumerate([(1.0, 2.2, 0.18, 1.1), (0.66, 3.5, 0.24, 1.0),
                                           (0.38, 5.4, 0.32, 0.9)]):
        env = np.exp(-((x - 8.4) ** 2) / 7.0)
        ax.plot(x, 2.1 + amp * env * np.sin(freq * x * 2.4 + i), color=TEAL, lw=lw, alpha=a, zorder=2)
    env = np.exp(-np.clip(x - 7.6, 0, None) / 1.5) * (x > 7.6)
    ax.plot(x, 2.1 + 1.25 * env * np.sin(5.4 * (x - 7.6)), color=TEAL, lw=2.0, alpha=0.95, zorder=2)
    ax.text(0.55, 3.62, "SEISMO CATCHER", color="#7FA8BF", fontsize=21, zorder=5, fontweight="bold")
    ax.text(0.58, 3.05, "UNIHIKER K10  ·  模拟地震波探测", color="#9FC3D8", fontsize=13, zorder=5)
    fig.savefig(os.path.join(IMG, "fig0_横幅.png"), facecolor=INK)
    plt.close(fig)


# ==================================================================
# 装置示意图
# ==================================================================
def setup():
    W, H = 12.0, 7.6
    fig, ax = canvas(W, H)
    ax.text(0.3, 7.24, "“震感捕手”实验装置（侧视示意）", fontsize=15, color=INK, fontweight="bold")
    ax.text(0.3, 6.86, "震源、传播介质、测点三者位置固定，只改变测点距离", fontsize=9.5, color=MUTED)

    floor = 2.15
    ax.add_patch(Rectangle((0.2, 1.25), 11.6, 0.90, fc="#F1EDE6", ec="none", zorder=0))
    ax.plot([0.2, 11.8], [floor, floor], color=LINE, lw=1.4, zorder=1)
    ax.text(10.55, 1.55, "地面（安静、无人走动）", fontsize=8, color=MUTED)

    # 桌子
    top_y = 3.55
    ax.add_patch(Rectangle((0.9, top_y), 10.3, 0.22, fc=WOOD, ec=WOOD_D, lw=1.2, zorder=3))
    for lx in (1.35, 10.35):
        ax.add_patch(Rectangle((lx, floor), 0.16, top_y - floor, fc="#C79A6B", ec=WOOD_D, lw=1.0, zorder=2))
        # 隔振垫
        ax.add_patch(FancyBboxPatch((lx - 0.16, floor - 0.12), 0.48, 0.13,
                                    boxstyle="round,pad=0,rounding_size=0.03",
                                    fc="#B9C6D4", ec="none", zorder=4))
    ax.text(9.55, floor + 0.05, "隔振垫（泡沫）", fontsize=7.5, color=MUTED, ha="right")
    ax.annotate("", xy=(10.3, floor + 0.02), xytext=(10.0, floor + 0.18),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    # 落球管
    ax.add_patch(FancyBboxPatch((1.68, top_y + 0.22), 0.30, 2.60,
                                boxstyle="round,pad=0,rounding_size=0.03",
                                fc="#E8EDF3", ec=LINE, lw=1.2, zorder=3, alpha=0.95))
    ax.text(1.10, 6.42, "定高落球管", fontsize=8.5, color=INK)
    ax.text(1.10, 6.20, "（PVC/纸筒，h=0.50 m）", fontsize=7.5, color=MUTED)
    ax.annotate("", xy=(1.70, 6.32), xytext=(1.55, 6.32),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    # 球
    ax.add_patch(Circle((1.83, 5.86), 0.105, fc="#7F8C99", ec="#5B6B7F", lw=1.0, zorder=5))
    ax.add_patch(Circle((1.80, 5.90), 0.035, fc="#D5DDE5", ec="none", zorder=6))
    ax.text(2.12, 5.82, "钢球 直径20 mm", fontsize=8, color=INK)
    arrow(ax, 1.83, 5.64, 1.83, 3.98, color=AMBER, lw=1.4, ls=(0, (4, 3)))
    ax.text(2.02, 4.90, "自由下落", fontsize=7.5, color=AMBER)

    # 钢片震源
    ax.add_patch(Rectangle((1.52, top_y + 0.22), 0.62, 0.05, fc="#5B6B7F", ec="none", zorder=6))
    ax.text(0.30, 4.62, "钢片 = 震源", fontsize=8.2, color=INK, fontweight="bold")
    ax.text(0.30, 4.40, "（位置固定，标记为 0 m）", fontsize=7.6, color=INK)
    ax.annotate("", xy=(1.62, top_y + 0.26), xytext=(1.30, 4.34),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    # 刻度尺
    ry = top_y + 0.40
    x0 = 2.18
    scale = 3.62       # 每米对应的横坐标长度
    ax.plot([x0, x0 + 2.1 * scale], [ry, ry], color=INK, lw=1.2, zorder=5)
    for d in np.arange(0, 2.11, 0.1):
        xx = x0 + d * scale
        big = abs(d * 10 - round(d * 10)) < 1e-6 and abs(d * 10 % 5) < 1e-6
        ax.plot([xx, xx], [ry, ry + (0.10 if big else 0.055)], color=INK, lw=0.8, zorder=5)
        if big:
            ax.text(xx, ry + 0.13, "%.1f" % d, fontsize=7, color=INK, ha="center")
    ax.text(x0 + 2.12 * scale, ry + 0.13, "m", fontsize=7, color=INK)

    # K10
    kx = x0 + 0.80 * scale
    ax.add_patch(FancyBboxPatch((kx - 0.42, top_y + 0.22), 0.84, 0.52,
                                boxstyle="round,pad=0,rounding_size=0.05",
                                fc="#1F3B57", ec=INK, lw=1.2, zorder=6))
    ax.add_patch(Rectangle((kx - 0.33, top_y + 0.30), 0.50, 0.34, fc="#0B1220", ec="#3C5A78", lw=0.6, zorder=7))
    for i, c in enumerate([TEAL, AMBER, CORAL]):
        ax.plot([kx - 0.31, kx + 0.13], [top_y + 0.54 - i * 0.09, top_y + 0.54 - i * 0.09],
                color=c, lw=0.8, zorder=8)
    ax.add_patch(Circle((kx + 0.30, top_y + 0.36), 0.03, fc=TEAL, ec="none", zorder=8))
    ax.annotate("行空板 K10\n（平放，Z 轴竖直）", xy=(kx, top_y + 0.74), xytext=(kx - 0.55, 4.65),
                fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9,
                                connectionstyle="arc3,rad=0.2"))

    ax.text(6.25, 2.78, "长桌面 = 传播介质（木板/瓷砖/地毯，可更换）", fontsize=8.5, color=INK)
    ax.annotate("", xy=(7.7, top_y), xytext=(7.2, 2.86),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    # 底部链路
    y = 0.35
    items = [("① 定高落球", "能量可重复"), ("② 桌面波传播", "振幅随距离衰减"),
             ("③ K10 采集", "200 Hz / 三轴"), ("④ CSV 存卡", "现场可回放"), ("⑤ 拟合与盲测", "模型做预测")]
    bw, gap = 2.05, 0.28
    x = 0.35
    for i, (t1, t2) in enumerate(items):
        fc = "#FFFFFF" if i not in (2,) else "#E8F5F2"
        box(ax, x, y, bw, 0.78, fc=fc, ec=TEAL if i == 2 else LINE, lw=1.2, r=0.06)
        ax.text(x + bw / 2, y + 0.48, t1, fontsize=8.6, ha="center", color=INK, fontweight="bold")
        ax.text(x + bw / 2, y + 0.22, t2, fontsize=7.4, ha="center", color=MUTED)
        if i < 4:
            arrow(ax, x + bw + 0.04, y + 0.37, x + bw + gap - 0.02, y + 0.37, color=TEAL, lw=1.0, ms=8)
        x += bw + gap

    fig.savefig(os.path.join(IMG, "fig6_装置示意图.png"), facecolor=PAPER)
    plt.close(fig)


# ==================================================================
# 科学原理
# ==================================================================
def principle():
    W, H = 12.6, 4.3
    fig, ax = canvas(W, H)
    ax.text(0.3, 3.98, "三个关键科学原理", fontsize=14, color=INK, fontweight="bold")

    # (a) P 波 / S 波
    x0, x1 = 0.45, 4.0
    ax.text(0.45, 3.62, "① P 波与 S 波", fontsize=10.5, color=TEAL, fontweight="bold")
    # P 波：疏密
    ax.text(0.45, 3.28, "P 波（纵波）", fontsize=8, color=MUTED)
    for i in range(28):
        xx = 0.5 + i * 0.125
        d = np.sin(i * 0.9) * 0.055
        ax.add_patch(Circle((xx + d, 2.98), 0.035, fc=BLUE, ec="none", alpha=0.85))
    arrow(ax, 0.5, 2.82, 3.95, 2.82, color=BLUE, lw=1.0, ms=8)
    ax.text(2.2, 2.62, "质点沿传播方向振动", fontsize=7.4, color=MUTED, ha="center")
    # S 波
    ax.text(0.45, 2.30, "S 波（横波）", fontsize=8, color=MUTED)
    xs = np.linspace(0.5, 3.95, 200)
    ax.plot(xs, 2.02 + 0.13 * np.sin(xs * 9.0), color=CORAL, lw=1.3)
    for xx in np.linspace(0.55, 3.9, 14):
        ax.plot([xx, xx], [2.02, 2.02 + 0.13 * np.sin(xx * 9.0)], color=CORAL, lw=0.5, alpha=0.5)
        ax.add_patch(Circle((xx, 2.02 + 0.13 * np.sin(xx * 9.0)), 0.032, fc=CORAL, ec="none"))
    arrow(ax, 0.5, 1.80, 3.95, 1.80, color=CORAL, lw=1.0, ms=8)
    ax.text(2.2, 1.60, "质点垂直于传播方向振动", fontsize=7.4, color=MUTED, ha="center")
    ax.text(0.45, 1.30, "P 波先到、S 波后到；两者速度差\n正是地震台判断震中距的依据。",
            fontsize=7.8, color=INK, linespacing=1.5)
    ax.plot([4.28, 4.28], [0.55, 3.75], color=LINE, lw=0.9)

    # (b) 三轴分解
    ax.text(4.52, 3.62, "② 三轴分解", fontsize=10.5, color=TEAL, fontweight="bold")
    ox, oy = 5.55, 1.85
    arrow(ax, ox, oy, ox + 0.95, oy, color=INK, lw=1.3, ms=9)
    arrow(ax, ox, oy, ox, oy + 0.95, color=INK, lw=1.3, ms=9)
    arrow(ax, ox, oy, ox - 0.55, oy - 0.55, color=INK, lw=1.3, ms=9)
    ax.text(ox + 0.98, oy - 0.04, "X", fontsize=9, color=INK)
    ax.text(ox - 0.06, oy + 1.00, "Z", fontsize=9, color=INK)
    ax.text(ox - 0.66, oy - 0.66, "Y", fontsize=9, color=INK)
    ax.annotate("", xy=(ox + 0.72, oy + 0.46), xytext=(ox, oy),
                arrowprops=dict(arrowstyle="-|>", color=CORAL, lw=1.8, mutation_scale=12))
    ax.text(ox + 0.42, oy + 0.60, "a", fontsize=10, color=CORAL)
    ax.plot([ox + 0.72, ox + 0.72], [oy, oy + 0.46], color=GREY if False else MUTED, lw=0.7, ls=":")
    ax.text(4.52, 1.05, "a = √(ax² + ay² + az²)\nθ = arctan(az / √(ax²+ay²))", fontsize=8.2,
            color=INK, linespacing=1.6)
    ax.text(4.52, 0.58, "由三分量之比反推振动方向", fontsize=7.4, color=MUTED)
    ax.plot([8.30, 8.30], [0.55, 3.75], color=LINE, lw=0.9)

    # (c) 衰减
    ax.text(8.55, 3.62, "③ 振幅随距离衰减", fontsize=10.5, color=TEAL, fontweight="bold")
    axr = fig.add_axes([8.52 / W, 1.55 / H, 3.30 / W, 1.80 / H])
    r = np.linspace(0.15, 2.0, 200)
    A = 0.20 * r ** -0.70
    axr.plot(r, A, color=CORAL, lw=1.6)
    rr = np.array([0.2, 0.4, 0.6, 0.8, 1.0, 1.4, 1.8, 2.0])
    axr.plot(rr, 0.20 * rr ** -0.70 * np.array([1.02, 0.99, 1.01, 0.98, 1.0, 1.03, 0.97, 1.0]),
             "o", ms=3.5, color=TEAL)
    axr.set_xlabel("震源距 r (m)", fontsize=7, labelpad=1)
    axr.set_ylabel("PGA (g)", fontsize=7)
    axr.tick_params(labelsize=6.5, colors=MUTED, length=2)
    for s in ("top", "right"):
        axr.spines[s].set_visible(False)
    axr.grid(color="#E8EDF3", lw=0.6)
    axr.set_axisbelow(True)
    axr.set_xlabel("")
    ax.text(8.55, 1.02, "A = A0 · r^(-n)：距离越远，震感越弱。", fontsize=7.6, color=INK)
    ax.text(8.55, 0.80, "反过来，就能从振幅反推距离。", fontsize=7.6, color=INK)

    fig.savefig(os.path.join(IMG, "fig7_科学原理.png"), facecolor=PAPER)
    plt.close(fig)


# ==================================================================
# 连线图
# ==================================================================
def wiring():
    W, H = 12.0, 6.4
    fig, ax = canvas(W, H)
    ax.text(0.3, 6.02, "硬件连线图：零外接，一块板就是一台地震台", fontsize=14, color=INK, fontweight="bold")
    ax.text(0.3, 5.66, "行空板 K10 板载三轴加速度计、屏幕、按键、TF 卡槽与电池接口，无需面包板和杜邦线",
            fontsize=9, color=MUTED)

    # 中心 K10
    cx, cy, cw, ch = 4.75, 2.15, 2.5, 2.75
    box(ax, cx, cy, cw, ch, fc="#1F3B57", ec=INK, lw=1.6, r=0.12)
    ax.add_patch(FancyBboxPatch((cx + 0.28, cy + 1.32), 1.94, 1.08,
                                boxstyle="round,pad=0,rounding_size=0.06",
                                fc="#0B1220", ec="#3C5A78", lw=0.8))
    ax.plot([cx + 0.42, cx + 2.08], [cy + 2.09, cy + 2.09], color=TEAL, lw=1.0)
    ax.plot([cx + 0.42, cx + 2.08], [cy + 2.00, cy + 2.00], color=AMBER, lw=1.0)
    ax.plot([cx + 0.42, cx + 2.08], [cy + 1.91, cy + 1.91], color=CORAL, lw=1.0)
    ax.text(cx + cw / 2, cy + 2.55, "UNIHIKER K10", fontsize=10, color="#FFFFFF",
            ha="center", fontweight="bold")
    ax.text(cx + cw / 2, cy + 1.08, "ESP32-S3 N16R8\nWi-Fi / BLE / 2.8″ 屏", fontsize=7.4,
            color="#BBD3E3", ha="center", linespacing=1.5)
    ax.text(cx + cw / 2, cy + 0.45, "SC7A20H 三轴加速度计\n±2/4/8/16 g", fontsize=7.6,
            color="#FFFFFF", ha="center", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="#2E6F95", ec="none"))

    # 左侧板载
    left = [
        ("A / B 按键", "开始记录 · 翻页", TEAL),
        ("RGB 指示灯 ×3", "震动等级 / 报警", AMBER),
        ("蜂鸣器 / 扬声器", "阈值报警", CORAL),
    ]
    y = 4.25
    for t, s, c in left:
        box(ax, 0.35, y, 2.55, 0.62, fc="#FFFFFF", ec=c, lw=1.1, r=0.06)
        ax.text(0.48, y + 0.38, t, fontsize=8.4, color=INK, fontweight="bold")
        ax.text(0.48, y + 0.15, s, fontsize=7.2, color=MUTED)
        arrow(ax, 2.94, y + 0.31, cx - 0.04, y + 0.31, color=c, lw=1.0, ms=8)
        y -= 0.86

    # 右侧存储/供电
    right = [
        ("TF 卡（/sd）", "CSV 原始波形 + 台账", TEAL),
        ("USB-C 5V", "供电 / 连电脑取数", BLUE),
        ("PH2.0 电池", "3.7 V 锂电池，脱机记录", AMBER),
    ]
    y = 4.25
    for t, s, c in right:
        box(ax, 9.08, y, 2.55, 0.62, fc="#FFFFFF", ec=c, lw=1.1, r=0.06)
        ax.text(9.20, y + 0.38, t, fontsize=8.4, color=INK, fontweight="bold")
        ax.text(9.20, y + 0.15, s, fontsize=7.2, color=MUTED)
        arrow(ax, cx + cw + 0.04, y + 0.31, 9.04, y + 0.31, color=c, lw=1.0, ms=8)
        y -= 0.86

    # 底部数据流
    ax.text(0.35, 1.42, "数据流", fontsize=9, color=MUTED)
    steps = [("振动信号", TEAL), ("K10 采样 200 Hz", TEAL), ("CSV 文件", TEAL),
             ("电脑分析", BLUE), ("图表/结论", BLUE)]
    x = 0.35
    for i, (t, c) in enumerate(steps):
        box(ax, x, 0.55, 1.85, 0.62, fc="#FFFFFF", ec=c, lw=1.0, r=0.05)
        ax.text(x + 0.925, 0.86, t, fontsize=7.8, ha="center", color=INK)
        if i < 4:
            arrow(ax, x + 1.87, 0.86, x + 2.15, 0.86, color=c, lw=0.9, ms=7)
        x += 2.18

    ax.text(0.35, 0.22, "可选扩展：Gravity I²C 传感器（如光线、温湿度）接 4Pin I²C 口，用于记录环境背景。",
            fontsize=7.6, color=MUTED)
    fig.savefig(os.path.join(IMG, "fig8_连线图.png"), facecolor=PAPER)
    plt.close(fig)


# ==================================================================
# 屏幕界面
# ==================================================================
def _screen_frame(ax, x, y, w, h, title):
    box(ax, x - 0.10, y - 0.10, w + 0.20, h + 0.20, fc="#22303F", ec="#0B1220", lw=1.4, r=0.10)
    ax.add_patch(Rectangle((x, y), w, h, fc="#0B1220", ec="none", zorder=4))
    ax.text(x + w / 2, y + h + 0.16, title, fontsize=8.5, color=MUTED, ha="center")


def screen_ui():
    W, H = 11.6, 5.85
    fig, ax = canvas(W, H)
    ax.text(0.3, 5.55, "K10 屏幕界面（240 × 320，中文版）",
            fontsize=13, color=INK, fontweight="bold")

    def screen(ox, oy, sw=3.35, sh=4.47, title=""):
        box(ax, ox - 0.10, oy - 0.10, sw + 0.20, sh + 0.20, fc="#22303F", ec="#0B1220", lw=1.4, r=0.10)
        ax.add_patch(Rectangle((ox, oy), sw, sh, fc="#0B1220", ec="none", zorder=4))
        if title:
            ax.text(ox + sw / 2, oy + sh + 0.14, title, fontsize=8.5, color=MUTED, ha="center")
        sx = lambda px: ox + px * sw / 240.0
        sy = lambda py: oy + (320.0 - py) * sh / 320.0
        return sx, sy

    # ---------------- 监测页 ----------------
    ox, oy = 0.45, 0.45
    sx, sy = screen(ox, oy, title="① 实时监测页")
    ax.text(sx(10), sy(10), "震感捕手", fontsize=13.5, color="#E5E7EB", va="top", zorder=6)
    ax.text(sx(10), sy(34), "监测中", fontsize=13.5, color="#22D3EE", va="top", zorder=6)
    ax.text(sx(10), sy(58), "峰值 0.327 g", fontsize=13.5, color="#34D399", va="top", zorder=6)
    ax.text(sx(10), sy(82), "E1 0.80m #1", fontsize=9.5, color="#7C8AA0", va="top", zorder=6)
    for k, c in enumerate(["#22D3EE", "#F59E0B", "#A78BFA"]):
        mid = 205 + k * 40
        ax.plot([sx(0), sx(240)], [sy(mid), sy(mid)], color="#1E2A3A", lw=0.6, zorder=5)
        xs = np.linspace(0, 1, 120)
        env = np.exp(-((xs - 0.45) ** 2) / 0.03)
        ax.plot(sx(2 + xs * 236), sy(mid - 26 * env * np.sin(xs * 46 + k)),
                color=c, lw=0.8, zorder=6)
    ax.text(sx(10), sy(156), "x123 y-45  z-936", fontsize=7.5, color="#7C8AA0", va="top", zorder=6)
    ax.text(sx(10), sy(176), "A:记录 B:取消", fontsize=7.5, color="#7C8AA0", va="top", zorder=6)

    # ---------------- 结果页 ----------------
    ox2 = 6.35
    sx, sy = screen(ox2, oy, title="② 记录结果页")
    ax.text(sx(10), sy(10), "记录完成", fontsize=13.5, color="#34D399", va="top", zorder=6)
    ax.text(sx(10), sy(44), "峰值 0.327 g", fontsize=13.5, color="#F59E0B", va="top", zorder=6)
    for txt, yy in [("方向 Z", 88), ("主频 28.4 Hz", 112), ("时长 186 ms", 136)]:
        ax.text(sx(10), sy(yy), txt, fontsize=12.5, color="#E5E7EB", va="top", zorder=6)
    ax.text(sx(10), sy(170), "已存卡", fontsize=9.5, color="#7C8AA0", va="top", zorder=6)
    ax.text(sx(10), sy(276), "B:返回", fontsize=9.5, color="#7C8AA0", va="top", zorder=6)

    ax.text(0.3, 0.08, "说明：按 main.cpp 的 drawPage()/drawResult() 实际布局复刻；实机为彩色 LCD，字体略有差异。",
            fontsize=7.2, color=MUTED)
    fig.savefig(os.path.join(IMG, "fig9_屏幕界面.png"), facecolor=PAPER)
    plt.close(fig)


# ==================================================================
# 探究流程
# ==================================================================
def flow():
    W, H = 12.4, 3.3
    fig, ax = canvas(W, H)
    ax.text(0.3, 3.00, "“做中学”探究流程：五步走完一个真实问题", fontsize=14, color=INK, fontweight="bold")

    steps = [
        ("① 真实问题", "教室不同位置，", "震感一样吗？", TEAL),
        ("② 作出假设", "振幅随距离", "按幂律衰减", BLUE),
        ("③ 设计实验", "定高落球、固定测点、", "重复 5 次、控制变量", AMBER),
        ("④ 采集分析", "K10 记录 → CSV →", "拟合曲线 → 盲测检验", CORAL),
        ("⑤ 结论迭代", "给出校园抗震建议，", "改进装置再测", TEAL),
    ]
    n = len(steps)
    bw, bh = 2.16, 1.55
    gap = (W - 0.6 - n * bw) / (n - 1)
    y0 = 0.95
    x = 0.3
    centers = []
    for i, (t, l1, l2, c) in enumerate(steps):
        box(ax, x, y0, bw, bh, fc="#FFFFFF", ec=c, lw=1.3, r=0.08)
        ax.add_patch(Rectangle((x, y0 + bh - 0.27), bw, 0.27, fc=c, ec="none", zorder=4))
        ax.text(x + bw / 2, y0 + bh - 0.135, t, fontsize=9.2, color="#FFFFFF", ha="center",
                va="center", fontweight="bold", zorder=5)
        ax.text(x + bw / 2, y0 + 0.62, l1, fontsize=7.6, color=INK, ha="center", va="center")
        ax.text(x + bw / 2, y0 + 0.38, l2, fontsize=7.6, color=INK, ha="center", va="center")
        centers.append(x + bw / 2)
        if i < n - 1:
            arrow(ax, x + bw + 0.03, y0 + bh / 2 - 0.10, x + bw + gap - 0.03, y0 + bh / 2 - 0.10,
                  color=MUTED, lw=1.0, ms=9)
        x += bw + gap

    yp = 0.55
    ax.plot([centers[-1], centers[-1]], [y0, yp], color=TEAL, lw=1.0, ls=(0, (4, 3)), zorder=2)
    ax.plot([centers[-1], centers[0]], [yp, yp], color=TEAL, lw=1.0, ls=(0, (4, 3)), zorder=2)
    arrow(ax, centers[0], yp, centers[0], y0 - 0.02, color=TEAL, lw=1.0, ms=9)
    ax.text((centers[0] + centers[-1]) / 2, 0.24,
            "数据不满意 → 改装置 / 改参数 → 再测一轮", fontsize=7.4, color=TEAL, ha="center")
    fig.savefig(os.path.join(IMG, "fig10_探究流程.png"), facecolor=PAPER)
    plt.close(fig)


if __name__ == "__main__":
    cover()
    banner()
    setup()
    principle()
    wiring()
    screen_ui()
    flow()
    print("图片已生成 →", IMG)
