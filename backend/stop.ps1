# 停止后端服务（PowerShell 里执行 .\stop.ps1，或直接双击 stop.bat）
# 原理：找到占用 8000 端口的进程并结束它

$connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Host "8000 端口没有正在运行的服务。" -ForegroundColor Yellow
    exit 0
}

$connections | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
    $process = Get-Process -Id $_ -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host ("停止进程 {0} ({1})" -f $process.Id, $process.ProcessName) -ForegroundColor Cyan
        Stop-Process -Id $process.Id -Force
    }
}
Write-Host "服务已停止。" -ForegroundColor Green
