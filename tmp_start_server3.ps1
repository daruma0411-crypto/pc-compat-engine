# 既存サーバーを停止
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq '' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# プロセス環境変数から取得（$env: = 現セッション引き継ぎ）
$apiKey = $env:ANTHROPIC_API_KEY
Write-Host "API Key (process env):" ($apiKey -ne '' -and $null -ne $apiKey)
if ($apiKey) { Write-Host $apiKey.Substring(0, 15) "..." }

$job = Start-Job -ScriptBlock {
    param($key, $dir)
    $env:ANTHROPIC_API_KEY = $key
    $env:PORT = '10001'
    Set-Location $dir
    python app.py 2>&1
} -ArgumentList $apiKey, 'C:\Users\iwashita.AKGNET\pc-compat-engine'

Write-Host "Job ID:" $job.Id
Start-Sleep 10

try {
    $r = Invoke-WebRequest -Uri 'http://localhost:10001/' -TimeoutSec 15
    Write-Host "Server ready:" $r.StatusCode
} catch {
    Write-Host "Error:" $_.Exception.Message
    Write-Host "Job output:"
    Receive-Job -Job $job -Keep
}
