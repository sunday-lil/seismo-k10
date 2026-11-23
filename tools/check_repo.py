# -*- coding: utf-8 -*-
"""
仓库静态自检：不联网、不编译，只查“能查出来的错”。

    python tools/check_repo.py

检查项：
  1. C++ 括号平衡（逐行扫描，跳过字符串与注释）
  2. Python 语法（py_compile）
  3. 文档里引用的路径是否存在
  4. 明显的过期引用（24 页 / galaxy / 06_遥测 等）
  5. 必需文件是否齐全
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []
WARNS = []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNS.append(msg)


# ---------- 1. C++ 括号 ----------
def scan_braces(path):
    depth = 0
    in_raw = False
    in_block = False
    for i, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        t = line
        if in_block:
            if "*/" in t:
                in_block = False
                t = t.split("*/", 1)[1]
            else:
                continue
        if in_raw:
            if ')HTML"' in t:
                in_raw = False
            continue
        if 'R"HTML(' in t:
            after = t.split('R"HTML(', 1)[1]
            if ')HTML"' not in after:
                in_raw = True
            t = t.split('R"HTML(', 1)[0]
        if "/*" in t:
            head, rest = t.split("/*", 1)
            if "*/" in rest:
                t = head + rest.split("*/", 1)[1]
            else:
                t = head
                in_block = True
        t = t.split("//")[0]
        t = re.sub(r'"(\\.|[^"\\])*"', '""', t)
        t = re.sub(r"'(\\.|[^'\\])'", "''", t)
        depth += t.count("{") - t.count("}")
        if depth < 0:
            err("%s:%d 右括号多余" % (path, i))
            return
    if depth != 0:
        err("%s 括号不平衡（差 %d）" % (path, depth))


# ---------- 2. Python 语法 ----------
def check_python(path):
    r = subprocess.run([sys.executable, "-m", "py_compile", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        err("%s 语法错误：%s" % (path, r.stderr.strip().split("\n")[-1]))


# ---------- 3. 文档里的路径 ----------
LINK = re.compile(r"`([^`\s]+\.(?:py|cpp|md|json|pdf|docx|zip|png|jpg))`")


def check_links(path):
    base = os.path.dirname(path)
    text = open(path, encoding="utf-8", errors="ignore").read()
    for m in LINK.finditer(text):
        target = m.group(1)
        if target.startswith(("http", "/", "S:")) or "%" in target or "*" in target or "/" not in target:
            continue
        if not (os.path.exists(os.path.join(base, target)) or
                os.path.exists(os.path.join(ROOT, target))):
            warn("%s 引用了不存在的文件：%s" % (os.path.relpath(path, ROOT), target))


# ---------- 4. 过期引用 ----------
STALE = ["galaxy/", "06_遥测", "K10端/main.cpp", "24 页", "震感捕手_源码与数据.zip.bak"]


def check_stale(path):
    if path.endswith("CHANGELOG.md"):
        return
    text = open(path, encoding="utf-8", errors="ignore").read()
    for s in STALE:
        if s in text:
            warn("%s 含过期引用：%s" % (os.path.relpath(path, ROOT), s))


# ---------- 5. 必需文件 ----------
REQUIRED = [
    "README.md", "STATUS.md", "CHANGELOG.md",
    "普通/02_代码/K10端/normal/v0/main.cpp",
    "普通/01_作品文档/震感捕手_科学教育实践案例.docx",
    "普通/01_作品文档/震感捕手_科学教育实践案例.pdf",
    "普通/06_教学包/震感捕手_教学实施包.pdf",
    "web/02_代码/v0/main_web.cpp",
]


def main():
    cpps = []
    pys = []
    mds = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules", ".gradle", "build")]
        for f in files:
            p = os.path.join(base, f)
            if f.endswith(".cpp"):
                cpps.append(p)
            elif f.endswith(".py"):
                pys.append(p)
            elif f.endswith(".md"):
                mds.append(p)

    for p in cpps:
        scan_braces(p)
    for p in pys:
        check_python(p)
    for p in mds:
        check_links(p)
        check_stale(p)
    for rel in REQUIRED:
        if not os.path.exists(os.path.join(ROOT, rel)):
            err("缺少必需文件：%s" % rel)

    print("检查 %d 个 C++ / %d 个 Python / %d 个 Markdown" % (len(cpps), len(pys), len(mds)))
    for w in WARNS:
        print("  [warn] " + w)
    for e in ERRORS:
        print("  [FAIL] " + e)
    if ERRORS:
        sys.exit(1)
    print("通过：无硬错误")


if __name__ == "__main__":
    main()
