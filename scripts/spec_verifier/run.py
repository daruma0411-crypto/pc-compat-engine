#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec_verifier/run.py
公式スペック検証・修正 エントリーポイント

使い方:
  python -m scripts.spec_verifier.run --phase 1           # ケース全15件 dry-run
  python -m scripts.spec_verifier.run --phase 1 --apply   # 実際に更新
  python -m scripts.spec_verifier.run --phase 2 --apply   # PSU全15件
  python -m scripts.spec_verifier.run --id nzxt_nzxt-h510 --apply  # 1件のみ
  python -m scripts.spec_verifier.run --phase 1 --no-headless       # 非headless
"""

import argparse
import sys
import time

from .config import PHASE_CONFIG
from .base import verify_product


def main():
    parser = argparse.ArgumentParser(description="公式サイトのスペック値検証・修正")
    parser.add_argument("--phase", type=int, choices=[1, 2], help="フェーズ番号（1=ケース, 2=PSU）")
    parser.add_argument("--id", type=str, help="特定の製品IDのみ処理")
    parser.add_argument("--apply", action="store_true", help="実際にファイルを更新する（省略時はdry-run）")
    parser.add_argument("--no-headless", action="store_true", help="ブラウザを表示モードで起動（bot検知回避）")
    args = parser.parse_args()

    dry_run = not args.apply
    headless = not args.no_headless

    if dry_run:
        print("=" * 60)
        print("★ DRY-RUN モード（--apply を付けると実際に更新されます）")
        print("=" * 60)

    # 対象を決定
    if args.id:
        # 全フェーズから検索
        targets = {}
        for phase_cfg in PHASE_CONFIG.values():
            if args.id in phase_cfg:
                targets[args.id] = phase_cfg[args.id]
        if not targets:
            print(f"[ERROR] ID '{args.id}' が config に見つかりません")
            sys.exit(1)
    elif args.phase:
        targets = PHASE_CONFIG[args.phase]
    else:
        print("[ERROR] --phase か --id を指定してください")
        parser.print_help()
        sys.exit(1)

    # 実行
    results = {"ok": [], "diff": [], "skip": [], "error": []}

    for product_id, cfg in targets.items():
        result = verify_product(product_id, cfg, dry_run=dry_run, headless=headless)
        results[result["status"]].append(product_id)
        time.sleep(1.5)  # レート制限

    # サマリー
    print(f"\n{'='*60}")
    print(f"【結果サマリー】{'（dry-run）' if dry_run else '（更新済み）'}")
    print(f"  OK（変更なし）: {len(results['ok'])}件  {results['ok']}")
    print(f"  DIFF（要修正）: {len(results['diff'])}件  {results['diff']}")
    print(f"  SKIP（取得失敗）: {len(results['skip'])}件  {results['skip']}")
    print(f"  ERROR: {len(results['error'])}件  {results['error']}")

    if dry_run and (results['diff'] or results['skip']):
        print(f"\n--apply を付けて再実行すると DIFF 件数が更新されます")


if __name__ == "__main__":
    main()
