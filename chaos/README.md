# 双摆混沌（chaos）

在行空板 K10 上同时积分两个双摆，初值只差 1e-6 rad，实时画相图、估李雅普诺夫指数。

## 结论

| 量 | 值 |
|---|---|
| 李雅普诺夫指数 λ | 0.93 /s |
| 可预报时长（Δ=0.001 rad） | 1.9 s |
| 可预报时长（Δ=0.5 rad） | 7.9 s |
| 7 秒内距离放大 | 约 60 万倍 |

## 目录

```
01_作品文档/选题说明.md
02_代码/K10端/main_chaos.cpp   实时积分 + 相图 + λ 估计
02_代码/分析端/sim_chaos.py     数值实验与三张图
03_数据/  divergence.csv / predict_horizon.csv / metrics.json
04_图片/  fig1_divergence / fig2_phase / fig3_horizon
05_发布/  发帖正文.md
```

## 跑一遍

```bash
python 02_代码/分析端/sim_chaos.py
```

## 许可

代码 MIT，文档 CC BY-NC-SA 4.0。
