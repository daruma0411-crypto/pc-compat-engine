"""
MB スクレイパー完了を待って、残り4カテゴリを連続実行
"""
import sys, os, subprocess, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT  = os.path.join(BASE_DIR, 'workspace', 'data')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

MB_PATH = os.path.join(DATA_ROOT, 'kakaku_mb', 'products.jsonl')

STEPS = [
    ('CPU',        'kakaku_scraper_cpu.py',    'kakaku_cpu'),
    ('ケース',      'kakaku_scraper_case.py',   'kakaku_case'),
    ('PSU',        'kakaku_scraper_psu.py',    'kakaku_psu'),
    ('CPUクーラー', 'kakaku_scraper_cooler.py', 'kakaku_cooler'),
]

def count(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())

def wait_for_mb():
    """MB件数が60秒間増えなければ完了とみなす"""
    print('MB スクレイパー完了待機中...')
    prev = count(MB_PATH)
    while True:
        time.sleep(60)
        cur = count(MB_PATH)
        print(f'  MB: {cur}件 (前回: {prev}件)')
        if cur == prev:
            print(f'  → 60秒間変化なし → 完了とみなす ({cur}件)')
            return cur
        prev = cur

def run(label, script, dir_name):
    before = count(os.path.join(DATA_ROOT, dir_name, 'products.jsonl'))
    print(f'\n{"="*55}')
    print(f'[START] {label}')
    print(f'{"="*55}')
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, script)],
        cwd=BASE_DIR, encoding='utf-8', errors='replace',
    )
    after = count(os.path.join(DATA_ROOT, dir_name, 'products.jsonl'))
    status = '完了' if r.returncode == 0 else 'エラー'
    print(f'[{status}] {label}: +{after - before}件 (合計 {after}件)')
    return r.returncode == 0, after

def main():
    mb_count = wait_for_mb()
    print(f'\nMB完了: {mb_count}件')

    results = [('MB', True, mb_count)]
    for label, script, dir_name in STEPS:
        ok, total = run(label, script, dir_name)
        results.append((label, ok, total))

    print(f'\n{"="*55}')
    print('【全カテゴリ完了サマリー】')
    for label, ok, total in results:
        mark = '✓' if ok else '✗'
        print(f'  {mark} {label:12}: {total:5}件')
    print(f'{"="*55}')

    # git commit
    print('\ngit add & commit...')
    subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR)
    subprocess.run(
        ['git', 'commit', '-m', f'feat: 価格.com全カテゴリスクレイプ完了 MB:{mb_count}件+CPU/ケース/PSU/クーラー'],
        cwd=BASE_DIR
    )
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR)
    print('push完了')

if __name__ == '__main__':
    main()
