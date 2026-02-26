"""
価格更新（堅牢版）: 100件ごとに中間保存、再開可能
Usage: python tmp_price_update_robust.py [cpu|mb|case|cooler|all]
"""
import sys, os, json, re, time, logging, shutil
sys.path.insert(0, r'C:\Users\iwashita.AKGNET\pc-compat-engine\scripts')

from kakaku_scraper_base import fetch, extract_min_price, DATA_ROOT
from datetime import datetime, timezone

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
SAVE_INTERVAL = 100  # 何件ごとに中間保存するか

# ログ設定
log_path = r'C:\Users\iwashita.AKGNET\pc-compat-engine\logs\price_update_robust.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger()

TARGETS = {
    'cpu':    os.path.join(DATA_ROOT, 'kakaku_cpu',    'products.jsonl'),
    'mb':     os.path.join(DATA_ROOT, 'kakaku_mb',     'products.jsonl'),
    'case':   os.path.join(DATA_ROOT, 'kakaku_case',   'products.jsonl'),
    'cooler': os.path.join(DATA_ROOT, 'kakaku_cooler', 'products.jsonl'),
}


def update_prices_robust(jsonl_path: str, cat_name: str, today: str) -> int:
    """100件ごとに中間保存しながら価格更新"""
    if not os.path.exists(jsonl_path):
        log.warning(f'[{cat_name}] ファイルなし: {jsonl_path}')
        return 0

    # ファイル読み込み
    entries = []
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception as e:
                    log.warning(f'[{cat_name}] JSON parse error: {e}')

    total = len(entries)
    already_done = sum(1 for e in entries if e.get('price_updated_at') == today)
    log.info(f'[{cat_name}] 開始: {total}件 / 更新済み={already_done}件 / 残り={(total - already_done)}件')

    updated = 0
    errors = 0
    processed_since_save = 0

    def save_progress():
        tmp_path = jsonl_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')
        shutil.move(tmp_path, jsonl_path)

    for i, entry in enumerate(entries):
        # 今日更新済みはスキップ
        if entry.get('price_updated_at') == today:
            continue

        url = entry.get('source_url', '')
        code_m = re.search(r'(K0\d{9})', url)
        if not code_m:
            continue

        code = code_m.group(1)
        try:
            html = fetch(f'https://kakaku.com/item/{code}/spec/', delay_range=(1.0, 2.0))
            if not html:
                errors += 1
                continue
            price = extract_min_price(html)
            if price and price > 0:
                entry['price_min'] = price
                entry['price_updated_at'] = today
                updated += 1
                processed_since_save += 1
        except Exception as e:
            log.error(f'[{cat_name}] fetch error for {code}: {e}')
            errors += 1
            continue

        # 中間保存
        if processed_since_save >= SAVE_INTERVAL:
            save_progress()
            log.info(f'[{cat_name}] 中間保存: {i+1}/{total}件処理, {updated}件更新')
            processed_since_save = 0

    # 最終保存
    save_progress()
    log.info(f'[{cat_name}] 完了: {updated}件更新, {errors}件エラー / {total}件')
    return updated


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['all']
    if 'all' in targets:
        targets = list(TARGETS.keys())

    log.info(f'=== 価格更新開始 TODAY={TODAY} targets={targets} ===')

    total = 0
    for cat in targets:
        if cat not in TARGETS:
            log.warning(f'不明なカテゴリ: {cat}')
            continue
        n = update_prices_robust(TARGETS[cat], cat, TODAY)
        total += n

    log.info(f'=== 全完了 合計{total}件更新 ===')


if __name__ == '__main__':
    main()
