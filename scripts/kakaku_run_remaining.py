"""
MB完了後、残り4カテゴリを順次実行（Windowsデタッチプロセス対応版）
"""
import sys, os, subprocess, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT  = os.path.join(BASE_DIR, 'workspace', 'data')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON     = sys.executable

STEPS = [
    ('ケース',      'kakaku_scraper_case.py',   'kakaku_case'),   # SEOページ優先
    ('CPU',        'kakaku_scraper_cpu.py',    'kakaku_cpu'),
    ('PSU',        'kakaku_scraper_psu.py',    'kakaku_psu'),
    ('CPUクーラー', 'kakaku_scraper_cooler.py', 'kakaku_cooler'),
]

def count(dir_name):
    path = os.path.join(DATA_ROOT, dir_name, 'products.jsonl')
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for l in f if l.strip())

def wait_mb_finish():
    print('MB完了待機中...')
    prev = -1
    stable = 0
    while True:
        cur = count('kakaku_mb')
        if cur == prev:
            stable += 1
            print(f'  MB: {cur}件 (変化なし {stable}回目)')
            if stable >= 2:
                print(f'  → MB完了判定: {cur}件')
                return cur
        else:
            stable = 0
            print(f'  MB: {cur}件 (進行中)')
        prev = cur
        time.sleep(60)

def run_step(label, script, dir_name):
    before = count(dir_name)
    print(f'\n{"="*55}')
    print(f'[START] {label} (既存: {before}件)')
    print(f'{"="*55}')
    sys.stdout.flush()

    proc = subprocess.run(
        [PYTHON, os.path.join(SCRIPT_DIR, script)],
        cwd=BASE_DIR,
    )
    after = count(dir_name)
    added = after - before
    status = '完了' if proc.returncode == 0 else 'エラー'
    print(f'[{status}] {label}: {before}件 → {after}件 (+{added}件)')
    sys.stdout.flush()
    return proc.returncode == 0, after

def main():
    mb_count = wait_mb_finish()
    print(f'\nMB完了: {mb_count}件')

    results = [('MB', True, mb_count)]
    for label, script, dir_name in STEPS:
        ok, total = run_step(label, script, dir_name)
        results.append((label, ok, total))

    print(f'\n{"="*55}')
    print('【全カテゴリ完了サマリー】')
    grand = 0
    for label, ok, total in results:
        mark = '✓' if ok else '✗'
        print(f'  {mark} {label:12}: {total:5}件')
        grand += total
    print(f'  合計: {grand}件')
    print(f'{"="*55}')
    sys.stdout.flush()

    # SEOページ再生成
    print('\n' + '='*55)
    print('[START] SEOページ再生成')
    print('='*55)
    sys.stdout.flush()
    seo_result = subprocess.run(
        [PYTHON, os.path.join(SCRIPT_DIR, 'generate_seo_pages.py')],
        cwd=BASE_DIR,
    )
    seo_status = '完了' if seo_result.returncode == 0 else 'エラー'
    print(f'[{seo_status}] SEOページ生成')
    sys.stdout.flush()

    # git commit & push
    print('\ngit commit & push...')
    subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR)
    subprocess.run(
        ['git', 'commit', '-m',
         f'feat: 価格.com全カテゴリスクレイプ完了+SEOページ再生成 MB:{mb_count}件'],
        cwd=BASE_DIR
    )
    subprocess.run(['git', 'push', 'origin', 'main'], cwd=BASE_DIR)
    print('完了')

if __name__ == '__main__':
    main()
