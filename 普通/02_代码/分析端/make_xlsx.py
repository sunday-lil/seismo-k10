# -*- coding: utf-8 -*-
"""生成《震感捕手·实测记录表.xlsx》——学生实验时直接填写，公式自动算均值和拟合。"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import ScatterChart, Reference, Series

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(ROOT, "..", "..", "03_数据", "实测记录表.xlsx"))

INK = "12263A"
TEAL = "1B998B"
HEAD = PatternFill("solid", fgColor=INK)
SUB = PatternFill("solid", fgColor="E8F2F0")
INPUT = PatternFill("solid", fgColor="FFF7E6")
CALC = PatternFill("solid", fgColor="EEF2F6")
WHITE = Font(color="FFFFFF", bold=True, size=10, name="微软雅黑")
BODY = Font(size=10, name="微软雅黑")
BOLD = Font(size=10, name="微软雅黑", bold=True)
THIN = Side(style="thin", color="C9D2DE")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def title_row(ws, row, text, span=8):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(size=14, bold=True, name="微软雅黑", color=INK)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 28


def header_row(ws, row, headers, widths=None):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill = HEAD
        c.font = WHITE
        c.alignment = CENTER
        c.border = BOX
    ws.row_dimensions[row].height = 30
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def note(ws, row, text, span=8):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(size=9, name="微软雅黑", color="5B6B7F")
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 46


def build():
    wb = Workbook()

    # ---------------- 0 使用说明 ----------------
    ws = wb.active
    ws.title = "0-使用说明"
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "震感捕手 · 实测记录表", 6)
    ws["A2"] = "配套：行空板 K10 采集程序 main.py ｜ 分析脚本 analyze.py ｜ 作品文档"
    ws["A2"].font = Font(size=9, color="5B6B7F", name="微软雅黑")

    steps = [
        ("① 先跑通设备", "把 main.py 存到 K10，改 EXP / DIST_M / TRIAL / NOTE 四个参数；按 A 键记录，确认 /sd 下生成 CSV。"),
        ("② 做实验一", "在 0.2–2.0 m 之间取 10 个距离，每个距离重复 5 次；把每次的 PGA 填进「1-实验一」黄色格子。"),
        ("③ 做实验二", "同一距离（建议 0.60 m），分别垂直落球、水平敲击、45° 斜击，各 5 次；填「2-实验二」。"),
        ("④ 做实验三", "搭 3 个四层模型（无斜撑 / X 形斜撑 / 斜撑+顶部配重），轻敲顶部记录自由衰减；f0、ζ 用 analyze.py 算出后填入。"),
        ("⑤ 做盲测", "请同学把震源移到 3 个未知位置（0.5–1.8 m），你先用拟合式预测，再用卷尺量真值，填「4-盲测」。"),
        ("⑥ 替换文档图表", "把 03_数据/实测/ 下的 CSV 放好，运行 analyze.py 和 build_doc.py，作品文档里的数字与图会自动更新。"),
    ]
    r = 4
    for t, d in steps:
        ws.cell(row=r, column=1, value=t).font = BOLD
        ws.cell(row=r, column=1).alignment = LEFT
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        c = ws.cell(row=r, column=2, value=d)
        c.font = Font(size=9.5, name="微软雅黑", color="334155")
        c.alignment = LEFT
        ws.row_dimensions[r].height = 42
        r += 1

    ws.column_dimensions["A"].width = 16
    for col in "BCDEF":
        ws.column_dimensions[col].width = 16

    note(ws, r + 1, "填写规则：黄色=要填，灰色=自动算，不要改公式。每个数据都要保留原始 CSV，文件名与表格里的编号一一对应。", 6)
    note(ws, r + 2, "安全提示：钢球只从固定高度自由下落，不许对着人；搬桌子要两人；TF 卡插拔前先断电。", 6)

    # ---------------- 1 实验一 ----------------
    ws = wb.create_sheet("1-实验一_距离衰减")
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "实验一：振幅随震源距的衰减", 9)
    ws["A2"] = "介质："
    ws["B2"] = "木桌"
    ws["D2"] = "落球高度 h："
    ws["E2"] = "0.50 m"
    ws["G2"] = "日期："
    for c in ("A2", "D2", "G2"):
        ws[c].font = BOLD
        ws[c].alignment = Alignment(horizontal="right")
    for c in ("B2", "E2", "H2"):
        ws[c].fill = INPUT
        ws[c].border = BOX
    ws.merge_cells("H2:I2")
    header_row(ws, 4, ["距离 r (m)", "第1次 PGA (g)", "第2次", "第3次", "第4次", "第5次",
                       "平均 PGA (g)", "标准差", "变异系数 %"],
               [12, 14, 10, 10, 10, 10, 14, 10, 12])
    for i in range(10):
        row = 5 + i
        c1 = ws.cell(row=row, column=1, value=round(0.2 * (i + 1), 2))
        c1.border = BOX
        c1.alignment = CENTER
        c1.number_format = "0.0"
        for j in range(2, 7):
            c = ws.cell(row=row, column=j)
            c.fill = INPUT
            c.border = BOX
            c.alignment = CENTER
        ws.cell(row=row, column=7, value="=IF(COUNT(B%d:F%d)=0,\"\",AVERAGE(B%d:F%d))" % (row, row, row, row))
        ws.cell(row=row, column=8, value="=IF(COUNT(B%d:F%d)<2,\"\",STDEV(B%d:F%d))" % (row, row, row, row))
        ws.cell(row=row, column=9, value="=IFERROR(H%d/G%d*100,\"\")" % (row, row))
        for j in range(7, 10):
            c = ws.cell(row=row, column=j)
            c.fill = CALC
            c.border = BOX
            c.alignment = CENTER
            c.number_format = "0.000"

    note(ws, 16, "提示：同一距离的 5 次数据不要挑好看的，全部记录；若某次明显异常（比如球弹了两次），在原始 CSV 的 note 里写明原因。", 9)

    # 拟合区
    ws["A18"] = "幂律拟合  A = A0 · r^(-n)"
    ws["A18"].font = Font(size=11, bold=True, name="微软雅黑", color=TEAL)
    ws.merge_cells("A18:D18")
    rows = [
        ("衰减指数 n", "=IFERROR(-SLOPE(LN(G5:G14),LN(A5:A14)),\"\")", "0.000"),
        ("系数 A0 (g)", "=IFERROR(EXP(INTERCEPT(LN(G5:G14),LN(A5:A14))),\"\")", "0.000"),
        ("拟合优度 R²", "=IFERROR(RSQ(LN(G5:G14),LN(A5:A14)),\"\")", "0.000"),
        ("留一法平均误差 %", "见 analyze.py 输出", "0.0"),
    ]
    for k, (name, formula, fmt) in enumerate(rows):
        r = 19 + k
        ws.cell(row=r, column=1, value=name).font = BOLD
        ws.cell(row=r, column=1).border = BOX
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        c = ws.cell(row=r, column=3, value=formula)
        c.fill = CALC
        c.border = BOX
        c.alignment = CENTER
        c.number_format = fmt
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)

    note(ws, 24, "结论怎么写：n 接近 0.5 说明能量主要在二维面上摊开；n 越大，衰减越快。把 n 与真实地震波衰减规律做比较。", 9)

    # 散点图
    ch = ScatterChart()
    ch.title = "PGA - 距离"
    ch.x_axis.title = "r (m)"
    ch.y_axis.title = "PGA (g)"
    ch.height = 8
    ch.width = 13
    xref = Reference(ws, min_col=1, min_row=5, max_row=14)
    yref = Reference(ws, min_col=7, min_row=4, max_row=14)
    s = Series(yref, xref, title="实测均值")
    s.marker.symbol = "circle"
    s.marker.size = 7
    ch.series.append(s)
    ws.add_chart(ch, "A27")

    # ---------------- 2 实验二 ----------------
    ws = wb.create_sheet("2-实验二_振动方向")
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "实验二：振动方向与三轴分量", 8)
    ws["A2"] = "距离固定 0.60 m；每种方向重复 5 次"
    ws["A2"].font = Font(size=9, color="5B6B7F", name="微软雅黑")
    header_row(ws, 4, ["敲击方式", "次数", "X 轴 PGA (g)", "Y 轴 PGA (g)", "Z 轴 PGA (g)",
                       "水平分量 (g)", "方向角 θ (°)", "备注"],
               [16, 8, 14, 14, 14, 14, 14, 20])
    cases = [("垂直落球", "V"), ("水平敲击", "H"), ("45° 斜击", "D")]
    r = 5
    for name, key in cases:
        for k in range(1, 6):
            ws.cell(row=r, column=1, value=name if k == 1 else "")
            ws.cell(row=r, column=2, value=k)
            for j in (3, 4, 5):
                c = ws.cell(row=r, column=j)
                c.fill = INPUT
            ws.cell(row=r, column=6, value="=IF(COUNT(C%d:D%d)=0,\"\",SQRT(C%d^2+D%d^2))" % (r, r, r, r))
            ws.cell(row=r, column=7, value="=IFERROR(DEGREES(ATAN2(E%d,F%d)),\"\")" % (r, r))
            for j in range(3, 8):
                c = ws.cell(row=r, column=j)
                c.border = BOX
                c.alignment = CENTER
                c.number_format = "0.000"
            ws.cell(row=r, column=1).border = BOX
            ws.cell(row=r, column=2).border = BOX
            r += 1
    note(ws, 21, "判断标准：θ>70° 以垂直振动为主；θ<20° 以水平振动为主；θ≈45° 两个方向都有。与 P 波（垂直为主）、S 波（水平为主）作类比。", 8)

    # ---------------- 3 实验三 ----------------
    ws = wb.create_sheet("3-实验三_建筑共振")
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "实验三：三种建筑模型的固有频率与响应", 7)
    ws["A2"] = "模型：雪糕棒 + 热熔胶，四层，底板 12×12 cm；K10 平放楼顶，轻敲顶部后自由衰减"
    ws["A2"].font = Font(size=9, color="5B6B7F", name="微软雅黑")
    header_row(ws, 4, ["模型", "次数", "固有频率 f0 (Hz)", "阻尼比 ζ", "顶部 PGA (g)", "相对 A 的 PGA 变化 %", "现象记录"],
               [18, 8, 16, 12, 14, 18, 26])
    models = [("A 无斜撑", "A"), ("B X 形斜撑", "B"), ("C 斜撑+顶部配重", "C")]
    r = 5
    for name, key in models:
        for k in range(1, 6):
            ws.cell(row=r, column=1, value=name if k == 1 else "")
            ws.cell(row=r, column=2, value=k)
            for j in (3, 4, 5):
                c = ws.cell(row=r, column=j)
                c.fill = INPUT
                c.number_format = "0.000"
            ws.cell(row=r, column=6, value="=IFERROR((E%d/AVERAGE($E$5:$E$9)-1)*100,\"\")" % r)
            for j in range(1, 7):
                c = ws.cell(row=r, column=j)
                c.border = BOX
                c.alignment = CENTER
            r += 1
    ws.cell(row=r + 1, column=1, value="三种模型均值").font = BOLD
    for j, col in ((3, "C"), (4, "D"), (5, "E")):
        c = ws.cell(row=r + 1, column=j, value="=IFERROR(AVERAGE(%s5:%s%d),\"\")" % (col, col, r - 1))
        c.number_format = "0.000"
        c.border = BOX
        c.fill = CALC
    note(ws, r + 3, "讨论：斜撑让 f0 变大（更刚），配重让 f0 变小但 ζ 变大（更阻尼）。顶部 PGA 谁最小？为什么不是“越刚越好”？", 7)

    # ---------------- 4 盲测 ----------------
    ws = wb.create_sheet("4-盲测")
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "盲测：用模型反推震源距离", 6)
    ws["A2"] = "先预测、后量真值。预测式：r = (A0 / A)^(1/n)，A0 与 n 取「1-实验一」的拟合结果。"
    ws["A2"].font = Font(size=9, color="5B6B7F", name="微软雅黑")
    header_row(ws, 4, ["编号", "测得 PGA (g)", "预测距离 (m)", "真实距离 (m)", "绝对误差 (m)", "相对误差 %"],
               [10, 16, 16, 16, 14, 14])
    for i in range(1, 4):
        rr = 4 + i
        ws.cell(row=rr, column=1, value="u%d" % i)
        ws.cell(row=rr, column=2).fill = INPUT
        ws.cell(row=rr, column=3, value="=IFERROR(('1-实验一_距离衰减'!C20/B%d)^(1/'1-实验一_距离衰减'!C19),\"\")" % rr)
        ws.cell(row=rr, column=4).fill = INPUT
        ws.cell(row=rr, column=5, value="=IFERROR(ABS(C%d-D%d),\"\")" % (rr, rr))
        ws.cell(row=rr, column=6, value="=IFERROR(E%d/D%d*100,\"\")" % (rr, rr))
        for j in range(1, 7):
            c = ws.cell(row=rr, column=j)
            c.border = BOX
            c.alignment = CENTER
            c.number_format = "0.000"
    ws.cell(row=8, column=1, value="平均绝对误差 %").font = BOLD
    c = ws.cell(row=8, column=2, value="=IFERROR(AVERAGE(F5:F7),\"\")")
    c.number_format = "0.0"
    c.fill = CALC
    c.border = BOX
    note(ws, 10, "反思：哪个距离误差最大？是“模型不对”还是“信号太弱、噪声占比高”？把原因写进作品文档的误差分析。", 6)

    # ---------------- 5 台账 ----------------
    ws = wb.create_sheet("5-原始数据台账")
    ws.sheet_view.showGridLines = False
    title_row(ws, 1, "原始数据台账（从 K10 的 events.csv 直接粘贴）", 9)
    cols = ["exp", "dist_m", "trial", "fs", "pga_g", "f_hz", "dur_ms", "note", "file"]
    header_row(ws, 3, cols, [8, 10, 8, 8, 10, 10, 10, 16, 28])
    ws.freeze_panes = "A4"
    note(ws, 5, "每次记录 K10 都会往 events.csv 追加一行；实验结束把整张表复制过来，作为数据溯源的凭证。", 9)

    wb.save(OUT)
    print("已生成：", OUT)


if __name__ == "__main__":
    build()
