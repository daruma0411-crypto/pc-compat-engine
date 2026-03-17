#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter投稿用の汎用画像生成
- スペックカード（ゲーム推奨スペック）
- ランキング画像
- 比較画像
サイズ: 1200x628px（Twitter推奨）
"""
import sys
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

FONT_PATHS = [
    r'C:\Windows\Fonts\meiryo.ttc',
    r'C:\Windows\Fonts\msgothic.ttc',
    r'C:\Windows\Fonts\YuGothM.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc',
]

OUTPUT_DIR = Path(__file__).parent.parent / 'static' / 'tweet_images'
GAMES_DATA = Path(__file__).parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'
SITE_URL = 'https://pc-jisaku.com'


def get_font(size=24):
    for fp in FONT_PATHS:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_spec_card(game_name, gpu, cpu, ram, output_path=None):
    """ゲーム推奨スペックカード画像"""
    W, H = 1200, 628
    img = Image.new('RGB', (W, H), (18, 18, 30))
    draw = ImageDraw.Draw(img)
    
    # グラデーション背景
    for y in range(H):
        r = int(18 + (40 - 18) * y / H)
        g = int(18 + (20 - 18) * y / H)
        b = int(30 + (60 - 30) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # アクセントバー
    draw.rectangle([(0, 0), (W, 6)], fill=(0, 200, 120))
    
    font_title = get_font(42)
    font_label = get_font(24)
    font_value = get_font(32)
    font_small = get_font(18)
    
    # タイトル
    title = f"🎮 {game_name}"
    if len(title) > 30:
        title = title[:28] + "..."
    draw.text((60, 40), title, fill=(255, 255, 255), font=font_title)
    draw.text((60, 100), "推奨スペック", fill=(0, 200, 120), font=font_label)
    
    # スペック情報
    specs = [
        ("GPU", gpu, (255, 100, 100)),
        ("CPU", cpu, (100, 180, 255)),
        ("RAM", f"{ram}GB", (255, 200, 50)),
    ]
    
    y_start = 160
    for i, (label, value, color) in enumerate(specs):
        y = y_start + i * 120
        # ラベルボックス
        draw.rounded_rectangle([(60, y), (160, y + 50)], radius=8, fill=color)
        draw.text((75, y + 8), label, fill=(0, 0, 0), font=font_label)
        # 値
        if len(str(value)) > 35:
            value = str(value)[:33] + "..."
        draw.text((180, y + 5), str(value), fill=(255, 255, 255), font=font_value)
    
    # フッター
    draw.text((60, H - 60), f"📊 {SITE_URL}", fill=(150, 150, 170), font=font_small)
    draw.text((60, H - 35), "あなたのPCで動くか診断 →", fill=(100, 100, 120), font=font_small)
    
    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        slug = game_name.lower().replace(' ', '-')[:30]
        output_path = OUTPUT_DIR / f"spec-{slug}.png"
    
    img.save(str(output_path), 'PNG')
    return str(output_path)


def generate_ranking_image(title, items, output_path=None):
    """ランキング画像（TOP5等）"""
    W, H = 1200, 628
    img = Image.new('RGB', (W, H), (18, 18, 30))
    draw = ImageDraw.Draw(img)
    
    # グラデーション背景
    for y in range(H):
        r = int(18 + (35 - 18) * y / H)
        g = int(18 + (18 - 18) * y / H)
        b = int(30 + (50 - 30) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    draw.rectangle([(0, 0), (W, 6)], fill=(255, 200, 50))
    
    font_title = get_font(36)
    font_item = get_font(28)
    font_small = get_font(18)
    
    draw.text((60, 30), f"🏆 {title}", fill=(255, 255, 255), font=font_title)
    
    colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50), (150, 150, 170), (150, 150, 170)]
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    
    for i, item in enumerate(items[:5]):
        y = 100 + i * 95
        color = colors[i] if i < len(colors) else (150, 150, 170)
        
        # バー
        bar_width = int((W - 200) * (1 - i * 0.12))
        draw.rounded_rectangle([(60, y), (60 + bar_width, y + 70)], radius=10, fill=(*color, 40))
        draw.rounded_rectangle([(60, y), (64, y + 70)], radius=0, fill=color)
        
        text = f"{medals[i]} {item}"
        if len(text) > 45:
            text = text[:43] + "..."
        draw.text((80, y + 18), text, fill=(255, 255, 255), font=font_item)
    
    draw.text((60, H - 40), f"📊 {SITE_URL}", fill=(150, 150, 170), font=font_small)
    
    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"ranking-{random.randint(1000,9999)}.png"
    
    img.save(str(output_path), 'PNG')
    return str(output_path)


def generate_comparison_image(title, left_label, right_label, left_items, right_items, output_path=None):
    """VS比較画像"""
    W, H = 1200, 628
    img = Image.new('RGB', (W, H), (18, 18, 30))
    draw = ImageDraw.Draw(img)
    
    for y in range(H):
        draw.line([(0, y), (W, y)], fill=(18 + int(20 * y/H), 18, 30 + int(20 * y/H)))
    
    font_title = get_font(36)
    font_vs = get_font(48)
    font_label = get_font(28)
    font_item = get_font(22)
    font_small = get_font(18)
    
    draw.text((W//2 - 150, 20), title, fill=(255, 255, 255), font=font_title)
    
    # 左
    draw.rounded_rectangle([(40, 80), (560, H - 60)], radius=15, fill=(30, 50, 80))
    draw.text((200, 100), left_label, fill=(100, 180, 255), font=font_label)
    for i, item in enumerate(left_items[:5]):
        draw.text((70, 160 + i * 70), f"• {item}", fill=(220, 220, 240), font=font_item)
    
    # VS
    draw.text((W//2 - 30, H//2 - 30), "VS", fill=(255, 100, 100), font=font_vs)
    
    # 右
    draw.rounded_rectangle([(640, 80), (W - 40, H - 60)], radius=15, fill=(80, 30, 30))
    draw.text((800, 100), right_label, fill=(255, 100, 100), font=font_label)
    for i, item in enumerate(right_items[:5]):
        draw.text((670, 160 + i * 70), f"• {item}", fill=(220, 220, 240), font=font_item)
    
    draw.text((60, H - 40), f"📊 {SITE_URL}", fill=(150, 150, 170), font=font_small)
    
    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"vs-{random.randint(1000,9999)}.png"
    
    img.save(str(output_path), 'PNG')
    return str(output_path)


def generate_game_spec_card_from_db(game=None):
    """DBからランダムにゲームを選んでスペックカード生成"""
    games = []
    with open(GAMES_DATA, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                rec = d.get('specs', {}).get('recommended', {})
                if rec.get('gpu'):
                    games.append(d)
    
    if game is None:
        game = random.choice(games)
    
    name = game['name']
    rec = game.get('specs', {}).get('recommended', {})
    gpu = rec.get('gpu', ['不明'])
    if isinstance(gpu, list):
        gpu = gpu[0] if gpu else '不明'
    cpu = rec.get('cpu', ['不明'])
    if isinstance(cpu, list):
        cpu = cpu[0] if cpu else '不明'
    ram = rec.get('ram_gb', '不明')
    
    return generate_spec_card(name, gpu, cpu, ram), game


if __name__ == '__main__':
    # テスト生成
    print("=== スペックカード ===")
    path, game = generate_game_spec_card_from_db()
    print(f"✅ {game['name']}: {path}")
    
    print("\n=== ランキング ===")
    path = generate_ranking_image(
        "コスパ最強GPU TOP5",
        ["RTX 4060 (¥44,800)", "RX 7600 (¥35,800)", "RTX 4060 Ti (¥58,800)", "RTX 4070 (¥82,800)", "RX 7700 XT (¥62,800)"]
    )
    print(f"✅ {path}")
    
    print("\n=== 比較 ===")
    path = generate_comparison_image(
        "GPU対決",
        "RTX 4070", "RX 7800 XT",
        ["¥82,800", "12GB VRAM", "DLSS 3対応", "消費電力 200W", "Ray Tracing◎"],
        ["¥72,800", "16GB VRAM", "FSR 3対応", "消費電力 263W", "1440p最強"]
    )
    print(f"✅ {path}")
