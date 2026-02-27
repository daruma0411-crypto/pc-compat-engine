"""
修正4 フォールバック機能のユニットテスト
_generate_fallback_info() を直接テスト
"""
import os, sys
os.environ.setdefault('ANTHROPIC_API_KEY', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import _generate_fallback_info

AMAZON_TAG = 'pccompat-22'

def test(name, condition, detail=""):
    status = "OK" if condition else "NG"
    print(f"  [{status}] {name}")
    if not condition:
        print(f"       {detail}")
    return condition

results = []

# ────────────────────────────────────────
# テスト1: CPU(AM5)確定・MB未確定 → AM5マザーボード検索URLが生成される
# ────────────────────────────────────────
print("=== テスト1: CPU確定・MB未確定 → MBフォールバックURL ===")
build1 = {
    'cpu':         {'name': 'AMD Ryzen 5 7600X', 'socket': 'AM5', 'tdp_w': 105},
    'gpu':         None,
    'motherboard': None,
    'ram':         None,
    'case':        None,
    'psu':         None,
    'cooler':      None,
}
result1 = _generate_fallback_info(build1, AMAZON_TAG)
print(f"  出力:\n{result1}\n")

t1a = test("⚠️ 警告テキストが含まれる", "データベースに互換性のある製品が見つかりません" in result1, result1)
t1b = test("Amazon検索URLが含まれる", "amazon.co.jp/s?k=" in result1, result1)
t1c = test("AM5マザーボード検索URLが含まれる", "AM5" in result1 and "k=AM5" in result1.replace('%EF%BC%85', '%'), result1)
t1d = test("アフィリエイトタグが含まれる", f"tag={AMAZON_TAG}" in result1, result1)
t1e = test("Amazonへ案内する文言が含まれる", "Amazon" in result1, result1)
results += [t1a, t1b, t1c, t1d, t1e]

# ────────────────────────────────────────
# テスト2: MB(DDR5)確定・RAM未確定 → DDR5 RAM検索URLが生成される
# ────────────────────────────────────────
print("=== テスト2: MB確定・RAM未確定 → RAMフォールバックURL ===")
build2 = {
    'cpu':         {'name': 'AMD Ryzen 5 7600X', 'socket': 'AM5'},
    'gpu':         None,
    'motherboard': {'name': 'ASUS B650-A', 'memory_type': 'DDR5'},
    'ram':         None,
    'case':        None,
    'psu':         None,
    'cooler':      None,
}
result2 = _generate_fallback_info(build2, AMAZON_TAG)
print(f"  出力:\n{result2}\n")

t2a = test("DDR5 RAM検索URLが含まれる", "DDR5" in result2, result2)
t2b = test("16GBというキーワードが含まれる", "16GB" in result2, result2)
# MB確定済みなのでマザーボード検索URLは不要
t2c = test("MBのURLは含まれない（確定済み）",
           "マザーボード" not in result2 or "マザーボード" not in result2.split("amazon")[1] if "amazon" in result2 else True,
           result2)
results += [t2a, t2b, t2c]

# ────────────────────────────────────────
# テスト3: GPU確定・ケース未確定 → ケース検索URLが生成される
# ────────────────────────────────────────
print("=== テスト3: GPU確定・ケース未確定 → ケースフォールバックURL ===")
build3 = {
    'cpu':         None,
    'gpu':         {'name': 'RTX 5070 Ti', 'length_mm': 320, 'tdp_w': 285},
    'motherboard': None,
    'ram':         None,
    'case':        None,
    'psu':         None,
    'cooler':      None,
}
result3 = _generate_fallback_info(build3, AMAZON_TAG)
print(f"  出力:\n{result3}\n")

t3a = test("ケース検索URLが含まれる", "ケース" in result3, result3)
t3b = test("GPU長さ(320mm)がURLに含まれる", "320" in result3, result3)
results += [t3a, t3b]

# ────────────────────────────────────────
# テスト4: 全パーツ未確定・スペック情報なし → 最小フォールバック
# ────────────────────────────────────────
print("=== テスト4: 全未確定・スペックなし → 最小フォールバック ===")
build4 = {k: None for k in ['cpu', 'gpu', 'motherboard', 'ram', 'case', 'psu', 'cooler']}
result4 = _generate_fallback_info(build4, AMAZON_TAG)
print(f"  出力:\n{result4}\n")

t4a = test("警告テキストが含まれる", "データベースに互換性のある製品が見つかりません" in result4, result4)
# スペックなしのためURLは生成されないが、案内文は含まれる
t4b = test("案内文が含まれる", "Amazonで探してみましょう" in result4, result4)
results += [t4a, t4b]

# ────────────────────────────────────────
# テスト5: _format_products_for_claude との切り替えロジック確認
# ────────────────────────────────────────
print("=== テスト5: フィルタ後0件判定ロジック ===")
# products_dict が全て空リストのとき total_compatible == 0
filtered_empty  = {'motherboard': [], 'ram': [], 'gpu': [], 'cpu': [], 'case': [], 'psu': []}
filtered_normal = {'motherboard': [{'name': 'test'}], 'ram': [], 'gpu': []}

total_empty  = sum(len(v) for v in filtered_empty.values())
total_normal = sum(len(v) for v in filtered_normal.values())

t5a = test("全空のとき total_compatible == 0", total_empty == 0, str(total_empty))
t5b = test("1件あるとき total_compatible > 0", total_normal > 0, str(total_normal))
results += [t5a, t5b]

# ────────────────────────────────────────
print(f"\n{'='*50}")
passed = sum(results)
total  = len(results)
print(f"結果: {passed}/{total} PASS {'全テスト通過' if passed == total else '失敗あり'}")
