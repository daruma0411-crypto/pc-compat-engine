"""
価格.com 価格バッチ更新スクリプト（差分検出対応）
週1で実行し、全kakakuカテゴリの価格を更新・差分ログ出力・git push する。

実行方法:
  python scripts/kakaku_price_updater.py

自動化:
  GitHub Actions weekly-price-update.yml (毎週日曜 06:00 JST)
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from datetime import datetime, timezone
from kakaku_scraper_base import (
    DATA_ROOT, get_all_codes,
    update_prices_with_diff, save_diff_log,
    update_prices_in_jsonl,  # 後方互換
)

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# kakakuカテゴリごとの LIST_URL と products.jsonl パス
KAKAKU_CATEGORIES = {
    'gpu':    {
        'list_url': 'https://kakaku.com/pc/videocard/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_gpu', 'products.jsonl'),
    },
    'ram':    {
        'list_url': 'https://kakaku.com/pc/pc-memory/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_ram', 'products.jsonl'),
    },
    'cpu':    {
        'list_url': 'https://kakaku.com/pc/cpu/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_cpu', 'products.jsonl'),
    },
    'mb':     {
        'list_url': 'https://kakaku.com/pc/motherboard/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_mb', 'products.jsonl'),
    },
    'psu':    {
        'list_url': 'https://kakaku.com/pc/power-supply/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_psu', 'products.jsonl'),
    },
    'case':   {
        'list_url': 'https://kakaku.com/pc/pc-case/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_case', 'products.jsonl'),
    },
    'cooler': {
        'list_url': 'https://kakaku.com/pc/cpu-cooler/itemlist.aspx',
        'jsonl': os.path.join(DATA_ROOT, 'kakaku_cooler', 'products.jsonl'),
    },
}

DIFF_LOG_DIR = os.path.join(DATA_ROOT, 'diff_logs')
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_scraper(script_name: str):
    """GPU/RAM スクレイパーを子プロセスで実行（新規製品の追加）"""
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    print(f'\n{"="*50}')
    print(f'実行: {script_name}')
    print('='*50)
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=REPO_ROOT,
        encoding='utf-8',
        errors='replace',
    )
    if result.returncode != 0:
        print(f'[WARN] {script_name} が異常終了 (code={result.returncode})')


def git_commit_and_push():
    """変更を git commit して push する"""
    print('\n=== git commit & push ===')
    data_dir = os.path.join(REPO_ROOT, 'workspace', 'data')

    def run(cmd):
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result.returncode

    # ステージング: 全kakakuデータ + diff_logs
    add_paths = []
    for cat_info in KAKAKU_CATEGORIES.values():
        add_paths.append(cat_info['jsonl'])
    add_paths.append(DIFF_LOG_DIR)
    run(['git', 'add'] + add_paths)

    # 変更があるか確認
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'],
                            cwd=REPO_ROOT)
    if result.returncode == 0:
        print('変更なし。コミットをスキップします。')
        return

    commit_msg = f'auto: kakaku price update {TODAY}'
    rc = run(['git', 'commit', '-m', commit_msg])
    if rc != 0:
        print('[WARN] git commit 失敗')
        return

    rc = run(['git', 'push', 'origin', 'main'])
    if rc != 0:
        print('[WARN] git push 失敗')
    else:
        print('push 完了')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='価格.com 価格バッチ更新')
    parser.add_argument('--category', choices=list(KAKAKU_CATEGORIES.keys()),
                        help='単一カテゴリのみ処理（並列実行用）')
    parser.add_argument('--no-scraper', action='store_true',
                        help='新規製品スクレイパーをスキップ')
    args = parser.parse_args()

    print(f'価格バッチ更新開始: {TODAY}')
    print(f'リポジトリ: {REPO_ROOT}')

    if args.category:
        categories = {args.category: KAKAKU_CATEGORIES[args.category]}
        print(f'対象カテゴリ: {args.category}')
    else:
        categories = KAKAKU_CATEGORIES
        print(f'全カテゴリ: {list(KAKAKU_CATEGORIES.keys())}')

    # 1. 新規製品スクレイパー（全カテゴリ実行時のみ）
    if not args.no_scraper and not args.category:
        run_scraper('kakaku_scraper_gpu.py')
        run_scraper('kakaku_scraper_ram.py')

    # 2. active_codes 収集 + 差分検出付き価格更新
    all_diffs = {}
    print(f'\n{"="*50}')
    print('差分検出付き価格更新')
    print('='*50)

    for cat_name, cat_info in categories.items():
        print(f'\n--- {cat_name} ---')

        # 一覧ページから現在 active なコードを収集
        print(f'  一覧ページ走査: {cat_info["list_url"]}')
        active_codes = set(get_all_codes(cat_info['list_url']))
        print(f'  active コード: {len(active_codes)}件')

        # 差分検出付き価格更新
        diff = update_prices_with_diff(cat_info['jsonl'], TODAY, active_codes)
        all_diffs[cat_name] = diff

    # 3. 差分ログ出力
    save_diff_log(DIFF_LOG_DIR, TODAY, all_diffs)

    # 4. git commit & push（全カテゴリ実行時のみ。並列時はワークフロー側で処理）
    if not args.category:
        git_commit_and_push()

    print(f'\n=== 処理完了 {TODAY} ===')


if __name__ == '__main__':
    main()
