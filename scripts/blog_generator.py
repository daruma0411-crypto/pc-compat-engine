#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事自動生成
Claude API (Haiku) を使用して記事を生成し static/blog/ に保存

使い方:
  python blog_generator.py --count 3    # 3記事生成（テスト）
  python blog_generator.py --count 30   # 30記事生成（月次）
  python blog_generator.py --dry-run    # API呼び出しなしのテスト
"""

import os
import json
import random
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

from blog_templates import BLOG_TEMPLATES

# 環境変数
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
BLOG_DIR = WORKSPACE_DIR / "static" / "blog"
BLOG_DIR.mkdir(exist_ok=True, parents=True)

# サイトURL
SITE_URL = "https://pc-compat-engine-production.up.railway.app"

# GA ID
GA_ID = "G-PPNEBG625J"

# 対象ゲーム（人気順）
TARGET_GAMES = [
    "Elden Ring", "Cyberpunk 2077", "Baldur's Gate 3",
    "Starfield", "Hogwarts Legacy", "Palworld",
    "Helldivers 2", "Final Fantasy VII Rebirth", "Dragon's Dogma 2",
    "Monster Hunter Wilds", "Apex Legends", "Valorant",
    "Counter-Strike 2", "Fortnite", "Call of Duty Modern Warfare III",
]

# GPU モデル
TARGET_GPUS = ["4060", "4070", "4080", "3060", "3070", "5070"]

# 予算帯
TARGET_BUDGETS = ["8", "10", "12", "15", "18", "20"]

# 生成済み記事の重複チェック用
HISTORY_FILE = BLOG_DIR / "generation_history.json"


def load_generation_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_generation_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def slugify(text):
    """タイトルをファイル名用スラッグに変換"""
    text = text.lower()
    text = re.sub(r'[「」\[\]【】（）()\'\"、。・]', '', text)
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')[:60]


def generate_article_html(title, content, keywords):
    """記事の完全なHTMLを生成"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_display = datetime.now().strftime('%Y年%m月%d日')
    keywords_str = ', '.join(keywords)

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | PC互換チェッカー</title>
<meta name="description" content="{title} - PCゲーム互換性診断とおすすめPC構成">
<meta name="keywords" content="{keywords_str}">
<link rel="canonical" href="{SITE_URL}/blog/{slugify(title)}.html">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 16px; line-height: 1.8; color: #333; background: #fafafa; }}
a {{ color: #4CAF50; }}
h1 {{ color: #1a1a1a; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; font-size: 1.5rem; }}
h2 {{ color: #2c3e50; margin-top: 32px; font-size: 1.2rem; }}
h3 {{ color: #34495e; margin-top: 24px; }}
.site-nav {{ background: #1a1a1a; padding: 10px 16px; margin: -16px -16px 20px; display: flex; align-items: center; gap: 16px; }}
.site-nav a {{ color: #78FFCB; text-decoration: none; font-size: 14px; }}
.site-nav .nav-logo {{ font-weight: bold; font-size: 16px; }}
.article-meta {{ color: #666; font-size: 0.9em; margin-bottom: 24px; }}
.article-content {{ background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.article-content h2 {{ border-left: 4px solid #4CAF50; padding-left: 12px; }}
.article-content ul, .article-content ol {{ padding-left: 24px; }}
.article-content li {{ margin-bottom: 6px; }}
.article-content table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
.article-content th, .article-content td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
.article-content th {{ background: #4CAF50; color: white; }}
.article-cta {{ margin-top: 32px; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; text-align: center; }}
.article-cta h3 {{ color: #fff; margin: 0 0 8px; }}
.article-cta p {{ color: rgba(255,255,255,0.9); margin: 0 0 16px; font-size: 14px; }}
.cta-button {{ display: inline-block; background: #fff; color: #667eea; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
.cta-button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.3); }}
.page-footer {{ margin-top: 40px; padding: 20px 0; border-top: 1px solid #e0e0e0; text-align: center; font-size: 13px; color: #777; }}
.page-footer a {{ color: #4CAF50; margin: 0 8px; }}
.disclaimer {{ color: #777; font-size: 12px; margin-top: 16px; padding: 10px; background: #f8f8f8; border-left: 3px solid #ffa500; border-radius: 4px; }}
@media (max-width: 600px) {{
  body {{ padding: 10px; }}
  h1 {{ font-size: 1.2rem; }}
  .article-content {{ padding: 16px; }}
}}
</style>
</head>
<body>
<nav class="site-nav">
  <a href="{SITE_URL}/" class="nav-logo">PC互換チェッカー</a>
  <a href="{SITE_URL}/">ホーム</a>
  <a href="{SITE_URL}/about.html">このサイトについて</a>
</nav>

<article>
  <h1>{title}</h1>
  <div class="article-meta">
    <time datetime="{date_str}">{date_display}</time> | PC互換チェッカー
  </div>

  <div class="article-content">
    {content}
    <p class="disclaimer">※ 本記事のFPS値・性能値は一般的な目安です。実際の動作はPC環境・ゲーム設定により異なります。</p>
  </div>

  <div class="article-cta">
    <h3>あなたのPCで動くか診断</h3>
    <p>AI診断チャットで詳しく確認できます</p>
    <a href="{SITE_URL}/" class="cta-button">無料で診断する →</a>
  </div>
</article>

<footer class="page-footer">
  <a href="{SITE_URL}/">ホーム</a>
  <a href="{SITE_URL}/about.html">このサイトについて</a>
  <a href="{SITE_URL}/privacy.html">プライバシーポリシー</a>
  <p>&copy; 2026 PC互換チェッカー</p>
</footer>
</body>
</html>'''


def generate_blog_post(template, variables, dry_run=False):
    """Claude APIで記事本文を生成"""
    title = template['title'].format(**variables)
    keywords = [kw.format(**variables) for kw in template['keywords']]
    keywords_str = ', '.join(keywords)

    prompt = template['prompt'].format(keywords=keywords_str, **variables)

    print(f"  記事生成中: {title}")

    if dry_run:
        content = f"<h2>テスト記事</h2><p>これは{title}のテスト記事です。</p>"
        return title, generate_article_html(title, content, keywords), keywords

    if not ANTHROPIC_API_KEY:
        print("  [ERROR] ANTHROPIC_API_KEY が未設定")
        return None, None, None

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        content = message.content[0].text
        html = generate_article_html(title, content, keywords)
        return title, html, keywords

    except Exception as e:
        print(f"  [ERROR] API呼び出し失敗: {e}")
        return None, None, None


def generate_posts(count=30, dry_run=False):
    """記事を生成"""
    history = load_generation_history()
    generated_titles = set(h.get('title', '') for h in history)

    generated = 0
    new_entries = []

    for i in range(count):
        # ランダムにテンプレート選択
        template = random.choice(BLOG_TEMPLATES)

        # 変数設定
        variables = {
            'game': random.choice(TARGET_GAMES),
            'gpu_model': random.choice(TARGET_GPUS),
            'budget': random.choice(TARGET_BUDGETS),
        }

        title = template['title'].format(**variables)

        # 重複チェック
        if title in generated_titles:
            continue

        print(f"[{generated + 1}/{count}] {template['id']}")

        title, html, keywords = generate_blog_post(template, variables, dry_run=dry_run)

        if html:
            # ファイル名生成
            date_prefix = datetime.now().strftime('%Y%m%d')
            filename = f"{date_prefix}-{template['id']}-{slugify(title)}.html"

            # 保存
            filepath = BLOG_DIR / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  [OK] {filepath.name}")

            generated_titles.add(title)
            new_entries.append({
                'title': title,
                'filename': filename,
                'template': template['id'],
                'keywords': keywords,
                'generated_at': datetime.now().isoformat(),
            })
            generated += 1

            # レート制限対策
            if not dry_run:
                time.sleep(1)

    # 履歴保存
    history.extend(new_entries)
    save_generation_history(history)

    print(f"\n{generated}/{count} 記事生成完了！ → {BLOG_DIR}")


def main():
    parser = argparse.ArgumentParser(description='Blog Auto Generator')
    parser.add_argument('--count', type=int, default=30, help='生成記事数')
    parser.add_argument('--dry-run', action='store_true', help='API呼び出しなしのテスト')
    args = parser.parse_args()

    generate_posts(count=args.count, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
