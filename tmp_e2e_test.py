# -*- coding: utf-8 -*-
"""E2Eテスト: 互換チェック提案型フロー"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "http://localhost:10001"
SESSION = "test-e2e-local-001"
history = []  # フロントエンドと同じく会話履歴を維持

def chat(message, retries=2):
    for i in range(retries):
        try:
            r = requests.post(f"{BASE}/api/chat",
                json={
                    "message": message,
                    "session_id": SESSION,
                    "history": history,
                },
                timeout=120, verify=False)
            res = r.json()
            # フロントエンド同様に履歴に追加
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": res.get("reply", "")})
            return res
        except Exception as e:
            print(f"  [retry {i+1}] {e}", flush=True)
            time.sleep(5)
    return None

print("=== Turn 1: RTX 4070 + Lancool 216 互換チェック ===", flush=True)
res1 = chat("RTX 4070をLancool 216に入れたい")
if res1:
    t = res1.get('type', '?')
    print(f"type: {t}", flush=True)
    print(f"reply: {res1.get('reply', '')[:300]}", flush=True)
    checks = res1.get('checks', []) or (res1.get('diagnosis', {}) or {}).get('checks', [])
    print(f"checks: {len(checks)}件", flush=True)
    for c in checks:
        print(f"  - [{c.get('status','?')}] {c.get('label','?')}", flush=True)
    verdict = (res1.get('diagnosis', {}) or {}).get('verdict', '-')
    if verdict != '-':
        print(f"verdict: {verdict}", flush=True)
else:
    print("FAIL: レスポンスなし", flush=True)
    sys.exit(1)

print(flush=True)
print("=== Turn 2: 提案リクエスト ===", flush=True)
print(f"  (history: {len(history)}件)", flush=True)
res2 = chat("マザーボード・電源・CPUクーラーは提案ください")
if res2:
    t = res2.get('type', '?')
    print(f"type: {t}", flush=True)
    print(f"reply: {res2.get('reply', '')[:300]}", flush=True)
    builds = res2.get('recommended_build', [])
    print(f"recommended_build: {len(builds)}件", flush=True)
    for b in builds:
        confirmed = "✅確定" if b.get('confirmed') else "🤖提案"
        print(f"  {confirmed} [{b.get('category','?')}] {b.get('name','?')[:60]}", flush=True)
    total = res2.get('total_estimate', '')
    if total:
        print(f"total_estimate: {total}", flush=True)
    radar = res2.get('radar_scores')
    if radar:
        print(f"radar_scores: {radar}", flush=True)
    if t == 'clarify':
        print("  ⚠️ clarifyに落ちた - intentやhistory問題の可能性", flush=True)
else:
    print("FAIL: レスポンスなし", flush=True)
    sys.exit(1)

print(flush=True)
if res2.get('type') in ('recommendation', 'suggestion') and len(res2.get('recommended_build', [])) >= 2:
    print("=== 全テスト PASS ✅ ===", flush=True)
else:
    print("=== 警告: 提案フローが期待通り動作していない可能性あり ===", flush=True)
    print(f"Turn1 type={res1.get('type')}, Turn2 type={res2.get('type')}", flush=True)
