@echo off
setlocal
rem ============================================================
rem  震感捕手 遥测版 APK 一键编译
rem  环境：系统 JDK 26 + Gradle 9.9.1 + AGP 9.5.1
rem  Gradle 装在 D:\toolchain，不依赖 C:\tools
rem  工程目录含中文，先同步到 %TEMP% 再编译
rem ============================================================

set GRADLE_BIN=D:\toolchain\gradle-9.9.1\bin\gradle.bat
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk

if not exist "%GRADLE_BIN%" goto nogradle
if not exist "%ANDROID_HOME%\platforms\android-37.0" goto nosdk

rem 系统 JAVA_HOME 就是最新的 JDK 26，直接沿用
if not defined JAVA_HOME goto nojava

set SRC=%~dp0
set PROJ=%SRC%android
set WORK=%TEMP%\seismo_android

echo [1/4] 同步工程到 %WORK%
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"
xcopy "%PROJ%\app" "%WORK%\app" /E /I /Y /Q >nul
copy /Y "%PROJ%\build.gradle.kts" "%WORK%\" >nul
copy /Y "%PROJ%\settings.gradle.kts" "%WORK%\" >nul
copy /Y "%PROJ%\gradle.properties" "%WORK%\" >nul
copy /Y "%PROJ%\local.properties" "%WORK%\" >nul

echo [2/4] 编译（AGP 9.5.1 / Gradle 9.9.1 / JDK 26）
cd /d "%WORK%"
call "%GRADLE_BIN%" assembleDebug --no-daemon
if errorlevel 1 goto fail

echo [3/4] 拷贝 APK
copy /Y "%WORK%\app\build\outputs\apk\debug\app-debug.apk" "%SRC%k10-telemetry.apk" >nul

echo [4/4] 完成
echo.
echo APK: %SRC%k10-telemetry.apk
pause
exit /b 0

:nogradle
echo [ERROR] 找不到 Gradle：%GRADLE_BIN%
pause
exit /b 1

:nosdk
echo [ERROR] 找不到 Android SDK 37：%ANDROID_HOME%
pause
exit /b 1

:nojava
echo [ERROR] JAVA_HOME 未设置
pause
exit /b 1

:fail
echo.
echo 编译失败，看上面的输出。
pause
exit /b 1
