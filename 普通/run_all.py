# -*- coding: utf-8 -*-
"""
一键入口：检查依赖 → 分析数据 → 生成 Word 文档。

双击根目录的“一键运行.bat”即可（bat 里只有 ASCII，避免中文编码问题）。
也可以直接运行：python run_all.py
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PY = sys.executable
ANALYZE = os.path.join(ROOT, "02_代码", "分析端", "analyze.py")
BUILD = os.path.join(ROOT, "02_代码", "分析端", "build_doc.py")
REQ = os.path.join(ROOT, "requirements.txt")


def say(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("gbk", "replace").decode("gbk"), flush=True)


def ensure_deps():
    need = ["numpy", "pandas", "scipy", "matplotlib", "docx", "openpyxl"]
    missing = []
    for m in need:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return True
    say("[提示] 缺少依赖：%s，正在安装……" % ", ".join(missing))
    r = subprocess.run([PY, "-m", "pip", "install", "-r", REQ])
    if r.returncode != 0:
        say("[错误] 依赖安装失败，请检查网络后重试。")
        return False
    return True


def run(script, label):
    say("")
    say(">>> %s" % label)
    r = subprocess.run([PY, script], cwd=ROOT)
    if r.returncode != 0:
        say("[错误] %s 失败，请把上面的报错发给我。" % label)
        return False
    return True


def main():
    say("=" * 42)
    say("  震感捕手：一键分析并生成作品文档")
    say("=" * 42)
    if not os.path.exists(ANALYZE):
        say("[错误] 找不到 02_代码/分析端/analyze.py，请确认文件完整。")
        return 1
    if not ensure_deps():
        return 1
    if not run(ANALYZE, "[1/2] 分析数据、生成图表"):
        return 1
    if not run(BUILD, "[2/2] 生成 Word 文档"):
        return 1
    say("")
    say("完成！")
    say("  文档：01_作品文档/震感捕手_科学教育实践案例.docx")
    say("  图片：04_图片/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
