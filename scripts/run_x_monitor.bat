@echo off
REM X Monitor Scraper 定期実行スクリプト（15分ごと）
REM タスクスケジューラから呼び出される

cd /d C:\Users\iwashita.AKGNET\pc-compat-engine

REM Flask が起動していなければ起動する
netstat -an | findstr ":10000" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Starting Flask...
    start "" /B python app.py > logs\flask.log 2>&1
    REM 起動待ち
    timeout /t 8 /nobreak >nul
)

REM X 監視スクリプト実行
python scripts\x_monitor_scraper.py
