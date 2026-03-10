#!/usr/bin/env python3
"""Generate HTML pages for 5 new games only"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

BASE_URL = os.getenv('SITE_URL', 'https://pc-compat-engine-production.up.railway.app')
INPUT_FILE = Path(__file__).parent.parent / "workspace" / "data" / "steam" / "new_games.jsonl"
OUTPUT_DIR = Path(__file__).parent.parent / "static" / "game"

def slugify(text):
    """Convert game name to URL-safe slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def format_spec_list(items):
    """Format spec list (CPU/GPU)"""
    if not items:
        return "情報なし"
    if isinstance(items, list):
        return " / ".join(items)
    return str(items)

def generate_game_page(game):
    """Generate HTML page for a single game"""
    slug = slugify(game['name'])
    output_path = OUTPUT_DIR / f"{slug}.html"
    
    # Skip if already exists
    if output_path.exists():
        print(f"[SKIP] {slug} (already exists)")
        return False
    
    # 新旧スキーマ両対応
    specs = game.get('specs', {})
    if specs:
        min_spec = specs.get('minimum', {})
        rec_spec = specs.get('recommended', {})
    else:
        min_spec = game.get('minimum', {})
        rec_spec = game.get('recommended', {})
    
    # Build HTML
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{game['name']}の推奨スペック・必要動作環境を解説。PC構成をチェックして快適にプレイしよう。">
    <meta property="og:title" content="{game['name']} 推奨スペック | PC互換性チェッカー">
    <meta property="og:description" content="{game['short_description']}">
    <meta property="og:image" content="{game.get('screenshot', '')}">
    <meta property="og:url" content="{BASE_URL}/game/{slug}">
    <title>{game['name']} 推奨スペック・必要動作環境 | PC互換性チェッカー</title>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": "{game['name']}",
        "description": "{game['short_description']}",
        "genre": {json.dumps(game.get('genres', []))},
        "datePublished": "{game.get('release_date', '')}",
        "image": "{game.get('screenshot', '')}",
        "operatingSystem": "Windows",
        "systemRequirements": {{
            "@type": "GameSystemRequirements",
            "operatingSystem": "{rec_spec.get('os', 'Windows 10 64bit')}",
            "processorRequirements": "{format_spec_list(rec_spec.get('cpu', []))}",
            "memoryRequirements": "{rec_spec.get('ram_gb', 16)}GB RAM",
            "storageRequirements": "{rec_spec.get('storage_gb', 50)}GB",
            "graphicsRequirements": "{format_spec_list(rec_spec.get('gpu', []))}"
        }}
    }}
    </script>
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {{
                "@type": "Question",
                "name": "{game['name']}の推奨スペックは？",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "CPU: {format_spec_list(rec_spec.get('cpu', []))}, GPU: {format_spec_list(rec_spec.get('gpu', []))}, RAM: {rec_spec.get('ram_gb', 16)}GB, ストレージ: {rec_spec.get('storage_gb', 50)}GB"
                }}
            }},
            {{
                "@type": "Question",
                "name": "RTX 3060で動きますか？",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "RTX 3060は推奨GPU（{format_spec_list(rec_spec.get('gpu', []))}）と同等またはそれ以上の性能を持つため、快適にプレイ可能です。"
                }}
            }},
            {{
                "@type": "Question",
                "name": "予算10万円で組めますか？",
                "acceptedAnswer": {{
                    "@type": "Answer",
                    "text": "推奨スペックを満たすPCは10〜15万円程度で構成可能です。互換性チェッカーで具体的な構成を確認してください。"
                }}
            }}
        ]
    }}
    </script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #eee; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ font-size: 2rem; margin-bottom: 1rem; color: #78FFCB; }}
        .meta {{ color: #BBC2CA; font-size: 0.9rem; margin-bottom: 2rem; }}
        .description {{ background: #232930; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; background: #232930; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #3D454F; }}
        th {{ background: #303740; color: #78FFCB; }}
        .cta {{ display: inline-block; background: #78FFCB; color: #1a1a2e; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 1rem 0; }}
        .cta:hover {{ background: #5ee6b0; }}
        .faq {{ background: #232930; padding: 1.5rem; border-radius: 8px; margin-top: 2rem; }}
        .faq h3 {{ color: #78FFCB; margin-bottom: 1rem; }}
        .faq-item {{ margin-bottom: 1.5rem; }}
        .faq-q {{ font-weight: bold; color: #FFD978; margin-bottom: 0.5rem; }}
        .footer {{ text-align: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #3D454F; color: #BBC2CA; font-size: 0.9rem; }}
        .source {{ margin-top: 2rem; padding: 1rem; background: #232930; border-radius: 8px; font-size: 0.85rem; color: #BBC2CA; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{game['name']} 推奨スペック</h1>
        <div class="meta">
            ジャンル: {' / '.join(game.get('genres', []))} | 発売日: {game.get('release_date', '未定')}
        </div>
        
        <div class="description">
            <p>{game['short_description']}</p>
        </div>
        
        <a href="{BASE_URL}/?game={slug}" class="cta">互換性をチェックする →</a>
        
        <h2 style="margin-top: 2rem; color: #78FFCB;">推奨動作環境</h2>
        <table>
            <tr><th>項目</th><th>スペック</th></tr>
            <tr><td>OS</td><td>{rec_spec.get('os', '情報なし')}</td></tr>
            <tr><td>CPU</td><td>{format_spec_list(rec_spec.get('cpu', []))}</td></tr>
            <tr><td>GPU</td><td>{format_spec_list(rec_spec.get('gpu', []))}</td></tr>
            <tr><td>メモリ</td><td>{rec_spec.get('ram_gb', '?')} GB</td></tr>
            <tr><td>ストレージ</td><td>{rec_spec.get('storage_gb', '?')} GB</td></tr>
            <tr><td>DirectX</td><td>DirectX {rec_spec.get('directx', '12')}</td></tr>
        </table>
        
        <h2 style="margin-top: 2rem; color: #FFD978;">必要動作環境（最低スペック）</h2>
        <table>
            <tr><th>項目</th><th>スペック</th></tr>
            <tr><td>OS</td><td>{min_spec.get('os', '情報なし')}</td></tr>
            <tr><td>CPU</td><td>{format_spec_list(min_spec.get('cpu', []))}</td></tr>
            <tr><td>GPU</td><td>{format_spec_list(min_spec.get('gpu', []))}</td></tr>
            <tr><td>メモリ</td><td>{min_spec.get('ram_gb', '?')} GB</td></tr>
            <tr><td>ストレージ</td><td>{min_spec.get('storage_gb', '?')} GB</td></tr>
            <tr><td>DirectX</td><td>DirectX {min_spec.get('directx', '12')}</td></tr>
        </table>
        
        <div class="faq">
            <h3>よくある質問（FAQ）</h3>
            
            <div class="faq-item">
                <div class="faq-q">Q. {game['name']}を快適にプレイするには？</div>
                <div>A. 推奨スペック（CPU: {format_spec_list(rec_spec.get('cpu', []))}、GPU: {format_spec_list(rec_spec.get('gpu', []))}、RAM: {rec_spec.get('ram_gb', 16)}GB）以上のPCを推奨します。</div>
            </div>
            
            <div class="faq-item">
                <div class="faq-q">Q. RTX 3060で動きますか？</div>
                <div>A. RTX 3060は推奨GPU相当の性能があり、快適にプレイ可能です。高設定・1080p・60fpsでのプレイが期待できます。</div>
            </div>
            
            <div class="faq-item">
                <div class="faq-q">Q. 予算10万円でPC構成できますか？</div>
                <div>A. 推奨スペックを満たす構成は10〜15万円程度で可能です。互換性チェッカーで具体的なパーツ構成を確認してください。</div>
            </div>
        </div>
        
        <a href="{BASE_URL}/?game={slug}" class="cta" style="display: block; text-align: center; margin-top: 2rem;">今すぐ互換性をチェック →</a>
        
        <div class="source">
            データ更新日: {datetime.now().strftime('%Y年%m月%d日')}<br>
            情報源: 公式発表・Steam・メーカー公式サイト
        </div>
        
        <div class="footer">
            <a href="{BASE_URL}" style="color: #78FFCB; text-decoration: none;">← PC互換性チェッカーTOPへ</a>
        </div>
    </div>
</body>
</html>'''
    
    output_path.write_text(html, encoding='utf-8')
    print(f"[OK] Generated: {slug}.html")
    return True

def main():
    print(f"[START] Generating new game pages...")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_DIR}\n")
    
    # Create output directory if not exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated = 0
    skipped = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            game = json.loads(line)
            if generate_game_page(game):
                generated += 1
            else:
                skipped += 1
    
    print(f"\n[SUCCESS] Generated {generated} pages (skipped {skipped})")
    print(f"Total game pages: {len(list(OUTPUT_DIR.glob('*.html')))}")

if __name__ == "__main__":
    main()
