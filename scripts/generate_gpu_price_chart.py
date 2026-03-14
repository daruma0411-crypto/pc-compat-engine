#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU価格チャート画像生成
Twitter投稿用の価格比較バーチャート画像を動的生成する

サイズ: 1200x628px（Twitter推奨）
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# フォント検索パス
FONT_PATHS = [
    r'C:\Windows\Fonts\meiryo.ttc',
    r'C:\Windows\Fonts\msgothic.ttc',
    r'C:\Windows\Fonts\YuGothM.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
]

BAR_COLORS = [
    (0, 200, 120),   # 緑
    (0, 180, 220),   # 水色
    (100, 140, 255), # 青
    (180, 100, 255), # 紫
    (255, 140, 60),  # オレンジ
    (255, 70, 100),  # 赤
    (255, 200, 0),   # 黄
    (120, 220, 100), # ライム
]

SITE_URL = "pc-jisaku.com"


def find_font():
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def generate_gpu_price_chart(output_path=None):
    """GPU最安値比較チャート画像を生成

    Returns:
        str: 画像ファイルパス
    """
    # データ読み込み
    sys.path.insert(0, str(Path(__file__).parent))
    from blog_data_loader import load_gpu_prices

    gpu_prices = load_gpu_prices()
    if not gpu_prices:
        return None

    # 主要GPUだけ抽出（最安値順にソート）
    target_chips = [
        'RTX 5070', 'RTX 5070 Ti', 'RTX 4070 SUPER', 'RTX 4070',
        'RTX 4060 Ti', 'RTX 4060', 'RX 7800 XT', 'RX 7600',
    ]

    chart_data = []
    for chip in target_chips:
        for key, data in gpu_prices.items():
            if chip.lower() in key.lower():
                chart_data.append({
                    'name': chip,
                    'price': data['min_price'],
                    'count': data['count'],
                })
                break

    if len(chart_data) < 3:
        return None

    # 価格順ソート
    chart_data.sort(key=lambda x: x['price'])

    # 最大8件に制限
    chart_data = chart_data[:8]

    # 画像生成
    width, height = 1200, 628
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # グラデーション背景
    top = (0x12, 0x12, 0x28)
    bottom = (0x1a, 0x1a, 0x38)
    for y in range(height):
        ratio = y / height
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # フォント
    font_path = find_font()
    if font_path:
        try:
            font_title = ImageFont.truetype(font_path, 32)
            font_label = ImageFont.truetype(font_path, 22)
            font_price = ImageFont.truetype(font_path, 24)
            font_footer = ImageFont.truetype(font_path, 18)
        except Exception:
            default = ImageFont.load_default()
            font_title = font_label = font_price = font_footer = default
    else:
        default = ImageFont.load_default()
        font_title = font_label = font_price = font_footer = default

    # タイトル
    from datetime import datetime
    today = datetime.now().strftime('%Y年%m月%d日')
    title = f"GPU最安値比較 — {today}時点"
    draw.text((40, 25), title, fill=(255, 255, 255), font=font_title)

    subtitle = f"価格.com調べ | {sum(d['count'] for d in chart_data)}製品から最安値を抽出"
    draw.text((40, 68), subtitle, fill=(140, 150, 180), font=font_footer)

    # 区切り線
    draw.line([(40, 100), (width - 40, 100)], fill=(50, 50, 80), width=1)

    # バーチャート
    max_price = max(d['price'] for d in chart_data)
    bar_area_x = 200
    bar_area_width = width - bar_area_x - 80
    bar_start_y = 120
    bar_height = 42
    bar_gap = 8
    bar_total = bar_height + bar_gap

    for i, data in enumerate(chart_data):
        y = bar_start_y + i * bar_total
        color = BAR_COLORS[i % len(BAR_COLORS)]

        # GPU名ラベル
        draw.text((40, y + 8), data['name'], fill=(200, 210, 230), font=font_label)

        # バー
        bar_width = int((data['price'] / max_price) * bar_area_width * 0.85)
        draw.rectangle(
            [bar_area_x, y + 4, bar_area_x + bar_width, y + bar_height - 4],
            fill=color,
        )

        # 価格テキスト（バーの右端）
        price_text = f"¥{data['price']:,}"
        draw.text(
            (bar_area_x + bar_width + 12, y + 6),
            price_text,
            fill=(240, 240, 255),
            font=font_price,
        )

    # フッター
    footer_y = height - 50
    draw.line([(40, footer_y - 10), (width - 40, footer_y - 10)], fill=(50, 50, 80), width=1)
    draw.text((40, footer_y), SITE_URL, fill=(100, 110, 140), font=font_footer)
    tagline = "PC互換チェッカー | 14,000件パーツDB"
    bbox = draw.textbbox((0, 0), tagline, font=font_footer)
    tw = bbox[2] - bbox[0]
    draw.text((width - tw - 40, footer_y), tagline, fill=(140, 150, 180), font=font_footer)

    # 保存
    if output_path is None:
        out_dir = Path(__file__).parent / 'temp_images'
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / 'gpu_price_chart.png')

    img.save(output_path, quality=95)
    return output_path


if __name__ == '__main__':
    path = generate_gpu_price_chart()
    if path:
        print(f"GPU価格チャート生成: {path}")
    else:
        print("データ不足で生成できませんでした")
