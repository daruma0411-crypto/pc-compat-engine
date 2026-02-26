# 既存Pythonサーバーをすべて停止
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# 現プロセスに環境変数をセット（子プロセスに引き継がれる）
$env:PORT = '10001'
# ANTHROPIC_API_KEYは既にセット済みのはず

$logFile = 'C:\Users\iwashita.AKGNET\pc-compat-engine\tmp_server.log'
'' | Set-Content $logFile

$proc = Start-Process -FilePath 'python' -ArgumentList 'app.py' `
    -WorkingDirectory 'C:\Users\iwashita.AKGNET\pc-compat-engine' `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $logFile `
    -WindowStyle Hidden `
    -PassThru

Write-Host "PID:" $proc.Id
Start-Sleep 8

try {
    $r = Invoke-WebRequest -Uri 'http://localhost:10001/' -TimeoutSec 15
    Write-Host "Server ready:" $r.StatusCode
    Write-Host "OK"
} catch {
    Write-Host "Error:" $_.Exception.Message
    Write-Host "=== Server log (first 30 lines) ==="
    Get-Content $logFile -ErrorAction SilentlyContinue | Select-Object -First 30
}
