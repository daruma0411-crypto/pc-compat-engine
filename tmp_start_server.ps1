$apiKey = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'Machine')
if (-not $apiKey) { $apiKey = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User') }
$env:ANTHROPIC_API_KEY = $apiKey
$env:PORT = '10001'
Set-Location 'C:\Users\iwashita.AKGNET\pc-compat-engine'
Start-Process python -ArgumentList 'app.py' -WindowStyle Hidden -PassThru | Select-Object Id
Write-Host "Server starting..."
Start-Sleep 8
try {
    $r = Invoke-WebRequest -Uri 'http://localhost:10001/' -TimeoutSec 10
    Write-Host "Server ready:" $r.StatusCode
} catch {
    Write-Host "Server not ready:" $_.Exception.Message
}
