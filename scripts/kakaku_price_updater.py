"""
価格.com 価格バッチ更新スクリプト
週1で実行し、GPU/CPU/RAM の最安値を更新して git push する。

実行方法:
  python scripts/kakaku_price_updater.py

タスクスケジューラ:
  run_price_update.bat を毎週月曜 AM6:00 に実行
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from datetime import datetime, timezone
from kakaku_scraper_base import DATA_ROOT, update_prices_in_jsonl

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# 価格更新対象ディレクトリ（既存スペックデータあり）
PRICE_UPDATE_TARGETS = [
    os.path.join(DATA_ROOT, 'kakaku_cpu',     'products.jsonl'),
    os.path.join(DATA_ROOT, 'kakaku_mb',      'products.jsonl'),
    os.path.join(DATA_ROOT, 'kakaku_psu',     'products.jsonl'),
    os.path.join(DATA_ROOT, 'kakaku_case',    'products.jsonl'),
    os.path.join(DATA_ROOT, 'kakaku_cooler',  'products.jsonl'),
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_scraper(script_name: str):
    """GPU/RAM スクレイパーを子プロセスで実行"""
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

    # ステージング
    run(['git', 'add',
         os.path.join(data_dir, 'kakaku_gpu', 'products.jsonl'),
         os.path.join(data_dir, 'kakaku_ram', 'products.jsonl'),
         os.path.join(data_dir, 'kakaku_cpu', 'products.jsonl'),
         os.path.join(data_dir, 'kakaku_mb',  'products.jsonl'),
         os.path.join(data_dir, 'kakaku_psu', 'products.jsonl'),
         os.path.join(data_dir, 'kakaku_case','products.jsonl'),
    ])

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

    rc = run(['git', 'push', 'origin', 'master'])
    if rc != 0:
        print('[WARN] git push 失敗')
    else:
        print('push 完了')


def main():
    print(f'価格バッチ更新開始: {TODAY}')
    print(f'リポジトリ: {REPO_ROOT}')

    # 1. GPU スクレイパー（新規収集 + 価格）
    run_scraper('kakaku_scraper_gpu.py')

    # 2. RAM スクレイパー（新規収集 + 価格）
    run_scraper('kakaku_scraper_ram.py')

    # 3. 既存 CPU/MB/PSU/Case の価格を更新
    print(f'\n{"="*50}')
    print('既存エントリの価格更新')
    print('='*50)
    total_updated = 0
    for jsonl_path in PRICE_UPDATE_TARGETS:
        total_updated += update_prices_in_jsonl(jsonl_path, TODAY)
    print(f'合計更新: {total_updated}件')

    # 4. git commit & push
    git_commit_and_push()

    print(f'\n=== 全処理完了 {TODAY} ===')


if __name__ == '__main__':
    main()
