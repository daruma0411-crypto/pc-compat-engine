"""
価格.com 全カテゴリ スクレイパー 連続実行
MB → CPU → ケース → PSU → CPUクーラー の順で実行
"""
import sys, os, subprocess, time, json, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT  = os.path.join(BASE_DIR, 'workspace', 'data')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ('マザーボード', 'kakaku_scraper_mb.py',     'kakaku_mb'),
    ('CPU',          'kakaku_scraper_cpu.py',    'kakaku_cpu'),
    ('ケース',        'kakaku_scraper_case.py',   'kakaku_case'),
    ('PSU',          'kakaku_scraper_psu.py',    'kakaku_psu'),
    ('CPUクーラー',   'kakaku_scraper_cooler.py', 'kakaku_cooler'),
]

def count_lines(dir_name):
    path = os.path.join(DATA_ROOT, dir_name, 'products.jsonl')
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())

def run_step(label, script, dir_name):
    before = count_lines(dir_name)
    script_path = os.path.join(SCRIPT_DIR, script)
    print(f'\n{"="*60}')
    print(f'[START] {label} (既存: {before}件)')
    print(f'{"="*60}')

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        encoding='utf-8',
        errors='replace',
    )

    after = count_lines(dir_name)
    added = after - before
    ok = result.returncode == 0
    status = '✓ 完了' if ok else '✗ エラー'
    print(f'\n[{status}] {label}: {before}件 → {after}件 (+{added}件追加)')
    return ok, added

def print_summary(results):
    print(f'\n{"="*60}')
    print('【全カテゴリ 完了サマリー】')
    print(f'{"="*60}')
    total = 0
    for label, ok, added, dir_name in results:
        status = '✓' if ok else '✗'
        count  = count_lines(dir_name)
        print(f'  {status} {label:12}: {count:5}件 (+{added}件)')
        total += count
    print(f'  {"─"*40}')
    print(f'  全カテゴリ合計: {total}件')

def main():
    # MBが既に実行中の場合はスキップ可能
    skip_mb = count_lines('kakaku_mb') > 0
    print(f'kakaku_mb: {count_lines("kakaku_mb")}件 → {"実行済みのためスキップ" if skip_mb else "実行します"}')

    results = []
    for label, script, dir_name in STEPS:
        if skip_mb and dir_name == 'kakaku_mb':
            before = count_lines(dir_name)
            print(f'\n[SKIP] {label}: {before}件 (既存データあり)')
            results.append((label, True, 0, dir_name))
            continue

        ok, added = run_step(label, script, dir_name)
        results.append((label, ok, added, dir_name))
        if not ok:
            print(f'[WARN] {label}でエラーが発生しましたが続行します')

    print_summary(results)

if __name__ == '__main__':
    main()
