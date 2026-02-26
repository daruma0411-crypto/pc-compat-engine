"""DB照合デバッグ: "RTX 4070" がどの製品にマッチするか確認"""
import sys, os
sys.path.insert(0, r'C:\Users\iwashita.AKGNET\pc-compat-engine')
sys.stdout.reconfigure(encoding='utf-8')

# app.pyから_lookup_pc_specsをインポート
import app

result = app._lookup_pc_specs(['RTX 4070'])
print('=== "RTX 4070" マッチ結果 ===')
if 'RTX 4070' in result:
    p = result['RTX 4070']
    print(f"  name: {p.get('name')}")
    print(f"  category: {p.get('category')}")
    print(f"  model: {p.get('model', 'N/A')}")
else:
    print('  マッチなし')

result2 = app._lookup_pc_specs(['RTX 4070 Super'])
print('\n=== "RTX 4070 Super" マッチ結果 ===')
if 'RTX 4070 Super' in result2:
    p = result2['RTX 4070 Super']
    print(f"  name: {p.get('name')}")
    print(f"  category: {p.get('category')}")
else:
    print('  マッチなし')

result3 = app._lookup_pc_specs(['RTX 4070 Ti Super'])
print('\n=== "RTX 4070 Ti Super" マッチ結果 ===')
if 'RTX 4070 Ti Super' in result3:
    p = result3['RTX 4070 Ti Super']
    print(f"  name: {p.get('name')}")
    print(f"  category: {p.get('category')}")
else:
    print('  マッチなし')
