#!/usr/bin/env python3
"""
DB データ補完スクリプト
設計書: Downloads/db_enrich_plan.md

処理順:
1. CPU: ゴミ削除 → 重複排除 → socket付与 → TDP付与 → memory_type付与
2. GPU: カテゴリ誤分類修正 → チップ名抽出 → length_mm/tdp_w補完
3. RAM: capacity_gb補完
4. 結果サマリー出力
"""

import json
import re
import shutil
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "workspace" / "data"

# ---------------------------------------------------------------------------
# CPU 設定
# ---------------------------------------------------------------------------

SOCKET_RULES = [
    # AMD Ryzen (順序注意: 9000, 7000 → AM5 / 5000, 3000 → AM4)
    (r'ryzen.*9\d{3}',                        'AM5'),
    (r'ryzen.*7\d{3}',                        'AM5'),
    (r'ryzen.*5\d{3}',                        'AM4'),
    (r'ryzen.*3\d{3}',                        'AM4'),
    # Intel
    (r'core ultra',                            'LGA1851'),
    (r'i[3579][-\s]?14\d{2}|14[0-9]{3}[a-z]?', 'LGA1700'),
    (r'i[3579][-\s]?13\d{2}|13[0-9]{3}[a-z]?', 'LGA1700'),
    (r'i[3579][-\s]?12\d{2}|12[0-9]{3}[a-z]?', 'LGA1700'),
]

TDP_MAP = {
    # Ryzen 9000 (AM5)
    '9950x': 170, '9900x': 120, '9800x3d': 120,
    '9700x': 65, '9600x': 65, '9600': 65, '9500f': 65,
    # Ryzen 7000 (AM5)
    '7950x': 170, '7900x': 170, '7800x3d': 120,
    '7700x': 105, '7700': 65, '7600x': 105, '7600': 65, '7500f': 65,
    # Ryzen 5000 (AM4)
    '5950x': 105, '5900x': 105, '5800x3d': 105, '5800x': 105,
    '5700x': 65, '5700g': 65, '5600x': 65, '5600g': 65, '5600': 65, '5500': 65,
    '5600gt': 65, '5600xt': 65, '5500gt': 65, '5700xt': 65,
    # Ryzen 3000 (AM4)
    '3950x': 105, '3900x': 105, '3800x': 105,
    '3700x': 65, '3600x': 95, '3600': 65, '3600xt': 95,
    '3500': 65, '3400g': 65, '3200g': 65, '3100': 65,
    # Core Ultra 200 (LGA1851)
    'ultra 9 285k': 125, 'ultra 7 265k': 125, 'ultra 5 245k': 125,
    'ultra 9 285': 65, 'ultra 7 265': 65, 'ultra 7 265f': 65,
    'ultra 5 225': 65, 'ultra 5 225f': 65,
    # Core 14世代 (LGA1700)
    '14900k': 125, '14700k': 125, '14600k': 125,
    '14900': 65, '14700': 65, '14600': 65, '14500': 65,
    '14400': 65, '14400f': 65, '14100': 60, '14100f': 60,
    # Core 13世代 (LGA1700)
    '13900k': 125, '13700k': 125, '13600k': 125,
    '13900': 65, '13700': 65, '13600': 65, '13500': 65,
    '13400': 65, '13400f': 65, '13100': 60, '13100f': 60,
    # Core 12世代 (LGA1700)
    '12900k': 125, '12700k': 125, '12600k': 125,
    '12900': 65, '12700': 65, '12600': 65, '12500': 65,
    '12400': 65, '12400f': 65, '12100': 60, '12100f': 60,
}

SOCKET_MEMORY_MAP = {
    'AM5':     ['DDR5'],
    'AM4':     ['DDR4'],
    'LGA1700': ['DDR4', 'DDR5'],
    'LGA1851': ['DDR5'],
}

# ---------------------------------------------------------------------------
# GPU 設定
# ---------------------------------------------------------------------------

# length_mmは安全側（最大値に近い値）を使用
GPU_CHIP_REFERENCE = {
    # RTX 40系
    'RTX 4060':          {'length_mm': 240, 'tdp_w': 115, 'vram_gb': 8},
    'RTX 4060 TI':       {'length_mm': 285, 'tdp_w': 160, 'vram_gb': 8},
    'RTX 4070':          {'length_mm': 285, 'tdp_w': 200, 'vram_gb': 12},
    'RTX 4070 SUPER':    {'length_mm': 304, 'tdp_w': 220, 'vram_gb': 12},
    'RTX 4070 TI':       {'length_mm': 305, 'tdp_w': 285, 'vram_gb': 12},
    'RTX 4070 TI SUPER': {'length_mm': 305, 'tdp_w': 285, 'vram_gb': 16},
    'RTX 4080':          {'length_mm': 340, 'tdp_w': 320, 'vram_gb': 16},
    'RTX 4080 SUPER':    {'length_mm': 340, 'tdp_w': 320, 'vram_gb': 16},
    'RTX 4090':          {'length_mm': 370, 'tdp_w': 450, 'vram_gb': 24},
    # RTX 30系
    'RTX 3050':          {'length_mm': 224, 'tdp_w': 130, 'vram_gb': 8},
    'RTX 3060':          {'length_mm': 242, 'tdp_w': 170, 'vram_gb': 12},
    'RTX 3060 TI':       {'length_mm': 242, 'tdp_w': 200, 'vram_gb': 8},
    'RTX 3070':          {'length_mm': 285, 'tdp_w': 220, 'vram_gb': 8},
    'RTX 3070 TI':       {'length_mm': 285, 'tdp_w': 290, 'vram_gb': 8},
    'RTX 3080':          {'length_mm': 285, 'tdp_w': 320, 'vram_gb': 10},
    'RTX 3080 TI':       {'length_mm': 285, 'tdp_w': 350, 'vram_gb': 12},
    'RTX 3090':          {'length_mm': 320, 'tdp_w': 350, 'vram_gb': 24},
    'RTX 3090 TI':       {'length_mm': 336, 'tdp_w': 450, 'vram_gb': 24},
    # RTX 20系
    'RTX 2060':          {'length_mm': 229, 'tdp_w': 160, 'vram_gb': 6},
    'RTX 2060 SUPER':    {'length_mm': 269, 'tdp_w': 175, 'vram_gb': 8},
    'RTX 2070':          {'length_mm': 268, 'tdp_w': 175, 'vram_gb': 8},
    'RTX 2070 SUPER':    {'length_mm': 268, 'tdp_w': 215, 'vram_gb': 8},
    'RTX 2080':          {'length_mm': 268, 'tdp_w': 215, 'vram_gb': 8},
    'RTX 2080 SUPER':    {'length_mm': 268, 'tdp_w': 250, 'vram_gb': 8},
    'RTX 2080 TI':       {'length_mm': 267, 'tdp_w': 260, 'vram_gb': 11},
    # RX 7000系 (RDNA 3)
    'RX 7600':           {'length_mm': 220, 'tdp_w': 165, 'vram_gb': 8},
    'RX 7600 XT':        {'length_mm': 220, 'tdp_w': 190, 'vram_gb': 16},
    'RX 7700 XT':        {'length_mm': 267, 'tdp_w': 245, 'vram_gb': 12},
    'RX 7800 XT':        {'length_mm': 267, 'tdp_w': 263, 'vram_gb': 16},
    'RX 7900 GRE':       {'length_mm': 267, 'tdp_w': 260, 'vram_gb': 16},
    'RX 7900 XT':        {'length_mm': 287, 'tdp_w': 315, 'vram_gb': 20},
    'RX 7900 XTX':       {'length_mm': 287, 'tdp_w': 355, 'vram_gb': 24},
    # RX 6000系 (RDNA 2)
    'RX 6400':           {'length_mm': 165, 'tdp_w':  53, 'vram_gb': 4},
    'RX 6500 XT':        {'length_mm': 180, 'tdp_w':  107, 'vram_gb': 4},
    'RX 6600':           {'length_mm': 235, 'tdp_w': 132, 'vram_gb': 8},
    'RX 6600 XT':        {'length_mm': 267, 'tdp_w': 160, 'vram_gb': 8},
    'RX 6650 XT':        {'length_mm': 267, 'tdp_w': 180, 'vram_gb': 8},
    'RX 6700':           {'length_mm': 267, 'tdp_w': 220, 'vram_gb': 10},
    'RX 6700 XT':        {'length_mm': 267, 'tdp_w': 230, 'vram_gb': 12},
    'RX 6750 XT':        {'length_mm': 267, 'tdp_w': 250, 'vram_gb': 12},
    'RX 6800':           {'length_mm': 267, 'tdp_w': 250, 'vram_gb': 16},
    'RX 6800 XT':        {'length_mm': 267, 'tdp_w': 300, 'vram_gb': 16},
    'RX 6900 XT':        {'length_mm': 267, 'tdp_w': 300, 'vram_gb': 16},
    'RX 6950 XT':        {'length_mm': 267, 'tdp_w': 335, 'vram_gb': 16},
    # RX 5000系 (RDNA 1)
    'RX 5500 XT':        {'length_mm': 228, 'tdp_w': 130, 'vram_gb': 8},
    'RX 5600 XT':        {'length_mm': 235, 'tdp_w': 150, 'vram_gb': 6},
    'RX 5700':           {'length_mm': 264, 'tdp_w': 180, 'vram_gb': 8},
    'RX 5700 XT':        {'length_mm': 264, 'tdp_w': 225, 'vram_gb': 8},
}

MAKER_GPU_DIRS = [
    'asus', 'gigabyte', 'msi', 'palit', 'zotac', 'sapphire',
    'powercolor', 'gainward', 'sparkle', 'pny', 'kuroutoshikou',
    'asrock',
]

# ---------------------------------------------------------------------------
# ユーティリティ関数
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list:
    items = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_jsonl(path: Path, items: list) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def backup(path: Path) -> None:
    bak = path.with_suffix('.jsonl.bak')
    shutil.copy2(path, bak)
    print(f"  Backup: {bak.name}")


def count_filled(items: list, *keys) -> int:
    """specs内のキーが全て埋まっているものの件数を返す"""
    count = 0
    for item in items:
        specs = item.get('specs') or {}
        if all(specs.get(k) is not None for k in keys):
            count += 1
    return count


def pct(numerator, denominator) -> str:
    if denominator == 0:
        return '0%'
    return f'{numerator / denominator * 100:.0f}%'


# ---------------------------------------------------------------------------
# CPU 処理
# ---------------------------------------------------------------------------

def is_valid_cpu(name: str) -> bool:
    """SOCKET_RULESのいずれかにマッチするCPUだけ保持"""
    n = name.lower()
    for pattern, _ in SOCKET_RULES:
        if re.search(pattern, n):
            return True
    return False


def get_socket(name: str) -> str | None:
    n = name.lower()
    for pattern, socket in SOCKET_RULES:
        if re.search(pattern, n):
            return socket
    return None


def normalize_cpu_name(name: str) -> str:
    """BOX/バルク/Tray/with Cooler等のサフィックスを除去して型番を正規化"""
    n = name
    # 「インテル」→「Intel」
    n = n.replace('インテル ', 'Intel ').replace('インテル　', 'Intel ')
    # サフィックス除去（順序注意）
    n = re.sub(r'\s+with\s+\w[\w\s]*?Cooler\b.*$', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+(BOX|バルク|Bulk|Tray|OEM|MPK)\b.*$', '', n, flags=re.IGNORECASE)
    n = n.strip()
    return n


def get_tdp(name: str) -> int | None:
    n = name.lower()
    # 長いキーから先にマッチ（"ultra 9 285k" が "ultra 9 285" より先）
    for model, tdp in sorted(TDP_MAP.items(), key=lambda x: -len(x[0])):
        if model in n:
            return tdp
    return None


def process_cpu(cpu_path: Path) -> None:
    print("\n=== タスク1: CPU 補完 ===")
    items = load_jsonl(cpu_path)
    total_before = len(items)

    socket_before = count_filled(items, 'socket')
    tdp_before    = count_filled(items, 'tdp_w')
    print(f"  補完前: {total_before}件")
    print(f"  socket充足率 (補完前): {pct(socket_before, total_before)}")
    print(f"  tdp充足率    (補完前): {pct(tdp_before, total_before)}")

    # 1-1. ゴミ削除
    items = [p for p in items if is_valid_cpu(p['name'])]
    print(f"  ゴミ削除後: {len(items)}件")

    # 1-2. 重複排除
    name_map: dict[str, list] = defaultdict(list)
    for p in items:
        key = normalize_cpu_name(p['name']).lower()
        name_map[key].append(p)

    deduped = []
    for key, group in name_map.items():
        best = min(group, key=lambda x: x.get('price_min') or 9_999_999)
        deduped.append(best)

    deduped.sort(key=lambda x: x['name'])
    print(f"  重複排除後: {len(deduped)}件")
    items = deduped

    # 1-3. socket 付与
    for p in items:
        specs = p.setdefault('specs', {})
        if not specs.get('socket'):
            socket = get_socket(p['name'])
            if socket:
                specs['socket'] = socket

    # 1-4. TDP / memory_type 付与
    for p in items:
        specs = p.setdefault('specs', {})
        if not specs.get('tdp_w'):
            tdp = get_tdp(p['name'])
            if tdp:
                specs['tdp_w'] = tdp
        if not specs.get('memory_type'):
            socket = specs.get('socket')
            if socket and socket in SOCKET_MEMORY_MAP:
                specs['memory_type'] = SOCKET_MEMORY_MAP[socket]

    socket_after = count_filled(items, 'socket')
    tdp_after    = count_filled(items, 'tdp_w')
    total_after  = len(items)
    print(f"  補完後: {total_after}件")
    print(f"  socket充足率 (補完後): {pct(socket_after, total_after)}")
    print(f"  tdp充足率    (補完後): {pct(tdp_after, total_after)}")

    save_jsonl(cpu_path, items)
    print(f"  保存完了: {cpu_path}")


# ---------------------------------------------------------------------------
# GPU 処理
# ---------------------------------------------------------------------------

def extract_gpu_chip(name: str, gpu_chip_field: str = '') -> str | None:
    """GPU名とgpu_chipフィールドからチップ名を正規化して抽出"""
    for text in [gpu_chip_field, name]:
        if not text:
            continue
        # NVIDIA RTX（スペースなし/ハイフン区切りも対応）
        m = re.search(
            r'RTX[\s\-]?(\d{4})[\s\-]?(Ti[\s\-]?SUPER|Ti|SUPER)?',
            text, re.IGNORECASE
        )
        if m:
            number = m.group(1)
            suffix_raw = (m.group(2) or '').strip()
            suffix = re.sub(r'[\s\-]+', ' ', suffix_raw).upper().strip()
            chip = f"RTX {number}"
            if suffix:
                chip += f" {suffix}"
            return chip
        # AMD RX（XTX, GRE, XT にも対応）
        m = re.search(
            r'RX[\s\-]?(\d{4})[\s\-]?(XTX|GRE|XT)?',
            text, re.IGNORECASE
        )
        if m:
            number = m.group(1)
            suffix = (m.group(2) or '').strip().upper()
            chip = f"RX {number}"
            if suffix:
                chip += f" {suffix}"
            return chip
    return None


def build_chip_map() -> dict:
    """メーカーGPUデータからチップ→スペックのマップを構築"""
    chip_map: dict[str, dict] = {}

    for maker_dir in MAKER_GPU_DIRS:
        path = DATA_DIR / maker_dir / 'products.jsonl'
        if not path.exists():
            continue
        items = load_jsonl(path)
        for p in items:
            if p.get('category') != 'gpu':
                continue
            specs = p.get('specs') or {}
            chip = extract_gpu_chip(p['name'], specs.get('gpu_chip', ''))
            if not chip:
                continue
            if chip not in chip_map:
                chip_map[chip] = {}
            # length_mm: 最大値を採用（安全側）
            length = specs.get('length_mm')
            if length and (chip_map[chip].get('length_mm') is None or length > chip_map[chip]['length_mm']):
                chip_map[chip]['length_mm'] = length
            # tdp_w: 最大値を採用
            tdp = specs.get('tdp_w')
            if tdp and (chip_map[chip].get('tdp_w') is None or tdp > chip_map[chip]['tdp_w']):
                chip_map[chip]['tdp_w'] = tdp
            # vram_gb: 最初の値
            vram = specs.get('vram_gb')
            if vram and chip_map[chip].get('vram_gb') is None:
                chip_map[chip]['vram_gb'] = vram

    print(f"  chip_map構築: {len(chip_map)}チップ")
    return chip_map


def fix_gpu_category() -> int:
    """全データディレクトリを走査してGPUの誤分類を修正"""
    gpu_pattern = re.compile(r'\b(GeForce|Radeon|RTX|RX)\b', re.IGNORECASE)
    fixed = 0

    for products_path in DATA_DIR.glob('*/products.jsonl'):
        items = load_jsonl(products_path)
        changed = False
        for p in items:
            if p.get('category') != 'gpu' and gpu_pattern.search(p.get('name', '')):
                p['category'] = 'gpu'
                changed = True
                fixed += 1
        if changed:
            save_jsonl(products_path, items)
            print(f"    誤分類修正: {products_path.parent.name} ({fixed}件)")

    return fixed


def process_gpu(gpu_path: Path) -> None:
    print("\n=== タスク2: GPU 補完 ===")

    # 2-1. カテゴリ誤分類修正
    print("  [2-1] カテゴリ誤分類修正...")
    fixed_count = fix_gpu_category()
    print(f"  修正件数: {fixed_count}件")

    # kakaku_gpu を再読み込み（修正後）
    items = load_jsonl(gpu_path)
    total = len(items)

    length_before = count_filled(items, 'length_mm')
    tdp_before    = count_filled(items, 'tdp_w')
    print(f"  補完前: {total}件")
    print(f"  length_mm充足率 (補完前): {pct(length_before, total)}")
    print(f"  tdp_w充足率     (補完前): {pct(tdp_before, total)}")

    # 2-2. chip_mapを構築
    print("  [2-2] メーカーデータからchip_map構築...")
    chip_map = build_chip_map()

    # 2-3. kakaku_gpuに補完
    print("  [2-3] kakaku_gpuに補完...")
    for p in items:
        specs = p.setdefault('specs', {})
        chip = extract_gpu_chip(p['name'], specs.get('gpu_chip', ''))
        if not chip:
            continue

        # chip_mapを優先、なければGPU_CHIP_REFERENCEを使用
        ref = chip_map.get(chip) or GPU_CHIP_REFERENCE.get(chip)
        if not ref:
            continue

        if not specs.get('length_mm') and ref.get('length_mm'):
            specs['length_mm'] = ref['length_mm']
        if not specs.get('tdp_w') and ref.get('tdp_w'):
            specs['tdp_w'] = ref['tdp_w']
        if not specs.get('vram_gb') and ref.get('vram_gb'):
            specs['vram_gb'] = ref['vram_gb']

    length_after = count_filled(items, 'length_mm')
    tdp_after    = count_filled(items, 'tdp_w')
    print(f"  length_mm充足率 (補完後): {pct(length_after, total)}")
    print(f"  tdp_w充足率     (補完後): {pct(tdp_after, total)}")

    save_jsonl(gpu_path, items)
    print(f"  保存完了: {gpu_path}")


# ---------------------------------------------------------------------------
# RAM 処理
# ---------------------------------------------------------------------------

def extract_ram_capacity(name: str) -> int | None:
    """名前からRAMの合計容量(GB)を抽出"""
    # "XXGBxN" パターン
    m = re.search(r'(\d+)\s*GB\s*[xX×]\s*(\d+)', name)
    if m:
        return int(m.group(1)) * int(m.group(2))
    # "XX GB N枚組" パターン
    m = re.search(r'(\d+)\s*GB.*?(\d+)\s*枚', name)
    if m:
        return int(m.group(1)) * int(m.group(2))
    # 単体 "XXGB" パターン（最後の手段）
    m = re.search(r'(\d+)\s*GB', name)
    if m:
        return int(m.group(1))
    return None


def process_ram(ram_path: Path) -> None:
    print("\n=== タスク3: RAM 補完 ===")
    items = load_jsonl(ram_path)
    total = len(items)

    cap_before = count_filled(items, 'capacity_gb')
    print(f"  補完前: {total}件")
    print(f"  capacity_gb充足率 (補完前): {pct(cap_before, total)}")

    for p in items:
        specs = p.setdefault('specs', {})
        if specs.get('capacity_gb') is None:
            cap = extract_ram_capacity(p['name'])
            if cap:
                specs['capacity_gb'] = cap

    cap_after = count_filled(items, 'capacity_gb')
    print(f"  capacity_gb充足率 (補完後): {pct(cap_after, total)}")

    save_jsonl(ram_path, items)
    print(f"  保存完了: {ram_path}")


# ---------------------------------------------------------------------------
# 検証テスト
# ---------------------------------------------------------------------------

def run_tests(cpu_path: Path, gpu_path: Path) -> None:
    print("\n=== 検証テスト ===")
    all_pass = True

    cpu_items = load_jsonl(cpu_path)
    gpu_items = load_jsonl(gpu_path)

    # テスト1: Ryzen 5 7600X → socket:AM5, tdp_w:105
    t1 = next((p for p in cpu_items if '7600x' in p['name'].lower()), None)
    if t1:
        specs = t1.get('specs', {})
        ok = specs.get('socket') == 'AM5' and specs.get('tdp_w') == 105
        print(f"  テスト1 [{'PASS' if ok else 'FAIL'}]: Ryzen 5 7600X → socket={specs.get('socket')}, tdp_w={specs.get('tdp_w')}")
        if not ok:
            all_pass = False
    else:
        print("  テスト1 [SKIP]: Ryzen 5 7600X が見つからない")

    # テスト2: RTX 4060 Ti → length_mm, tdp_w, vram_gb が存在
    t2 = next((p for p in gpu_items if re.search(r'rtx[\s-]*4060[\s-]*ti', p['name'], re.IGNORECASE)), None)
    if t2:
        specs = t2.get('specs', {})
        ok = specs.get('length_mm') and specs.get('tdp_w') and specs.get('vram_gb')
        print(f"  テスト2 [{'PASS' if ok else 'FAIL'}]: RTX 4060 Ti → length_mm={specs.get('length_mm')}, tdp_w={specs.get('tdp_w')}, vram_gb={specs.get('vram_gb')}")
        if not ok:
            all_pass = False
    else:
        print("  テスト2 [SKIP]: RTX 4060 Ti が見つからない")

    # テスト3: CPU件数
    cpu_count = len(cpu_items)
    ok3 = 80 <= cpu_count <= 500
    print(f"  テスト3 [{'PASS' if ok3 else 'FAIL'}]: CPU件数 = {cpu_count} (期待: 80〜500件)")
    if not ok3:
        all_pass = False

    # テスト4: ゲーミングGPU（GeForce RTX / Radeon RX）のlength_mm充足率 80%以上
    def is_gaming_gpu(p):
        name = p.get('name', '')
        gpu_chip = (p.get('specs') or {}).get('gpu_chip', '')
        for text in [gpu_chip, name]:
            if re.search(r'GeForce\s+RTX\s+\d{4}', text, re.IGNORECASE):
                return True
            if re.search(r'Radeon\s+RX\s+\d{4}', text, re.IGNORECASE):
                return True
        return False

    gaming_gpus = [p for p in gpu_items if is_gaming_gpu(p)]
    gaming_with_len = [p for p in gaming_gpus if (p.get('specs') or {}).get('length_mm')]
    length_filled = count_filled(gpu_items, 'length_mm')
    ok4 = len(gaming_with_len) / len(gaming_gpus) >= 0.80 if gaming_gpus else False
    print(f"  テスト4 [{'PASS' if ok4 else 'FAIL'}]: ゲーミングGPU length_mm = {pct(len(gaming_with_len), len(gaming_gpus))} ({len(gaming_with_len)}/{len(gaming_gpus)}件)")
    print(f"           全GPU length_mm = {pct(length_filled, len(gpu_items))} (ワークステーション向け除く)")
    if not ok4:
        all_pass = False

    # テスト5: MB/ケース/PSU の件数が壊れていないこと
    for cat_dir in ['asrock_mb', 'asus_mb', 'gigabyte_mb', 'msi_mb', 'cases', 'seasonic_psu']:
        p = DATA_DIR / cat_dir / 'products.jsonl'
        if p.exists():
            count = sum(1 for line in open(p, encoding='utf-8') if line.strip())
            ok5 = count > 0
            print(f"  テスト5 [{'PASS' if ok5 else 'FAIL'}]: {cat_dir} = {count}件")
            if not ok5:
                all_pass = False

    print(f"\n  {'全テスト PASS' if all_pass else '一部テスト FAIL'}")
    return all_pass


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DB データ補完スクリプト enrich_db.py")
    print("=" * 60)

    cpu_path = DATA_DIR / 'kakaku_cpu' / 'products.jsonl'
    gpu_path = DATA_DIR / 'kakaku_gpu' / 'products.jsonl'
    ram_path = DATA_DIR / 'kakaku_ram' / 'products.jsonl'

    # バックアップ（既にバックアップが存在する場合はスキップ）
    print("\n[Step 0] バックアップ")
    for path in [cpu_path, gpu_path, ram_path]:
        if path.exists():
            bak = path.with_suffix('.jsonl.bak')
            if not bak.exists():
                backup(path)
            else:
                print(f"  既存バックアップを使用: {bak.name}")
        else:
            print(f"  注意: {path} が存在しません")

    # CPU（バックアップから処理する）
    if cpu_path.with_suffix('.jsonl.bak').exists():
        # バックアップから元データを使う
        bak = cpu_path.with_suffix('.jsonl.bak')
        import shutil as _shutil
        _shutil.copy2(bak, cpu_path)
        print(f"\n  バックアップから復元して処理: kakaku_cpu")
    if cpu_path.exists():
        process_cpu(cpu_path)

    # GPU（バックアップから処理する）
    if gpu_path.with_suffix('.jsonl.bak').exists():
        bak = gpu_path.with_suffix('.jsonl.bak')
        import shutil as _shutil
        _shutil.copy2(bak, gpu_path)
        print(f"\n  バックアップから復元して処理: kakaku_gpu")
    if gpu_path.exists():
        process_gpu(gpu_path)

    # RAM（バックアップから処理する）
    if ram_path.with_suffix('.jsonl.bak').exists():
        bak = ram_path.with_suffix('.jsonl.bak')
        import shutil as _shutil
        _shutil.copy2(bak, ram_path)
        print(f"\n  バックアップから復元して処理: kakaku_ram")
    if ram_path.exists():
        process_ram(ram_path)

    # 検証テスト
    run_tests(cpu_path, gpu_path)

    print("\n完了!")


if __name__ == '__main__':
    main()
