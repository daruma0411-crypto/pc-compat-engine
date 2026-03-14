#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推奨スペックカード画像生成モジュール
Twitter投稿用のスペックカード画像を動的生成する

サイズ: 1200x628px（Twitter推奨）
テーマ: ダーク（#1a1a2e → #16213e グラデーション）
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

# スペックの重さに応じたアクセントカラー
COLOR_GREEN = (0, 200, 120)    # 軽い（RAM ≤ 8GB）
COLOR_YELLOW = (255, 200, 0)   # 中程度（RAM 12-16GB）
COLOR_RED = (255, 70, 70)      # 重い（RAM ≥ 24GB）

# メタスコアバッジ色
METACRITIC_GREEN = (102, 204, 0)
METACRITIC_YELLOW = (255, 204, 0)
METACRITIC_RED = (255, 60, 60)

SITE_URL = "pc-jisaku.com"


def find_font():
    """利用可能なフォントを検索"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def _get_accent_color(ram_gb: int) -> tuple:
    """RAM容量に応じたアクセントカラーを返す"""
    if ram_gb <= 8:
        return COLOR_GREEN
    elif ram_gb <= 16:
        return COLOR_YELLOW
    else:
        return COLOR_RED


def _get_metacritic_color(score: int) -> tuple:
    """メタスコアに応じたバッジ色を返す"""
    if score >= 75:
        return METACRITIC_GREEN
    elif score >= 50:
        return METACRITIC_YELLOW
    else:
        return METACRITIC_RED


def _draw_gradient(draw: ImageDraw.Draw, width: int, height: int):
    """ダークテーマのグラデーション背景を描画"""
    top = (0x1a, 0x1a, 0x2e)     # #1a1a2e
    bottom = (0x16, 0x21, 0x3e)  # #16213e

    for y in range(height):
        ratio = y / height
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill):
    """角丸四角形を描画"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)


def generate_spec_card(
    game_name: str,
    gpu: str,
    cpu: str,
    ram_gb: int,
    storage_gb: int = None,
    metacritic_score: int = None,
    output_path: str = None,
) -> str:
    """スペックカード画像を生成して保存パスを返す

    Args:
        game_name: ゲーム名
        gpu: 推奨GPU名
        cpu: 推奨CPU名
        ram_gb: 推奨RAM (GB)
        storage_gb: 推奨ストレージ (GB)、省略可
        metacritic_score: メタスコア (0-100)、省略可
        output_path: 出力先パス。省略時は自動生成

    Returns:
        生成した画像の絶対パス
    """
    width, height = 1200, 628

    # 出力パス決定
    if output_path is None:
        safe_name = game_name.replace(' ', '_').replace('/', '_')[:40]
        out_dir = Path(__file__).parent / 'spec_cards'
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f'{safe_name}_spec.png')

    # 画像作成
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # グラデーション背景
    _draw_gradient(draw, width, height)

    # 薄い装飾ライン（左端に縦のアクセントバー）
    accent = _get_accent_color(ram_gb)
    draw.rectangle([0, 0, 6, height], fill=accent)

    # フォント読み込み
    font_path = find_font()
    if font_path:
        try:
            font_label_sm = ImageFont.truetype(font_path, 22)
            font_game = ImageFont.truetype(font_path, 44)
            font_spec_key = ImageFont.truetype(font_path, 24)
            font_spec_val = ImageFont.truetype(font_path, 28)
            font_footer = ImageFont.truetype(font_path, 20)
            font_meta_score = ImageFont.truetype(font_path, 36)
            font_meta_label = ImageFont.truetype(font_path, 14)
        except Exception:
            default = ImageFont.load_default()
            font_label_sm = default
            font_game = default
            font_spec_key = default
            font_spec_val = default
            font_footer = default
            font_meta_score = default
            font_meta_label = default
    else:
        default = ImageFont.load_default()
        font_label_sm = default
        font_game = default
        font_spec_key = default
        font_spec_val = default
        font_footer = default
        font_meta_score = default
        font_meta_label = default

    # --- 上部エリア ---

    # 「推奨スペック」ラベル（左上）
    draw.text((40, 30), "推奨スペック", fill=(180, 180, 190), font=font_label_sm)

    # 区切り線
    draw.line([(40, 62), (300, 62)], fill=(60, 60, 90), width=1)

    # ゲーム名（中央上、最大30文字で切り詰め）
    max_chars = 30
    display_name = game_name if len(game_name) <= max_chars else game_name[:max_chars] + '...'
    bbox = draw.textbbox((0, 0), display_name, font=font_game)
    text_w = bbox[2] - bbox[0]
    # 左寄せだが余白を確保
    game_x = 40
    game_y = 80
    draw.text((game_x, game_y), display_name, fill=(255, 255, 255), font=font_game)

    # ゲーム名の下にアクセントライン
    game_underline_y = game_y + (bbox[3] - bbox[1]) + 12
    draw.rectangle([40, game_underline_y, 40 + min(text_w, 500), game_underline_y + 3], fill=accent)

    # --- メタスコアバッジ（右上） ---
    if metacritic_score is not None:
        meta_color = _get_metacritic_color(metacritic_score)
        badge_x = width - 130
        badge_y = 30
        badge_size = 70

        # バッジ背景（角丸四角形）
        _draw_rounded_rect(
            draw,
            (badge_x, badge_y, badge_x + badge_size, badge_y + badge_size),
            radius=10,
            fill=meta_color,
        )

        # スコア数値
        score_text = str(metacritic_score)
        bbox = draw.textbbox((0, 0), score_text, font=font_meta_score)
        sw = bbox[2] - bbox[0]
        sh = bbox[3] - bbox[1]
        draw.text(
            (badge_x + (badge_size - sw) // 2, badge_y + (badge_size - sh) // 2 - 4),
            score_text,
            fill=(255, 255, 255),
            font=font_meta_score,
        )

        # 「Metacritic」ラベル
        meta_label = "Metacritic"
        bbox = draw.textbbox((0, 0), meta_label, font=font_meta_label)
        mlw = bbox[2] - bbox[0]
        draw.text(
            (badge_x + (badge_size - mlw) // 2, badge_y + badge_size + 6),
            meta_label,
            fill=(140, 140, 160),
            font=font_meta_label,
        )

    # --- 中央：スペック行 ---
    spec_items = [
        ("GPU", gpu),
        ("CPU", cpu),
        ("RAM", f"{ram_gb}GB"),
    ]
    if storage_gb is not None:
        spec_items.append(("Storage", f"{storage_gb}GB"))

    # スペック表示エリアの開始位置
    spec_start_y = 180
    row_height = 80
    spec_area_x = 60
    bar_width = 5
    bar_height = 50

    for i, (label, value) in enumerate(spec_items):
        row_y = spec_start_y + i * row_height

        # 背景行（半透明風の暗いバー）
        row_bg = (255, 255, 255, 8)
        draw.rectangle(
            [spec_area_x, row_y, width - 60, row_y + row_height - 10],
            fill=(30, 30, 55),
        )

        # 左端のカラーバー
        bar_y = row_y + (row_height - 10 - bar_height) // 2
        draw.rectangle(
            [spec_area_x, row_y, spec_area_x + bar_width, row_y + row_height - 10],
            fill=accent,
        )

        # ラベル（GPU / CPU / RAM / Storage）
        label_x = spec_area_x + 24
        label_y = row_y + 12
        draw.text(
            (label_x, label_y),
            label,
            fill=(160, 170, 200),
            font=font_spec_key,
        )

        # 値
        value_x = spec_area_x + 140
        value_y = row_y + 10
        draw.text(
            (value_x, value_y),
            value,
            fill=(240, 240, 255),
            font=font_spec_val,
        )

    # --- 下部エリア ---

    # 区切り線
    footer_line_y = height - 80
    draw.line(
        [(40, footer_line_y), (width - 40, footer_line_y)],
        fill=(50, 50, 80),
        width=1,
    )

    # サイトURL（左下）
    draw.text(
        (40, height - 60),
        SITE_URL,
        fill=(100, 110, 140),
        font=font_footer,
    )

    # 「PC互換チェッカー | 無料スペック診断」（右下）
    tagline = "PC互換チェッカー | 無料スペック診断"
    bbox = draw.textbbox((0, 0), tagline, font=font_footer)
    tw = bbox[2] - bbox[0]
    draw.text(
        (width - tw - 40, height - 60),
        tagline,
        fill=(140, 150, 180),
        font=font_footer,
    )

    # 保存
    output_path = str(output_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
    return output_path


if __name__ == '__main__':
    test_dir = Path(__file__).parent / 'spec_cards'
    test_dir.mkdir(exist_ok=True)

    # テスト1: 重いゲーム（赤アクセント）
    p1 = generate_spec_card(
        game_name="Cyberpunk 2077: Phantom Liberty",
        gpu="GeForce RTX 4070 / Radeon RX 7800 XT",
        cpu="Intel Core i7-12700 / AMD Ryzen 7 7800X3D",
        ram_gb=32,
        storage_gb=100,
        metacritic_score=86,
        output_path=str(test_dir / 'test_heavy.png'),
    )
    print(f"生成: {p1}")

    # テスト2: 中程度のゲーム（黄アクセント）
    p2 = generate_spec_card(
        game_name="Monster Hunter Wilds",
        gpu="GeForce RTX 3070",
        cpu="Intel Core i7-10700",
        ram_gb=16,
        storage_gb=80,
        metacritic_score=72,
        output_path=str(test_dir / 'test_medium.png'),
    )
    print(f"生成: {p2}")

    # テスト3: 軽いゲーム（緑アクセント）
    p3 = generate_spec_card(
        game_name="Stardew Valley",
        gpu="GeForce GTX 1050",
        cpu="Intel Core i5-8400",
        ram_gb=4,
        output_path=str(test_dir / 'test_light.png'),
    )
    print(f"生成: {p3}")

    # テスト4: メタスコアなし
    p4 = generate_spec_card(
        game_name="日本語テスト: 長いゲーム名が三十文字を超えた場合はちゃんと切り詰められるか",
        gpu="RTX 4090",
        cpu="Ryzen 9 7950X",
        ram_gb=64,
        storage_gb=200,
        output_path=str(test_dir / 'test_truncate.png'),
    )
    print(f"生成: {p4}")

    print(f"\nテスト画像を生成しました: {test_dir}/")
