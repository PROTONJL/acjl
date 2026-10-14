# 启动后端服务（PowerShell 里执行 .\start.ps1，或直接双击 start.bat）
# 窗口保持打开时服务持续运行，按 Ctrl+C 停止。

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $backendDir

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[1/3] 未找到虚拟环境，正在创建..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

if (-not (Test-Path ".\.env")) {
    Write-Host "[!] 缺少 .env，已从 .env.example 复制，请填写数据库密码后重新运行。" -ForegroundColor Yellow
    Copy-Item .env.example .env
    exit 1
}

Write-Host "[2/3] 初始化数据库（幂等，可重复执行）..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m app.db.init_db --with-demo

Write-Host "[3/3] 启动服务：http://localhost:8000  （接口文档 /docs）" -ForegroundColor Green
Write-Host "      本机访问：http://127.0.0.1:8000    局域网访问：http://<本机IP>:8000"
Write-Host "      按 Ctrl+C 停止`n"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
