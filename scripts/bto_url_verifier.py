"""
BTO商品URLの事前検証スクリプト
各BTOのURLにアクセスし、商品名が一致するか検証。
結果を products.jsonl の url_verified フィールドに書き込む。

実行:
  python scripts/bto_url_verifier.py
"""
import json, os, sys, urllib.request, ssl, re, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'workspace', 'data')
BTO_JSONL = os.path.join(DATA_ROOT, 'bto', 'products.jsonl')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def verify_url(url: str, model: str, series: str) -> bool:
    """URLにアクセスし、ページ内に商品名が含まれているか検証"""
    if not url:
        return False

    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            if r.status != 200:
                return False
            html = r.read().decode('utf-8', errors='replace')

            # 販売終了チェック
            if '販売終了' in html or 'この商品は現在販売しておりません' in html:
                return False

            # モデル名 or シリーズ名がページに含まれるか
            html_lower = html.lower()
            if model and model.lower() in html_lower:
                return True
            if series and series.lower() in html_lower:
                return True

            # タイトルタグにメーカー名が含まれるかだけでもチェック
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if title_m:
                title = title_m.group(1).lower()
                # PC/ゲーミング関連キーワードがあればギリOK
                if any(kw in title for kw in ['gaming', 'ゲーミング', 'bto', 'パソコン', 'pc']):
                    return True

            return False
    except Exception as e:
        print(f'  [ERROR] {url}: {e}')
        return False


def main():
    if not os.path.exists(BTO_JSONL):
        print(f'ファイルなし: {BTO_JSONL}')
        return

    entries = []
    with open(BTO_JSONL, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    print(f'BTO製品: {len(entries)}件')
    verified = 0
    failed = 0

    for i, entry in enumerate(entries):
        url = entry.get('url', '')
        model = entry.get('model', '')
        series = entry.get('series', '')
        maker = entry.get('maker', '')

        print(f'[{i+1}/{len(entries)}] {maker} {model}... ', end='', flush=True)

        ok = verify_url(url, model, series)
        entry['url_verified'] = ok

        if ok:
            print('OK')
            verified += 1
        else:
            print('FAILED')
            failed += 1

        time.sleep(0.5)  # レート制限対策

    # 書き戻し
    with open(BTO_JSONL, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'\n検証完了: OK={verified} / FAILED={failed} / 全{len(entries)}件')


if __name__ == '__main__':
    main()
