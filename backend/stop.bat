@echo off
chcp 65001 > nul
rem ============================================================
rem  个人记账本 - 停止服务（双击本文件即可）
rem  原理：找到占用 8000 端口的进程并结束它
rem ============================================================

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:"TCP.*:8000 .*LISTENING"') do (
    set FOUND=1
    echo 停止进程 PID=%%a
    taskkill /PID %%a /F > nul
)

if "%FOUND%"=="0" (
    echo 8000 端口没有正在运行的服务。
) else (
    echo 服务已停止。
)
timeout /t 2 > nul
