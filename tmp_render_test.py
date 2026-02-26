# -*- coding: utf-8 -*-
"""Render本番サーバーのE2Eテスト（スリープ解除待ち対応）"""
import sys, io, requests, time, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://pc-compat-engine.onrender.com"
history = []

def chat(msg, max_wait=180):
    for i in range(6):
        try:
            r = requests.post(f"{BASE}/api/chat",
                json={"message": msg, "session_id": "render-e2e", "history": history},
                timeout=max_wait, verify=False)
            res = r.json()
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": res.get("reply", "")})
            return res
        except Exception as e:
            print(f"  [retry {i+1}/6] {e}", flush=True)
            if i < 5: time.sleep(20)
    return None

print("Renderスリープ解除中（最大180秒待機）...", flush=True)
# ヘルスチェックで起動確認
for i in range(10):
    try:
        r = requests.get(f"{BASE}/api/health", timeout=30, verify=False)
        if r.status_code == 200:
            print(f"Health OK ({i+1}回目): {r.text[:100]}", flush=True)
            break
    except Exception as e:
        print(f"  health wait {i+1}/10: {e}", flush=True)
        time.sleep(20)

print("\n=== Turn 1: 互換チェック ===", flush=True)
r1 = chat("RTX 4070をLancool 216に入れたい")
if r1:
    print(f"type: {r1.get('type')}", flush=True)
    print(f"reply: {r1.get('reply','')[:200]}", flush=True)
    builds = r1.get('recommended_build', [])
    print(f"builds: {len(builds)}件", flush=True)
else:
    print("FAIL Turn1", flush=True); sys.exit(1)

print("\n=== Turn 2: 提案リクエスト ===", flush=True)
r2 = chat("マザーボード・電源・CPUクーラーは提案ください")
if r2:
    print(f"type: {r2.get('type')}", flush=True)
    builds2 = r2.get('recommended_build', [])
    print(f"builds: {len(builds2)}件", flush=True)
    for b in builds2:
        c = "✅" if b.get('confirmed') else "🤖"
        print(f"  {c} [{b.get('category')}] {b.get('name','')[:50]}", flush=True)
    print(f"total: {r2.get('total_estimate','')}", flush=True)
    if r2.get('type') in ('recommendation','suggestion') and len(builds2) >= 2:
        print("\n=== PASS ✅ ===", flush=True)
    else:
        print("\n=== 期待外の動作 ===", flush=True)
else:
    print("FAIL Turn2", flush=True); sys.exit(1)
