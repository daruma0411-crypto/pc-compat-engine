#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railwayの診断ログを取得して分析する
Railway上のログはデプロイ時に消えるので定期的に取得が必要
"""
import sys
import json
import requests

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'


def fetch_and_analyze():
    """診断ログAPIから取得して分析"""
    try:
        resp = requests.get(f'{SITE_URL}/api/diagnosis-logs', timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ ログ取得失敗: {resp.status_code}")
            return
        
        logs = resp.json().get('logs', [])
        print(f"📊 診断ログ: {len(logs)}件\n")
        
        # パーツ別の出現回数
        parts_count = {}
        verdicts = {}
        
        for log in logs:
            for part in log.get('parts', []):
                parts_count[part] = parts_count.get(part, 0) + 1
            v = log.get('verdict', 'UNKNOWN')
            verdicts[v] = verdicts.get(v, 0) + 1
        
        print("🔧 よく診断されるパーツ TOP10:")
        for part, count in sorted(parts_count.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count}回: {part}")
        
        print(f"\n📋 診断結果:")
        for v, count in sorted(verdicts.items(), key=lambda x: -x[1]):
            print(f"  {v}: {count}件")
    
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == '__main__':
    fetch_and_analyze()
