@echo off
chcp 65001 > nul
rem ============================================================
rem  个人记账本 - 一键启动（双击本文件即可）
rem  窗口保持打开时服务持续运行；按 Ctrl+C 或关闭窗口即停止。
rem ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 未找到虚拟环境，正在创建...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist ".env" (
    echo [!] 缺少 .env，已从 .env.example 复制，请填写数据库密码后重新双击。
    copy .env.example .env > nul
    pause
    exit /b 1
)

echo [2/3] 初始化数据库（幂等，可重复执行）...
.venv\Scripts\python.exe -m app.db.init_db --with-demo

echo [3/3] 启动服务：
echo      本机   http://127.0.0.1:8000
echo      局域网 http://本机IP:8000
echo      接口文档 http://127.0.0.1:8000/docs
echo      按 Ctrl+C 停止服务
echo.

.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
