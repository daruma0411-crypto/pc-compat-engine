"""
価格.com マザーボード スクレイパー
保存先: workspace/data/kakaku_mb/products.jsonl
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes, get_raw_specs,
    load_existing_ids, save_entry, make_id, normalize_maker
)
from datetime import datetime, timezone

LIST_URL  = 'https://kakaku.com/pc/motherboard/itemlist.aspx'
DIR_NAME  = 'kakaku_mb'
NOW       = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

# ---- スペック正規化 ----

def normalize_socket(raw: str) -> str:
    """CPUソケット正規化"""
    s = raw.replace(' ', '').upper()
    if 'AM5'  in s: return 'AM5'
    if 'AM4'  in s: return 'AM4'
    if 'AM3'  in s: return 'AM3'
    if '1851' in s: return 'LGA1851'
    if '1700' in s: return 'LGA1700'
    if '1200' in s: return 'LGA1200'
    if '1151' in s: return 'LGA1151'
    return raw.replace('Socket', '').replace('socket', '').strip()

def normalize_ff(raw: str) -> str:
    """フォームファクター正規化"""
    s = raw.replace(' ', '').lower()
    if 'eatx' in s or 'e-atx' in s: return 'E-ATX'
    if 'microatx' in s or 'matx' in s or 'm-atx' in s: return 'Micro-ATX'
    if 'miniatx' in s: return 'Mini-ATX'
    if 'miniitx' in s or 'mini-itx' in s: return 'Mini-ITX'
    if 'atx' in s: return 'ATX'
    return raw.strip()

def normalize_memory_type(raw: str) -> str:
    """メモリタイプ正規化"""
    s = raw.upper()
    if 'DDR5' in s: return 'DDR5'
    if 'DDR4' in s: return 'DDR4'
    if 'DDR3' in s: return 'DDR3'
    return raw.strip()

def extract_chipset(product_name: str) -> str | None:
    """製品名からチップセットを抽出"""
    # 例: B650E, Z890, X670E, B760, H870, A620 等
    m = re.search(
        r'\b(X870E?|X670E?|B850|B650E?|A620|Z890|Z790|B760|H770|H610|B860|H870'
        r'|Z690|B660|H670|Z590|B560|H570|H510'
        r'|X570|B550|A520|X470|B450|A320)\b',
        product_name, re.IGNORECASE
    )
    return m.group(1).upper() if m else None

def parse_int(s: str) -> int | None:
    """文字列から最初の整数を抽出"""
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def parse_size(raw: str) -> str | None:
    """幅x奥行き from '305x244 mm' → '305x244'"""
    m = re.search(r'(\d+)\s*[xX×]\s*(\d+)', raw)
    return f"{m.group(1)}x{m.group(2)}" if m else None

def build_mb_entry(raw: dict) -> dict | None:
    """raw_specs → 製品エントリー"""
    code      = raw['code']
    name      = raw['name']
    maker_raw = raw['maker_raw']
    sr        = raw['specs_raw']

    if not name:
        return None

    maker = normalize_maker(maker_raw) if maker_raw else normalize_maker(name)

    # スペック組み立て
    socket   = normalize_socket(sr.get('CPUソケット', '')) or None
    ff       = normalize_ff(sr.get('フォームファクタ', '')) or None
    mem_type = normalize_memory_type(sr.get('詳細メモリタイプ', '')) or None
    chipset  = sr.get('チップセット') or extract_chipset(name)
    if chipset:
        chipset = re.sub(r'^AMD|^Intel', '', chipset).strip()

    mem_slots  = parse_int(sr.get('メモリスロット数', ''))
    max_mem    = parse_int(sr.get('最大メモリー容量', ''))
    m2_slots   = parse_int(sr.get('M.2ソケット数', ''))
    sata_ports = parse_int(sr.get('SATA', ''))
    size       = parse_size(sr.get('幅x奥行き', ''))

    specs = {
        'chipset':      chipset,
        'socket':       socket,
        'form_factor':  ff,
        'memory_type':  mem_type,
        'memory_slots': mem_slots,
        'max_memory_gb': max_mem,
        'm2_slots':     m2_slots,
        'sata_ports':   sata_ports,
        'size_mm':      size,
        # 追加情報（あれば）
        'wireless_lan': sr.get('無線LAN') or None,
        'pcie_x16':     sr.get('PCI-Express 16X') or None,
    }
    # Noneのキーは除去
    specs = {k: v for k, v in specs.items() if v is not None}

    return {
        'id':               make_id('kakaku', code),
        'name':             name,
        'maker':            maker,
        'category':         'motherboard',
        'source_url':       raw['source_url'],
        'manual_url':       None,
        'manual_path':      None,
        'manual_scraped_at': None,
        'created_at':       NOW,
        'specs':            specs,
    }


def main():
    out_dir  = os.path.join(DATA_ROOT, DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, 'products.jsonl')

    existing_ids = load_existing_ids(jsonl_path)
    print(f'既存: {len(existing_ids)}件')

    # 1. 製品コード収集
    print('\n=== STEP1: 製品コード収集 ===')
    codes = get_all_codes(LIST_URL)
    print(f'収集: {len(codes)}件')

    # 2. 各製品のスペック取得・保存
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

        entry = build_mb_entry(raw)
        if not entry:
            failed += 1
            continue

        save_entry(jsonl_path, entry)
        existing_ids.add(entry_id)
        added += 1

        if added % 20 == 0 or i % 50 == 0:
            print(f'  [{i}/{len(codes)}] 追加:{added} スキップ:{skipped} 失敗:{failed}')

    print(f'\n=== 完了 ===')
    print(f'追加: {added}件 / スキップ: {skipped}件 / 失敗: {failed}件')
    print(f'保存先: {jsonl_path}')


if __name__ == '__main__':
    main()
