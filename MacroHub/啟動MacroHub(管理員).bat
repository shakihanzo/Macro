@echo off
cd /d "%~dp0"

:: 檢查是否已經是管理員
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 正在以管理員身份執行...
    C:\ProgramData\anaconda3\python.exe main.py
    pause
) else (
    echo 正在請求管理員權限...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && C:\ProgramData\anaconda3\python.exe main.py && pause' -Verb RunAs"
)
