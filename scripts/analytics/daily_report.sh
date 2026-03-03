#!/bin/bash
# 毎日AM 9:00に実行（cron / タスクスケジューラ設定）
# crontab: 0 9 * * * /path/to/pc-compat-engine/scripts/analytics/daily_report.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily analytics report..."

# HTMLレポート生成
python scripts/analytics/generate_report.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] HTML report generated"

# Telegram通知
python scripts/analytics/notify_telegram.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Telegram notification sent"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done."
