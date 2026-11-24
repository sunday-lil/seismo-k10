# -*- coding: utf-8 -*-
"""
生成「追光台」示意渲染图（非实拍，用于帖子配图）。

输出：
  04_图片/mockup_rig.png      装置全景（等轴视角的扁平插画）
  04_图片/mockup_screen.png   屏幕界面特写
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "04_图片"))
os.makedirs(OUT, exist_ok=True)

S = 3                    # 超采样倍数
BG_TOP = (11, 18, 32)
BG_BOT = (18, 28, 44)
TEAL = (27, 153, 139)
AMBER = (253, 186, 116)
BLUE = (56, 189, 248)
INK = (230, 237, 247)
DIM = (124, 138, 160)


def font(size, bold=False):
    cands = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def gradient(w, h):
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.point((0, y), c)
    return img.resize((w, h))


def rotext(draw, xy, text, fnt, fill):
    draw.text(xy, text, font=fnt, fill=fill)


def panel_poly(cx, cy, w, h, tilt_deg, pan_deg=0.0):
    """返回倾斜光伏板四角（简易透视）"""
    t = math.radians(tilt_deg)
    k = math.cos(t)          # 俯视压缩
    sk = math.sin(t) * 0.12
    w2, h2 = w / 2, h / 2 * k
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = cx + sx * w2
        y = cy + sy * h2 + sx * sk * h2 * 0.6
        pts.append((x, y))
    return pts


def draw_rig(W=1600, H=1100):
    W, H = W * S, H * S
    img = gradient(W, H).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # 地面
    d.rectangle([0, int(H * 0.72), W, H], fill=(24, 34, 50, 255))
    d.line([0, int(H * 0.72), W, int(H * 0.72)], fill=(40, 54, 74, 255), width=3)

    # 光源（太阳/台灯）+ 光晕
    lx, ly = int(W * 0.78), int(H * 0.20)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((260 * S, 26), (180 * S, 40), (110 * S, 70), (60 * S, 120)):
        gd.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, 196, 92, a))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(18 * S // 2)))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([lx - 46 * S, ly - 46 * S, lx + 46 * S, ly + 46 * S], fill=(255, 214, 130, 255))
    d.ellipse([lx - 30 * S, ly - 30 * S, lx + 30 * S, ly + 30 * S], fill=(255, 246, 214, 255))

    # 光束：从光源指向板面，细而淡
    px, py = int(W * 0.42), int(H * 0.30)
    for off in (-90, -30, 30, 90):
        d.line([lx, ly, px + off * S, py + 40 * S], fill=(255, 214, 130, 34), width=4 * S)

    # 底座
    base = [int(W * 0.18), int(H * 0.66), int(W * 0.62), int(H * 0.72)]
    d.rounded_rectangle(base, radius=10 * S, fill=(30, 42, 60, 255), outline=(52, 68, 92, 255), width=3)

    # 立柱
    d.rectangle([int(W * 0.30), int(H * 0.44), int(W * 0.335), int(H * 0.67)], fill=(44, 56, 76, 255))

    # 舵机（水平/俯仰）
    d.rounded_rectangle([int(W * 0.285), int(H * 0.415), int(W * 0.35), int(H * 0.47)],
                        radius=6 * S, fill=(88, 100, 118, 255), outline=(120, 132, 150, 255), width=2)
    d.rounded_rectangle([int(W * 0.245), int(H * 0.30), int(W * 0.30), int(H * 0.355)],
                        radius=6 * S, fill=(88, 100, 118, 255), outline=(120, 132, 150, 255), width=2)

    # 光伏板
    pts = panel_poly(int(W * 0.42), int(H * 0.30), int(W * 0.30), int(H * 0.20), 28)
    d.polygon(pts, fill=(22, 42, 74, 255))
    d.line(pts + [pts[0]], fill=(90, 150, 220, 255), width=3)
    # 电池片格线
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    for i in range(1, 6):
        xx = x0 + (x1 - x0) * i / 6
        d.line([xx, y0 + (y1 - y0) * 0.18, xx, y1 - (y1 - y0) * 0.05],
               fill=(70, 120, 190, 160), width=2)
    for j in range(1, 4):
        yy = y0 + (y1 - y0) * j / 4
        d.line([x0 + (x1 - x0) * 0.04, yy, x1 - (x1 - x0) * 0.04, yy],
               fill=(70, 120, 190, 160), width=2)

    # K10 板子
    bx, by = int(W * 0.60), int(H * 0.50)
    bw, bh = int(W * 0.20), int(H * 0.24)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10 * S,
                        fill=(16, 26, 42, 255), outline=(56, 76, 104, 255), width=3)
    # 屏幕
    sx0, sy0 = bx + int(bw * 0.10), by + int(bh * 0.10)
    sw, sh = int(bw * 0.80), int(bh * 0.62)
    d.rounded_rectangle([sx0, sy0, sx0 + sw, sy0 + sh], radius=4 * S, fill=(8, 14, 24, 255))
    f1 = font(20 * S, True); f2 = font(15 * S); f3 = font(12 * S)
    rotext(d, (sx0 + 12 * S, sy0 + 8 * S), "追光台", f1, AMBER)
    rotext(d, (sx0 + 12 * S, sy0 + 40 * S), "死区追光", f2, BLUE)
    rotext(d, (sx0 + 12 * S, sy0 + 66 * S), "P 352 mW", f2, (253, 230, 138))
    rotext(d, (sx0 + 12 * S, sy0 + 90 * S), "偏差 0.6°", f3, INK)
    rotext(d, (sx0 + 12 * S, sy0 + 112 * S), "净能量 2045", f3, (134, 239, 172))
    # 按键
    d.ellipse([bx + 14 * S, by + bh - 26 * S, bx + 34 * S, by + bh - 6 * S], fill=(120, 132, 150, 255))
    d.ellipse([bx + 44 * S, by + bh - 26 * S, bx + 64 * S, by + bh - 6 * S], fill=(120, 132, 150, 255))

    # 接线
    d.line([int(W * 0.335), int(H * 0.45), bx, int(H * 0.60)], fill=(220, 80, 80, 200), width=4 * S)
    d.line([int(W * 0.335), int(H * 0.47), bx, int(H * 0.64)], fill=(60, 60, 70, 220), width=4 * S)

    # 标注
    fa = font(15 * S)
    def label(x, y, text, color=DIM):
        d.line([x, y, x + 26 * S, y - 14 * S], fill=(90, 106, 128, 255), width=2)
        rotext(d, (x + 30 * S, y - 26 * S), text, fa, color)

    label(int(W * 0.80), int(H * 0.30), "模拟光源 100 W", (255, 214, 130))
    label(int(W * 0.30), int(H * 0.16), "光伏板 6V/1W", (140, 190, 240))
    label(int(W * 0.12), int(H * 0.50), "9g 舵机 ×2", (170, 180, 200))
    label(int(W * 0.40), int(H * 0.78), "INA219 测 U/I", (200, 170, 170))
    label(int(W * 0.78), int(H * 0.62), "行空板 K10", (170, 180, 200))

    # 标题
    ft = font(34 * S, True); fs = font(17 * S)
    rotext(d, (60 * S, 46 * S), "追光台：一块板跑两路电池", ft, INK)
    rotext(d, (62 * S, 92 * S), "固定倾角 vs 连续追光 vs 死区追光 · 同一光源下比净发电量", fs, DIM)

    out = img.resize((W // S, H // S), Image.LANCZOS).convert("RGB")
    out.save(os.path.join(OUT, "mockup_rig.png"), quality=95)
    return out


def draw_screen(W=720, H=1280):
    W, H = W * S, H * S
    img = Image.new("RGB", (W, H), (8, 14, 24))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([30 * S, 30 * S, W - 30 * S, H - 30 * S], radius=24 * S,
                        fill=(11, 18, 32), outline=(40, 56, 78), width=3)
    f1 = font(38 * S, True); f2 = font(26 * S); f3 = font(20 * S)
    rotext(d, (70 * S, 90 * S), "追光台", f1, AMBER)
    rotext(d, (70 * S, 170 * S), "死区追光", f2, BLUE)
    rotext(d, (70 * S, 230 * S), "P 352 mW", f2, (253, 230, 138))
    rotext(d, (70 * S, 290 * S), "偏差 0.6°", f3, INK)
    rotext(d, (70 * S, 340 * S), "净能量 2045 mWh", f3, (134, 239, 172))
    rotext(d, (70 * S, 410 * S), "A:切换  B:归零", f3, DIM)
    # 简易曲线
    pts = []
    for i in range(0, 560, 4):
        x = 80 * S + i * S
        y = (980 + 90 * math.sin(i / 60.0) * math.exp(-i / 900.0)) * S
        pts.append((x, y))
    d.line(pts, fill=TEAL, width=4 * S, joint="curve")
    d.line([80 * S, 1080 * S, 640 * S, 1080 * S], fill=(30, 42, 60), width=2)
    out = img.resize((W // S, H // S), Image.LANCZOS)
    out.save(os.path.join(OUT, "mockup_screen.png"))
    return out


if __name__ == "__main__":
    draw_rig()
    draw_screen()
    print("saved mockup_rig.png / mockup_screen.png")
