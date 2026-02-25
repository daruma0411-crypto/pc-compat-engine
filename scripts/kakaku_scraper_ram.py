"""
価格.com RAM スクレイパー
保存先: workspace/data/kakaku_ram/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs, extract_min_price,
    load_existing_ids, save_entry, make_id, normalize_maker, fetch
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/dram/itemlist.aspx'
DIR_NAME = 'kakaku_ram'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
TODAY    = datetime.now(timezone.utc).strftime('%Y-%m-%d')


def parse_int(s: str):
    m = re.search(r'\d+', str(s))
    return int(m.group()) if m else None


def build_ram_entry(raw: dict, price: int | None) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    # メモリ規格 (DDR5/DDR4)
    mem_type = (sr.get('メモリ規格', '') or sr.get('規格', '')
                or sr.get('メモリタイプ', '')).strip() or None

    # 容量
    cap_raw = sr.get('メモリ容量', '') or sr.get('容量', '') or sr.get('総容量', '')
    # "32GB (16GB×2)" → 32
    cap_m = re.search(r'(\d+)\s*GB', str(cap_raw), re.IGNORECASE)
    capacity_gb = int(cap_m.group(1)) if cap_m else None

    # 動作クロック
    speed_raw = sr.get('動作クロック', '') or sr.get('DDR5-', '') or ''
    speed_m = re.search(r'(\d{3,5})', str(speed_raw))
    speed_mhz = int(speed_m.group(1)) if speed_m else None

    specs = {}
    if mem_type:    specs['memory_type'] = mem_type
    if capacity_gb: specs['capacity_gb'] = capacity_gb
    if speed_mhz:   specs['speed_mhz']  = speed_mhz

    entry = {
        'id':          make_id('kakaku', code),
        'name':        name,
        'maker':       maker,
        'category':    'ram',
        'source_url':  raw['source_url'],
        'created_at':  NOW,
        'specs':       specs,
    }
    if price and price > 0:
        entry['price_min']        = price
        entry['price_updated_at'] = TODAY

    return entry


def main():
    out_dir    = os.path.join(DATA_ROOT, DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, 'products.jsonl')

    existing_ids = load_existing_ids(jsonl_path)
    print(f'既存: {len(existing_ids)}件')

    print('\n=== STEP1: 製品コード収集 ===')
    codes = get_all_codes(LIST_URL)
    print(f'収集: {len(codes)}件')

    print('\n=== STEP2: スペック＋価格取得 ===')
    added = skipped = failed = 0
    for i, code in enumerate(codes, 1):
        entry_id = make_id('kakaku', code)
        if entry_id in existing_ids:
            skipped += 1
            continue

        raw = get_raw_specs(code)
        if not raw or not raw.get('name'):
            failed += 1
            continue

        spec_html = fetch(f'https://kakaku.com/item/{code}/spec/')
        price = extract_min_price(spec_html) if spec_html else None

        entry = build_ram_entry(raw, price)
        if not entry:
            failed += 1
            continue

        save_entry(jsonl_path, entry)
        existing_ids.add(entry_id)
        added += 1

        if added % 20 == 0 or i % 100 == 0:
            print(f'  [{i}/{len(codes)}] 追加:{added} スキップ:{skipped} 失敗:{failed}')

    print(f'\n=== 完了 ===')
    print(f'追加: {added}件 / スキップ: {skipped}件 / 失敗: {failed}件')
    print(f'保存先: {jsonl_path}')


if __name__ == '__main__':
    main()
