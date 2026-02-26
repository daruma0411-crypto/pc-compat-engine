"""詳細レスポンス確認"""
import json, urllib.request, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'http://localhost:10000'

msg = 'ROG MAXIMUS Z890 HEROにRTX 4080 SUPERとCorsair 4000D Airflowで組みたい'

body = json.dumps({'message': msg}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(
    f'{BASE}/api/chat', data=body,
    headers={'Content-Type': 'application/json; charset=utf-8'}
)
with urllib.request.urlopen(req, timeout=60) as r:
    resp = json.loads(r.read().decode('utf-8'))

print(f'=== テスト1 フルレスポンス ===')
print(f'type: {resp.get("type")}')
print(f'\n[reply]\n{resp.get("reply", "")}')
print(f'\n[compat_info]\n{resp.get("compat_info", "(なし)")}')
print(f'\n[tip]\n{resp.get("tip", "(なし)")}')
print(f'\n[total_estimate]\n{resp.get("total_estimate", "(なし)")}')
print(f'\n[recommended_build] ({len(resp.get("recommended_build", []))}件):')
for p in (resp.get("recommended_build") or []):
    print(f'  {p}')
print(f'\n[game]: {resp.get("game")}')
print(f'\n[game_req_scores]: {resp.get("game_req_scores")}')
print(f'\n[radar_scores]: {resp.get("radar_scores")}')
