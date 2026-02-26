"""価格更新プロセスのモニタリング"""
import json, os, time
from datetime import datetime

DATA_ROOT = r'C:\Users\iwashita.AKGNET\pc-compat-engine\workspace\data'
LOG_DIR = r'C:\Users\iwashita.AKGNET\pc-compat-engine\logs'

cats = [
    ('kakaku_cpu',    'price_cpu.log'),
    ('kakaku_mb',     'price_mb.log'),
    ('kakaku_psu',    'price_psu_case_cooler.log'),
    ('kakaku_case',   'price_psu_case_cooler.log'),
    ('kakaku_cooler', 'price_psu_case_cooler.log'),
]

print(f"\n=== モニタリング {datetime.now().strftime('%H:%M:%S')} ===")
for cat, logfile in cats:
    path = os.path.join(DATA_ROOT, cat, 'products.jsonl')
    if not os.path.exists(path):
        print(f'  [{cat}] ファイルなし')
        continue
    with open(path, encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    total = len(lines)
    priced = sum(1 for l in lines if '"price_min": ' in l and
                 json.loads(l).get('price_min', 0) > 0)
    pct = priced/total*100 if total else 0
    print(f'  [{cat}] {priced}/{total} ({pct:.1f}%)')

print("\n=== ログ末尾 ===")
for logfile in set(l for _, l in cats):
    lpath = os.path.join(LOG_DIR, logfile)
    if os.path.exists(lpath):
        size = os.path.getsize(lpath)
        print(f'  {logfile} ({size}B):')
        with open(lpath, encoding='utf-8') as f:
            lines = f.readlines()
        for l in lines[-3:]:
            print(f'    {l.rstrip()}')
