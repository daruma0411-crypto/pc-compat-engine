"""
Steam ゲーム詳細スクレイパー

top_games.json の appid ごとに appdetails API を叩き、
raw/{appid}.json に保存後パースして games.jsonl に追記する。

途中再開: raw/{appid}.json または games.jsonl に記録済みの appid はスキップ。
レート制限: 1.5秒/リクエスト、429 時は 60 秒待機、最大 3 回リトライ。

実行:
    python scripts/steam_scraper.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# steam_parser を同じ scripts/ ディレクトリから import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from steam_parser import parse_spec_html

DATA_DIR        = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'workspace', 'data', 'steam'
)
RAW_DIR         = os.path.join(DATA_DIR, 'raw')
TOP_GAMES_PATH  = os.path.join(DATA_DIR, 'top_games.json')
GAMES_JSONL     = os.path.join(DATA_DIR, 'games.jsonl')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

INTERVAL            = 1.5
RETRY_COUNT         = 3
RATE_LIMIT_WAIT     = 60
CHECKPOINT_INTERVAL = 200


def fetch_appdetails(appid: int) -> dict | None:
    """appdetails API を呼び出してレスポンス dict を返す。失敗時は None。"""
    url = f'https://store.steampowered.com/api/appdetails?appids={appid}&l=japanese'
    for attempt in range(RETRY_COUNT):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode('utf-8'))
            return data.get(str(appid), {})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f'  [429] レート制限 → {RATE_LIMIT_WAIT}秒待機')
                time.sleep(RATE_LIMIT_WAIT)
            else:
                wait = 2 ** attempt
                print(f'  [WARN] appid={appid} HTTP {e.code} → {wait}s')
                time.sleep(wait)
        except Exception as e:
            wait = 2 ** attempt
            print(f'  [WARN] appid={appid} attempt={attempt+1} {e} → {wait}s')
            time.sleep(wait)
    return None


def load_appids() -> list[int]:
    with open(TOP_GAMES_PATH, encoding='utf-8') as f:
        return [g['appid'] for g in json.load(f)]


def load_processed_appids() -> set[int]:
    """games.jsonl から処理済み appid を収集（途中再開用）"""
    processed: set[int] = set()
    if not os.path.exists(GAMES_JSONL):
        return processed
    with open(GAMES_JSONL, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                processed.add(json.loads(line)['appid'])
            except Exception:
                pass
    return processed


def build_entry(appid: int, data: dict) -> dict | None:
    """API レスポンスから games.jsonl エントリを生成。対象外は None。"""
    if not data.get('success') or not data.get('data'):
        return None

    d = data['data']
    if d.get('type') != 'game':
        return None
    if not d.get('platforms', {}).get('windows', False):
        return None

    pc_req = d.get('pc_requirements', {})
    minimum     = parse_spec_html(pc_req.get('minimum', ''))     if isinstance(pc_req, dict) else {}
    recommended = parse_spec_html(pc_req.get('recommended', '')) if isinstance(pc_req, dict) else {}

    metacritic  = d.get('metacritic', {}).get('score') if d.get('metacritic') else None
    release     = d.get('release_date', {}).get('date', '') if d.get('release_date') else ''
    genres      = [g['description'] for g in d.get('genres', [])]
    screenshot  = d.get('screenshots', [{}])[0].get('path_thumbnail') if d.get('screenshots') else None

    return {
        'appid':             appid,
        'name':              d.get('name', ''),
        'short_description': d.get('short_description', ''),
        'genres':            genres,
        'release_date':      release,
        'metacritic_score':  metacritic,
        'screenshot':        screenshot,
        'minimum':           minimum or None,
        'recommended':       recommended or None,
        'scraped_at':        datetime.now(timezone.utc).isoformat(),
    }


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    appids    = load_appids()
    processed = load_processed_appids()
    pending   = [a for a in appids if a not in processed]

    print(f'対象: {len(appids)}件 / 処理済: {len(processed)}件 / 未処理: {len(pending)}件')

    success = skipped = failed = 0

    for i, appid in enumerate(pending, 1):
        raw_path = os.path.join(RAW_DIR, f'{appid}.json')

        # raw キャッシュがあれば再利用（API 呼び出し不要）
        if os.path.exists(raw_path):
            with open(raw_path, encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = fetch_appdetails(appid)
            if data is None:
                failed += 1
                print(f'  [{i}/{len(pending)}] appid={appid} FAILED')
                time.sleep(INTERVAL)
                continue
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            time.sleep(INTERVAL)

        entry = build_entry(appid, data)
        if entry is None:
            skipped += 1
        else:
            with open(GAMES_JSONL, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            success += 1

        if i % CHECKPOINT_INTERVAL == 0:
            print(
                f'[チェックポイント] {i}/{len(pending)} 完了 '
                f'| 成功:{success} スキップ:{skipped} 失敗:{failed}'
            )

    print(f'\n完了: 成功={success} スキップ={skipped} 失敗={failed}')
    print(f'→ {GAMES_JSONL}')


if __name__ == '__main__':
    main()
