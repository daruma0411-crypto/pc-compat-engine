#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Noctua CPUクーラー スクレイパー（Playwright Chromium 非 headless 方式）

noctua.at は Vercel Security Checkpoint のため、
Playwright Chromium を使って実ブラウザで自動取得する。

使い方:
  python noctua_cooler_scraper.py             # 5件
  python noctua_cooler_scraper.py --limit 10  # 10件
  python noctua_cooler_scraper.py --all       # 全件

出力: pc-compat-engine/workspace/data/noctua_cooler/products.jsonl
"""

import argparse
import json
import pathlib
import re
import sys
import time

try:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install playwright beautifulsoup4 && playwright install chromium", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://noctua.at"
LIST_URL = f"{BASE_URL}/en/products/cpu-cooler-retail"

OUTPUT_PATH = (
    pathlib.Path(__file__).parent.parent
    / "workspace" / "data" / "noctua_cooler" / "products.jsonl"
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def _wait_pass(page, max_sec: int = 20) -> bool:
    """Vercel チャレンジが通過するまで待機"""
    for _ in range(max_sec):
        try:
            title = page.title()
            if "Vercel" not in title and "checkpoint" not in title.lower():
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def get_product_urls(page) -> list[dict]:
    """製品一覧ページから個別製品 URL と名前を取得"""
    print(f"製品一覧取得中: {LIST_URL}", file=sys.stderr)
    try:
        page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
    except Exception:
        pass
    _wait_pass(page, 20)
    page.keyboard.press("Escape")
    time.sleep(2)

    # ページ下部にスクロールして全製品を読み込む
    for _ in range(4):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.2)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(1)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    urls = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=re.compile(r"/en/products/nh-[a-z0-9-]+")):
        href: str = a["href"]
        # カテゴリページ（/en/products/browse/... 等）は除外
        if re.search(r"/en/products/(browse|cpu-cooler|fan)", href):
            continue
        full_url = BASE_URL + href if href.startswith("/") else href
        if full_url in seen:
            continue
        seen.add(full_url)

        # 製品名を取得
        name = ""
        img = a.find("img", alt=True)
        if img and img.get("alt"):
            name = img["alt"].strip()
        if not name:
            name = a.get("title", "").strip() or a.get_text(strip=True)[:60]

        urls.append({"name": name, "url": full_url})

    print(f"  製品 URL: {len(urls)} 件", file=sys.stderr)
    return urls


def _extract_height(text: str) -> int | None:
    """全高（mm）を抽出"""
    patterns = [
        r"total\s+height\s+(\d+)\s*mm",                   # "Total height 168 mm" (spec page)
        r"total\s+height[:\s]+(\d+)\s*mm",
        r"standing\s+(\d+)\s*mm\s+tall",                  # "Standing 165mm tall"
        r"at\s+a\s+height\s+of\s+(?:only\s+)?(\d+)\s*mm", # "At a height of only 145mm"
        r"height\s+of\s+(?:only\s+)?(\d+)\s*mm",          # "height of only 37mm"
        r"(\d+)\s*mm.*?cpu\s*cooler\s*clearance",          # "165mm CPU cooler clearance"
        r"cooler\s+height[:\s]+(\d+)\s*mm",
        r"height\s+\(without\s+fan\)[:\s]+(\d+)\s*mm",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            # 合理的な範囲（20〜200mm）のみ採用
            if 20 <= val <= 200:
                return val
    return None


def _extract_fan_size(text: str) -> int | None:
    """ファンサイズ（mm）を抽出"""
    patterns = [
        # "Fan configuration 2x 140x140x25mm" (spec page)
        r"fan\s+configuration[:\s]+\d+x\s*(\d+)x",
        # "NF-A15 140mm fans", "NF-A12x25 120mm"
        r"NF-[A-Z]\d+[a-z0-9]*\s+(\d+)\s*mm",
        # "140mm fans"
        r"(\d+)\s*mm\s+(?:size\s+)?(?:fan|fans)",
        # "fan size: 140mm"
        r"fan\s+size[:\s]+(\d+)\s*mm",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if val in (80, 92, 120, 140, 150, 200):
                return val
    return None


def _extract_sockets(text: str) -> list[str] | None:
    """対応ソケット一覧を抽出（重複排除・順序保持）"""
    known = [
        "AM5", "AM4", "AM3+", "AM3", "AM2+", "AM2",
        "LGA1851", "LGA1700", "LGA1200",
        "LGA1150", "LGA1151", "LGA1155", "LGA1156",
        "LGA2066", "LGA2011-3", "LGA2011",
        "LGA775", "LGA1366",
        "sTRX4", "sTR4", "sWRX8",
    ]
    found = []
    for sock in known:
        if re.search(r"\b" + re.escape(sock) + r"\b", text, re.IGNORECASE):
            found.append(sock)
    return found or None


def _extract_tdp(text: str) -> int | None:
    """TDP目安（W）を抽出"""
    patterns = [
        r"TDP\s+rating[:\s]+(\d+)\s*W",
        r"TDP[:\s]+up\s+to\s+(\d+)\s*W",
        r"up\s+to\s+(\d+)\s*W\s+TDP",
        r"(\d+)\s*W\s+TDP",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 30 <= val <= 500:
                return val
    return None


def parse_product_page(html: str, url: str, name: str) -> dict:
    """製品ページ HTML からスペックを抽出してレコードを返す"""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # ページタイトルから名前を取得
    h1 = soup.find("h1")
    page_name = h1.get_text(strip=True) if h1 else name
    if not page_name:
        page_name = name

    # モデル名: URL から抽出
    m = re.search(r"/products/([^/?#]+)", url)
    model = m.group(1).upper() if m else page_name

    height_mm = _extract_height(text)
    socket_support = _extract_sockets(text)
    fan_size_mm = _extract_fan_size(text)
    tdp_rating_w = _extract_tdp(text)

    return {
        "source": "noctua",
        "category": "cpu_cooler",
        "name": page_name,
        "model": model,
        "product_url": url,
        "height_mm": height_mm,
        "socket_support": socket_support,
        "fan_size_mm": fan_size_mm,
        "tdp_rating_w": tdp_rating_w,
    }


# ── メイン ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Noctua CPUクーラー スクレイパー")
    parser.add_argument("--limit", type=int, default=5, help="取得件数 (デフォルト: 5)")
    parser.add_argument("--all", action="store_true", help="全件取得")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent=_UA,
            viewport={"width": 1280, "height": 900},
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        list_page = ctx.new_page()

        product_urls = get_product_urls(list_page)
        list_page.close()

        limit = len(product_urls) if args.all else args.limit
        targets = product_urls[:limit]
        print(f"\n対象: {len(targets)} 件\n", file=sys.stderr)

        results = []
        for i, prod in enumerate(targets, 1):
            # /specifications サブページから構造化スペックを取得
            spec_url = prod["url"].rstrip("/") + "/specifications"
            print(f"[{i}/{len(targets)}] {spec_url}", file=sys.stderr)
            page = ctx.new_page()
            try:
                try:
                    page.goto(spec_url, wait_until="networkidle", timeout=30000)
                except Exception:
                    pass

                passed = _wait_pass(page, 15)
                if not passed:
                    print("  ⚠️  Vercel チャレンジ未通過", file=sys.stderr)
                    page.close()
                    time.sleep(2)
                    continue

                page.keyboard.press("Escape")
                time.sleep(1)

                html = page.content()
                rec = parse_product_page(html, prod["url"], prod["name"])
                # spec_url が製品ページと異なる場合でも product_url は元 URL を保持
                results.append(rec)
                print(
                    f"  ✅ {rec['name']} | "
                    f"height={rec['height_mm']}mm | "
                    f"fan={rec['fan_size_mm']}mm | "
                    f"tdp={rec['tdp_rating_w']}W | "
                    f"sockets={rec['socket_support']}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"  ❌ ERROR: {e}", file=sys.stderr)
            finally:
                try:
                    page.close()
                except Exception:
                    pass
            time.sleep(2)

        browser.close()

    # JSONL 保存
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in results:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n✅ 保存: {OUTPUT_PATH} ({len(results)} 件)", file=sys.stderr)

    # サマリー
    print(
        f"\n{'モデル':<22} {'高さ':^7} {'ファン':^6} {'TDP':^6} ソケット",
        file=sys.stderr,
    )
    print("-" * 80, file=sys.stderr)
    for r in results:
        print(
            f"  {r['model']:<20} "
            f"{str(r['height_mm'])+'mm' if r['height_mm'] else 'None':^7} "
            f"{str(r['fan_size_mm'])+'mm' if r['fan_size_mm'] else 'None':^6} "
            f"{str(r['tdp_rating_w'])+'W' if r['tdp_rating_w'] else 'None':^6} "
            f"{', '.join(r['socket_support'] or [])}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
