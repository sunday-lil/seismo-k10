# 震感捕手 · 遥测版（v1.1）

给主帖那个“脱机记录”的版本加一个 WiFi 遥测端：手机连上同一个网络，打开 App 就能看实时波形、远程触发记录。

主版本（比赛提交版）在 [`../普通/`](../普通/)。

## 目录

```
web/
├── 01_作品文档/
│   └── v1.1_功能说明.md      这一版改了什么、为什么这么改
├── 02_代码/
│   ├── README.md             架构、API、烧录、编译 APK
│   ├── v0/main_web.cpp       K10 固件（WiFi + Web 服务器）
│   ├── android/              APK 工程
│   ├── build_apk.bat         一键编译
│   ├── 震感捕手_遥测版.apk    已编译好的安装包
│   └── 遥测版_源码与APK.zip   发帖附件
├── 03_数据/                  说明（数据与普通版共用）
├── 04_图片/
│   └── 手机端截图.png
└── 05_发布/
    └── 发帖正文_v1.1.md
```

## 已发布

https://mc.dfrobot.com.cn/article-387228.html

## 一句话

K10 变成一个 HTTP 服务器，`/api/wave` 给波形，`/api/record` 触发记录；
手机端是一个 WebView 壳，全屏加载 K10 的网页控制台。

## 快速开始

1. 烧 `02_代码/v0/main_web.cpp`（Mind+ 代码模式，板型行空板 K10）
2. 首启开热点 `K10-Seismo-Setup`，手机连上，浏览器进 `192.168.4.1` 填 WiFi
3. 重启后看 K10 屏幕第 5 行的 IP
4. App 填这个 IP（或 `seismo.local`）

## 状态

- [x] 固件：配网、HTTP 接口、网页控制台
- [x] APK：连接、全屏、断线提示、自动尝试地址
- [x] 实机验证：vivo Y75A，实时波形与峰值正常
- [x] v1.1 帖子发布：https://mc.dfrobot.com.cn/article-387228.html
