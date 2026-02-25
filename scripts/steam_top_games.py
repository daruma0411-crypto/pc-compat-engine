"""
Steam トップゲーム appid リスト取得

topsellers × 10ページ + popularnew × 10ページ から appid を収集し
workspace/data/steam/top_games.json に保存する。

実行:
    python scripts/steam_top_games.py
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'workspace', 'data', 'steam'
)
OUTPUT_PATH = os.path.join(DATA_DIR, 'top_games.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

CATEGORIES  = ['topsellers', 'popularnew']
PAGES       = 20
PAGE_SIZE   = 25
INTERVAL    = 1.0


def fetch_page(filter_type: str, start: int) -> list[int]:
    """Steam 検索 API から appid リストを取得
    レスポンス: {"items": [{"name": "...", "logo": ".../apps/{appid}/..."}]}
    """
    url = (
        f'https://store.steampowered.com/search/results/'
        f'?filter={filter_type}&hidef2p=1&json=1'
        f'&count={PAGE_SIZE}&start={start}'
    )
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8'))
        appids = []
        for item in data.get('items', []):
            logo = item.get('logo', '')
            m = re.search(r'/apps/(\d+)/', logo)
            if m:
                appids.append(int(m.group(1)))
        return appids
    except Exception as e:
        print(f'  [WARN] filter={filter_type} start={start} error={e}')
        return []


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    seen: set[int] = set()
    games: list[dict] = []

    for category in CATEGORIES:
        print(f'\n[{category}] 取得中...')
        for page in range(PAGES):
            start = page * PAGE_SIZE
            appids = fetch_page(category, start)
            new = sum(1 for a in appids if a not in seen)
            for a in appids:
                if a not in seen:
                    seen.add(a)
                    games.append({'appid': a})
            print(f'  page {page+1}: {len(appids)}件取得 / 新規 {new}件 / 累計 {len(games)}件')
            time.sleep(INTERVAL)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

    print(f'\n完了: {len(games)} appid → {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
