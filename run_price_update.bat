@echo off
cd /d "%~dp0"
echo [%date% %time%] 価格バッチ更新開始 >> logs\price_update.log
python scripts\kakaku_price_updater.py >> logs\price_update.log 2>&1
echo [%date% %time%] 完了 >> logs\price_update.log
