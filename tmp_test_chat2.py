"""テスト5: RTX 4070で組みたい（ティアミスマッチ修正確認）"""
import json, urllib.request, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'http://localhost:10000'

tests = [
    ('5', 'RTX 4070で組みたい'),
    ('5b', 'RTX 4070 Superで組みたい'),
    ('5c', 'RTX 4070 Ti Superで組みたい'),
    ('8', 'ROG STRIX X870-F GAMING WIFIにRX 9070 XTとSSD 2枚積んでHDDも使う構成'),
]

for num, msg in tests:
    sep = '='*60
    print(f'\n{sep}')
    print(f'[テスト{num}] {msg}')
    print(sep)
    try:
        body = json.dumps({'message': msg}, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            f'{BASE}/api/chat', data=body,
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode('utf-8'))
        for key in ('reply', 'response', 'message', 'answer'):
            if key in resp:
                print(resp[key][:600])
                break
        else:
            for k, v in resp.items():
                print(f'  {k}: {str(v)[:300]}')
    except Exception as e:
        print(f'  ERROR: {e}')

print('\n=== 完了 ===')
