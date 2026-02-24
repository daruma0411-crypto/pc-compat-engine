$taskName = "XMonitorScraper"
$batchFile = "C:\Users\iwashita.AKGNET\pc-compat-engine\scripts\run_x_monitor.bat"

# 既存タスク削除
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# アクション: バッチファイルを実行
$action = New-ScheduledTaskAction -Execute $batchFile

# トリガー: 15分ごと（今すぐから開始）
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)

# 設定: ネットワーク不要、最大10分で終了
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

# 登録（現在のユーザーで実行）
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Limited `
    -Force

Write-Host ""
Write-Host "=== 登録完了 ===" -ForegroundColor Green
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
Write-Host "次回実行: $(( Get-ScheduledTaskInfo -TaskName $taskName ).NextRunTime)"
