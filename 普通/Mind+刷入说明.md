# 用 Mind+ 代码模式刷入 main.cpp

Mind+ 的 K10 上传模式在代码视图里就是 **Arduino C++**（`#include "unihiker_k10.h"`），可以直接粘贴、编译、上传。不用另烧 MicroPython 固件。

---

## 第 1 步：装 Mind+、加 K10 支持（只做一次）

1. 装 **Mind+ V1.8.1 RC1.0 或更高**（低于这个版本没有 K10）。
2. 打开 Mind+，切到 **上传模式**。
3. 点左下角 **扩展** → **主控板** → **行空板 K10** → 返回。

## 第 2 步：连接板子

1. USB 线插 K10 的 Type-C 口。
2. 点 Mind+ 上方 **连接设备**，选对应的 COM 口。
3. 连上后，设备名旁边会出现绿色状态。

## 第 3 步：进代码模式

1. 在编辑区右上角找到 **“代码 / 积木”** 切换（有的版本叫“代码视图”）。
2. 切过去后，代码区第一行应该是 `#include "unihiker_k10.h"`。
3. 如果代码区是**灰色只读**的，说明当前是“积木生成代码”的预览，不能编辑——换 Arduino IDE（见文末）。

## 第 4 步：粘贴 main.cpp

1. 用记事本或 VS Code 打开 `02_代码/K10端/normal/v0/main.cpp`。
2. **Ctrl+A 全选 → Ctrl+C 复制**。
3. 回 Mind+ 代码区：**Ctrl+A 全选原代码 → Delete 删掉 → Ctrl+V 粘贴**。
4. 确认粘贴后文件里能看到这三个关键位置（缺一个都会编译不过）：
   - 顶部 `#include "unihiker_k10.h"`
   - `UNIHIKER_K10 k10;`
   - 末尾 `void setup()` 和 `void loop()`

> **不要**把 Mind+ 自带的示例代码和 main.cpp 混在一起——两份代码都有 `setup()`/`loop()`，会重复定义。

## 第 5 步：改参数

只改这几行（在文件顶部）：

```cpp
#define EXP_ID      "E1"     // 实验一 E1 / 实验二 E2 / 实验三 E3
#define DIST_M      0.60f    // 这次测点离震源几米
#define TRIAL_NO    1        // 第几次重复
#define NOTE_TXT    "wood"   // 木桌 wood / 瓷砖 tile
```

## 第 6 步：编译上传

1. 点 **上传**（→ 图标），看下方编译输出。
2. 出现 `上传成功` / `Done uploading` 即可。
3. 板子会自动复位，屏幕出现：

   ```
   SEISMO CATCHER
   MONITOR
   PGA 0.000 g
   （三条彩色波形）
   ```

出现这个界面 → 成功，去 [上机操作卡](上机操作卡.md) 第 1 步开始做实验。

---

## 编译/上传报错对照

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| `unihiker_k10.h: No such file or directory` | Mind+ 没加载 K10 主控板 | 回第 1 步，扩展里选“行空板 K10” |
| `redefinition of 'void setup()'` | 示例代码没删干净 | 全选删除后再粘，只留 main.cpp |
| `'class UNIHIKER_K10' has no member 'initSDFile'` | Mind+ 内置库版本较旧 | 删掉 `k10.initSDFile();` 这一行，改用串口输出（程序会自动回退） |
| `fopen` 相关报错 | 个别版本不开放文件系统 | 把 `saveToTfCard()` 里 `#if 1` 改成 `#if 0`，强制走串口 |
| 上传卡在 `Connecting...` | 没进下载模式 | 按住 **BOOT** 再点上传，出现 `Connecting` 后松开 |
| 屏幕花屏 / 只显示一半 | 屏幕方向不对 | 改 `SCREEN_DIR`（0–3） |

---

## 如果代码区是灰色只读

那就不是可编辑的代码模式，粘不了。用 Arduino IDE：

1. 装 Arduino IDE 2.x
2. 首选项 → 附加开发板管理器网址：
   `https://downloadcd.dfrobot.com.cn/UNIHIKER/package_unihiker_index.json`
3. 开发板管理器搜 `unihiker` 安装
4. 选板 `UNIHIKER K10`、选端口 → 打开 `main.cpp` → 上传

---

## 刷完以后

屏幕自检通过后，实验步骤见 [上机操作卡](上机操作卡.md)：

摆台 → 静置自检 → 试落 3 次 → 每个距离 5 次 → 取数据 → 双击 `一键运行.bat` 出文档。

数据优先写 TF 卡（`S:/E1_d060_t1.csv`）；没插卡或写卡失败时，程序会把同一段 CSV 从 USB 串口输出，用 `serial_capture.py` 接住。
