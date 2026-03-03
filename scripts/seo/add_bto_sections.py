#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO強化: 全ゲームページにBTO推奨セクションを追加

実行方法:
python scripts/seo/add_bto_sections.py
"""

import json
from pathlib import Path

# ゲームデータ読み込み
GAMES_PATH = Path(__file__).parent.parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'
GENERATED_SCHEMAS_PATH = Path(__file__).parent.parent / 'generated_schemas_v2'

def load_games():
    """ゲームデータ読み込み"""
    games = []
    with open(GAMES_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                games.append(json.loads(line))
    return games


def generate_bto_section(game):
    """BTO推奨セクションのHTML生成"""
    
    name = game['name']
    rec = game.get('specs', {}).get('recommended', {})
    
    # スペック取得
    gpu = rec.get('gpu', ['不明'])[0] if rec.get('gpu') else '不明'
    cpu = rec.get('cpu', ['不明'])[0] if rec.get('cpu') else '不明'
    ram = rec.get('ram_gb', '不明')
    
    # 特殊文字除去
    gpu = gpu.replace('™', '').replace('®', '').strip()
    cpu = cpu.replace('™', '').replace('®', '').strip()
    
    html = f'''
<!-- BTO推奨セクション（SEO強化） -->
<section class="bto-recommendation" itemscope itemtype="https://schema.org/Article">
  <h2 itemprop="headline">「{name}」を快適にプレイできるおすすめBTO PC</h2>
  
  <p itemprop="description">
    {name}の推奨スペック（GPU: {gpu}, CPU: {cpu}, RAM: {ram}GB）
    を満たし、快適に動作するBTO PCをお探しですか？
    当サイトのAI診断なら、あなたの予算と目的に最適なゲーミングPCを即座に提案します。
  </p>
  
  <h3>予算別おすすめ構成</h3>
  <div class="budget-tiers">
    <div class="tier">
      <h4>【15万円】エントリーモデル</h4>
      <ul>
        <li>解像度: 1080p（Full HD）</li>
        <li>フレームレート: 60fps</li>
        <li>画質設定: 中〜高</li>
      </ul>
    </div>
    
    <div class="tier recommended">
      <h4>【25万円】スタンダードモデル ⭐推奨</h4>
      <ul>
        <li>解像度: 1440p（WQHD）</li>
        <li>フレームレート: 144fps</li>
        <li>画質設定: 最高</li>
      </ul>
    </div>
    
    <div class="tier">
      <h4>【35万円】ハイエンドモデル</h4>
      <ul>
        <li>解像度: 4K（Ultra HD）</li>
        <li>フレームレート: 60fps以上</li>
        <li>画質設定: ウルトラ + レイトレ</li>
      </ul>
    </div>
  </div>
  
  <a href="/?game={name}" class="cta-button">
    AI診断で最適なBTO PCを見つける
  </a>
</section>

<!-- Schema.org 追加 -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{name}を快適にプレイできるおすすめBTO PC",
  "description": "{name}の推奨スペックを満たすBTOパソコンの選び方",
  "author": {{
    "@type": "Organization",
    "name": "PC互換チェッカー"
  }}
}}
</script>
'''
    
    return html


def main():
    """メイン処理"""
    
    print("=== BTO推奨セクション追加スクリプト ===\n")
    
    # ゲームデータ読み込み
    games = load_games()
    print(f"[OK] {len(games)}ゲームを読み込みました")
    
    # 出力ディレクトリ作成
    output_dir = Path(__file__).parent / 'bto_sections_html'
    output_dir.mkdir(exist_ok=True)
    
    # 各ゲームのBTOセクション生成
    success_count = 0
    
    for game in games:
        try:
            name = game['name']
            slug = name.lower().replace(' ', '-').replace(':', '').replace('™', '').replace('®', '')
            
            # HTML生成
            html = generate_bto_section(game)
            
            # ファイル保存
            filename = output_dir / f"{slug}_bto_section.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            
            success_count += 1
            
            if success_count % 50 == 0:
                print(f"[進捗] {success_count}/{len(games)}ゲーム処理完了")
                
        except Exception as e:
            print(f"[ERROR] {game.get('name', 'Unknown')}: {e}")
            continue
    
    print(f"\n[完了] {success_count}/{len(games)}ゲームのBTOセクションを生成しました")
    print(f"[保存先] {output_dir.absolute()}")
    print("\n次のステップ:")
    print("1. 生成されたHTMLを各ゲームページの</article>直前に挿入")
    print("2. static/style.css に BTO推奨セクションのCSSを追加")
    print("3. サイトを再デプロイ")


if __name__ == '__main__':
    main()
