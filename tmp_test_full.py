"""フル応答確認テスト"""
import json, urllib.request, sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'http://localhost:10000'

tests = [
    ('1', 'ROG MAXIMUS Z890 HEROにRTX 4080 SUPERとCorsair 4000D Airflowで組みたい'),
    ('5', 'RTX 4070で組みたい'),
    ('6', 'Z890 AORUS MASTERにRTX 4090 GAMING X TRIOとSamsung 990 Pro 2TBを入れたい'),
    ('7', 'MEG Z790 GODLIKE MAXにRTX 4090とNVMe SSD 2枚、HDD 4本で組みたい'),
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

        # キー一覧を確認
        print(f'[レスポンスキー]: {list(resp.keys())}')

        for key in ('reply', 'response', 'message', 'answer'):
            if key in resp:
                print(f'\n--- {key} ({len(resp[key])}文字) ---')
                print(resp[key])  # 全文表示
                break
        else:
            for k, v in resp.items():
                print(f'\n--- {k} ---')
                print(str(v))

    except Exception as e:
        print(f'  ERROR: {e}')

print('\n\n=== 完了 ===')
