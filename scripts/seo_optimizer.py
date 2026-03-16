#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO最適化スクリプト
既存HTMLファイルのメタディスクリプション・タイトルを最適化
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Windows コンソールのエンコード問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def optimize_game_page_meta(html_path):
    """ゲームページのSEO最適化"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # ゲーム名を抽出
    title_match = re.search(r'<title>(.*?)</title>', html)
    if not title_match:
        return False
    
    original_title = title_match.group(1)
    game_name = original_title.split('推奨スペック')[0].strip()
    
    # SEO最適化タイトル（検索意図を含む）
    new_title = f"{game_name} 推奨スペック【2026年最新】必要GPU・CPU・メモリは？"
    
    # メタディスクリプション生成
    new_description = (
        f"{game_name}の推奨スペック・必要動作環境を徹底解説。"
        f"GPU・CPU・メモリの推奨構成、60fps/144fps別の目安、"
        f"価格.com最新価格データで予算も確認可能。"
    )
    
    # 既存のメタタグを置換
    html = re.sub(
        r'<title>.*?</title>',
        f'<title>{new_title}</title>',
        html
    )
    
    # メタディスクリプション追加/置換
    if '<meta name="description"' in html:
        html = re.sub(
            r'<meta name="description" content=".*?">',
            f'<meta name="description" content="{new_description}">',
            html
        )
    else:
        html = html.replace(
            '<meta charset="UTF-8">',
            f'<meta charset="UTF-8">\n    <meta name="description" content="{new_description}">'
        )
    
    # 保存
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return True


def optimize_blog_meta(html_path):
    """ブログ記事のSEO最適化"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # タイトル抽出
    title_match = re.search(r'<title>(.*?)</title>', html)
    if not title_match:
        return False
    
    title = title_match.group(1)
    
    # メタディスクリプション生成（タイトルから）
    description = f"{title}を徹底解説。価格.com最新データ使用、初心者向け。自作PC・ゲーミングPC構成の参考に。"
    
    # メタディスクリプション追加/置換
    if '<meta name="description"' in html:
        html = re.sub(
            r'<meta name="description" content=".*?">',
            f'<meta name="description" content="{description}">',
            html
        )
    else:
        html = html.replace(
            '<meta charset="UTF-8">',
            f'<meta charset="UTF-8">\n    <meta name="description" content="{description}">'
        )
    
    # 保存
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return True


def main():
    """メイン処理"""
    base_dir = Path(__file__).parent.parent
    
    # ゲームページ最適化
    games_dir = base_dir / 'static' / 'games'
    if games_dir.exists():
        count = 0
        for html_file in games_dir.glob('*.html'):
            if optimize_game_page_meta(html_file):
                count += 1
        print(f"✅ ゲームページ最適化: {count}件")
    
    # ブログ記事最適化
    blog_dir = base_dir / 'static' / 'blog'
    if blog_dir.exists():
        count = 0
        for html_file in blog_dir.glob('*.html'):
            if optimize_blog_meta(html_file):
                count += 1
        print(f"✅ ブログ記事最適化: {count}件")
    
    print("\n🎉 SEO最適化完了")


if __name__ == '__main__':
    main()
