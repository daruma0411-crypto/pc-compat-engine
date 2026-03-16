#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日次KPIレポートをTelegramに送信
"""
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Windows コンソールのエンコード問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def send_telegram_message(message):
    """OpenClaw message ツールでTelegramに送信"""
    try:
        result = subprocess.run(
            ['openclaw', 'message', 'send', '--channel', 'telegram', '--target', '8343317462', '--message', message],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Telegram送信エラー: {e}")
        return False


def main():
    """日次KPIレポートを生成してTelegramに送信"""
    # daily_marketing_check.py を実行
    result = subprocess.run(
        ['python', 'scripts/daily_marketing_check.py'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=Path(__file__).parent.parent
    )
    
    if result.returncode != 0:
        error_msg = f"❌ KPIチェック失敗\n\n{result.stderr}"
        send_telegram_message(error_msg)
        sys.exit(1)
    
    # 出力をTelegramに送信
    report = result.stdout
    
    # サマリーを抽出（最初の30行程度）
    lines = report.split('\n')
    summary = '\n'.join(lines[:35])
    
    # Telegram送信
    if send_telegram_message(summary):
        print("✅ KPIレポートをTelegramに送信しました")
    else:
        print("⚠️ Telegram送信失敗（ローカルログには記録済み）")


if __name__ == '__main__':
    main()
