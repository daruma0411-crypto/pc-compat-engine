#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""404内部リンクを除去し、実在するゲームページだけにリンクし直す"""
import sys
import re
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'
BLOG_DIR = Path(__file__).parent.parent / 'static' / 'blog'
GAMES_DATA = Path(__file__).parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'


def get_valid_game_slugs():
    """実在するゲームのスラッグ一覧を取得"""
    slugs = {}
    with open(GAMES_DATA, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            name = d.get('name', '')
            # slugを生成（app.pyの仕様に合わせる）
            slug = name.lower().replace(' ', '-').replace("'", '').replace(':', '').replace('™', '')
            slugs[name] = slug
    return slugs


def main():
    valid_slugs = get_valid_game_slugs()
    
    count = 0
    for html_file in BLOG_DIR.glob('*.html'):
        if html_file.name == 'index.html':
            continue
        
        html = html_file.read_text(encoding='utf-8')
        
        if 'internal-links' not in html:
            continue
        
        # 既存の内部リンクセクションを除去
        html = re.sub(
            r'\n<div class="internal-links".*?</div>\n',
            '\n',
            html,
            flags=re.DOTALL
        )
        
        # 実在するゲームだけで内部リンクを再構築
        links = []
        for game_name, slug in valid_slugs.items():
            if game_name in html and len(links) < 5:
                links.append(f'<li><a href="{SITE_URL}/game/{slug}">{game_name} 推奨スペック</a></li>')
        
        if links:
            link_section = f'''
<div class="internal-links" style="margin-top:2em;padding:1em;background:#f8f9fa;border-radius:8px;">
  <h3>📌 関連ゲームページ</h3>
  <ul>
    {''.join(links)}
  </ul>
  <p><a href="{SITE_URL}/">→ PC互換チェッカーでスペック診断する</a></p>
</div>
'''
            html = html.replace('</body>', f'{link_section}\n</body>')
        
        html_file.write_text(html, encoding='utf-8')
        count += 1
        status = f"✅ {len(links)}リンク" if links else "🔗 リンクなし"
        print(f"  {status} {html_file.name}")
    
    print(f"\n修正完了: {count}件")


if __name__ == '__main__':
    main()
