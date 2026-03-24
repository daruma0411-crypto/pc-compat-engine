#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railwayの診断ログを取得して分析する
Railway上のログはデプロイ時に消えるので定期的に取得が必要
"""
import sys
import json
import urllib3
urllib3.disable_warnings()
import requests
_old = requests.Session.request
def _p(self, *a, **kw):
    kw['verify'] = False
    return _old(self, *a, **kw)
requests.Session.request = _p

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'


def fetch_and_save():
    """診断ログを取得してローカルに保存"""
    from datetime import datetime
    from pathlib import Path
    
    save_dir = Path(__file__).parent.parent / 'workspace' / 'data' / 'diagnosis_logs'
    save_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    save_path = save_dir / f'{today}.jsonl'
    
    try:
        resp = requests.get(f'{SITE_URL}/api/diagnosis-logs', timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ ログ取得失敗: {resp.status_code}")
            return []
        
        logs = resp.json().get('logs', [])
        
        # ローカルに保存
        with open(save_path, 'w', encoding='utf-8') as f:
            for log in logs:
                f.write(json.dumps(log, ensure_ascii=False) + '\n')
        
        print(f"✅ {len(logs)}件を {save_path.name} に保存")
        return logs
    
    except Exception as e:
        print(f"❌ エラー: {e}")
        return []


def analyze(logs):
    """ログを分析"""
    if not logs:
        print("📊 診断ログ: 0件（データなし）")
        return
    
    print(f"📊 診断ログ: {len(logs)}件\n")
    
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


def fetch_and_analyze():
    logs = fetch_and_save()
    analyze(logs)


if __name__ == '__main__':
    fetch_and_analyze()
