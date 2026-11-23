# 项目状态

最后更新：2026-11-20

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
