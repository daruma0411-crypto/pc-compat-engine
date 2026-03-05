#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OG画像生成スクリプト
og-image.html → og-image.png (1200x630)
"""
import sys
from playwright.sync_api import sync_playwright
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent.parent
HTML_PATH = BASE_DIR / "og-image.html"
OUTPUT_PATH = BASE_DIR / "og-image.png"

def generate_og_image():
    """HTMLをPNG画像に変換"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        
        # HTMLを開く（file://プロトコル）
        page.goto(f"file:///{HTML_PATH.as_posix()}")
        
        # レンダリング完了を待つ
        page.wait_for_timeout(1000)
        
        # スクリーンショット
        page.screenshot(path=str(OUTPUT_PATH))
        
        browser.close()
        print(f"✅ OG画像生成完了: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_og_image()
