# -*- coding: utf-8 -*-
"""生成《震感捕手 · 教学实施包》docx"""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "震感捕手_教学实施包.docx")
GREEN = RGBColor(0x1B, 0x99, 0x8B)
DARK = RGBColor(0x1F, 0x2A, 0x37)
GREY = RGBColor(0x55, 0x60, 0x70)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(2.0)

st = doc.styles["Normal"]
st.font.name = "微软雅黑"
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_after = Pt(6)


def h(text, size=16, color=GREEN, before=14, after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    return p


def para(text, size=10.5, color=DARK, bold=False, indent=True):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0.74) if indent else Cm(0)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.bold = bold
    return p


def bullet(text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.size = Pt(size)
    return p


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def table(headers, rows, widths=None, font=9.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, x in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(x)
        r.bold = True
        r.font.size = Pt(font)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(hdr[i], "1B998B")
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(x))
            r.font.size = Pt(font)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ================= 封面 =================
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(90)
r = p.add_run("震感捕手")
r.bold = True
r.font.size = Pt(34)
r.font.color.rgb = GREEN

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("教学实施包")
r.font.size = Pt(22)
r.font.color.rgb = DARK

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(30)
r = p.add_run("三课时教案 · 学生学案 · 评价量表 · 复刻清单")
r.font.size = Pt(12)
r.font.color.rgb = GREY

doc.add_page_break()

# ================= 一、课程定位 =================
h("一、课程定位")
para("本案例面向初中 7–9 年级，用一块行空板 K10 和一张课桌，把"
     "“地震波为什么传得远就弱”“怎么从振幅反推距离”这两个问题，"
     "做成学生可以亲手测量、亲手拟合的探究活动。")

h("1.1 对应课标", size=12, before=8)
table(
    ["课标领域", "要求", "本案例的落点"],
    [
        ["物质科学", "理解振动与波的基本特征", "用三轴加速度计记录振动，观察振幅随距离衰减"],
        ["科学探究", "能提出问题、设计实验、处理数据", "控制变量：落球高度、桌面、测点朝向"],
        ["跨学科", "数学与科学的结合", "对数坐标、幂律拟合、留一验证"],
        ["信息科技", "用程序采集与处理数据", "C++ 采集 + Python 分析与出图"],
    ],
    widths=[3.2, 6.0, 8.0],
)

h("1.2 三个核心概念", size=12, before=8)
bullet("振动与波：波形图上一串上下起伏，就是质点随时间的位移")
bullet("衰减：能量摊在越来越大的面上，振幅随距离下降，呈幂律")
bullet("模型与误差：用 10 个点拟合一条曲线，再看它能不能预测第 11 个点")

# ================= 二、教案 =================
doc.add_page_break()
h("二、三课时教案")

h("第 1 课时　问题从哪里来（45 分钟）", size=12, before=8)
table(
    ["时间", "环节", "教师做什么", "学生做什么"],
    [
        ["0–8", "情境", "播地震疏散演练视频，问“为什么二楼晃得比一楼凶”", "自由发言，写下自己的猜测"],
        ["8–20", "聚焦", "把问题收敛成“振幅怎么随距离变”", "小组讨论，提出可测量的量"],
        ["20–32", "装置", "展示 K10 与落球装置，演示一次记录", "观察屏幕：波形、峰值、主频"],
        ["32–42", "设计", "引导控制变量：哪些必须一样？", "每组写出 3 条控制变量"],
        ["42–45", "作业", "布置：预测 1 m 处的峰值是 0.2 m 处的几分之一", "写下预测值与理由"],
    ],
    widths=[1.8, 2.4, 7.0, 6.4],
)

h("第 2 课时　动手测（45 分钟）", size=12, before=8)
table(
    ["时间", "环节", "教师做什么", "学生做什么"],
    [
        ["0–5", "复习", "回顾控制变量清单", "复述本组的三条控制变量"],
        ["5–15", "示范", "演示上电、校准、按 A 记录、读卡", "一人操作，一人记录，一人计时"],
        ["15–35", "测量", "巡视，纠正“移动测点时碰桌子”", "0.2–2.0 m 共 10 档，每档 5 次"],
        ["35–42", "初看", "把各组数据抄到黑板", "看组间差异，讨论哪里没控住"],
        ["42–45", "整理", "布置数据交给课代表汇总", "导出 CSV，命名规范"],
    ],
    widths=[1.8, 2.4, 7.0, 6.4],
)

h("第 3 课时　数据说话（45 分钟）", size=12, before=8)
table(
    ["时间", "环节", "教师做什么", "学生做什么"],
    [
        ["0–10", "作图", "演示对数坐标怎么画", "用表格或脚本画 A–r 散点"],
        ["10–22", "拟合", "讲幂律 A = A0·r^(−n)，演示拟合", "求自己组的 n，与别组比较"],
        ["22–32", "盲测", "给出 3 个未知距离，让学生用曲线反推", "算出预测距离与误差"],
        ["32–40", "讨论", "为什么远处误差大？", "从“信号小、噪声占比大”角度解释"],
        ["40–45", "总结", "归纳：模型能做什么、不能做什么", "写 100 字结论"],
    ],
    widths=[1.8, 2.4, 7.0, 6.4],
)

# ================= 三、学案 =================
doc.add_page_break()
h("三、学生学案")
para("姓名：____________　　班级：____________　　组别：____________")

h("3.1 我的预测（第 1 课时）", size=12, before=8)
para("如果 0.2 m 处的峰值是 A，那么 1.0 m 处的峰值大约是 ______ A。")
para("理由：____________________________________________________________")

h("3.2 数据记录表（第 2 课时）", size=12, before=8)
table(
    ["距离 r (m)", "第 1 次", "第 2 次", "第 3 次", "第 4 次", "第 5 次", "平均 PGA (g)"],
    [[f"{d:.1f}", "", "", "", "", "", ""] for d in [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]],
    widths=[2.4, 1.9, 1.9, 1.9, 1.9, 1.9, 2.6],
)

h("3.3 分析与结论（第 3 课时）", size=12, before=8)
para("我拟合出的指数 n = ________，A0 = ________")
para("盲测三个未知距离，预测值分别是：________、________、________")
para("与真实值相比，平均误差 ________%")
para("结论（100 字）：____________________________________________________")

# ================= 四、评价量表 =================
doc.add_page_break()
h("四、评价量表")
para("四个维度，每维 4 级。建议教师评 + 自评 + 组间互评各占三分之一。")

table(
    ["维度", "4 级（优秀）", "3 级（良好）", "2 级（合格）", "1 级（待改进）"],
    [
        ["提出问题",
         "能自己把现象转成可测量的问题，并说明为什么这样转",
         "在提示下能转成可测量的问题",
         "能复述老师给出的问题",
         "停留在“好玩/厉害”的描述"],
        ["实验设计",
         "主动列出控制变量，并解释每条的作用",
         "能列出控制变量，解释不完整",
         "在清单提示下完成",
         "变量混乱，数据无法比较"],
        ["数据处理",
         "会用对数坐标与拟合，能说明 R² 的含义",
         "会算平均与作图，拟合需帮助",
         "能填表、能画散点",
         "数据缺失或记错"],
        ["解释与反思",
         "能指出模型局限（边界反射、采样率），并提出改进",
         "能说出一个局限",
         "能复述老师总结的局限",
         "认为模型“就是对的”"],
    ],
    widths=[2.6, 4.6, 4.0, 3.6, 3.4],
    font=9,
)

# ================= 五、复刻清单 =================
doc.add_page_break()
h("五、复刻清单（一页版）")

h("5.1 物料", size=12, before=8)
table(
    ["名称", "规格", "数量", "参考价"],
    [
        ["行空板 K10", "DFR0992-EN", "1", "¥299"],
        ["钢球", "直径 20 mm", "1", "¥3"],
        ["纸筒 / PVC 管", "内径 25 mm，长 500 mm", "1", "¥5"],
        ["钢片", "100×60×2 mm", "1", "¥5"],
        ["卷尺", "3 m", "1", "¥8"],
        ["TF 卡", "8 GB 以上，FAT32", "1", "¥15"],
        ["长桌", "≥2.2 m，或两张课桌拼接", "1", "—"],
    ],
    widths=[4.2, 8.0, 1.6, 2.4],
)

h("5.2 关键参数", size=12, before=8)
table(
    ["参数", "值", "在哪改"],
    [
        ["采样率", "200 Hz", "main.cpp 的 FS_HZ"],
        ["触发阈值", "0.05 g", "TRIG_G"],
        ["记录长度", "触发前 1 s + 后 4 s", "PRE_S / POST_S"],
        ["报警阈值", "0.25 g（屏幕变红）", "ALARM_G"],
        ["实验编号", "E1", "EXP_ID"],
        ["测点距离", "0.60 m", "DIST_M"],
    ],
    widths=[4.0, 6.4, 6.0],
)

h("5.3 30 分钟上手", size=12, before=8)
bullet("① 把 main.cpp 粘进 Mind+ 代码模式，板型选行空板 K10，上传（约 30 秒）")
bullet("② 插 TF 卡，上电，屏幕出现“启动中 → 监测中”，静置 10 秒")
bullet("③ 按 A 键，屏幕变“等待触发”，从纸筒丢下钢球")
bullet("④ 4 秒后显示峰值、主频、时长；数据在卡里 S:/E1_d060_t1.csv")
bullet("⑤ 换一个测点，改 DIST_M 后重烧，或直接按 A 再测一次")

h("5.4 我们踩过的坑", size=12, before=8)
table(
    ["现象", "原因", "解决"],
    [
        ["PGA 一直是 1.936 g", "板子平放时 Z 轴约 −936 mg，没减基线就直接取绝对值", "上电先做 0.5 s 基线校准"],
        ["数据写不进卡", "路径写成 /sdcard/", "K10 的 TF 卡挂载点是 S:/"],
        ["串口看不到输出", "波特率用了 9600", "改成 115200"],
        ["波形在屏幕上出框", "横轴 240 px 放了 240×5 个点", "按窗口宽度抽稀后再画"],
        ["两次测量差很多", "移动测点时碰了桌子", "测点画框，每次放回同一点"],
    ],
    widths=[4.6, 6.4, 5.4],
)

# ================= 六、FAQ =================
h("六、常见问题")
qa = [
    ("没有 TF 卡能用吗？",
     "能。没插卡时同一段 CSV 会从 USB 串口整块输出，电脑端用 serial_capture.py 接住并落盘。"),
    ("没有钢球怎么办？",
     "用一元硬币或小螺丝代替，但每次必须从同一高度落下，否则能量不可比。"),
    ("桌子不够长？",
     "把 0.2–2.0 m 改成 0.1–1.0 m，结论方向不变，只是衰减指数会偏小。"),
    ("数据一定要 5 次吗？",
     "3 次也能做，但误差棒会明显变大，讨论时要说明样本量偏小。"),
    ("为什么不用手机测？",
     "手机采样率不稳、时间戳不连续；K10 的 200 Hz 是硬定时，能拿到等间隔序列。"),
]
for q, a in qa:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    r = p.add_run("Q：" + q)
    r.bold = True
    r.font.size = Pt(10.5)
    r.font.color.rgb = GREEN
    para("A：" + a, indent=False)

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("本实施包随《震感捕手 · 科学教育实践案例》一同发布，代码 MIT，文档 CC BY-NC-SA 4.0。")
r.font.size = Pt(8.5)
r.font.color.rgb = GREY

doc.save(OUT)
print("saved", OUT)
