"""DB内の4070系GPU確認"""
import json, os, glob, sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_ROOT = r'C:\Users\iwashita.AKGNET\pc-compat-engine\workspace\data'

found = []
for jsonl in glob.glob(os.path.join(DATA_ROOT, '**', 'products.jsonl'), recursive=True):
    with open(jsonl, encoding='utf-8') as f:
        for line in f:
            try:
                d = json.loads(line)
                name = d.get('name', '')
                if '4070' in name.lower() or '4070' in str(d.get('model', '')).lower():
                    cat = d.get('category', 'unknown')
                    found.append(f"[{cat}] {name}")
            except:
                pass

found.sort()
for x in found:
    print(x)
print(f'\n計 {len(found)} 件')
