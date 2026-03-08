#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事自動生成（毎日1本・実データ連動・旬対応）
Claude API (Opus 4.6) を使用して記事を生成し static/blog/ に保存

使い方:
  python blog_generator.py --count 1           # 1記事生成（日次）
  python blog_generator.py --weekly-report      # 週刊レポート生成
  python blog_generator.py --dry-run            # API呼び出しなしのテスト
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
from blog_data_loader import get_data_context, get_source_note

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

# 対象ゲーム（英語名→日本語名マッピング）
TARGET_GAMES = {
    "Elden Ring": "エルデンリング",
    "Cyberpunk 2077": "サイバーパンク2077",
    "Baldur's Gate 3": "バルダーズ・ゲート3",
    "Starfield": "スターフィールド",
    "Hogwarts Legacy": "ホグワーツ・レガシー",
    "Palworld": "パルワールド",
    "Helldivers 2": "ヘルダイバー2",
    "Final Fantasy VII Rebirth": "ファイナルファンタジーVII リバース",
    "Dragon's Dogma 2": "ドラゴンズドグマ2",
    "Monster Hunter Wilds": "モンスターハンターワイルズ",
    "Apex Legends": "エーペックスレジェンズ",
    "Valorant": "ヴァロラント",
    "Counter-Strike 2": "カウンターストライク2",
    "Fortnite": "フォートナイト",
    "Call of Duty Modern Warfare III": "コール オブ デューティ モダン・ウォーフェアIII",
}

# GPU モデル
TARGET_GPUS = ["4060", "4070", "4080", "3060", "3070", "5070"]

# 予算帯
TARGET_BUDGETS = ["8", "10", "12", "15", "18", "20"]

# 生成済み記事の重複チェック用
HISTORY_FILE = BLOG_DIR / "generation_history.json"

# 季節・イベントコンテキスト
SEASON_CONTEXT = {
    1: "年末年始セール直後で、新しいPCを組んだ人が多い時期です。初心者向けの記事が求められます。",
    2: "春の新生活シーズン前。学生・新社会人向けのPC選びが注目されます。",
    3: "新年度・新生活準備シーズン。PC購入需要が高まる時期です。GDC開催月でもあり新作発表も多いです。",
    4: "新年度スタート。新入学・新社会人がPC環境を整える時期です。",
    5: "GW（ゴールデンウィーク）で時間がある人がゲームを始める時期。セールも多いです。",
    6: "Steamサマーセール直前。セールに備えたPC準備やゲーム選びの記事が求められます。",
    7: "Steamサマーセール中〜直後。新作ゲームの発表が多い時期です。夏休み前でPC需要も上がります。",
    8: "夏休み真っ只中。学生のPC自作需要が最大化。gamescom開催月で新作情報も豊富。",
    9: "秋の大型タイトルラッシュ開始。Tokyo Game Show開催月。",
    10: "年末商戦に向けた大型タイトル発売ラッシュ。ハロウィンセールもあります。",
    11: "ブラックフライデー・サイバーマンデーセール。パーツ購入の最大チャンス。",
    12: "年末商戦ピーク。Steamウィンターセール。クリスマス・年末年始用PCの駆け込み需要。",
}


def load_generation_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_generation_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def slugify(text):
    """タイトルをファイル名用スラッグに変換（ASCII英数字のみ）"""
    text = text.lower()
    # 日本語→英語の簡易変換
    jp_map = {
        '予算': 'budget', '万円': 'man', '最強': 'best', '版': '',
        '週刊': 'weekly', '月': 'month', '第': 'week', '週': '',
        '年': 'y', 'で組む': '', 'で遊べる': '', 'の推奨スペックと': '-spec-',
        'が動かない時の対処法': '-fix', 'が重い': '-heavy',
        'カクつく原因と解決策': '-lag-fix', '選': 'picks',
        'を入れるために必要なスペック': '-mod-spec',
        'をで遊ぶために必要な': '-for-', '中古パーツで組む': 'used-parts-',
        'ノートで': 'laptop-', 'は快適に遊べる': '',
        'おすすめ': 'recommend', 'パーツ価格ウォッチ': 'parts-price-watch',
        '更新': 'update', 'ゲーミング構成': 'gaming-build',
        '最新ゲーム推奨スペックランキング': 'spec-ranking',
    }
    for jp, en in jp_map.items():
        text = text.replace(jp, en)
    # ASCII英数字とハイフンのみ残す
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')[:80]


def get_season_context():
    """現在の月に応じた季節コンテキストを返す"""
    month = datetime.now().month
    return SEASON_CONTEXT.get(month, "")


def get_week_of_month():
    """月の第N週を返す"""
    now = datetime.now()
    return (now.day - 1) // 7 + 1


def get_date_variables():
    """日付関連の変数を生成"""
    now = datetime.now()
    return {
        'today': now.strftime('%Y年%m月%d日'),
        'today_short': now.strftime('%Y年%m月'),
        'month': str(now.month),
        'week': str(get_week_of_month()),
        'season_context': get_season_context(),
    }


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
<meta property="og:type" content="article">
<meta property="og:title" content="{title} | PC互換チェッカー">
<meta property="og:description" content="{title} - PCゲーム互換性診断とおすすめPC構成">
<meta property="og:url" content="{SITE_URL}/blog/{slugify(title)}.html">
<meta property="og:image" content="{SITE_URL}/static/og-image.png">
<meta property="og:site_name" content="PC互換チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@syoyutarou">
<meta name="twitter:title" content="{title}">
<meta name="twitter:image" content="{SITE_URL}/static/og-image.png">
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
.source-note {{ color: #777; font-size: 12px; margin-top: 16px; padding: 10px; background: #f0f8ff; border-left: 3px solid #4682b4; border-radius: 4px; }}
.source-note a {{ color: #4682b4; }}
.disclaimer {{ color: #777; font-size: 12px; margin-top: 8px; padding: 10px; background: #f8f8f8; border-left: 3px solid #ffa500; border-radius: 4px; }}
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
    <p class="source-note">※ 価格データ：<a href="https://kakaku.com/" rel="nofollow">価格.com</a>調べ（{date_display}時点）。ゲーム動作環境：各ゲーム公式/Steam掲載情報。</p>
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
        # dry-runでもデータコンテキストを表示して確認
        print(f"  [DATA] data_context ({len(variables.get('data_context', ''))}文字)")
        content = f"<h2>テスト記事</h2><p>これは{title}のテスト記事です。</p>"
        return title, generate_article_html(title, content, keywords), keywords

    if not ANTHROPIC_API_KEY:
        print("  [ERROR] ANTHROPIC_API_KEY が未設定")
        return None, None, None

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        content = message.content[0].text
        # APIレスポンスからマークダウンコードフェンスを除去
        content = re.sub(r'^```html?\s*\n?', '', content.strip())
        content = re.sub(r'\n?```\s*$', '', content.strip())
        html = generate_article_html(title, content, keywords)
        return title, html, keywords

    except Exception as e:
        print(f"  [ERROR] API呼び出し失敗: {e}")
        return None, None, None


def generate_posts(count=1, dry_run=False, weekly_report=False):
    """記事を生成"""
    history = load_generation_history()
    generated_titles = set(h.get('title', '') for h in history)

    # 日付変数を準備
    date_vars = get_date_variables()
    source_note = get_source_note()

    generated = 0
    new_entries = []

    # 週刊レポートモード
    if weekly_report:
        template = next((t for t in BLOG_TEMPLATES if t['id'] == 'weekly_report'), None)
        if not template:
            print("[ERROR] weekly_report テンプレートが見つかりません")
            return

        variables = {
            **date_vars,
            'source_note': source_note,
            'data_context': get_data_context('weekly_report', {}),
        }

        title = template['title'].format(**variables)
        if title in generated_titles:
            print(f"[SKIP] 今週のレポートは生成済み: {title}")
        else:
            print(f"[週刊レポート] {template['id']}")
            title, html, keywords = generate_blog_post(template, variables, dry_run=dry_run)
            if html:
                date_prefix = datetime.now().strftime('%Y%m%d')
                filename = f"{date_prefix}-{template['id']}-{slugify(title)}.html"
                filepath = BLOG_DIR / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"  [OK] {filepath.name}")
                new_entries.append({
                    'title': title,
                    'filename': filename,
                    'template': template['id'],
                    'keywords': keywords,
                    'generated_at': datetime.now().isoformat(),
                })
                generated += 1

    # 通常記事モード
    attempts = 0
    max_attempts = count * 5
    # weekly_reportテンプレートは通常モードでは除外
    normal_templates = [t for t in BLOG_TEMPLATES if t['id'] != 'weekly_report']

    while generated < count + (1 if weekly_report else 0) - (1 if weekly_report and new_entries else 0) and attempts < max_attempts:
        attempts += 1

        template = random.choice(normal_templates)

        game_en = random.choice(list(TARGET_GAMES.keys()))
        game_ja = TARGET_GAMES[game_en]
        variables = {
            'game': game_ja,
            'game_en': game_en,
            'gpu_model': random.choice(TARGET_GPUS),
            'budget': random.choice(TARGET_BUDGETS),
            **date_vars,
            'source_note': source_note,
        }

        # テンプレート別の実データを注入
        variables['data_context'] = get_data_context(template['id'], variables)

        title = template['title'].format(**variables)

        if title in generated_titles:
            continue

        print(f"[{generated + 1}/{count}] {template['id']}")

        title, html, keywords = generate_blog_post(template, variables, dry_run=dry_run)

        if html:
            date_prefix = datetime.now().strftime('%Y%m%d')
            filename = f"{date_prefix}-{template['id']}-{slugify(title)}.html"

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

            if not dry_run:
                time.sleep(1)

    # 履歴保存
    history.extend(new_entries)
    save_generation_history(history)

    print(f"\n{len(new_entries)}記事生成完了！ → {BLOG_DIR}")


def main():
    parser = argparse.ArgumentParser(description='Blog Auto Generator (Daily)')
    parser.add_argument('--count', type=int, default=1, help='生成記事数（デフォルト: 1）')
    parser.add_argument('--weekly-report', action='store_true', help='週刊レポートを生成')
    parser.add_argument('--dry-run', action='store_true', help='API呼び出しなしのテスト')
    args = parser.parse_args()

    generate_posts(count=args.count, dry_run=args.dry_run, weekly_report=args.weekly_report)


if __name__ == '__main__':
    main()
