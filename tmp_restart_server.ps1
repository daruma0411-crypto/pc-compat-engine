# ポート10000のFlaskサーバーを全停止して再起動
$pids = @()
$lines = netstat -ano | findstr ":10000"
foreach ($line in $lines) {
    if ($line -match 'LISTENING') {
        $pid = ($line -split '\s+')[-1]
        if ($pid -match '^\d+$') {
            $pids += $pid
        }
    }
}
$pids = $pids | Sort-Object -Unique
foreach ($p in $pids) {
    Write-Host "Stopping PID $p"
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3
Write-Host "Starting new server..."
Set-Location "C:\Users\iwashita.AKGNET\pc-compat-engine"
Start-Process cmd -ArgumentList "/c python app.py > tmp_server.log 2>&1" -WindowStyle Hidden
Start-Sleep -Seconds 6
try {
    $r = Invoke-WebRequest -Uri "http://localhost:10000/api/health" -TimeoutSec 5
    Write-Host "Server UP: $($r.Content)"
} catch {
    Write-Host "Server DOWN: $_"
    Get-Content "tmp_server.log" -Tail 5
}
