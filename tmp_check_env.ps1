# 全ストアを確認
$m = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'Machine')
$u = [System.Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User')
$p = $env:ANTHROPIC_API_KEY

Write-Host "Machine:" ($null -ne $m -and $m.Length -gt 0) ($m.Substring(0, [Math]::Min(15, ($m ?? '').Length)) + '...')
Write-Host "User:" ($null -ne $u -and $u.Length -gt 0) ($u.Substring(0, [Math]::Min(15, ($u ?? '').Length)) + '...')
Write-Host "Process:" ($null -ne $p -and $p.Length -gt 0) ($p.Substring(0, [Math]::Min(15, ($p ?? '').Length)) + '...')

# .env ファイル確認
$envFile = Get-Content 'C:\Users\iwashita.AKGNET\pc-compat-engine\.env' -ErrorAction SilentlyContinue
if ($envFile) {
    $envFile | Where-Object { $_ -match 'ANTHROPIC' }
}
