"""
ケース / PSU / CPUクーラー 順次実行スクリプト
"""
import sys, os, subprocess, json

# ログファイルに出力
_log_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'kakaku_run2.log'
)
_log_fh = open(_log_path, 'w', encoding='utf-8', buffering=1)
sys.stdout = _log_fh
sys.stderr = _log_fh

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT  = os.path.join(BASE_DIR, 'workspace', 'data')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON     = sys.executable

STEPS = [
    ('ケース',      'kakaku_scraper_case.py',   'kakaku_case'),
    ('PSU',        'kakaku_scraper_psu.py',    'kakaku_psu'),
    ('CPUクーラー', 'kakaku_scraper_cooler.py', 'kakaku_cooler'),
]

def count(dir_name):
    path = os.path.join(DATA_ROOT, dir_name, 'products.jsonl')
    if not os.path.exists(path): return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())

def run(label, script, dir_name):
    before = count(dir_name)
    print(f'\n{"="*55}')
    print(f'[START] {label} (既存: {before}件)')
    print(f'{"="*55}', flush=True)
    r = subprocess.run(
        [PYTHON, os.path.join(SCRIPT_DIR, script)],
        cwd=BASE_DIR,
    )
    after = count(dir_name)
    status = '完了' if r.returncode == 0 else 'エラー'
    print(f'[{status}] {label}: {before}件 → {after}件 (+{after-before}件)', flush=True)
    return r.returncode == 0, after

results = []
for label, script, dir_name in STEPS:
    ok, total = run(label, script, dir_name)
    results.append((label, ok, total))

print(f'\n{"="*55}')
print('【完了サマリー】')
for label, ok, total in results:
    mark = '✓' if ok else '✗'
    print(f'  {mark} {label:12}: {total:5}件')
print(f'{"="*55}', flush=True)

# git commit & push
print('\ngit commit & push...')
subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR)
mb_c  = count('kakaku_mb')
cpu_c = count('kakaku_cpu')
case_c= count('kakaku_case')
psu_c = count('kakaku_psu')
cool_c= count('kakaku_cooler')
msg = (f'feat: 価格.com全カテゴリ完了 '
       f'MB:{mb_c} CPU:{cpu_c} ケース:{case_c} PSU:{psu_c} クーラー:{cool_c}')
subprocess.run(['git', 'commit', '-m', msg], cwd=BASE_DIR)
subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR)
print('push完了', flush=True)
_log_fh.flush()
