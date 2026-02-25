"""
価格.com GPU スクレイパー
保存先: workspace/data/kakaku_gpu/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs, extract_min_price,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/videocard/itemlist.aspx'
DIR_NAME = 'kakaku_gpu'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
TODAY    = datetime.now(timezone.utc).strftime('%Y-%m-%d')


def parse_int(s: str):
    m = re.search(r'\d+', str(s))
    return int(m.group()) if m else None


def parse_vram(s: str) -> int | None:
    """'8 GB', '12GB GDDR6' などから GB 数値を返す"""
    m = re.search(r'(\d+)\s*GB', str(s), re.IGNORECASE)
    return int(m.group(1)) if m else None


def build_gpu_entry(raw: dict, price: int | None) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    # GPU チップ
    chip = (sr.get('GPUチップ', '') or sr.get('グラフィックスプロセッサー', '')
            or sr.get('グラフィックスチップ', '')).strip() or None

    # VRAM
    vram_raw = sr.get('ビデオメモリ', '') or sr.get('VRAM', '') or sr.get('メモリ容量', '')
    vram_gb = parse_vram(vram_raw)

    # TDP / 消費電力
    tdp_raw = (sr.get('TDP', '') or sr.get('消費電力', '')
               or sr.get('最大消費電力', '') or sr.get('推奨電源容量', ''))
    tdp_w = parse_int(tdp_raw)

    # 基板長
    length_raw = sr.get('カード長', '') or sr.get('ボード長', '') or sr.get('カードサイズ', '')
    length_mm = parse_int(length_raw)

    specs = {}
    if chip:      specs['gpu_chip']  = chip
    if vram_gb:   specs['vram_gb']   = vram_gb
    if tdp_w:     specs['tdp_w']     = tdp_w
    if length_mm: specs['length_mm'] = length_mm

    entry = {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'gpu',
        'source_url':       raw['source_url'],
        'created_at':       NOW,
        'specs':            specs,
    }
    if price and price > 0:
        entry['price_min']        = price
        entry['price_updated_at'] = TODAY

    return entry


def main():
    import urllib.request
    from kakaku_scraper_base import fetch

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

        # 同ページから価格も抽出（get_raw_specs 内で取得済みの HTML を再利用できないため再フェッチ）
        spec_html = fetch(f'https://kakaku.com/item/{code}/spec/')
        price = extract_min_price(spec_html) if spec_html else None

        entry = build_gpu_entry(raw, price)
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
