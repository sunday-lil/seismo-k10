# 震感捕手 · 科学教育实践案例（地球奥秘 / 初中）

> 已发布：https://mc.dfrobot.com.cn/article-387097.html

> 用一块**行空板 K10**，把“看不见的震动”变成可读的数据：模拟地震波传播、识别振动方向、比较建筑共振、盲测震源距离。

这个文件夹是一套**可以直接改、直接跑、直接投稿**的完整案例包：作品文档、K10 程序、分析脚本、实测记录表、全部配图、发帖正文。

---

## 1. 五分钟看懂

| 你会得到 | 在哪里 |
| --- | --- |
| 27 页作品文档（DOCX + PDF，含 10 张图） | `01_作品文档/` |
| K10 采集程序（Arduino C++，触发 + 预触发 + CSV） | `02_代码/K10端/normal/v0/main.cpp` |
| 分析脚本（去重力 / PGA / FFT / 拟合 / 盲测） | `02_代码/分析端/analyze.py` |
| 学生用实测记录表（带公式） | `03_数据/实测记录表.xlsx` |
| 发帖正文（Markdown） | `05_发布/发帖正文.md` |
| 全部插图（320 dpi） | `04_图片/` |

**核心结论**：桌面振动振幅随距离呈幂律衰减 `A = 0.194·r^(−0.706)`（R² = 0.989）；三轴可分辨振动方向（86° / 10° / 46°）；斜撑使模型 f0 从 3.07 Hz 升到 5.78 Hz、顶部 PGA 下降 60%；三次盲测平均误差 7.9%。

---

## 2. 现在就能跑

```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 用示例数据跑一遍分析（不需要硬件）
python 02_代码/分析端/analyze.py
python 02_代码/分析端/build_doc.py
python 02_代码/分析端/make_figures.py
python 02_代码/分析端/make_xlsx.py
```

跑完会重新生成 `03_数据/分析结果/metrics.json`、`04_图片/*.png` 和那份 Word 文档。

**换成自己的实测数据**：把 K10 存下的 CSV 放进 `03_数据/实测/`，再运行一次 `analyze.py` 和 `build_doc.py` —— 文档里的数字、表格、图会全部自动更新（脚本会优先使用“实测”目录，没有才退回“示例数据”）。

---

## 3. 文件夹结构

```
普通/
├── 01_作品文档/
│   ├── 震感捕手_科学教育实践案例.docx      ← 主交付物（可编辑，27 页）
│   └── 震感捕手_科学教育实践案例.pdf       ← 同版 PDF，便于预览
├── 02_代码/
│   ├── K10端/README.md                     ← 两版索引
│   ├── K10端/normal/v0/main.cpp            ← 普通版：Arduino C++（比赛提交版）
│   ├── K10端/normal/v0/platformio.ini      ← PlatformIO 工程配置
│   └── 分析端/
│       ├── serial_capture.py               ← 串口抓数（没插卡时用）
│       ├── analyze.py                      ← 数据 → 指标 → 图表
│       ├── simulate_demo.py                ← 生成示例数据
│       ├── make_figures.py                 ← 封面/装置/原理/连线/界面/流程
│       ├── build_doc.py + doc_content.py    ← 数据 → Word 文档
│       └── make_xlsx.py                    ← 实测记录表
├── 03_数据/
│   ├── 实测记录表.xlsx                     ← 学生填写
│   ├── 示例数据/                           ← 89 个仿真 CSV（仅演示）
│   ├── 实测/                               ← 放你自己的 CSV（现在是空的）
│   └── 分析结果/metrics.json               ← 全部数字的唯一来源
├── 04_图片/                                ← 10 张插图 + 封面
├── 05_发布/
│   ├── 发帖正文.md                         ← 复制到 DF 社区即可
│   ├── 投稿检查清单.md
│   └── 图片/                               ← 帖子用图
├── 使用说明.md                             ← 先看这个（两条路线）
├── Mind+刷入说明.md                        ← 用 Mind+ 的话看这个
├── 上机操作卡.md                           ← 刷完之后照着做
├── 低配实验方案.md                         ← 场地/时间不够时的三套降级方案
├── 一键运行.bat / run.bat                   ← 双击：分析数据 + 重新生成文档
└── run_all.py                              ← 上面两个 bat 实际调用的脚本
```

---

## 4. 数据状态（重要）

`03_数据/示例数据/` 里的 89 个 CSV 是**物理模型仿真**生成的，用于验证分析流程和排版，**不是真实实验数据**。

文档第 2 页有一段醒目的“文档状态与替换说明”，第 3 章每张数据图的标题都标注了“示例数据”。投稿前请务必：

1. 用 K10 实测数据替换 `03_数据/实测/`；
2. 重跑 `analyze.py` + `build_doc.py`；
3. 补入实物照片和演示视频（`05_发布/投稿检查清单.md` 有拍摄清单）。

---

## 5. 硬件与软件

- **硬件**：行空板 K10（DFR0992-EN，ESP32-S3 + SC7A20H 三轴加速度计 + 2.8″ 屏 + TF 卡槽）
- **K10 端**：Arduino C++。Mind+ 代码模式（直接粘 `main.cpp`）、Arduino IDE 2.x + UNIHIKER K10 BSP、或 PlatformIO（`DFRobot/platform-unihiker`）
- **电脑端**：Python 3.10+，numpy / pandas / scipy / matplotlib / python-docx / openpyxl / pyserial

---

## 7. 遥测版（v1.1，独立目录）

同级目录 [`../web/`](../web/) 是遥测版：把 K10 变成 Web 服务器，手机连同一 WiFi 就能实时看波形、远程触发记录。它是独立的一套，不影响本目录。

```
K10 (200 Hz 采样 + WebServer)  ──HTTP/JSON──►  手机浏览器 / 配套 APK
```

- 接口：`/api/now`、`/api/wave`、`/api/record`、`/api/last`
- APK：`../web/02_代码/android/`（WebView 壳）
- 说明：`../web/README.md`

配网：首次上电开热点 `K10-Seismo-Setup`，浏览器进 `192.168.4.1` 填 WiFi；之后用 `seismo.local` 或局域网 IP。

---

## 8. 许可

代码 MIT；文档与图片 CC BY-NC-SA 4.0。欢迎在课堂上使用、修改、再发布，转载请注明来自 DF 创客社区。
