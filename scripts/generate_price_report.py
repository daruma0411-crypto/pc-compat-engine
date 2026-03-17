#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
価格変動レポート生成（ツイート + ブログ記事）
週次の価格.comデータ差分からコンテンツを自動生成
"""
import sys
import json
import random
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'
DIFF_DIR = Path(__file__).parent.parent / 'workspace' / 'data' / 'diff_logs'
BLOG_DIR = Path(__file__).parent.parent / 'static' / 'blog'


def load_diff(date_prefix, category):
    path = DIFF_DIR / f'{date_prefix}-{category}.jsonl'
    items = []
    if not path.exists():
        return items
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            if d.get('type') == 'price_changed':
                old_p = d.get('old_price', 0) or 0
                new_p = d.get('new_price', 0) or 0
                if old_p > 0 and new_p > 0:
                    d['diff'] = new_p - old_p
                    d['pct'] = (d['diff'] / old_p) * 100
                    items.append(d)
    return items


def generate_tweets(date_prefix='2026-03-15'):
    """価格変動ツイートを生成"""
    tweets = []
    
    # GPU値下げニュース
    gpu_changes = load_diff(date_prefix, 'gpu')
    gpu_drops = sorted([c for c in gpu_changes if c['diff'] < 0 and c['old_price'] < 300000], key=lambda x: x['pct'])
    
    if gpu_drops:
        top = gpu_drops[0]
        name = top['name'].split('[')[0].strip()
        if len(name) > 40:
            name = name[:38] + '...'
        old_p = top['old_price']
        new_p = top['new_price']
        pct = abs(top['pct'])
        tweet = (
            f"🔻 GPU値下げ速報\n\n"
            f"{name}\n"
            f"¥{old_p:,} → ¥{new_p:,}（{pct:.0f}%OFF）\n\n"
            f"他のGPU価格もチェック↓\n"
            f"{SITE_URL}\n\n"
            f"#GPU #自作PC"
        )
        tweets.append(tweet)
    
    # RAM価格動向
    ram_changes = load_diff(date_prefix, 'ram')
    ram_drops = [c for c in ram_changes if c['diff'] < 0]
    ram_rises = [c for c in ram_changes if c['diff'] > 0]
    
    if ram_rises and ram_drops:
        tweet = (
            f"📊 今週のメモリ価格動向\n\n"
            f"値上げ: {len(ram_rises)}件\n"
            f"値下げ: {len(ram_drops)}件\n\n"
        )
        if len(ram_rises) > len(ram_drops):
            tweet += "DDR5が全体的に値上がり傾向\n買うなら早めがいいかも\n\n"
        else:
            tweet += "DDR5が値下がり傾向\nもう少し待てばさらに安くなるかも\n\n"
        tweet += f"{SITE_URL}\n\n#メモリ #DDR5"
        tweets.append(tweet)
    
    # 掘り出し物（大幅値下げ）
    all_drops = []
    for cat in ['gpu', 'cpu', 'case', 'psu', 'cooler']:
        changes = load_diff(date_prefix, cat)
        for c in changes:
            if c['diff'] < 0 and c['pct'] < -20 and c['old_price'] < 100000:
                all_drops.append(c)
    
    all_drops.sort(key=lambda x: x['pct'])
    if len(all_drops) >= 3:
        tweet = "🏷️ 今週の掘り出し物TOP3\n\n"
        for i, d in enumerate(all_drops[:3]):
            name = d['name'].split('[')[0].strip()
            if len(name) > 30:
                name = name[:28] + '...'
            pct = abs(d['pct'])
            tweet += f"{i+1}. {name}\n   ¥{d['old_price']:,}→¥{d['new_price']:,}（{pct:.0f}%OFF）\n"
        tweet += f"\n{SITE_URL}\n\n#PCパーツ #セール"
        tweets.append(tweet)
    
    return tweets


def generate_blog_article(date_prefix='2026-03-15'):
    """価格変動ブログ記事を生成"""
    today = datetime.now().strftime('%Y%m%d')
    
    sections = []
    
    for cat, cat_jp in [('gpu', 'GPU'), ('cpu', 'CPU'), ('ram', 'メモリ'), ('case', 'PCケース'), ('psu', '電源')]:
        changes = load_diff(date_prefix, cat)
        if not changes:
            continue
        drops = sorted([c for c in changes if c['diff'] < 0], key=lambda x: x['pct'])[:5]
        rises = sorted([c for c in changes if c['diff'] > 0], key=lambda x: x['diff'], reverse=True)[:3]
        
        section = f'<h2>{cat_jp}（{len(changes)}件変動）</h2>\n'
        
        if drops:
            section += '<h3>🔻 値下げ注目</h3>\n<ul>\n'
            for d in drops:
                name = d['name'].split('[')[0].strip()
                section += f'<li><strong>{name}</strong><br>¥{d["old_price"]:,} → ¥{d["new_price"]:,}（{abs(d["pct"]):.1f}%OFF）</li>\n'
            section += '</ul>\n'
        
        if rises:
            section += '<h3>🔺 値上げ注意</h3>\n<ul>\n'
            for d in rises[:2]:
                name = d['name'].split('[')[0].strip()
                section += f'<li>{name}: ¥{d["old_price"]:,} → ¥{d["new_price"]:,}</li>\n'
            section += '</ul>\n'
        
        sections.append(section)
    
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>【週刊】PCパーツ価格ウォッチ 2026年3月第3週 | PC互換チェッカー</title>
<meta name="description" content="2026年3月第3週のPCパーツ価格変動レポート。GPU・CPU・メモリの値下げ情報、掘り出し物をまとめ。価格.comデータ基準。">
<style>
body {{ font-family: 'Hiragino Sans', 'Noto Sans JP', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #00c878; border-bottom: 2px solid #00c878; padding-bottom: 10px; }}
h2 {{ color: #64b5f6; margin-top: 30px; }}
h3 {{ color: #fff; }}
ul {{ list-style: none; padding: 0; }}
li {{ background: #2a2a4a; padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #00c878; }}
li strong {{ color: #fff; }}
a {{ color: #64b5f6; }}
.footer {{ margin-top: 40px; text-align: center; color: #888; }}
</style>
</head>
<body>
<h1>📊 【週刊】PCパーツ価格ウォッチ 2026年3月第3週</h1>
<p>価格.com最新データによる週次価格変動レポート</p>
<p>データ取得日: 2026年3月15日</p>

{''.join(sections)}

<div class="footer">
<p><a href="{SITE_URL}">PC互換チェッカー</a> | 価格.comデータ基準</p>
</div>
</body>
</html>'''
    
    filename = f'{today}-weekly_report-pcparts-price-watch-2026y03monthweek3.html'
    filepath = BLOG_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'✅ ブログ記事生成: {filename}')
    return filepath, filename


if __name__ == '__main__':
    print('=== ツイート生成 ===')
    tweets = generate_tweets()
    for i, t in enumerate(tweets, 1):
        print(f'\n--- ツイート{i} ---')
        print(t)
    
    print('\n=== ブログ記事生成 ===')
    filepath, filename = generate_blog_article()
    print(f'保存先: {filepath}')
