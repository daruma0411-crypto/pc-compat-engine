# 既存Pythonサーバーをすべて停止
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$apiKey = $env:ANTHROPIC_API_KEY
$env:PORT = '10001'

# Start-Process: stdout/stderrをファイルへ（NULだとAPIキーが渡らない可能性）
$logFile = 'C:\Users\iwashita.AKGNET\pc-compat-engine\tmp_server.log'
'' | Set-Content $logFile  # ログファイル初期化

$proc = Start-Process -FilePath 'python' -ArgumentList 'app.py' `
    -WorkingDirectory 'C:\Users\iwashita.AKGNET\pc-compat-engine' `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $logFile `
    -WindowStyle Hidden `
    -Environment @{
        ANTHROPIC_API_KEY = $apiKey
        PORT = '10001'
        PYTHONIOENCODING = 'utf-8'
    } `
    -PassThru

Write-Host "PID:" $proc.Id
Start-Sleep 8

# 疎通確認
try {
    $r = Invoke-WebRequest -Uri 'http://localhost:10001/' -TimeoutSec 15
    Write-Host "Server ready:" $r.StatusCode
} catch {
    Write-Host "Error:" $_.Exception.Message
    Write-Host "=== Server log ==="
    Get-Content $logFile -ErrorAction SilentlyContinue
}
