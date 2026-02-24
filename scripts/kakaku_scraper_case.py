"""
価格.com PCケース スクレイパー
保存先: workspace/data/kakaku_case/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/pccase/itemlist.aspx'
DIR_NAME = 'kakaku_case'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

# フォームファクター対応マトリックス（互換チェック用）
FF_SUPPORTED = {
    'E-ATX':     ['E-ATX', 'EATX', 'ATX', 'Micro-ATX', 'mATX', 'Mini-ITX'],
    'ATX':       ['ATX', 'Micro-ATX', 'mATX', 'Mini-ITX'],
    'Micro-ATX': ['Micro-ATX', 'mATX', 'Mini-ITX'],
    'Mini-ITX':  ['Mini-ITX'],
}

def normalize_ff(raw: str) -> str:
    s = raw.replace(' ', '').lower()
    if 'eatx' in s or 'e-atx' in s: return 'E-ATX'
    if 'microatx' in s or 'matx' in s or 'm-atx' in s: return 'Micro-ATX'
    if 'miniitx' in s or 'mini-itx' in s: return 'Mini-ITX'
    if 'atx' in s: return 'ATX'
    return raw.strip()

def parse_int(s: str):
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def build_case_entry(raw: dict) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    # 対応フォームファクター（最大）
    ff_raw = (sr.get('対応フォームファクタ', '')
              or sr.get('フォームファクタ', '')
              or sr.get('最大対応MBサイズ', ''))
    ff = normalize_ff(ff_raw) if ff_raw else None

    # GPU最大長
    gpu_len = parse_int(sr.get('グラフィックボード最大長', '')
                        or sr.get('拡張カード最大長', '')
                        or sr.get('ビデオカード最大長', ''))

    # CPUクーラー最大高
    cooler_h = parse_int(sr.get('CPUクーラー最大高', '')
                         or sr.get('クーラー最大高', ''))

    # ケースサイズ
    size_raw = (sr.get('外形寸法', '')
                or sr.get('本体サイズ', '')
                or sr.get('外寸', ''))

    # ドライブベイ
    bay35 = parse_int(sr.get('3.5インチベイ', '') or sr.get('3.5"ベイ', ''))
    bay25 = parse_int(sr.get('2.5インチベイ', '') or sr.get('2.5"ベイ', ''))

    # 電源付属
    psu_included = sr.get('電源', '') or sr.get('付属電源', '')
    has_psu = bool(psu_included and psu_included not in ('-', 'なし', '別売', ''))

    specs = {}
    if ff:         specs['form_factor']          = ff
    if gpu_len:    specs['max_gpu_length_mm']     = gpu_len
    if cooler_h:   specs['max_cooler_height_mm']  = cooler_h
    if bay35:      specs['drive_bays_35']         = bay35
    if bay25:      specs['drive_bays_25']         = bay25
    if size_raw:   specs['size_raw']              = size_raw.strip()[:80]
    specs['psu_included'] = has_psu

    return {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'case',
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

        entry = build_case_entry(raw)
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
