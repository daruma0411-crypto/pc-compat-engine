"""E2Eテスト: 互換チェック提案型フロー"""
import requests
import json
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://pc-compat-engine.onrender.com"
SESSION = "test-e2e-001"

def chat(message, retries=3):
    for i in range(retries):
        try:
            r = requests.post(f"{BASE}/api/chat",
                json={"message": message, "session_id": SESSION},
                timeout=90, verify=False)
            return r.json()
        except Exception as e:
            print(f"  [retry {i+1}] {e}")
            time.sleep(10)
    return None

print("=== Turn 1: RTX 4070 + Lancool 216 互換チェック ===")
res1 = chat("RTX 4070をLancool 216に入れたい")
if res1:
    print(f"type: {res1.get('type')}")
    print(f"reply: {res1.get('reply', '')[:200]}")
    checks = res1.get('checks', [])
    print(f"checks: {len(checks)}件")
    if checks:
        for c in checks[:3]:
            print(f"  - {c.get('category','?')}: {c.get('status','?')} {c.get('label','?')}")
else:
    print("FAIL: レスポンスなし")
    exit(1)

print()
print("=== Turn 2: 提案リクエスト ===")
res2 = chat("マザーボード・電源・CPUクーラーは提案ください")
if res2:
    print(f"type: {res2.get('type')}")
    print(f"reply: {res2.get('reply', '')[:200]}")
    builds = res2.get('recommended_build', [])
    print(f"recommended_build: {len(builds)}件")
    for b in builds:
        confirmed = "✅確定" if b.get('confirmed') else "🤖提案"
        print(f"  {confirmed} [{b.get('category','?')}] {b.get('name','?')[:50]}")
    total = res2.get('total_estimate', {})
    if total:
        print(f"total_estimate: ¥{total.get('min_yen','?')}〜¥{total.get('max_yen','?')}")
    radar = res2.get('radar_scores')
    if radar:
        print(f"radar_scores: {radar}")
else:
    print("FAIL: レスポンスなし")
    exit(1)

print()
print("=== 全テスト完了 ===")
