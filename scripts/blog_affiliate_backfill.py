#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存ブログ記事にアフィリエイト＋BTO推奨セクションをバックフィル

使い方:
  python blog_affiliate_backfill.py              # 全記事をバックフィル
  python blog_affiliate_backfill.py --dry-run    # 変更対象を確認（書き込みなし）
"""

import json
import re
import argparse
from pathlib import Path

# blog_generator から関数をインポート
from blog_generator import (
    generate_affiliate_section, BLOG_DIR, TARGET_GAMES, TARGET_GPUS, TARGET_BUDGETS,
)

HISTORY_FILE = BLOG_DIR / "generation_history.json"


def _infer_variables(entry):
    """generation_history のエントリからテンプレート変数を推定する"""
    title = entry.get('title', '')
    template_id = entry.get('template', '')
    keywords = entry.get('keywords', [])
    variables = {}

    # --- game の推定 ---
    for en_name, ja_name in TARGET_GAMES.items():
        if ja_name in title or en_name.lower() in title.lower():
            variables['game'] = ja_name
            variables['game_en'] = en_name
            break

    # --- gpu_model の推定 ---
    m = re.search(r'RTX\s*(\d{4})', title, re.IGNORECASE)
    if m:
        variables['gpu_model'] = m.group(1)
    else:
        # キーワードから探す
        for kw in keywords:
            m2 = re.search(r'RTX\s*(\d{4})', kw, re.IGNORECASE)
            if m2:
                variables['gpu_model'] = m2.group(1)
                break

    # --- budget の推定 ---
    m = re.search(r'(\d{1,3})万円', title)
    if m:
        variables['budget'] = m.group(1)

    # デフォルト値
    variables.setdefault('gpu_model', '5060')
    variables.setdefault('budget', '15')

    return variables


def backfill_article(filepath, template_id, variables, dry_run=False):
    """1記事にアフィリエイトセクションを追加"""
    html = filepath.read_text(encoding='utf-8')

    # 既にアフィリエイトセクションがある場合はスキップ
    if 'blog-affiliate-links' in html or 'blog-purchase-guide' in html:
        return False

    # アフィリエイトセクションを生成
    section = generate_affiliate_section(template_id, variables)
    if not section:
        return False

    # 挿入位置の優先順位: article-cta > </article> > </body>
    inserted = False
    for marker, replacement in [
        ('<div class="article-cta">', section + '\n\n  <div class="article-cta">'),
        ('</article>', section + '\n</article>'),
        ('</body>', section + '\n</body>'),
    ]:
        if marker in html:
            html = html.replace(marker, replacement, 1)
            inserted = True
            break

    if not inserted:
        return False

    if not dry_run:
        filepath.write_text(html, encoding='utf-8')

    return True


def main():
    parser = argparse.ArgumentParser(description='Blog Affiliate Backfill')
    parser.add_argument('--dry-run', action='store_true', help='変更せずに対象を表示')
    args = parser.parse_args()

    if not HISTORY_FILE.exists():
        print("[ERROR] generation_history.json が見つかりません")
        return

    history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
    history_filenames = set(e.get('filename', '') for e in history)
    updated = 0
    skipped = 0

    # --- Phase 1: generation_history にある記事 ---
    for entry in history:
        filename = entry.get('filename', '')
        template_id = entry.get('template', '')
        filepath = BLOG_DIR / filename

        if not filepath.exists():
            print(f"  [SKIP] ファイルなし: {filename}")
            skipped += 1
            continue

        variables = _infer_variables(entry)
        result = backfill_article(filepath, template_id, variables, dry_run=args.dry_run)

        if result:
            tag = '[DRY-RUN]' if args.dry_run else '[UPDATED]'
            print(f"  {tag} {filename} (template={template_id}, gpu={variables.get('gpu_model')}, budget={variables.get('budget')})")
            updated += 1
        else:
            print(f"  [SKIP] 既存セクションあり or 生成失敗: {filename}")
            skipped += 1

    # --- Phase 2: history にないが static/blog/ に存在する記事 ---
    for filepath in sorted(BLOG_DIR.glob('*.html')):
        if filepath.name == 'index.html' or filepath.name in history_filenames:
            continue
        # ファイル名からテンプレートを推定
        fname = filepath.name
        template_id = ''
        for tid in ['troubleshooting', 'gpu_list', 'budget_build', 'benchmark',
                     'laptop', 'high_res', 'performance', 'used_parts', 'mod',
                     'ranking', 'weekly_report']:
            if tid in fname:
                template_id = tid
                break

        entry = {'title': fname, 'filename': fname, 'template': template_id, 'keywords': []}
        variables = _infer_variables(entry)
        result = backfill_article(filepath, template_id, variables, dry_run=args.dry_run)

        if result:
            tag = '[DRY-RUN]' if args.dry_run else '[UPDATED]'
            print(f"  {tag} {fname} (推定template={template_id}, history外)")
            updated += 1
        else:
            print(f"  [SKIP] {fname} (history外)")
            skipped += 1

    print(f"\n完了: {updated}件更新, {skipped}件スキップ")


if __name__ == '__main__':
    main()
