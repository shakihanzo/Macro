@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    MacroHub 一鍵打包工具
echo ========================================
echo.

cd /d "%~dp0"
echo 正在使用 Anaconda Python 打包...
echo.

C:\ProgramData\anaconda3\python.exe build_exe.py

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo ✅ 打包成功！
    echo.
    echo 您的程式在這裡：
    echo %~dp0dist\MacroHub.exe
    echo.
    explorer "%~dp0dist"
) else (
    echo ❌ 打包失敗，請檢查錯誤訊息
)
echo ========================================
echo.
pause
