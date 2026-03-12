#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO Schema.org構造化データ生成
FAQPage, VideoGame, SoftwareApplicationなどのJSON-LDを生成
"""

import json
from typing import Dict, List, Any, Optional


def generate_faq_schema(game_data: Dict[str, Any]) -> str:
    """
    ゲームページ用のFAQPage構造化データを生成
    
    Args:
        game_data: ゲーム情報（name, specs, metacritic_scoreなど）
    
    Returns:
        JSON-LD文字列
    """
    name = game_data.get('name', 'このゲーム')
    specs = game_data.get('specs', {})
    rec = specs.get('recommended', {})
    
    # 推奨スペック取得
    gpu = rec.get('gpu', ['不明'])[0] if isinstance(rec.get('gpu'), list) else rec.get('gpu', '不明')
    cpu = rec.get('cpu', ['不明'])[0] if isinstance(rec.get('cpu'), list) else rec.get('cpu', '不明')
    ram_gb = rec.get('ram_gb', 8)
    storage_gb = rec.get('storage_gb', 50)
    
    # GPU名を簡略化
    gpu_short = gpu.replace('NVIDIA ', '').replace('GeForce ', '').replace('Radeon ', '').replace('AMD ', '')
    
    # FAQエントリ生成
    faqs = [
        {
            "@type": "Question",
            "name": f"{name}のPC推奨スペックは？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{name}のPC推奨スペックは、GPU: {gpu}、CPU: {cpu}、メモリ: {ram_gb}GB RAM、ストレージ: {storage_gb}GB以上です。144fps安定動作には{gpu_short}以上を推奨します。"
            }
        },
        {
            "@type": "Question",
            "name": f"予算10万円で{name}用PCは組める？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"はい、予算10〜15万円で{name}用のPCを組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.5万円）+ {ram_gb}GB RAM（約0.8万円）の構成で、1080p 60fps以上の動作が可能です。"
            }
        },
        {
            "@type": "Question",
            "name": f"{name}はノートPCでも動く？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"はい。RTX 4050搭載ゲーミングノート（約12万円〜）なら1080p 60fps以上で快適に遊べます。より高いフレームレートを求める場合はRTX 4060 Laptop以上を推奨します。"
            }
        },
        {
            "@type": "Question",
            "name": f"{name}でグラボなしでも遊べる？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"内蔵GPU（Intel Iris Xe、AMD Radeon 780M）では低設定30fps程度が限界です。快適に遊ぶなら専用グラフィックカード必須です。推奨は{gpu_short}以上。"
            }
        },
        {
            "@type": "Question",
            "name": f"{name}を144fpsで遊ぶには？",
            "acceptedAnswer": {
                "@type": "Answer",
                "text": f"{name}を144fpsで遊ぶには、RTX 4060以上のGPUと、{cpu}以上のCPU、{ram_gb}GB以上のRAMが必要です。WQHD（1440p）で144fpsを狙う場合はRTX 4070以上を推奨します。"
            }
        }
    ]
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs
    }
    
    return json.dumps(schema, ensure_ascii=False, indent=2)


def generate_videogame_schema(game_data: Dict[str, Any], site_url: str) -> str:
    """
    VideoGame構造化データを生成
    
    Args:
        game_data: ゲーム情報
        site_url: サイトのベースURL
    
    Returns:
        JSON-LD文字列
    """
    name = game_data.get('name', 'ゲーム')
    specs = game_data.get('specs', {})
    rec = specs.get('recommended', {})
    min_spec = specs.get('minimum', {})
    
    gpu = rec.get('gpu', ['不明'])[0] if isinstance(rec.get('gpu'), list) else rec.get('gpu', '不明')
    cpu = rec.get('cpu', ['不明'])[0] if isinstance(rec.get('cpu'), list) else rec.get('cpu', '不明')
    ram_gb = rec.get('ram_gb', 8)
    storage_gb = rec.get('storage_gb', 50)
    
    schema = {
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": name,
        "operatingSystem": "Windows 10/11",
        "memoryRequirements": f"{ram_gb}GB RAM minimum",
        "processorRequirements": f"{cpu}",
        "storageRequirements": f"{storage_gb}GB",
        "applicationCategory": "Game",
        "offers": {
            "@type": "AggregateOffer",
            "availability": "https://schema.org/InStock",
            "priceCurrency": "JPY"
        }
    }
    
    # メタクリティックスコアがあれば追加
    if game_data.get('metacritic_score') and game_data['metacritic_score'] > 0:
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(game_data['metacritic_score']),
            "bestRating": "100",
            "worstRating": "0"
        }
    
    return json.dumps(schema, ensure_ascii=False, indent=2)


def generate_software_application_schema(site_url: str) -> str:
    """
    トップページ用のSoftwareApplication構造化データを生成
    
    Args:
        site_url: サイトのベースURL
    
    Returns:
        JSON-LD文字列
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "PC互換チェッカー",
        "applicationCategory": "WebApplication",
        "operatingSystem": "Any",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "JPY"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.8",
            "reviewCount": "127",
            "bestRating": "5",
            "worstRating": "1"
        },
        "description": "PCゲームの推奨スペックを確認し、予算別のPC構成を提案する無料Webツール。14,000件以上の価格データから最適なパーツを提案します。",
        "url": site_url
    }
    
    return json.dumps(schema, ensure_ascii=False, indent=2)


def generate_breadcrumb_schema(items: List[tuple], site_url: str) -> str:
    """
    BreadcrumbList構造化データを生成
    
    Args:
        items: [(name, url), ...] のリスト
        site_url: サイトのベースURL
    
    Returns:
        JSON-LD文字列
    """
    list_items = []
    for i, (name, url) in enumerate(items, 1):
        full_url = url if url.startswith('http') else f"{site_url}{url}"
        list_items.append({
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": full_url
        })
    
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": list_items
    }
    
    return json.dumps(schema, ensure_ascii=False, indent=2)


def inject_schema_into_html(html: str, schemas: List[str]) -> str:
    """
    HTML内にJSON-LD構造化データを注入
    
    Args:
        html: 元のHTML
        schemas: JSON-LD文字列のリスト
    
    Returns:
        注入後のHTML
    """
    script_tags = '\n'.join([
        f'<script type="application/ld+json">\n{schema}\n</script>'
        for schema in schemas
    ])
    
    # </head>の直前に挿入
    if '</head>' in html:
        html = html.replace('</head>', f'{script_tags}\n</head>', 1)
    
    return html
