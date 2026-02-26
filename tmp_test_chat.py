"""チャットAPIテスト"""
import json, urllib.request, urllib.error, time, sys

BASE = 'http://localhost:10000'

tests = [
    ('1', 'ROG MAXIMUS Z890 HEROにRTX 4080 SUPERとCorsair 4000D Airflowで組みたい'),
    ('2', 'NZXT H1 V2にRTX 4090 GAMING X TRIOを入れたい'),
    ('3', 'Escape from Tarkovを高設定で安定60fps出したい。予算は15万くらい'),
    ('4', '4K動画編集とAfter Effectsメインで使いたい。できるだけ静かなPCがいい'),
    ('5', 'RTX 4070で組みたい'),
    ('6', 'Z890 AORUS MASTERにRTX 4090 GAMING X TRIOとSamsung 990 Pro 2TBを入れたい'),
    ('7', 'MEG Z790 GODLIKE MAXにRTX 4090とNVMe SSD 2枚、HDD 4本で組みたい'),
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
            f'{BASE}/api/chat',
            data=body,
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode('utf-8'))

        sys.stdout.flush()

        # レスポンス表示
        if 'reply' in resp:
            text = resp['reply']
        elif 'response' in resp:
            text = resp['response']
        elif 'message' in resp:
            text = resp['message']
        elif 'answer' in resp:
            text = resp['answer']
        else:
            # 全キー表示
            print('Keys:', list(resp.keys()))
            for k, v in resp.items():
                print(f'  {k}: {str(v)[:300]}')
            time.sleep(1)
            continue

        print(text[:800])
        if len(text) > 800:
            print('...(省略)...')

    except urllib.error.HTTPError as e:
        body_err = e.read().decode('utf-8', errors='replace')
        print(f'  HTTP ERROR {e.code}: {body_err[:300]}')
    except Exception as e:
        print(f'  ERROR: {e}')

    sys.stdout.flush()
    time.sleep(1)

print('\n\n=== 全テスト完了 ===')
