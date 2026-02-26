# PID 32612 のサーバーを停止
Get-Process -Id 32612 -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2

# 環境変数を取得して設定
$apiKey = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'Machine')
if (-not $apiKey) {
    $apiKey = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User')
}
Write-Host "API Key found:" ($null -ne $apiKey -and $apiKey.Length -gt 0)

# バックグラウンドジョブとして起動（環境変数はジョブに引き継がれる）
$job = Start-Job -ScriptBlock {
    param($key, $dir)
    $env:ANTHROPIC_API_KEY = $key
    $env:PORT = '10001'
    Set-Location $dir
    python app.py
} -ArgumentList $apiKey, 'C:\Users\iwashita.AKGNET\pc-compat-engine'

Write-Host "Job ID:" $job.Id
Start-Sleep 8

# 疎通確認
try {
    $r = Invoke-WebRequest -Uri 'http://localhost:10001/' -TimeoutSec 10
    Write-Host "Server ready:" $r.StatusCode
    Write-Host "OK"
} catch {
    Write-Host "Error:" $_.Exception.Message
    # ジョブの出力確認
    Receive-Job -Job $job
}
