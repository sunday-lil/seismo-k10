# 震感捕手 · 遥测端（K10 Web 服务器 + 手机 App）

把 K10 变成一个小型数据服务器：手机连上同一个 WiFi（或 K10 自己开的热点），
打开网页就能看到**实时波形和峰值**，点一下就能让 K10 记录一次，记录完直接读结果。

```
        ┌──────────────┐    WiFi     ┌──────────────┐
        │  K10 (ESP32) │◄───────────►│  手机 / 电脑  │
        │  WebServer   │  HTTP/JSON  │  浏览器 / APK │
        └──────────────┘             └──────────────┘
              │
         200 Hz 采样、写 TF 卡
```

## 一、为什么用 Web 而不是蓝牙

| 方案 | 优点 | 缺点 |
|---|---|---|
| **Web（本项目）** | 零安装、任何手机都能开、调试方便（浏览器 F12） | 需要同一网络 |
| 蓝牙 BLE | 不用网络 | 安卓端要写 GATT，iOS 兼容麻烦 |
| 串口转 WiFi 模块 | 稳 | 多一块硬件，违反“零外接” |

K10 本身带 WiFi，用 Web 是最省的路线。App 只是个“壳”，负责连接、全屏、常亮。

## 二、三种接入方式

**1. 浏览器（不装 App）**

- 热点模式：手机连 `K10-Seismo-Setup`，浏览器打开 `http://192.168.4.1/`
- 路由模式：`http://seismo.local/` 或 K10 的局域网 IP

**2. 配套 APK**

`android/` 目录，编译后安装，全屏加载同一个页面，记住地址、断线提示、长按改地址。

**3. 脚本（电脑端）**

```bash
curl http://192.168.4.1/api/now
curl http://192.168.4.1/api/wave
```

做数据分析时可以直接把 `/api/wave` 的 JSON 存下来。

## 三、配网

第一次上电没有保存过 WiFi → K10 开热点 `K10-Seismo-Setup`（无密码）。

1. 手机连这个热点
2. 打开 `http://192.168.4.1/`
3. 填 WiFi 名称和密码 → 保存并重启
4. 重启后自动连路由器，屏幕显示 IP

清除配网：访问 `http://<IP>/reset`，重启后回到热点模式。

## 四、HTTP 接口

| 方法 | 路径 | 返回 |
|---|---|---|
| GET | `/` | 网页控制台（含实时波形） |
| GET | `/api/now` | `{"state":"MONITOR","pga":0.042,"exp":"E1","dist":0.60,"trial":1,"fs":200,"base":-936,"seq":1234}` |
| GET | `/api/wave` | `{"seq":1234,"data":[[x,y,z],...]}`，单位 g，已去基线，约 120 点 |
| GET | `/api/record` | 触发一次记录，立即返回 `{"ok":1}` |
| GET | `/api/last` | 最近一次结果 `{"ok":1,"pga":0.31,"f":28.4,"dur":186,"axis":"Z","ms":...,"file":"S:/E1_d060_t1.csv"}` |
| GET | `/api/calib` | 重新校准基线 |
| GET | `/reset` | 清除配网并重启 |

`state` 取值：`MONITOR` / `RECORDING` / `DONE`。

## 五、烧录

1. Mind+ → 代码模式 → 新建项目 → 粘贴 `v0/main_web.cpp`
2. 板型选 **行空板 K10**，编译上传
3. 打开串口监视器（115200），能看到 `# AP 192.168.4.1` 或 `# STA IP ...`

> 遥测版和比赛用的 `main.cpp` 是两个独立程序，互不影响。
> 比赛那个是“脱机记录”，这个多了 WiFi 和网页。

## 六、编译 APK

**已经装好的环境（本机）**

| 组件 | 路径 |
|---|---|
| JDK 17 | `C:\tools\jdk-17.0.21+9` |
| Gradle 8.2.1 | `C:\tools\gradle-8.2.1` |
| Android SDK | `C:\Users\dog51\AppData\Local\Android\Sdk` |
| platform-tools / adb | `…\Sdk\platform-tools\adb.exe` |
| 平台 / 构建工具 | android-34、build-tools 34.0.0 |

环境变量 `JAVA_HOME`、`ANDROID_HOME`、`PATH` 已写入用户变量，新开终端生效。

**一键编译**

双击 `build_apk.bat`，产物自动放到 `02_代码/K10端/web/震感捕手_遥测版.apk`。

工程在中文目录下，AGP 会报 `non-ASCII characters`，脚本先同步到 `C:\tools\seismo_android` 再编译，最后拷回。手动编译也要走这一步。

**手动编译**

```bat
set JAVA_HOME=C:\tools\jdk-17.0.21+9
set ANDROID_HOME=C:\Users\dog51\AppData\Local\Android\Sdk
cd C:\tools\seismo_android
java -classpath C:\tools\gradle-8.2.1\lib\gradle-launcher-8.2.1.jar org.gradle.launcher.GradleMain assembleDebug --no-daemon
```

**安装到手机**

```bat
adb install -r 02_代码\K10端\web\震感捕手_遥测版.apk
```

或者把 APK 发到手机，点安装（允许“未知来源”）。

> 已编译好的 APK：`02_代码/K10端/web/震感捕手_遥测版.apk`（782 KB，debug 签名，可直接装）。
> 首启填地址：热点模式 `192.168.4.1`，路由模式填 K10 的 IP，也可以试 `seismo.local`。

## 七、实现要点（为什么这样写）

**1. HTTP 不抢采样**

主循环以 200 Hz 采样，每 20 ms 调一次 `server.handleClient()`。
采样用绝对时间戳 `g_nextUs += 1000000/FS_HZ` 推进，HTTP 处理花掉的 1–2 ms 不会累积成漂移。

**2. 记录时也不停服务**

记录阶段每 50 ms 服务一次 HTTP，`/api/now` 会返回 `RECORDING`，
手机端看到状态就知道别急着取结果。

**3. 数据用快照，不加锁**

HTTP 读的是 `waveWin[]` 快照，采样线程只做 memmove。
单核读写指针竞态最多让某一帧波形错位，不会崩，也不会影响记录精度。

**4. 网页端零依赖**

控制台是一个内嵌的 HTML（约 4 KB），用 Canvas 画三条波形，`fetch` 每 200 ms 拉一次。
不用 CDN、不用框架，断网也能跑。

## 八、常见问题

**手机连上了但打不开页面**
先看 K10 屏幕显示的 IP，多数是 AP 模式下手机没拿到 192.168.4.x 的地址（关掉移动数据再试）。

**`seismo.local` 解析不了**
安卓对 mDNS 支持看系统版本，直接用 IP 更稳。

**波形卡顿**
`/api/wave` 每次约 120 点 × 3 轴，WiFi 差时会掉帧；把网页里的 `setInterval(tick,200)` 调到 300–500 ms。

**记录时手机端转圈**
正常，4 秒内 HTTP 每 50 ms 才服务一次，手机端请求会排队。

## 九、后续可做

- `/api/export` 直接下载 CSV
- 多台 K10 组网做“校园震感地图”
- 用 WebSocket 替代轮询，延迟从 200 ms 降到 20 ms
- APK 里加本地缓存，断网时还能看最后一帧
