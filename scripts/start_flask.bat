@echo off
REM pc-compat-engine Flask サーバー起動スクリプト
REM タスクスケジューラ（ログオン時）から呼び出される

cd /d C:\Users\iwashita.AKGNET\pc-compat-engine

REM すでに起動済みか確認（port 10000）
netstat -an | findstr ":10000" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Flask already running on port 10000
    exit /b 0
)

REM バックグラウンドで起動
start "" /B python app.py > logs\flask.log 2>&1
echo Flask started. PID logged to logs\flask.log
