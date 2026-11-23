# -*- coding: utf-8 -*-
"""
生成《震感捕手 · 科学教育实践案例》Word 文档。
读取 03_数据/分析结果/metrics.json 与 04_图片/*.png，自动把数字和图表写进文档。
重新跑一次 analyze.py 再跑本脚本，即可用实测数据刷新全文。
"""
import os
import re
import sys

# 控制台编码兜底
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from doc_content import build_blocks

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(ROOT, "..", ".."))
IMG = os.path.join(PROJ, "04_图片")
OUT = os.path.join(PROJ, "01_作品文档", "震感捕手_科学教育实践案例.docx")

INK = RGBColor(0x12, 0x26, 0x3A)
TEAL = RGBColor(0x1B, 0x99, 0x8B)
MUTED = RGBColor(0x5B, 0x6B, 0x7F)
CORAL = RGBColor(0xE7, 0x6F, 0x51)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT_CN = "微软雅黑"
FONT_BODY = "宋体"
FONT_MONO = "Consolas"


# ------------------------------------------------------------------
# 基础工具
# ------------------------------------------------------------------
def set_run_font(run, name=FONT_BODY, size=10.5, bold=None, color=None, italic=None):
    run.font.name = name
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)


def add_rich(par, text, size=10.5, color=None, font=FONT_BODY):
    """支持 **粗体** 与 `代码` 两种行内标记。"""
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            r = par.add_run(part[2:-2])
            set_run_font(r, font, size, bold=True, color=color)
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            r = par.add_run(part[1:-1])
            set_run_font(r, FONT_MONO, size - 0.8, color=RGBColor(0x0B, 0x5A, 0x7A))
        else:
            r = par.add_run(part)
            set_run_font(r, font, size, color=color)
    return par


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def cell_margins(table, top=60, bottom=60, left=90, right=90):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement("w:" + side)
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def table_borders(table, color="D5DDE5", size=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def no_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tblPr.append(borders)


def left_accent(cell, color="1B998B", size=24):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    el = OxmlElement("w:left")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:color"), color)
    borders.append(el)
    tcPr.append(borders)


def keep_row(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    trPr.append(el)


def add_field(par, instr):
    r = par.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    r._r.append(fld_begin)
    r2 = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r2._r.append(it)
    r3 = par.add_run()
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    r3._r.append(fld_sep)
    r4 = par.add_run("1")
    r5 = par.add_run()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r5._r.append(fld_end)


# ------------------------------------------------------------------
# 文档环境
# ------------------------------------------------------------------
def setup_document():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.1)
    sec.bottom_margin = Cm(1.9)
    sec.left_margin = Cm(2.3)
    sec.right_margin = Cm(2.1)
    sec.header_distance = Cm(1.1)
    sec.footer_distance = Cm(1.0)

    normal = doc.styles["Normal"]
    normal.font.name = FONT_BODY
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    pf = normal.paragraph_format
    pf.line_spacing = 1.55
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)
    pf.first_line_indent = Cm(0.74)

    # 一级标题
    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT_CN
    h1.font.size = Pt(17)
    h1.font.bold = True
    h1.font.color.rgb = INK
    h1._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h1.paragraph_format.space_before = Pt(20)
    h1.paragraph_format.space_after = Pt(10)
    h1.paragraph_format.line_spacing = 1.2
    h1.paragraph_format.first_line_indent = Cm(0)
    h1.paragraph_format.keep_with_next = True
    pPr = h1._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), "1B998B")
    pBdr.append(bottom)
    pPr.append(pBdr)

    h2 = doc.styles["Heading 2"]
    h2.font.name = FONT_CN
    h2.font.size = Pt(13)
    h2.font.bold = True
    h2.font.color.rgb = TEAL
    h2._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(6)
    h2.paragraph_format.first_line_indent = Cm(0)
    h2.paragraph_format.keep_with_next = True

    h3 = doc.styles["Heading 3"]
    h3.font.name = FONT_CN
    h3.font.size = Pt(11)
    h3.font.bold = True
    h3.font.color.rgb = INK
    h3._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_CN)
    h3.paragraph_format.space_before = Pt(8)
    h3.paragraph_format.space_after = Pt(4)
    h3.paragraph_format.first_line_indent = Cm(0)
    h3.paragraph_format.keep_with_next = True

    # 页眉页脚
    header = sec.header
    hp = header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = hp.add_run("震感捕手  ·  科学教育“做中学”实践案例")
    set_run_font(r, FONT_CN, 8, color=MUTED)
    pPr = hp._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D5DDE5")
    pBdr.append(bottom)
    pPr.append(pBdr)

    footer = sec.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("— ")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)
    add_field(fp, " PAGE ")
    r = fp.add_run(" —")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)
    return doc


# ------------------------------------------------------------------
# 块渲染
# ------------------------------------------------------------------
def render(doc, blocks):
    for b in blocks:
        kind = b[0]

        if kind == "h1":
            doc.add_paragraph(b[1], style="Heading 1")
        elif kind == "h1pb":
            p = doc.add_paragraph(b[1], style="Heading 1")
            p.paragraph_format.page_break_before = True
        elif kind == "h2":
            doc.add_paragraph(b[1], style="Heading 2")
        elif kind == "h3":
            doc.add_paragraph(b[1], style="Heading 3")

        elif kind == "p":
            p = doc.add_paragraph()
            add_rich(p, b[1])
        elif kind == "lead":
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(8)
            add_rich(p, b[1], size=11, color=RGBColor(0x2A, 0x3B, 0x50))
        elif kind == "bullets":
            for item in b[1]:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.90)
                p.paragraph_format.first_line_indent = Cm(-0.45)
                p.paragraph_format.line_spacing = 1.45
                p.paragraph_format.space_after = Pt(3)
                add_rich(p, "•  " + item)

        elif kind == "fig":
            path, width, caption = b[1]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(os.path.join(IMG, path), width=Cm(width))
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.first_line_indent = Cm(0)
            cap.paragraph_format.space_after = Pt(10)
            add_rich(cap, caption, size=9, color=MUTED)

        elif kind == "table":
            headers, rows, widths = b[1]
            t = doc.add_table(rows=1, cols=len(headers))
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            t.autofit = False
            table_borders(t)
            cell_margins(t)
            hdr = t.rows[0]
            keep_row(hdr)
            trPr = hdr._tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader")
            trPr.append(th)
            for i, h in enumerate(headers):
                c = hdr.cells[i]
                c.width = Cm(widths[i])
                shade(c, "12263A")
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.15
                add_rich(p, h, size=9, color=WHITE)
            for row in rows:
                tr = t.add_row()
                keep_row(tr)
                for i, val in enumerate(row):
                    c = tr.cells[i]
                    c.width = Cm(widths[i])
                    p = c.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (i == 0 or len(str(val)) > 10)                         else WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.space_after = Pt(0)
                    p.paragraph_format.line_spacing = 1.2
                    add_rich(p, str(val), size=8.6)
            # 小表尽量整张不跨页；大表允许分页（表头会重复）
            if len(rows) <= 8:
                for tr in t.rows[:-1]:
                    for c in tr.cells:
                        for p in c.paragraphs:
                            p.paragraph_format.keep_with_next = True
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_after = Pt(2)
            spacer.paragraph_format.line_spacing = 0.6

        elif kind == "kpi":
            items = b[1]
            t = doc.add_table(rows=2, cols=len(items))
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            table_borders(t, "FFFFFF", 8)
            cell_margins(t, 130, 90, 50, 50)
            for i, (num, label) in enumerate(items):
                c = t.cell(0, i)
                c.width = Cm(4.1)
                shade(c, "F4F7FA")
                p = c.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                add_rich(p, "**" + num + "**", size=19, color=TEAL)
                c2 = t.cell(1, i)
                c2.width = Cm(4.1)
                shade(c2, "F4F7FA")
                p2 = c2.paragraphs[0]
                p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p2.paragraph_format.first_line_indent = Cm(0)
                p2.paragraph_format.space_after = Pt(0)
                p2.paragraph_format.line_spacing = 1.0
                add_rich(p2, label, size=8.5, color=MUTED)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

        elif kind == "callout":
            title, text = b[1]
            lines = [title] + text.split(chr(10))
            n = len(lines)
            for i, line in enumerate(lines):
                p = doc.add_paragraph()
                pf = p.paragraph_format
                pf.first_line_indent = Cm(0)
                pf.left_indent = Cm(0.58)
                pf.right_indent = Cm(0.12)
                pf.space_before = Pt(10 if i == 0 else 0)
                pf.space_after = Pt(11 if i == n - 1 else 2)
                pf.line_spacing = 1.35
                pf.keep_together = True
                if i < n - 1:
                    pf.keep_with_next = True
                pPr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "F1F8F6")
                pPr.append(shd)
                pBdr = OxmlElement("w:pBdr")
                left = OxmlElement("w:left")
                left.set(qn("w:val"), "single")
                left.set(qn("w:sz"), "24")
                left.set(qn("w:space"), "8")
                left.set(qn("w:color"), "1B998B")
                pBdr.append(left)
                pPr.append(pBdr)
                add_rich(p, line, size=9.2, color=TEAL if i == 0 else None)

        elif kind == "code":
            title, code = b[1]
            if title:
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.keep_with_next = True
                add_rich(p, title, size=9, color=MUTED)
            t = doc.add_table(rows=1, cols=1)
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            keep_row(t.rows[0])
            table_borders(t, "E2E8F0", 4)
            cell_margins(t, 80, 80, 120, 100)
            c = t.rows[0].cells[0]
            shade(c, "F7F9FC")
            p = c.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            lines = code.strip("\n").split("\n")
            for i, line in enumerate(lines):
                if i:
                    p.add_run().add_break()
                r = p.add_run(line if line else " ")
                set_run_font(r, FONT_MONO, 8.2, color=RGBColor(0x1F, 0x2A, 0x37))
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

        elif kind == "pagebreak":
            doc.add_page_break()

        elif kind == "spacer":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(b[1] if len(b) > 1 else 6)


# ------------------------------------------------------------------
# 封面
# ------------------------------------------------------------------
def cover(doc, M):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.first_line_indent = Cm(0)
    add_rich(p, "DF 创客社区  ·  “做中学·探未来”科学教育实践案例征集", size=9.5, color=MUTED)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(26)
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("震感捕手")
    set_run_font(r, FONT_CN, 40, bold=True, color=INK)

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("用一块行空板 K10，把“看不见的震动”变成可读的数据")
    set_run_font(r, FONT_CN, 14, color=TEAL)

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(2)
    r = p.add_run("模拟地震波传播 · 振动方向识别 · 建筑共振 · 盲测定位")
    set_run_font(r, FONT_CN, 8.5, color=MUTED)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(10)
    p.add_run().add_picture(os.path.join(IMG, "fig0_横幅.png"), width=Cm(15.2))

    info = [
        ("作品方向", "地球奥秘（模拟地震波探测）"),
        ("适用学段", "初中 7–9 年级"),
        ("核心硬件", "行空板 K10（DFR0992-EN）"),
        ("编程环境", "Arduino IDE / PlatformIO（C++）；分析端 Python 3"),
        ("建议课时", "3 课时（原理 1 + 实验 1 + 分析发布 1）"),
        ("材料成本", "约 380 元/套（含 K10 与 TF 卡）"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t, "E2E8F0", 4)
    cell_margins(t, 70, 70, 100, 100)
    for k, v in info:
        row = t.add_row()
        c0, c1 = row.cells
        c0.width = Cm(3.2)
        c1.width = Cm(11.6)
        shade(c0, "F5F7FA")
        p0 = c0.paragraphs[0]
        p0.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.space_after = Pt(0)
        add_rich(p0, k, size=8.6, color=MUTED)
        p1 = c1.paragraphs[0]
        p1.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.space_after = Pt(0)
        add_rich(p1, v, size=8.6)

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_before = Pt(14)
    add_rich(p, "作者 / 学校：______________________　　指导教师：______________________",
             size=9, color=MUTED)
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    add_rich(p, "版本：v1.0　|　2026 年 11 月", size=9, color=MUTED)
    doc.add_page_break()



# ------------------------------------------------------------------
# OOXML 子元素顺序规范化（Word 对顺序敏感，LibreOffice 较宽松）
# ------------------------------------------------------------------
_ORDER = {
    "w:pPr": ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
              "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
              "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
              "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
              "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
              "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
              "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr",
              "w:sectPr", "w:pPrChange"],
    "w:tcPr": ["w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge", "w:tcBorders",
               "w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign",
               "w:hideMark", "w:headers", "w:cellIns", "w:cellDel", "w:cellMerge", "w:tcPrChange"],
    "w:tblPr": ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual", "w:tblStyleRowBandSize",
                "w:tblStyleColBandSize", "w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd",
                "w:tblBorders", "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook",
                "w:tblCaption", "w:tblDescription", "w:tblPrChange"],
    "w:trPr": ["w:cnfStyle", "w:divId", "w:gridBefore", "w:gridAfter", "w:wBefore", "w:wAfter",
               "w:cantSplit", "w:trHeight", "w:tblHeader", "w:tblCellSpacing", "w:jc",
               "w:hidden", "w:ins", "w:del", "w:trPrChange"],
}


_ORDER_NS = {qn(k): [qn(t) for t in v] for k, v in _ORDER.items()}


def normalize_order(doc):
    fixed = 0
    for el in doc.element.body.iter():
        seq = _ORDER_NS.get(el.tag)
        if not seq:
            continue
        kids = list(el)
        ranked = sorted(kids, key=lambda c: seq.index(c.tag) if c.tag in seq else len(seq))
        if [k.tag for k in ranked] != [k.tag for k in kids]:
            fixed += 1
        for c in ranked:
            el.append(c)
    # 页眉页脚同样处理
    for sec in doc.sections:
        for part in (sec.header, sec.footer):
            for el in part._element.iter():
                seq = _ORDER_NS.get(el.tag)
                if not seq:
                    continue
                kids = list(el)
                ranked = sorted(kids, key=lambda c: seq.index(c.tag) if c.tag in seq else len(seq))
                for c in ranked:
                    el.append(c)
    return fixed


# ------------------------------------------------------------------
def main():
    with open(os.path.join(PROJ, "03_数据", "分析结果", "metrics.json"), encoding="utf-8") as f:
        M = json.load(f)

    doc = setup_document()
    cp = doc.core_properties
    cp.title = "震感捕手：用行空板 K10 做模拟地震波探测"
    cp.subject = "科学教育“做中学”实践案例 · 地球方向 · 初中"
    cp.author = "DF创客社区 · 震感捕手项目组"
    cp.keywords = "行空板K10; SC7A20H; 地震波; 科学探究; 跨学科实践"
    cp.comments = "案例包：作品文档 + K10 程序 + 分析脚本 + 实测记录表 + 配图"
    cover(doc, M)
    render(doc, build_blocks(M))
    fixed = normalize_order(doc)
    doc.save(OUT)
    print("规范化 XML 顺序：", fixed, "处")
    print("已生成：", OUT)


if __name__ == "__main__":
    main()
