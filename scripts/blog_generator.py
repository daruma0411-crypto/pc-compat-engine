#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事自動生成（毎日1本・実データ連動・旬対応）
Claude API (Opus 4.6) を使用して記事を生成し static/blog/ に保存

使い方:
  python blog_generator.py --count 1           # 1記事生成（日次）
  python blog_generator.py --weekly-report      # 週刊レポート生成
  python blog_generator.py --template benchmark # 特定テンプレートで生成
  python blog_generator.py --dry-run            # API呼び出しなしのテスト
"""

import os
import json
import random
import time
import argparse
import re
import urllib.parse
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
SITE_URL = os.getenv('SITE_URL', 'https://pc-jisaku.com')

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

# 筆者ペルソナ（Phase 1-1）
AUTHOR_SYSTEM_PROMPT = """あなたはPC自作歴8年の30代エンジニア「筆者」です。

## 人格
- 一人称は「筆者」
- PC自作が趣味で、年2〜3台は組んでいる
- 価格.comとAmazonのヘビーユーザー
- 好きなGPU: RTX 4070（コスパ最強だと信じている）
- 過去の失敗: 電源ケチって不安定になった、中古GPU掴まされた、等

## 文体ルール
1. 個人の経験・エピソードを記事中に最低3箇所入れること（「筆者も〜した」「筆者の環境では〜」）
2. 価格データを引用する際は必ず「価格.com調べ」と明記
3. 途中で文章を切らない。必ず結論と締めの一文まで書き切ること
4. HTMLタグ（h2, p, ol, ul, li, table）で構造化。コードフェンス（```）は絶対に使わない
5. 読者に語りかけるトーンで、BOT感を出さない
6. 「〜です・ます」と「〜だ・である」を混在させず、ですます調で統一
7. GPU・CPU・メモリ等のパーツ名は必ず<strong>タグで囲むこと（例: <strong>GeForce RTX 4060</strong>）"""

# テンプレート別CTA（Phase 1-4）
TEMPLATE_CTA = {
    'troubleshooting': {'heading': 'それでも解決しない？AIに無料相談', 'desc': 'あなたのPC環境を伝えるだけで、原因と対処法を提案します', 'button': 'AIに相談する →'},
    'budget_build': {'heading': 'この構成の互換性をチェック', 'desc': 'パーツ同士の相性をAIが自動診断', 'button': '互換性チェック →'},
    'benchmark': {'heading': 'あなたのGPUでFPS診断', 'desc': 'GPU名を入力するだけで推定FPSを表示', 'button': 'FPS診断する →'},
    'performance': {'heading': 'ボトルネック診断', 'desc': 'CPU/GPU/RAMのどこが足を引っ張っているか判定', 'button': 'ボトルネック診断 →'},
    'gpu_list': {'heading': 'あなたのGPUで遊べるゲーム一覧', 'desc': 'GPU名を入れると対応ゲームが分かります', 'button': '対応ゲーム検索 →'},
    'ranking': {'heading': 'あなたのPCスペックで何が動く？', 'desc': 'AI診断チャットで詳しく確認', 'button': 'スペック診断 →'},
}
DEFAULT_CTA = {'heading': 'あなたのPCで動くか診断', 'desc': 'AI診断チャットで詳しく確認できます', 'button': '無料で診断する →'}

# --- アフィリエイト設定 ---
AMAZON_TAG = 'pccompat-22'
RAKUTEN_A_ID = os.getenv('RAKUTEN_A_ID', '0eb4779e.5d30c5ba')
RAKUTEN_L_ID = os.getenv('RAKUTEN_L_ID', '0eb4779f.b871e4e3')
BTO_DATA_PATH = WORKSPACE_DIR / "workspace" / "data" / "bto" / "products.jsonl"


# --- アフィリエイトURL生成 ---

def _build_amazon_url(name):
    """Amazon検索URL（アフィリエイトタグ付き）"""
    return f'https://www.amazon.co.jp/s?k={urllib.parse.quote(name)}&tag={AMAZON_TAG}'


def _build_rakuten_url(name):
    """楽天検索URL（A8.net経由）"""
    search = f'https://search.rakuten.co.jp/search/mall/{urllib.parse.quote(name)}/'
    return (f'https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_A_ID}/{RAKUTEN_L_ID}'
            f'/?pc={urllib.parse.quote(search, safe="")}&link_type=hybrid_url&ts=1')


def _build_kakaku_url(name):
    """価格.com検索URL"""
    return f'https://kakaku.com/search_results/{urllib.parse.quote(name)}/'


# --- BTO マッチング ---

def _load_bto_products():
    """BTO products.jsonlを読み込む"""
    products = []
    if not BTO_DATA_PATH.exists():
        return products
    with open(BTO_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


_GPU_TIERS = {
    4: ['5090', '4090'],
    3: ['5080', '5070 ti', '4080', '4070 ti super', '4070 ti'],
    2: ['5070', '4070', '5060 ti', '4060 ti', '3070', '9070 xt', '9070'],
}


def _get_gpu_tier(gpu_name):
    """GPU名 → ティア (1=エントリー, 2=ミドル, 3=ハイ, 4=ウルトラ)"""
    name_lower = gpu_name.lower()
    for tier, chips in _GPU_TIERS.items():
        for chip in chips:
            if chip in name_lower:
                return tier
    return 1


def _match_bto_products(template_id, variables, max_items=3):
    """テンプレートに基づいてBTO製品をマッチング（メーカー分散）"""
    all_bto = _load_bto_products()
    if not all_bto:
        return []

    candidates = [p for p in all_bto if p.get('url')]

    if template_id == 'budget_build':
        budget_yen = int(variables.get('budget', '15')) * 10000
        lo, hi = budget_yen * 0.7, budget_yen * 1.3
        candidates = [p for p in candidates if lo <= p.get('price_jpy', 0) <= hi]
        candidates.sort(key=lambda x: abs(x.get('price_jpy', 0) - budget_yen))

    elif template_id == 'gpu_list':
        target_tier = _get_gpu_tier(f"RTX {variables.get('gpu_model', '4060')}")
        candidates.sort(key=lambda x: (
            abs(_get_gpu_tier(x.get('specs', {}).get('gpu', {}).get('name', '')) - target_tier),
            x.get('price_jpy', 999999)))

    elif template_id in ('high_res', 'mod'):
        candidates = [p for p in candidates
                      if _get_gpu_tier(p.get('specs', {}).get('gpu', {}).get('name', '')) >= 3]
        candidates.sort(key=lambda x: x.get('price_jpy', 0))

    elif template_id == 'used_parts':
        candidates = [p for p in candidates if p.get('price_jpy', 0) <= 200000]
        candidates.sort(key=lambda x: x.get('price_jpy', 0))

    else:
        candidates.sort(key=lambda x: abs(x.get('price_jpy', 0) - 250000))

    # メーカー分散
    result, seen = [], set()
    for p in candidates:
        maker = p.get('maker', '')
        if maker not in seen or len(result) < max_items:
            result.append(p)
            seen.add(maker)
        if len(result) >= max_items:
            break
    return result


# --- パーツリスト判定 ---

_TEMPLATE_PARTS = {
    'budget_build': {
        8:  ['GeForce RTX 4060', 'Ryzen 5 5500', 'DDR4 16GB'],
        10: ['GeForce RTX 4060', 'Ryzen 5 5500', 'DDR4 16GB'],
        12: ['GeForce RTX 5060', 'Ryzen 5 7500F', 'DDR5 16GB'],
        15: ['GeForce RTX 5060', 'Ryzen 7 7700', 'DDR5 16GB'],
        18: ['GeForce RTX 5070', 'Ryzen 7 9700X', 'DDR5 32GB'],
        20: ['GeForce RTX 5070', 'Ryzen 7 9700X', 'DDR5 32GB'],
        25: ['GeForce RTX 5080', 'Ryzen 9 9900X', 'DDR5 32GB'],
    },
    'gpu_list':        lambda v: [f"GeForce RTX {v.get('gpu_model', '4060')}"],
    'benchmark':       lambda v: [f"GeForce RTX {v.get('gpu_model', '5060')}", 'ゲーミングPC'],
    'high_res':        ['GeForce RTX 5070 Ti', 'GeForce RTX 5080', '4Kモニター'],
    'performance':     ['GeForce RTX 5060', 'DDR5 32GB メモリ', 'NVMe SSD 1TB'],
    'troubleshooting': ['GeForce RTX 5060', 'ゲーミングPC'],
    'used_parts':      ['GeForce RTX 3060 中古', 'GeForce RTX 3070 中古'],
    'mod':             ['GeForce RTX 5070 Ti 16GB', 'DDR5 32GB メモリ'],
    'laptop':          ['ゲーミングノートPC RTX 4060', 'ゲーミングノートPC RTX 4070'],
    'ranking':         ['GeForce RTX 5070', 'GeForce RTX 5060', 'ゲーミングPC'],
    'weekly_report':   ['GeForce RTX 5060', 'GeForce RTX 5070', 'DDR5 32GB'],
}


def _get_affiliate_parts(template_id, variables):
    """テンプレートに応じたアフィリエイト対象パーツを返す"""
    mapping = _TEMPLATE_PARTS.get(template_id)
    if mapping is None:
        return ['ゲーミングPC', 'GeForce RTX 5060']
    if callable(mapping):
        return mapping(variables)
    if isinstance(mapping, dict):
        budget = int(variables.get('budget', '15'))
        # 最も近い予算帯を選択
        closest = min(mapping.keys(), key=lambda k: abs(k - budget))
        return mapping[closest]
    return list(mapping)


# --- アフィリエイトセクション HTML 生成 ---

def generate_affiliate_section(template_id, variables):
    """おすすめ購入先セクション（パーツリンク + BTO推奨）のHTMLを生成"""
    parts = _get_affiliate_parts(template_id, variables or {})
    bto_list = _match_bto_products(template_id, variables or {}, max_items=3)

    if not parts and not bto_list:
        return ''

    h = []
    h.append('<div class="blog-affiliate-links blog-purchase-guide" style="margin-top:32px;padding:20px;background:#f8fdf8;border-radius:10px;border:1px solid #e0e0e0;">')
    h.append('<h2 style="margin:0 0 16px;font-size:1.2rem;color:#2c3e50;border-left:4px solid #4CAF50;padding-left:12px;">おすすめ購入先</h2>')

    # --- パーツ検索リンクテーブル ---
    if parts:
        h.append('<h3 style="font-size:1rem;color:#34495e;margin:12px 0 8px;">パーツを探す</h3>')
        h.append('<div style="overflow-x:auto;">')
        h.append('<table style="width:100%;border-collapse:collapse;margin-bottom:16px;min-width:400px;">')
        h.append('<thead><tr>'
                 '<th style="background:#4CAF50;color:#fff;padding:8px 10px;text-align:left;font-size:.85rem;">パーツ名</th>'
                 '<th style="background:#FF9900;color:#fff;padding:8px 10px;text-align:center;width:80px;font-size:.85rem;">Amazon</th>'
                 '<th style="background:#bf0000;color:#fff;padding:8px 10px;text-align:center;width:80px;font-size:.85rem;">楽天</th>'
                 '<th style="background:#0068b7;color:#fff;padding:8px 10px;text-align:center;width:80px;font-size:.85rem;">価格.com</th>'
                 '</tr></thead><tbody>')
        for part in parts:
            amz = _build_amazon_url(part)
            rak = _build_rakuten_url(part)
            kak = _build_kakaku_url(part)
            link_style = 'font-weight:bold;text-decoration:none;font-size:.85rem;'
            h.append(f'<tr>'
                     f'<td style="padding:8px 10px;border-bottom:1px solid #eee;font-weight:600;font-size:.9rem;">{part}</td>'
                     f'<td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;"><a href="{amz}" target="_blank" rel="noopener nofollow" style="color:#FF9900;{link_style}">検索</a></td>'
                     f'<td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;"><a href="{rak}" target="_blank" rel="noopener nofollow" style="color:#bf0000;{link_style}">検索</a></td>'
                     f'<td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;"><a href="{kak}" target="_blank" rel="noopener nofollow" style="color:#0068b7;{link_style}">検索</a></td>'
                     f'</tr>')
        h.append('</tbody></table></div>')

    # --- BTO推奨カード ---
    if bto_list:
        h.append('<h3 style="font-size:1rem;color:#34495e;margin:20px 0 12px;">自作が不安なら完成品PC（BTO）もおすすめ</h3>')
        h.append('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;">')
        for bto in bto_list:
            sp = bto.get('specs', {})
            gpu = sp.get('gpu', {}).get('name', '?')
            cpu = sp.get('cpu', {}).get('name', '?')
            ram_gb = sp.get('ram', {}).get('capacity_gb', '?')
            ram_type = sp.get('ram', {}).get('type', '')
            price = bto.get('price_jpy', 0)
            maker = bto.get('maker', '')
            series = bto.get('series', '')
            model = bto.get('model', '')
            url = bto.get('affiliate', {}).get('url', '') or bto.get('url', '')
            h.append(
                f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:14px;background:#fff;">'
                f'<div style="font-size:.75rem;color:#888;margin-bottom:2px;">{maker} {series}</div>'
                f'<div style="font-weight:bold;font-size:.95rem;margin-bottom:6px;color:#1a1a1a;">{model}</div>'
                f'<div style="font-size:.8rem;color:#555;margin-bottom:8px;line-height:1.4;">{gpu}<br>{cpu}<br>{ram_type} {ram_gb}GB</div>'
                f'<div style="font-size:1.1rem;font-weight:bold;color:#e63946;margin-bottom:10px;">¥{price:,}</div>'
                f'<a href="{url}" target="_blank" rel="noopener nofollow" '
                f'style="display:inline-block;background:#4CAF50;color:#fff;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:.85rem;font-weight:600;">詳細を見る →</a>'
                f'</div>')
        h.append('</div>')
        h.append('<p style="font-size:.75rem;color:#999;margin-top:8px;">※ 価格は記事執筆時点のものです。最新価格は各ショップにてご確認ください。</p>')

    h.append('</div>')
    return '\n'.join(h)


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


def _game_slug(game_en):
    """ゲーム英語名をファイル名用スラッグに変換"""
    slug = game_en.lower()
    slug = slug.replace("'", '').replace('"', '').replace(':', '')
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')[:30]


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


def get_related_articles(template_id, keywords, max_articles=3):
    """同テンプレート/同キーワードの既存記事を最大3件返す（Phase 1-5）"""
    history = load_generation_history()
    if not history:
        return []

    related = []
    keywords_lower = [kw.lower() for kw in keywords]

    for entry in reversed(history):
        if len(related) >= max_articles:
            break
        # 同テンプレート or キーワード一致
        is_same_template = entry.get('template') == template_id
        entry_keywords = [k.lower() for k in entry.get('keywords', [])]
        has_keyword_match = any(kw in ' '.join(entry_keywords) for kw in keywords_lower)

        if is_same_template or has_keyword_match:
            related.append({
                'title': entry['title'],
                'filename': entry['filename'],
            })

    return related


def generate_related_html(related_articles):
    """関連記事セクションのHTML生成"""
    if not related_articles:
        return ""

    items = []
    for a in related_articles:
        items.append(f'    <li><a href="{SITE_URL}/blog/{a["filename"]}">{a["title"]}</a></li>')

    return (
        '\n  <div class="related-articles" style="margin-top:28px;padding:16px;background:#f8fdf8;border-radius:8px;border:1px solid #e0e0e0;">\n'
        '    <h3 style="margin:0 0 12px;font-size:1rem;color:#2c3e50;">関連記事</h3>\n'
        '    <ul style="margin:0;padding-left:20px;">\n'
        + '\n'.join(items) + '\n'
        '    </ul>\n'
        '  </div>\n'
    )


def generate_article_html(title, content, keywords, template_id='', filename='', variables=None):
    """記事の完全なHTMLを生成（Schema.org + テンプレート別CTA + 関連記事 + アフィリエイト）"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_display = datetime.now().strftime('%Y年%m月%d日')
    keywords_str = ', '.join(keywords)

    # canonical URL用のファイル名（.html除去）
    url_slug = filename.replace('.html', '') if filename else slugify(title)

    # テンプレート別CTA（Phase 1-4）
    cta = TEMPLATE_CTA.get(template_id, DEFAULT_CTA)

    # 関連記事（Phase 1-5）
    related = get_related_articles(template_id, keywords)
    related_html = generate_related_html(related)

    # アフィリエイト購入セクション
    affiliate_html = generate_affiliate_section(template_id, variables or {})

    # Schema.org Article構造化データ（Phase 1-3）
    description_text = f"{title}【2026年最新】。自作PC・ゲーミングPC構成をAIが無料で即診断。パーツの互換性チェックも自動で完了。"
    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": date_str,
        "dateModified": date_str,
        "author": {
            "@type": "Person",
            "name": "PC互換チェッカー編集部"
        },
        "publisher": {
            "@type": "Organization",
            "name": "PC互換チェッカー",
            "url": SITE_URL
        },
        "description": description_text,
        "mainEntityOfPage": f"{SITE_URL}/blog/{url_slug}"
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}【2026年最新】| pc-jisaku.com</title>
<meta name="description" content="{description_text}">
<meta name="keywords" content="{keywords_str}">
<link rel="canonical" href="{SITE_URL}/blog/{url_slug}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}【2026年最新】| pc-jisaku.com">
<meta property="og:description" content="{description_text}">
<meta property="og:url" content="{SITE_URL}/blog/{url_slug}">
<meta property="og:image" content="{SITE_URL}/static/og-image.png">
<meta property="og:site_name" content="PC互換チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@pc_compat">
<meta name="twitter:title" content="{title}">
<meta name="twitter:image" content="{SITE_URL}/static/og-image.png">
<script type="application/ld+json">{schema_json}</script>
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
{related_html}
  </div>

{affiliate_html}

  <div class="article-cta">
    <h3>{cta['heading']}</h3>
    <p>{cta['desc']}</p>
    <a href="{SITE_URL}/" class="cta-button">{cta['button']}</a>
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


def validate_content(content):
    """生成コンテンツのバリデーション（Phase 1-2）"""
    issues = []

    # 最低2000文字チェック（目標5,000〜8,000文字）
    text_only = re.sub(r'<[^>]+>', '', content)
    if len(text_only) < 2000:
        issues.append(f"文字数不足: {len(text_only)}文字（最低2000文字）")

    # HTMLタグ開閉チェック
    for tag in ['h2', 'p', 'ol', 'ul', 'table']:
        opens = len(re.findall(f'<{tag}[^>]*>', content))
        closes = len(re.findall(f'</{tag}>', content))
        if opens > closes:
            # 自動補修: 閉じタグを追加
            for _ in range(opens - closes):
                content += f'</{tag}>'
            issues.append(f"<{tag}>タグ不一致を自動補修（開:{opens} 閉:{closes}）")

    return content, issues


def generate_blog_post(template, variables, dry_run=False):
    """Claude APIで記事本文を生成（systemプロンプト + バリデーション付き）
    Returns: (title, content_body, keywords) - content_bodyはHTML本文のみ。
    完全なHTMLはcallerがfilenameを確定後にgenerate_article_htmlで生成する。
    """
    title = template['title'].format(**variables)
    keywords = [kw.format(**variables) for kw in template['keywords']]
    keywords_str = ', '.join(keywords)

    prompt = template['prompt'].format(keywords=keywords_str, **variables)

    print(f"  記事生成中: {title}")

    if dry_run:
        # dry-runでもデータコンテキストを表示して確認
        print(f"  [DATA] data_context ({len(variables.get('data_context', ''))}文字)")
        print(f"  [CTA] {TEMPLATE_CTA.get(template['id'], DEFAULT_CTA)['heading']}")
        content = f"<h2>テスト記事</h2><p>これは{title}のテスト記事です。筆者もこのゲームをプレイしました。</p>" * 5
        return title, content, keywords

    if not ANTHROPIC_API_KEY:
        print("  [ERROR] ANTHROPIC_API_KEY が未設定")
        return None, None, None

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # 1回目: 6144トークン（5,000〜8,000文字記事対応）
        max_tokens = 6144
        for attempt in range(2):
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=max_tokens,
                system=AUTHOR_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            content = message.content[0].text
            # APIレスポンスからマークダウンコードフェンスを除去
            content = re.sub(r'^```html?\s*\n?', '', content.strip())
            content = re.sub(r'\n?```\s*$', '', content.strip())

            # 途中切れチェック（Phase 1-2）
            if message.stop_reason == 'max_tokens':
                if attempt == 0:
                    print(f"  [WARN] 途中切れ検出（{max_tokens}トークン） → 8192でリトライ")
                    max_tokens = 8192
                    continue
                else:
                    print(f"  [ERROR] 8192トークンでも途中切れ → スキップ")
                    return None, None, None

            # バリデーション
            content, issues = validate_content(content)
            for issue in issues:
                print(f"  [VALIDATE] {issue}")

            # 文字数不足でスキップ（目標5,000〜8,000文字）
            text_only = re.sub(r'<[^>]+>', '', content)
            if len(text_only) < 2000:
                print(f"  [SKIP] 文字数不足: {len(text_only)}文字（最低2000文字）")
                return None, None, None

            return title, content, keywords

    except Exception as e:
        print(f"  [ERROR] API呼び出し失敗: {e}")
        return None, None, None

    return None, None, None


def generate_posts(count=1, dry_run=False, weekly_report=False, template_filter=None):
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
            title, content_body, keywords = generate_blog_post(template, variables, dry_run=dry_run)
            if content_body:
                date_prefix = datetime.now().strftime('%Y%m%d')
                filename = f"{date_prefix}-{template['id']}-{slugify(title)}.html"
                html = generate_article_html(title, content_body, keywords, template['id'], filename, variables)
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

    # --template フィルタ（Phase 1-7）
    if template_filter:
        normal_templates = [t for t in normal_templates if t['id'] == template_filter]
        if not normal_templates:
            print(f"[ERROR] テンプレート '{template_filter}' が見つかりません")
            print(f"  利用可能: {', '.join(t['id'] for t in BLOG_TEMPLATES)}")
            return

    target_count = count + (1 if weekly_report else 0) - (1 if weekly_report and new_entries else 0)

    while generated < target_count and attempts < max_attempts:
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

        title, content_body, keywords = generate_blog_post(template, variables, dry_run=dry_run)

        if content_body:
            date_prefix = datetime.now().strftime('%Y%m%d')
            # ゲーム名をファイル名に含めて衝突を防ぐ
            game_part = _game_slug(variables.get('game_en', ''))
            base_slug = slugify(title)
            if game_part and game_part not in base_slug:
                filename = f"{date_prefix}-{template['id']}-{game_part}-{base_slug}.html"
            else:
                filename = f"{date_prefix}-{template['id']}-{base_slug}.html"

            # 衝突検知: 同一ファイル名が既にあれば連番を付与
            filepath = BLOG_DIR / filename
            counter = 2
            while filepath.exists() and filename not in [e.get('filename') for e in new_entries]:
                name_base = filename.replace('.html', '')
                filename = f"{name_base}-{counter}.html"
                filepath = BLOG_DIR / filename
                counter += 1

            html = generate_article_html(title, content_body, keywords, template['id'], filename, variables)
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

    # IndexNow通知（Bing/Yandex/Naverに即時インデックス依頼）
    if new_entries and not dry_run:
        try:
            import urllib.request
            site_url = os.getenv('SITE_URL', 'https://pc-jisaku.com')
            indexnow_key = '3f264e2600904952b0efaa0c0651442e'
            urls = [f"{site_url}/blog/{e['slug']}" for e in new_entries]
            payload = json.dumps({
                'host': 'pc-jisaku.com', 'key': indexnow_key,
                'keyLocation': f'{site_url}/static/{indexnow_key}.txt',
                'urlList': urls,
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.indexnow.org/indexnow', data=payload,
                headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"[IndexNow] Submitted {len(urls)} URLs, status: {resp.status}")
        except Exception as e:
            print(f"[IndexNow] Warning: {e}")


def main():
    parser = argparse.ArgumentParser(description='Blog Auto Generator (Daily)')
    parser.add_argument('--count', type=int, default=1, help='生成記事数（デフォルト: 1）')
    parser.add_argument('--weekly-report', action='store_true', help='週刊レポートを生成')
    parser.add_argument('--template', type=str, default=None, help='特定テンプレートで生成（例: troubleshooting, benchmark）')
    parser.add_argument('--dry-run', action='store_true', help='API呼び出しなしのテスト')
    args = parser.parse_args()

    generate_posts(
        count=args.count,
        dry_run=args.dry_run,
        weekly_report=args.weekly_report,
        template_filter=args.template,
    )


if __name__ == '__main__':
    main()
