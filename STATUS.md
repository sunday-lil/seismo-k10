# 项目状态

最后更新：2026-11-23

## 一、两个帖子

| 版本 | 地址 | 状态 |
|---|---|---|
| 主帖 v1.0（普通版） | https://mc.dfrobot.com.cn/article-387097.html | ✅ 已发布（审核通过） |
| 扩展 v1.1（遥测版） | https://mc.dfrobot.com.cn/article-387228.html | ✅ 已发布（审核通过） |

主帖改动已生效：26 页、标签 Arduino（micropython 已去掉）。

2026-11-20 追加：
- 开头加了「和同类 K10 地震波作品的区别」三条
- 新增「九、复刻清单」（BOM / 参数 / 30 分钟上手 / 踩坑），原「九、附件」顺延为「十」
- 附件换成 4.87 MB 新版：26 页文档（含附录 E 复刻清单）+ 教学实施包（10 页）+ 源码与示例数据
- 线上已下载验证：113 个文件，docx 内确认含「附录 E」

## 二、待办（按优先级）

| # | 事项 | 说明 |
|---|---|---|
| 2 | 主帖硬件清单仍是「行空版k10」 | 两次都没保存成功；不影响正文，下次有别的改动时一起修 |
| 3 | 演示视频 | 主帖已嵌 B 站视频；v1.1 帖暂无视频，可选 |

## 三、代码与环境

| 项 | 路径 / 版本 |
|---|---|
| K10 普通版固件 | `普通/02_代码/K10端/normal/v0/main.cpp` |
| K10 遥测版固件 | `web/02_代码/v0/main_web.cpp` |
| APK 工程 | `web/02_代码/android`（编译脚本 `web/02_代码/build_apk.bat`） |
| Python（文档/分析） | 3.12 内置运行时，含 numpy/pandas/scipy/matplotlib/python-docx/openpyxl |
| Node（docx→pdf） | v26.13.1 |
| Java | JDK 26（`JAVA_HOME=C:\Program Files\Java\latest\jdk-26`）——构建链全程用它 |
| Gradle | `D:\toolchain\gradle-9.9.1` |
| AGP / Kotlin | AGP 9.5.1（内置 Kotlin，不需要单独的 Kotlin 插件） |
| compileSdk | 37（platforms;android-37.0 + build-tools 36.1.0） |
| Android SDK | `%LOCALAPPDATA%\Android\Sdk`（platform 34 / build-tools 34.0.0 / platform-tools） |

> 2026-11-17 升级：AGP 8.2 → **AGP 9.5.1**，Gradle 8.2.1 → **9.9.1**，compileSdk 34 → **37**。现在整条构建链直接跑在 JDK 26 上，不再需要 JDK 17。`C:\tools` 已弃用。

## 四、常用命令

```bat
:: 重新生成文档（普通版）
cd 普通 && python run_all.py

:: 重新编译 APK
cd web\02_代码 && build_apk.bat

:: 装 APK
adb install -r "web\02_代码\震感捕手_遥测版.apk"
```

## 五、GitHub

当前没有本项目仓库（账号 `sunday-lil` 下 14 个仓库均非本项目）。
如需开源，建议单独建 `seismo-k10` 仓库，只放 `02_代码` 与文档，二进制（docx/pdf/apk/zip）走 Release。

## 五、v1.2 维护记录（2026-11-23）

修了三个会实际影响测量的 bug：

| 编号 | 问题 | 影响 | 修法 |
|---|---|---|---|
| 1 | 峰值窗口从触发点 +50 ms 开始 | 系统性低估 PGA | 改为触发点 −5 样本起 |
| 2 | 波形区 175+160=335 超出 320 | 画到屏幕外 | `WAVE_H` 改 142 |
| 3 | `waitButtonB()` 无超时 | B 键失灵时整机卡死 | 加 15 s 超时 |
| 4 | 遥测版同一个峰值窗口问题 | 同 1 | 同 1 |

2026-11-24：主帖已重传 v1.2 附件（5,119,715 B，与本地字节一致），
正文「26 页」改为「27 页」，文档第五章代码节选同步为 `i0 = trigIdx - 5`。
线上打包内已核验：固件含 `trigIdx - 5`、`WAVE_H 142`，文档不再出现「只看触发后 0.05」。

2026-11-24 二次更新：
- 复刻清单补「说明」一行（最小配置 335 元 / 含模型 380 元），教学包同步
- 硬件清单错别字「行空版k10」→「行空板k10」（仍缺空格与大小写，页面控件不回写模型）
- 附件更新为 5,132,195 B，线上字节一致

仓库：https://github.com/sunday-lil/seismo-k10 （191 个文件，公开）

自检：`python tools/check_repo.py`

## 六、追光台（赛道五，2026-11-24 发布）

- 帖子：https://mc.dfrobot.com.cn/article-387421.html
- 代码：`solar/02_代码/K10端/main_solar.cpp`
- 数据：`solar/03_数据/`（脚本生成），文末一行小字说明
- 图：装置示意 + 余弦定律 + 三条功率曲线 + 净能量柱状图（4 张，已核验）
- 附件：追光台_源码与数据.zip（13 个文件，350 KB，已核验可下载）

## 七、双摆混沌（2026-11-24 发布）

- 帖子：https://mc.dfrobot.com.cn/article-387422.html
- λ = 0.93 /s，可预报时长 1.9 / 3.8 / 6.5 / 7.9 s
- 正文 3 图 + 1 附件（301 KB），已核验
