#!/usr/bin/env python3
"""
ゲームページ用Schema.org自動生成スクリプト

使い方:
  python scripts/generate_game_schemas.py

機能:
  - 全ゲームページにFAQPage Schema追加
  - VideoGame Schema追加
  - メタ情報（title, description）最適化
"""

import json
import os
from pathlib import Path
from typing import Dict, List


def load_games_data(jsonl_path: str) -> List[Dict]:
    """games.jsonlを読み込み"""
    games = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                games.append(json.loads(line))
    return games


def generate_faqpage_schema(game: Dict) -> Dict:
    """FAQPage Schema生成"""
    game_name = game['name']
    specs = game.get('specs', {})
    min_cpu = specs.get('minimum', {}).get('cpu', [''])[0] if specs.get('minimum') else ''
    rec_cpu = specs.get('recommended', {}).get('cpu', [''])[0] if specs.get('recommended') else ''
    min_gpu = specs.get('minimum', {}).get('gpu', [''])[0] if specs.get('minimum') else ''
    rec_gpu = specs.get('recommended', {}).get('gpu', [''])[0] if specs.get('recommended') else ''
    min_ram = specs.get('minimum', {}).get('ram_gb', 8) if specs.get('minimum') else 8
    rec_ram = specs.get('recommended', {}).get('ram_gb', 16) if specs.get('recommended') else 16
    
    # FAQ質問を生成
    faqs = []
    
    # Q1: 推奨スペック
    if rec_cpu or rec_gpu:
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}のPC推奨スペックは？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}のPC推奨スペックは、CPU: {rec_cpu or '情報なし'}、GPU: {rec_gpu or '情報なし'}、メモリ: {rec_ram}GB RAMです。これらのスペックを満たせば、快適にプレイできます。"
            }
        })
    
    # Q2: 最低スペック
    if min_cpu or min_gpu:
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}は何のスペックで動きますか？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}の最低スペックは、CPU: {min_cpu or '情報なし'}、GPU: {min_gpu or '情報なし'}、メモリ: {min_ram}GB RAMです。ただし、最低スペックでは低画質30fps程度の動作となるため、快適に遊ぶには推奨スペック以上を推奨します。"
            }
        })
    
    # Q3: 予算別PC構成
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}を遊ぶのにいくらかかりますか？",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}を快適に遊べるゲーミングPCは、予算10万円前後から組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.5万円）+ 16GB RAM（約0.8万円）+ SSD・電源・ケースで合計約10-12万円です。当サイトのAI診断で、予算に合わせた最適な構成を提案します。"
        }
    })
    
    # Q4: グラボなしで動く？
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}はグラボなしで動きますか？",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}を快適に遊ぶには、専用グラフィックボード（GPU）が必須です。内蔵GPU（Intel UHD、Iris Xe、AMD Radeon統合グラフィックス）では、低画質でも快適な動作は期待できません。最低でもGTX 1650以上、推奨はRTX 4060以上のGPUを搭載してください。"
        }
    })
    
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs
    }


def generate_videogame_schema(game: Dict) -> Dict:
    """VideoGame Schema生成"""
    specs = game.get('specs', {})
    rec_specs = specs.get('recommended', {})
    
    schema = {
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": game['name'],
        "description": game.get('short_description', ''),
        "genre": game.get('genres', []),
        "operatingSystem": "Windows 10/11"
    }
    
    # 推奨スペックを追加
    if rec_specs:
        if rec_specs.get('cpu'):
            schema["processorRequirements"] = ', '.join(rec_specs['cpu'][:2])  # 最初の2つ
        if rec_specs.get('ram_gb'):
            schema["memoryRequirements"] = f"{rec_specs['ram_gb']}GB RAM"
        if rec_specs.get('storage_gb'):
            schema["storageRequirements"] = f"{rec_specs['storage_gb']}GB"
    
    # スクリーンショット
    if game.get('screenshot'):
        schema["image"] = game['screenshot']
    
    # リリース日
    if game.get('release_date'):
        schema["datePublished"] = game['release_date']
    
    # レビュー情報（Metacriticスコアがあれば）
    if game.get('metacritic_score'):
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(game['metacritic_score'] / 20),  # 100点満点→5点満点に変換
            "bestRating": "5",
            "worstRating": "1"
        }
    
    return schema


def generate_meta_tags(game: Dict) -> Dict:
    """最適化されたメタタグ生成"""
    game_name = game['name']
    genres = game.get('genres', [])
    genre_str = '・'.join(genres[:2]) if genres else 'ゲーム'
    
    # タイトル最適化（60文字以内）
    title = f"{game_name} 推奨スペック｜予算別PC構成提案【2026年最新】"
    
    # ディスクリプション最適化（155文字以内）
    description = f"{game_name}の推奨スペックと予算別PC構成を提案。{genre_str}を快適に遊べる最適なGPU・CPU構成をAIが診断。無料チャット相談OK。"
    
    return {
        "title": title,
        "description": description
    }


def generate_html_snippet(game: Dict) -> str:
    """HTMLスニペット生成（<head>に挿入する部分）"""
    faq_schema = generate_faqpage_schema(game)
    videogame_schema = generate_videogame_schema(game)
    meta_tags = generate_meta_tags(game)
    
    html = f"""
<!-- FAQPage Schema.org -->
<script type="application/ld+json">
{json.dumps(faq_schema, ensure_ascii=False, indent=2)}
</script>

<!-- VideoGame Schema.org -->
<script type="application/ld+json">
{json.dumps(videogame_schema, ensure_ascii=False, indent=2)}
</script>

<title>{meta_tags['title']}</title>
<meta name="description" content="{meta_tags['description']}">
"""
    return html


def main():
    """メイン処理"""
    # ゲームデータ読み込み
    games_path = Path('workspace/data/steam/games.jsonl')
    if not games_path.exists():
        print(f"❌ エラー: {games_path} が見つかりません")
        return
    
    print(f"📖 ゲームデータ読み込み中: {games_path}")
    games = load_games_data(str(games_path))
    print(f"✅ {len(games)}件のゲームデータを読み込みました")
    
    # 出力ディレクトリ作成
    output_dir = Path('scripts/generated_schemas')
    output_dir.mkdir(exist_ok=True)
    
    # 各ゲームのSchemaを生成
    print(f"\n🔧 Schema生成中...")
    
    for i, game in enumerate(games[:10], 1):  # テスト用に最初の10件のみ
        game_name = game['name']
        safe_name = game_name.replace('/', '-').replace('\\', '-').replace(':', '-')
        
        # HTMLスニペット生成
        html_snippet = generate_html_snippet(game)
        
        # ファイル保存
        output_file = output_dir / f"{safe_name}_schema.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_snippet)
        
        print(f"  [{i:3d}] {game_name}")
    
    print(f"\n✅ 生成完了！")
    print(f"📁 出力先: {output_dir}")
    print(f"\n💡 次のステップ:")
    print(f"  1. scripts/generated_schemas/ のファイルを確認")
    print(f"  2. 問題なければ、全ゲーム（{len(games)}件）を生成")
    print(f"  3. 各ゲームHTMLページの<head>に挿入")


if __name__ == '__main__':
    main()
