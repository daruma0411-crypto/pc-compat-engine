#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metacritic Score画像生成モジュール
Twitter投稿用のメタスコア画像を動的生成する

サイズ: 1200x628px（Twitter推奨）
色分け: 緑（75-100）、黄（50-74）、赤（0-49）
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# フォント検索パス（優先順）
FONT_PATHS = [
    # Windows
    r'C:\Windows\Fonts\meiryo.ttc',
    r'C:\Windows\Fonts\msgothic.ttc',
    r'C:\Windows\Fonts\YuGothM.ttc',
    # Linux (GitHub Actions Ubuntu)
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc',
    # macOS
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
]


def find_font():
    """利用可能なフォントを検索"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def generate_metacritic_image(game_name, score, output_path):
    """
    メタスコア画像を生成

    Args:
        game_name (str): ゲーム名
        score (int): メタスコア（0-100）
        output_path (str): 出力パス

    Returns:
        str: 生成した画像のパス。失敗時はNone
    """
    width, height = 1200, 628

    # スコアに応じた色設定
    if score >= 75:
        score_color = (102, 204, 0)   # 緑
        bg_gradient_top = (10, 25, 10)
        bg_gradient_bot = (20, 40, 20)
        rating_text = "Universal Acclaim"
    elif score >= 50:
        score_color = (255, 204, 0)   # 黄
        bg_gradient_top = (25, 20, 5)
        bg_gradient_bot = (40, 35, 10)
        rating_text = "Generally Favorable"
    else:
        score_color = (255, 60, 60)   # 赤
        bg_gradient_top = (25, 8, 8)
        bg_gradient_bot = (40, 12, 12)
        rating_text = "Mixed or Average"

    # 背景グラデーション
    img = Image.new('RGB', (width, height), color=bg_gradient_top)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(bg_gradient_top[0] + (bg_gradient_bot[0] - bg_gradient_top[0]) * ratio)
        g = int(bg_gradient_top[1] + (bg_gradient_bot[1] - bg_gradient_top[1]) * ratio)
        b = int(bg_gradient_top[2] + (bg_gradient_bot[2] - bg_gradient_top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # フォント読み込み
    font_path = find_font()
    if font_path:
        try:
            font_score = ImageFont.truetype(font_path, 160)
            font_label = ImageFont.truetype(font_path, 36)
            font_game = ImageFont.truetype(font_path, 48)
            font_rating = ImageFont.truetype(font_path, 32)
        except Exception:
            font_score = ImageFont.load_default()
            font_label = font_score
            font_game = font_score
            font_rating = font_score
    else:
        font_score = ImageFont.load_default()
        font_label = font_score
        font_game = font_score
        font_rating = font_score

    # 中央の円（スコア背景）
    cx, cy = width // 2, height // 2 - 20
    radius = 140

    # 円の影（ドロップシャドウ）
    shadow_offset = 6
    draw.ellipse(
        [cx - radius + shadow_offset, cy - radius + shadow_offset,
         cx + radius + shadow_offset, cy + radius + shadow_offset],
        fill=(0, 0, 0, 80)
    )

    # メインの円
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=score_color
    )

    # 円の内側に暗い枠線
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(0, 0, 0, 60), width=3
    )

    # スコアテキスト（中央）
    score_text = str(score)
    bbox = draw.textbbox((0, 0), score_text, font=font_score)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        (cx - tw // 2, cy - th // 2 - 10),
        score_text, fill='white', font=font_score
    )

    # 「METACRITIC SCORE」ラベル（上部）
    label = "METACRITIC SCORE"
    bbox = draw.textbbox((0, 0), label, font=font_label)
    lw = bbox[2] - bbox[0]
    draw.text(
        ((width - lw) // 2, 40),
        label, fill=(180, 180, 180), font=font_label
    )

    # 区切り線（上）
    line_y = 90
    draw.line(
        [(width // 2 - 200, line_y), (width // 2 + 200, line_y)],
        fill=(80, 80, 80), width=1
    )

    # ゲーム名（下部）
    max_chars = 45
    display_name = game_name if len(game_name) <= max_chars else game_name[:max_chars] + '...'
    bbox = draw.textbbox((0, 0), display_name, font=font_game)
    nw = bbox[2] - bbox[0]
    draw.text(
        ((width - nw) // 2, height - 140),
        display_name, fill='white', font=font_game
    )

    # 評価テキスト（最下部）
    bbox = draw.textbbox((0, 0), rating_text, font=font_rating)
    rw = bbox[2] - bbox[0]
    draw.text(
        ((width - rw) // 2, height - 75),
        rating_text, fill=(160, 160, 160), font=font_rating
    )

    # サイトURL（右下に小さく）
    site_text = "pc-compat-engine"
    bbox = draw.textbbox((0, 0), site_text, font=font_rating)
    draw.text(
        (width - (bbox[2] - bbox[0]) - 20, 15),
        site_text, fill=(80, 80, 80), font=font_rating
    )

    # 保存
    output_path = str(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    return output_path


if __name__ == '__main__':
    test_dir = Path(__file__).parent / 'test_images'
    test_dir.mkdir(exist_ok=True)

    generate_metacritic_image("Baldur's Gate 3", 96, test_dir / 'test_high.png')
    generate_metacritic_image("Monster Hunter Wilds", 68, test_dir / 'test_mid.png')
    generate_metacritic_image("Some Average Game", 45, test_dir / 'test_low.png')

    print(f"テスト画像を生成しました: {test_dir}/")
