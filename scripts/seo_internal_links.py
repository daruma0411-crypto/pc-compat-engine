#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事に内部リンク（関連ゲームページ・関連記事）を自動追加
SEO内部リンク強化スクリプト
"""
import sys
import re
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'
BLOG_DIR = Path(__file__).parent.parent / 'static' / 'blog'
GAMES_DATA = Path(__file__).parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'

# 人気ゲーム名 → URLスラッグマッピング
POPULAR_GAMES = {
    'Apex Legends': 'apex-legends',
    'エーペックスレジェンズ': 'apex-legends',
    'VALORANT': 'valorant',
    'ヴァロラント': 'valorant',
    'Fortnite': 'fortnite',
    'フォートナイト': 'fortnite',
    'Elden Ring': 'elden-ring',
    'エルデンリング': 'elden-ring',
    'Monster Hunter Wilds': 'monster-hunter-wilds',
    'モンスターハンターワイルズ': 'monster-hunter-wilds',
    'Cyberpunk 2077': 'cyberpunk-2077',
    'サイバーパンク2077': 'cyberpunk-2077',
    'Counter-Strike 2': 'counter-strike-2',
    'カウンターストライク2': 'counter-strike-2',
    'Palworld': 'palworld',
    'パルワールド': 'palworld',
    'Minecraft': 'minecraft',
    'マインクラフト': 'minecraft',
    "Dragon's Dogma 2": 'dragons-dogma-2',
    'ドラゴンズドグマ2': 'dragons-dogma-2',
    "Baldur's Gate 3": 'baldurs-gate-3',
    'バルダーズゲート3': 'baldurs-gate-3',
    'Starfield': 'starfield',
    'スターフィールド': 'starfield',
}


def add_internal_links(html_path):
    """ブログ記事にゲームページへの内部リンクを追加"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 既に内部リンクセクションがあればスキップ
    if '関連ゲームページ' in html or 'internal-links' in html:
        return False

    links = []
    for game_name, slug in POPULAR_GAMES.items():
        if game_name in html:
            links.append(f'<li><a href="{SITE_URL}/game/{slug}">{game_name} 推奨スペック</a></li>')

    if not links:
        return False

    # </article> or </main> or </body> の前に挿入
    link_section = f'''
<div class="internal-links" style="margin-top:2em;padding:1em;background:#f8f9fa;border-radius:8px;">
  <h3>📌 関連ゲームページ</h3>
  <ul>
    {''.join(links[:5])}
  </ul>
  <p><a href="{SITE_URL}/">→ PC互換チェッカーでスペック診断する</a></p>
</div>
'''

    # </body> の前に挿入
    html = html.replace('</body>', f'{link_section}\n</body>')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return True


def main():
    count = 0
    for html_file in BLOG_DIR.glob('*.html'):
        if html_file.name == 'index.html':
            continue
        if add_internal_links(html_file):
            count += 1
            print(f"  ✅ {html_file.name}")

    print(f"\n🔗 内部リンク追加: {count}件")


if __name__ == '__main__':
    main()
