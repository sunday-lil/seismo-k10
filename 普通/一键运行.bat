@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Please install Python 3.10+ and tick "Add Python to PATH".
  pause
  exit /b 1
)
python run_all.py
echo.
pause
