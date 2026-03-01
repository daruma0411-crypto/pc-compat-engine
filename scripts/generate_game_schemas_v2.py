#!/usr/bin/env python3
"""
ゲームページ用Schema.org自動生成スクリプト v2 (改善版)

使い方:
  python scripts/generate_game_schemas_v2.py

機能:
  - 全ゲームページにFAQPage Schema追加
  - VideoGame Schema追加
  - メタ情報（title, description）最適化
  
v2の改善点:
  - テンプレート文の修正
  - エラーハンドリング強化
  - 文字化け対策
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
                try:
                    games.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return games


def generate_faqpage_schema(game: Dict) -> Dict:
    """FAQPage Schema生成"""
    game_name = game['name']
    specs = game.get('specs', {})
    
    # 安全にスペックを取得
    min_specs = specs.get('minimum', {}) or {}
    rec_specs = specs.get('recommended', {}) or {}
    
    min_cpu_list = min_specs.get('cpu') or ['情報なし']
    min_cpu = min_cpu_list[0] if isinstance(min_cpu_list, list) and min_cpu_list else '情報なし'
    
    rec_cpu_list = rec_specs.get('cpu') or ['情報なし']
    rec_cpu = rec_cpu_list[0] if isinstance(rec_cpu_list, list) and rec_cpu_list else '情報なし'
    
    min_gpu_list = min_specs.get('gpu') or ['情報なし']
    min_gpu = min_gpu_list[0] if isinstance(min_gpu_list, list) and min_gpu_list else '情報なし'
    
    rec_gpu_list = rec_specs.get('gpu') or ['情報なし']
    rec_gpu = rec_gpu_list[0] if isinstance(rec_gpu_list, list) and rec_gpu_list else '情報なし'
    
    min_ram = min_specs.get('ram_gb', 8)
    rec_ram = rec_specs.get('ram_gb', 16)
    
    # FAQ質問を生成
    faqs = []
    
    # Q1: 推奨スペック
    if rec_cpu != '情報なし' or rec_gpu != '情報なし':
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}のPC推奨スペックは？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}のPC推奨スペックは、CPU: {rec_cpu}、GPU: {rec_gpu}、メモリ: {rec_ram}GB RAMです。これらのスペックを満たせば、高画質設定で60fps以上の快適なプレイが可能です。"
            }
        })
    
    # Q2: 最低スペック
    if min_cpu != '情報なし' or min_gpu != '情報なし':
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}の最低スペックは？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}の最低スペックは、CPU: {min_cpu}、GPU: {min_gpu}、メモリ: {min_ram}GB RAMです。ただし、最低スペックでは低画質30fps程度の動作となるため、快適に遊ぶには推奨スペック以上を推奨します。"
            }
        })
    
    # Q3: 予算別PC構成
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}を遊ぶのにいくらかかりますか？",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}を快適に遊べるゲーミングPCは、予算10万円前後から組めます。RTX 4060（約4.5万円）、Ryzen 5 7600（約2.5万円）、16GB RAM（約0.8万円）、SSD・電源・ケースで合計約10-12万円です。当サイトのAI診断で、予算に合わせた最適な構成を提案します。"
        }
    })
    
    # Q4: グラボなしで動く？
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}はグラボなしで動きますか？",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}を快適に遊ぶには、専用グラフィックボード（GPU）が必須です。内蔵GPU（Intel UHD Graphics、Iris Xe、AMD Radeon統合グラフィックス）では、低画質でも快適な動作は期待できません。最低でもGTX 1650以上、推奨はRTX 4060以上のGPUを搭載してください。"
        }
    })
    
    # FAQが空の場合はデフォルト質問を追加
    if not faqs:
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}を快適に遊ぶには？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}を快適に遊ぶには、ゲーミングPCの推奨スペックを確認し、予算に合わせたパーツ構成を検討することが重要です。当サイトのAI診断で、最適な構成を無料で提案します。"
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
    rec_specs = specs.get('recommended', {}) or {}
    
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
        cpu_list = rec_specs.get('cpu')
        if cpu_list and isinstance(cpu_list, list):
            schema["processorRequirements"] = ', '.join(cpu_list[:2])
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
        # 100点満点→5点満点に変換
        rating_value = round(game['metacritic_score'] / 20, 2)
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(rating_value),
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
    if len(title) > 60:
        title = f"{game_name} 推奨スペック｜PC構成【2026年版】"
    
    # ディスクリプション最適化（155文字以内）
    description = f"{game_name}の推奨スペックと予算別PC構成を提案。{genre_str}を快適に遊べる最適なGPU・CPU構成をAIが診断。無料チャット相談OK。"
    if len(description) > 155:
        description = f"{game_name}の推奨スペック。予算別PC構成をAI診断。無料相談OK。"
    
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
        print(f"[ERROR] File not found: {games_path}")
        return
    
    print(f"[INFO] Loading games data: {games_path}")
    games = load_games_data(str(games_path))
    print(f"[OK] Loaded {len(games)} games\n")
    
    # 出力ディレクトリ作成
    output_dir = Path('scripts/generated_schemas_v2')
    output_dir.mkdir(exist_ok=True)
    
    # 各ゲームのSchemaを生成
    print(f"[INFO] Generating schemas...\n")
    
    success_count = 0
    error_count = 0
    
    for i, game in enumerate(games, 1):
        try:
            game_name = game['name']
            safe_name = game_name.replace('/', '-').replace('\\', '-').replace(':', '-').replace('?', '').replace('*', '')
            
            # HTMLスニペット生成
            html_snippet = generate_html_snippet(game)
            
            # ファイル保存
            output_file = output_dir / f"{safe_name}_schema.html"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_snippet)
            
            success_count += 1
            if i % 50 == 0:
                try:
                    print(f"  [{i:3d}/{len(games)}] {game_name}")
                except:
                    print(f"  [{i:3d}/{len(games)}] (non-printable name)")
        
        except Exception as e:
            error_count += 1
            try:
                print(f"  [ERROR] {game.get('name', 'Unknown')}: {str(e)}")
            except:
                print(f"  [ERROR] (encoding error)")
    
    print(f"\n[DONE] Generation completed!")
    print(f"  Success: {success_count} files")
    print(f"  Errors: {error_count}")
    print(f"  Output: {output_dir}")


if __name__ == '__main__':
    main()
