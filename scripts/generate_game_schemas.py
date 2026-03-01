#!/usr/bin/env python3
"""
Schema.org

:
  python scripts/generate_game_schemas.py

:
  - FAQPage Schema
  - VideoGame Schema
  - title, description
"""

import json
import os
from pathlib import Path
from typing import Dict, List


def load_games_data(jsonl_path: str) -> List[Dict]:
    """games.jsonl"""
    games = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                games.append(json.loads(line))
    return games


def generate_faqpage_schema(game: Dict) -> Dict:
    """FAQPage Schema"""
    game_name = game['name']
    specs = game.get('specs', {})
    
    # 安全にスペックを取得
    min_specs = specs.get('minimum', {}) or {}
    rec_specs = specs.get('recommended', {}) or {}
    
    min_cpu_list = min_specs.get('cpu') or ['']
    min_cpu = min_cpu_list[0] if isinstance(min_cpu_list, list) and min_cpu_list else ''
    
    rec_cpu_list = rec_specs.get('cpu') or ['']
    rec_cpu = rec_cpu_list[0] if isinstance(rec_cpu_list, list) and rec_cpu_list else ''
    
    min_gpu_list = min_specs.get('gpu') or ['']
    min_gpu = min_gpu_list[0] if isinstance(min_gpu_list, list) and min_gpu_list else ''
    
    rec_gpu_list = rec_specs.get('gpu') or ['']
    rec_gpu = rec_gpu_list[0] if isinstance(rec_gpu_list, list) and rec_gpu_list else ''
    
    min_ram = min_specs.get('ram_gb', 8)
    rec_ram = rec_specs.get('ram_gb', 16)
    
    # FAQ
    faqs = []
    
    # Q1: 
    if rec_cpu or rec_gpu:
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}PC",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}PCCPU: {rec_cpu or ''}GPU: {rec_gpu or ''}: {rec_ram}GB RAM"
            }
        })
    
    # Q2: 
    if min_cpu or min_gpu:
        faqs.append({
            "@type": "Question",
            "name": f"{game_name}",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{game_name}CPU: {min_cpu or ''}GPU: {min_gpu or ''}: {min_ram}GB RAM30fps"
            }
        })
    
    # Q3: PC
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}PC10RTX 40604.5+ Ryzen 5 76002.5+ 16GB RAM0.8+ SSD10-12AI"
        }
    })
    
    # Q4: 
    faqs.append({
        "@type": "Question",
        "name": f"{game_name}",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": f"{game_name}GPUGPUIntel UHDIris XeAMD RadeonGTX 1650RTX 4060GPU"
        }
    })
    
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs
    }


def generate_videogame_schema(game: Dict) -> Dict:
    """VideoGame Schema"""
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
    
    # 
    if rec_specs:
        if rec_specs.get('cpu'):
            schema["processorRequirements"] = ', '.join(rec_specs['cpu'][:2])  # 2
        if rec_specs.get('ram_gb'):
            schema["memoryRequirements"] = f"{rec_specs['ram_gb']}GB RAM"
        if rec_specs.get('storage_gb'):
            schema["storageRequirements"] = f"{rec_specs['storage_gb']}GB"
    
    # 
    if game.get('screenshot'):
        schema["image"] = game['screenshot']
    
    # 
    if game.get('release_date'):
        schema["datePublished"] = game['release_date']
    
    # Metacritic
    if game.get('metacritic_score'):
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(game['metacritic_score'] / 20),  # 1005
            "bestRating": "5",
            "worstRating": "1"
        }
    
    return schema


def generate_meta_tags(game: Dict) -> Dict:
    """"""
    game_name = game['name']
    genres = game.get('genres', [])
    genre_str = ''.join(genres[:2]) if genres else ''
    
    # 60
    title = f"{game_name} PC2026"
    
    # 155
    description = f"{game_name}PC{genre_str}GPUCPUAIOK"
    
    return {
        "title": title,
        "description": description
    }


def generate_html_snippet(game: Dict) -> str:
    """HTML<head>"""
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
    """"""
    # 
    games_path = Path('workspace/data/steam/games.jsonl')
    if not games_path.exists():
        print(f" : {games_path} ")
        return
    
    print(f" : {games_path}")
    games = load_games_data(str(games_path))
    print(f" {len(games)}")
    
    # 
    output_dir = Path('scripts/generated_schemas')
    output_dir.mkdir(exist_ok=True)
    
    # Schema
    print(f"\n Schema...")
    
    for i, game in enumerate(games[:10], 1):  # 10
        game_name = game['name']
        safe_name = game_name.replace('/', '-').replace('\\', '-').replace(':', '-')
        
        # HTML
        html_snippet = generate_html_snippet(game)
        
        # 
        output_file = output_dir / f"{safe_name}_schema.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_snippet)
        
        print(f"  [{i:3d}] {game_name}")
    
    print(f"\n ")
    print(f" : {output_dir}")
    print(f"\n :")
    print(f"  1. scripts/generated_schemas/ ")
    print(f"  2. {len(games)}")
    print(f"  3. HTML<head>")


if __name__ == '__main__':
    main()

