# 教室混响 T60（reverb）

拍一次手，用行空板 K10 采集余响，Schroeder 反向积分拟合出混响时间 T60。

## 结论

| 房间 | Sabine 预测 | 实测 T60 | 偏差 |
|---|---:|---:|---:|
| 小教室 | 0.64 s | 0.55 s | +16.9% |
| 普通教室 | 1.00 s | 1.16 s | −13.7% |
| 大教室/礼堂 | 2.38 s | 2.60 s | −8.8% |

公式只是估计，验收必须实测。

## 目录

```
01_作品文档/选题说明.md
02_代码/K10端/main_reverb.cpp
02_代码/分析端/sim_reverb.py
03_数据/  ir_*.csv / rooms.csv / metrics.json
04_图片/  fig1_ir / fig2_schroeder / fig3_sabine
05_发布/  发帖正文.md
```

## 跑一遍

```bash
python 02_代码/分析端/sim_reverb.py
```

## 许可

代码 MIT，文档 CC BY-NC-SA 4.0。
