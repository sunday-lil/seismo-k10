# -*- coding: utf-8 -*-
"""
串口抓数：把 K10 从 USB 串口输出的 CSV 存成文件。

K10 端程序在 TF 卡不可写时，会把整段数据以
    ###BEGIN
    # exp=...
    t_ms,ax,ay,az
    ...
    ###END
的格式从串口发出来。本脚本负责接收并落盘。

用法：
    python serial_capture.py                 # 自动找串口
    python serial_capture.py --port COM7     # 指定串口
    python serial_capture.py --out ../03_数据/实测

依赖：pip install pyserial
"""
import os
import re
import time
import argparse

import serial
from serial.tools import list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.abspath(os.path.join(HERE, "..", "..", "03_数据", "实测"))


def pick_port(explicit=None):
    if explicit:
        return explicit
    cands = [p.device for p in list_ports.comports()
             if any(k in (p.description or "") for k in ("USB", "CP210", "CH340", "Serial"))]
    if len(cands) == 1:
        return cands[0]
    if not cands:
        raise SystemExit("没找到串口，请插好 USB 线，或用 --port 指定")
    print("发现多个串口：")
    for i, c in enumerate(cands):
        print("  [%d] %s" % (i, c))
    return cands[int(input("选择编号：").strip())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    port = pick_port(args.port)
    print("串口：", port, "  波特率：", args.baud)
    print("等待 K10 发来数据（按 A 键记录一次）... Ctrl+C 退出")

    ser = serial.Serial(port, args.baud, timeout=1)
    buf = []
    inside = False

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            if line == "###BEGIN":
                inside = True
                buf = []
                print("收到数据块，接收中...")
                continue
            if line == "###END":
                if not inside or len(buf) < 10:
                    print("数据块为空，忽略")
                    inside = False
                    continue
                inside = False
                meta = {}
                rows = []
                for ln in buf:
                    if ln.startswith("#"):
                        if "=" in ln:
                            k, v = ln[1:].split("=", 1)
                            meta[k.strip()] = v.strip()
                    elif ln.startswith("t_ms"):
                        continue
                    else:
                        rows.append(ln)
                exp = meta.get("exp", "E1")
                dist = int(round(float(meta.get("dist_m", 0)) * 100))
                trial = meta.get("trial", "1")
                name = "%s_d%03d_t%s.csv" % (exp, dist, trial)
                path = os.path.join(args.out, name)
                n = 1
                while os.path.exists(path):
                    path = os.path.join(args.out, "%s_d%03d_t%s_%d.csv" % (exp, dist, trial, n))
                    n += 1
                with open(path, "w", encoding="utf-8", newline="") as f:
                    for k, v in meta.items():
                        f.write("# %s=%s\n" % (k, v))
                    f.write("t_ms,ax,ay,az\n")
                    f.write("\n".join(rows) + "\n")
                print("已保存：", path, "（%d 行）" % len(rows))
                continue
            if inside:
                buf.append(line)
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
