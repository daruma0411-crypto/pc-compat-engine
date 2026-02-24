"""
価格.com 電源ユニット(PSU) スクレイパー
保存先: workspace/data/kakaku_psu/products.jsonl
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL = 'https://kakaku.com/pc/power-supply/itemlist.aspx'
DIR_NAME = 'kakaku_psu'
NOW      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

def parse_int(s: str):
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def normalize_efficiency(raw: str) -> str | None:
    """80PLUS認証ランク正規化"""
    s = raw.upper()
    for rank in ('TITANIUM', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'WHITE', '80PLUS'):
        if rank in s:
            return f'80PLUS {rank}' if rank != '80PLUS' else '80PLUS'
    return raw.strip() or None

def normalize_modular(raw: str) -> str | None:
    s = raw.lower()
    if 'フル' in s or 'full' in s:   return 'フルモジュラー'
    if 'セミ' in s or 'semi' in s:   return 'セミモジュラー'
    if 'なし' in s or 'non' in s:    return '非モジュラー'
    return raw.strip() or None

def build_psu_entry(raw: dict) -> dict | None:
    code = raw['code']
    name = raw['name']
    sr   = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(raw['maker_raw']) if raw['maker_raw'] else normalize_maker(name)

    wattage = parse_int(sr.get('電源容量', '') or sr.get('定格出力', ''))
    efficiency = normalize_efficiency(
        sr.get('80PLUS認証', '') or sr.get('変換効率', '') or sr.get('電源効率', ''))
    modular = normalize_modular(
        sr.get('モジュラーケーブル', '') or sr.get('ケーブル着脱', ''))
    ff_raw = sr.get('フォームファクタ', '') or sr.get('規格', '')
    ff = ff_raw.strip() if ff_raw else None

    # コネクタ情報
    pcie_conn = (sr.get('PCI-Express補助電源', '')
                 or sr.get('PCIe電源コネクタ', '')
                 or sr.get('PCI-Express電源コネクタ', ''))

    size_raw = sr.get('外形寸法', '') or sr.get('本体サイズ', '')

    specs = {}
    if wattage:    specs['wattage_w']   = wattage
    if efficiency: specs['efficiency']  = efficiency
    if modular:    specs['modular']     = modular
    if ff:         specs['form_factor'] = ff
    if pcie_conn:  specs['pcie_connectors'] = pcie_conn.strip()[:100]
    if size_raw:   specs['size_raw']    = size_raw.strip()[:80]

    return {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'psu',
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

        entry = build_psu_entry(raw)
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
