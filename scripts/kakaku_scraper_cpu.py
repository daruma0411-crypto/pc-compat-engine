"""
価格.com CPU スクレイパー
保存先: workspace/data/kakaku_cpu/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/cpu/itemlist.aspx'
DIR_NAME = 'kakaku_cpu'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

def normalize_socket(raw: str) -> str:
    s = raw.replace(' ', '').upper()
    if 'AM5'  in s: return 'AM5'
    if 'AM4'  in s: return 'AM4'
    if 'AM3'  in s: return 'AM3'
    if '1851' in s: return 'LGA1851'
    if '1700' in s: return 'LGA1700'
    if '1200' in s: return 'LGA1200'
    if '1151' in s: return 'LGA1151'
    if 'FCLGA' in s: return raw.replace('FCLGA','LGA').replace('fclga','LGA').strip()
    return raw.strip()

def parse_float(s: str):
    m = re.search(r'[\d.]+', s)
    return float(m.group()) if m else None

def parse_int(s: str):
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def build_cpu_entry(raw: dict) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    socket = normalize_socket(sr.get('ソケット形状', '') or sr.get('CPUソケット', '')) or None

    # コア数
    cores_raw   = sr.get('コア数', '') or sr.get('物理コア数', '')
    threads_raw = sr.get('スレッド数', '') or sr.get('論理コア数', '')
    cores   = parse_int(cores_raw)
    threads = parse_int(threads_raw)

    # クロック
    base  = parse_float(sr.get('動作クロック', '') or sr.get('ベースクロック', ''))
    boost = parse_float(sr.get('最大クロック', '') or sr.get('ターボ・ブーストクロック', ''))

    # TDP
    tdp = parse_int(sr.get('TDP', '') or sr.get('熱設計電力(TDP)', ''))

    # メモリ
    mem_type = sr.get('対応メモリ規格', '') or sr.get('メモリタイプ', '')
    if 'DDR5' in mem_type and 'DDR4' in mem_type:
        mem_type = 'DDR4/DDR5'
    elif 'DDR5' in mem_type:
        mem_type = 'DDR5'
    elif 'DDR4' in mem_type:
        mem_type = 'DDR4'
    elif 'DDR3' in mem_type:
        mem_type = 'DDR3'
    else:
        mem_type = None

    igpu = sr.get('内蔵グラフィックス', '') or sr.get('統合グラフィックス', '')
    has_igpu = bool(igpu and igpu not in ('-', 'なし', 'None', ''))

    # L3キャッシュ
    l3_raw = sr.get('L3キャッシュ', '') or sr.get('三次キャッシュ', '')
    l3 = parse_int(l3_raw)

    specs = {}
    if socket:       specs['socket']       = socket
    if cores:        specs['cores']        = cores
    if threads:      specs['threads']      = threads
    if base:         specs['base_clock_ghz'] = base
    if boost:        specs['boost_clock_ghz'] = boost
    if tdp:          specs['tdp_w']        = tdp
    if mem_type:     specs['memory_type']  = mem_type
    if l3:           specs['l3_cache_mb']  = l3
    specs['integrated_gpu'] = has_igpu
    if has_igpu and igpu not in ('-', ''):
        specs['igpu_model'] = igpu

    return {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'cpu',
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

        entry = build_cpu_entry(raw)
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
