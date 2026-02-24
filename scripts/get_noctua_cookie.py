#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Noctua Vercel クッキー自動取得スクリプト
- playwright (Python) を使って実 Chrome ブラウザで noctua.at にアクセス
- Vercel チャレンジを自動通過 → クッキーを取得して stdout に出力
- 取得したクッキー文字列を noctua_cooler_scraper.py に渡す

使い方:
  python get_noctua_cookie.py
  # 出力例: _vcrcs=xxxx; __vcid_c=yyyy
"""

import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

TARGET = "https://noctua.at/en/products/cpu-cooler-retail"


def main():
    print("Chrome を起動して noctua.at にアクセス中...", file=sys.stderr)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,  # 実ブラウザ（表示あり）
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        # webdriver フラグを隠す
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        print(f"  {TARGET} を開いています...", file=sys.stderr)
        page.goto(TARGET, wait_until="domcontentloaded")

        # Vercel チャレンジが解除されるまで待機（最大 30 秒）
        for i in range(30):
            title = page.title()
            if "Vercel" not in title and "checkpoint" not in title.lower():
                print(f"  ✅ チャレンジ通過: {title}", file=sys.stderr)
                break
            print(f"  待機中 ({i+1}/30): {title}", file=sys.stderr)
            time.sleep(1)
        else:
            print("  ⚠️  チャレンジが通過できませんでした（タイムアウト）", file=sys.stderr)

        # クッキーを取得
        cookies = ctx.cookies("https://noctua.at")
        browser.close()

    if not cookies:
        print("❌ クッキーが取得できませんでした", file=sys.stderr)
        sys.exit(1)

    # クッキー文字列を生成
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    print(f"✅ クッキー取得成功 ({len(cookies)} 個)", file=sys.stderr)
    print(f"  {cookie_str[:100]}...", file=sys.stderr)

    # stdout に出力（scraper に渡す用）
    print(cookie_str)


if __name__ == "__main__":
    main()
