"""
filter_compatible_parts() のユニットテスト
サーバーを起動せず、関数を直接テスト
"""
import os, sys
os.environ.setdefault('ANTHROPIC_API_KEY', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import filter_compatible_parts, _is_form_factor_compatible

# ================================================================
# テストデータ
# ================================================================

# CPU: Ryzen 5 7600X (AM5)
current_build_am5 = {
    'cpu': {'name': 'AMD Ryzen 5 7600X', 'socket': 'AM5', 'tdp_w': 105},
    'gpu': None, 'motherboard': None, 'ram': None,
    'case': None, 'psu': None, 'cooler': None,
}

# MB候補: AM5 x2、AM4 x1、LGA1700 x1
products_mb = {
    'motherboard': [
        {'name': 'ASUS ROG STRIX B650-A',  'specs': {'socket': 'AM5', 'memory_type': 'DDR5'}},
        {'name': 'MSI MAG X670E TOMAHAWK', 'specs': {'socket': 'AM5', 'memory_type': 'DDR5'}},
        {'name': 'Gigabyte B550 AORUS',    'specs': {'socket': 'AM4', 'memory_type': 'DDR4'}},
        {'name': 'ASUS PRIME Z790-A',      'specs': {'socket': 'LGA1700', 'memory_type': 'DDR5'}},
    ]
}

# MB確定 (AM5 + DDR5) → RAM候補
current_build_am5_mb = {
    **current_build_am5,
    'motherboard': {'name': 'ASUS ROG STRIX B650-A', 'socket': 'AM5', 'memory_type': 'DDR5'},
}

products_ram = {
    'ram': [
        {'name': 'Kingston FURY Beast DDR5-6000 16GB', 'specs': {'memory_type': 'DDR5'}},
        {'name': 'Crucial CT2K16G48C40U5 DDR5', 'specs': {}},           # specs.memory_typeなし・名前でDDR5判定
        {'name': 'G.SKILL Trident Z5 DDR5-6400',  'specs': {'memory_type': 'DDR5'}},
        {'name': 'Corsair Vengeance DDR4-3200',    'specs': {'memory_type': 'DDR4'}},  # 除外されるべき
    ]
}

# ================================================================
# テスト実行
# ================================================================

def test(name, condition, detail=""):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"{status}  {name}")
    if not condition:
        print(f"         詳細: {detail}")
    return condition

print("=" * 60)
print("filter_compatible_parts() ユニットテスト")
print("=" * 60)

# --- 修正1-A: AM5 CPU → AM4/LGA1700 MBを除外 ---
print("\n[修正1-A] AM5 CPU → MB互換フィルタ")
result_mb = filter_compatible_parts(products_mb, current_build_am5)
filtered_mb = result_mb.get('motherboard', [])
names_mb = [p['name'] for p in filtered_mb]
print(f"  フィルタ前: {len(products_mb['motherboard'])}件 → フィルタ後: {len(names_mb)}件")
print(f"  残ったMB: {names_mb}")

t1 = test("AM5 MBが2件残る", len(names_mb) == 2, f"actual={len(names_mb)}")
t2 = test("ASUS ROG STRIX B650-A (AM5) が残る",
          'ASUS ROG STRIX B650-A' in names_mb)
t3 = test("MSI MAG X670E TOMAHAWK (AM5) が残る",
          'MSI MAG X670E TOMAHAWK' in names_mb)
t4 = test("Gigabyte B550 AORUS (AM4) が除外される",
          'Gigabyte B550 AORUS' not in names_mb)
t5 = test("ASUS PRIME Z790-A (LGA1700) が除外される",
          'ASUS PRIME Z790-A' not in names_mb)

# --- 修正1-B: DDR5 MB → DDR4 RAMを除外 ---
print("\n[修正1-B] DDR5 MB → RAM互換フィルタ")
result_ram = filter_compatible_parts(products_ram, current_build_am5_mb)
filtered_ram = result_ram.get('ram', [])
names_ram = [p['name'] for p in filtered_ram]
print(f"  フィルタ前: {len(products_ram['ram'])}件 → フィルタ後: {len(names_ram)}件")
print(f"  残ったRAM: {names_ram}")

t6 = test("DDR5 RAMが3件残る", len(names_ram) == 3, f"actual={len(names_ram)}")
t7 = test("Corsair DDR4-3200 が除外される",
          'Corsair Vengeance DDR4-3200' not in names_ram)
t8 = test("specs.memory_typeなしでも名前からDDR5判定される",
          'Crucial CT2K16G48C40U5 DDR5' in names_ram)

# --- 修正1-C: current_buildにCPUなし → フィルタ無効（全件通す）---
print("\n[修正1-C] current_buildにCPUなし → MBフィルタ無効")
current_no_cpu = {k: None for k in current_build_am5}
result_no_cpu = filter_compatible_parts(products_mb, current_no_cpu)
names_no_cpu = [p['name'] for p in result_no_cpu.get('motherboard', [])]
t9 = test("CPUなしなら全MB(4件)通る", len(names_no_cpu) == 4, f"actual={len(names_no_cpu)}")

# --- フォームファクター互換 ---
print("\n[修正1-D] フォームファクター互換判定")
t10 = test("Mini-ITX MB × ATXケース → OK",  _is_form_factor_compatible('mini-itx', 'atx'))
t11 = test("ATX MB × ATXケース → OK",        _is_form_factor_compatible('atx', 'atx'))
t12 = test("E-ATX MB × ATXケース → NG",      not _is_form_factor_compatible('e-atx', 'atx'))
t13 = test("ATX MB × Micro-ATXケース → NG",  not _is_form_factor_compatible('atx', 'micro-atx'))

# --- 総括 ---
all_tests = [t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13]
passed = sum(all_tests)
total  = len(all_tests)
print(f"\n{'=' * 60}")
print(f"結果: {passed}/{total} PASS {'✅ 全テスト通過' if passed == total else '❌ 失敗あり'}")
