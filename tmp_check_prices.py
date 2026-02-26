import json, os

DATA_ROOT = r'C:\Users\iwashita.AKGNET\pc-compat-engine\workspace\data'
cats = ['kakaku_cpu', 'kakaku_mb', 'kakaku_psu', 'kakaku_case', 'kakaku_cooler', 'kakaku_gpu', 'kakaku_ram']

for cat in cats:
    path = os.path.join(DATA_ROOT, cat, 'products.jsonl')
    if not os.path.exists(path):
        print(f'[{cat}] FILE NOT FOUND')
        continue
    with open(path, encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    total = len(lines)
    priced = 0
    for l in lines:
        try:
            d = json.loads(l)
            if d.get('price_min') and d['price_min'] > 0:
                priced += 1
        except:
            pass
    pct = priced/total*100 if total else 0
    print(f'[{cat}] total={total} priced={priced} ({pct:.1f}%)')
