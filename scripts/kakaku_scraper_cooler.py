"""
価格.com CPUクーラー スクレイパー
保存先: workspace/data/kakaku_cooler/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/cpucooler/itemlist.aspx'
DIR_NAME = 'kakaku_cooler'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

def parse_int(s: str):
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def parse_float(s: str):
    m = re.search(r'[\d.]+', s)
    return float(m.group()) if m else None

def normalize_sockets(raw: str) -> list[str]:
    """対応ソケット文字列をリストに正規化"""
    sockets = []
    patterns = [
        ('AM5',    r'AM5'),
        ('AM4',    r'AM4'),
        ('AM3',    r'AM3\+?'),
        ('LGA1851',r'LGA\s*1851'),
        ('LGA1700',r'LGA\s*1700'),
        ('LGA1200',r'LGA\s*1200'),
        ('LGA1151',r'LGA\s*1151'),
        ('LGA2011', r'LGA\s*2011'),
    ]
    for label, pat in patterns:
        if re.search(pat, raw, re.IGNORECASE):
            sockets.append(label)
    return sockets if sockets else None

def build_cooler_entry(raw: dict) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    # 冷却方式
    cooler_type_raw = sr.get('冷却方式', '') or sr.get('タイプ', '')
    if '水冷' in cooler_type_raw or 'AIO' in cooler_type_raw or '簡易' in cooler_type_raw:
        cooler_type = '水冷'
    elif '空冷' in cooler_type_raw or 'ヒートシンク' in cooler_type_raw:
        cooler_type = '空冷'
    else:
        cooler_type = cooler_type_raw.strip() or '空冷'

    # 対応ソケット
    socket_raw = (sr.get('対応ソケット', '')
                  or sr.get('CPU対応ソケット', '')
                  or sr.get('対応CPU', ''))
    sockets = normalize_sockets(socket_raw) if socket_raw else None

    height    = parse_int(sr.get('高さ', '') or sr.get('ヒートシンク高さ', ''))
    tdp_rate  = parse_int(sr.get('対応TDP', '') or sr.get('TDP対応', '') or sr.get('冷却TDP', ''))
    fan_size  = parse_int(sr.get('ファン径', '') or sr.get('ファンサイズ', ''))
    noise     = parse_float(sr.get('最大騒音', '') or sr.get('ノイズレベル', ''))
    fan_rpm   = parse_int(sr.get('最大回転数', '') or sr.get('ファン回転数', ''))
    size_raw  = sr.get('外形寸法', '') or sr.get('本体サイズ', '')

    specs = {}
    specs['type'] = cooler_type
    if sockets:    specs['socket_support'] = sockets
    if height:     specs['height_mm']      = height
    if tdp_rate:   specs['tdp_rating_w']   = tdp_rate
    if fan_size:   specs['fan_size_mm']    = fan_size
    if noise:      specs['noise_db']       = noise
    if fan_rpm:    specs['max_rpm']        = fan_rpm
    if size_raw:   specs['size_raw']       = size_raw.strip()[:80]

    return {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'cpu_cooler',
        'source_url':       raw['source_url'],
        'manual_url':       None,
        'manual_path':      None,
        'manual_scraped_at': None,
        'created_at':       NOW,
        'specs':            specs,
    }


def main():
    out_dir    = os.path.join(DATA_ROOT, DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, 'products.jsonl')

    existing_ids = load_existing_ids(jsonl_path)
    print(f'既存: {len(existing_ids)}件')

    print('\n=== STEP1: 製品コード収集 ===')
    codes = get_all_codes(LIST_URL)
    print(f'収集: {len(codes)}件')

    print('\n=== STEP2: スペック取得 ===')
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

        entry = build_cooler_entry(raw)
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
