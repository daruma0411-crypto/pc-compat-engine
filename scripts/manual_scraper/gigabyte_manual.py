#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIGABYTE GPU スペックテキスト収集スクレイパー

GIGABYTE GPU 製品の公式スペックページ（#kf タブ）の全テキストを収集して
products.jsonl の null 値を補完する。

フロー:
  1. workspace/data/gigabyte/products.jsonl を読み込む
  2. product_url + #kf でスペックページ URL を生成
  3. Playwright でページ取得・テキスト抽出
  4. manuals/{model}.txt に保存
  5. products.jsonl の null 値を補完して上書き

使い方:
  python gigabyte_manual.py             # 最初の5件（デフォルト）
  python gigabyte_manual.py --limit 3  # 3件
  python gigabyte_manual.py --all      # 全件
  python gigabyte_manual.py --no-headless  # ブラウザ表示（デバッグ用）
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR.parent))

from manual_scraper.base import extract_manual_specs, _UA, _ROOT

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

# ─── 定数 ────────────────────────────────────────────────────────────────────

_JSONL_PATH = _ROOT / "workspace" / "data" / "gigabyte" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "gigabyte" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# ─── ヘルパー ─────────────────────────────────────────────────────────────────

def _spec_url(product_url: str) -> str:
    """
    product_url からスペックページ URL を返す。
    GIGABYTE は URL 末尾に #kf を付与してスペックタブへ遷移する。
    """
    base = product_url.rstrip("/")
    return base + "#kf"


def _model_key(product: dict) -> str:
    """製品の識別キーを返す（product_id > part_no > name の優先順）"""
    pid = product.get("product_id", "")
    if pid:
        return pid
    purl = product.get("product_url", "").rstrip("/")
    if purl:
        seg = purl.split("/")[-1]
        if seg:
            return seg.upper()
    for key in ("part_no", "name"):
        val = product.get(key, "")
        if val:
            return re.sub(r"[<>/\\|?*\":]", "_", str(val))[:80]
    return "unknown"


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


JS_GIGABYTE_SPEC = """
() => {
    const lines = [];
    // スペックテーブルを探す (.spec-list, table.detail-spec, etc.)
    const rows = document.querySelectorAll('.spec-list li, table tr, .detail-spec tr, .sp-table tr, .spec_table tr, .Key-Feature-Spec tr, .key-feature-spec tr');
    rows.forEach(row => {
        const text = row.textContent.replace(/\\s+/g, ' ').trim();
        if (text.length > 3) lines.push(text);
    });
    // フォールバック: sp-section / key-feature セクションも試す
    if (lines.length < 5) {
        document.querySelectorAll('.sp-section, .key-feature-section, [class*="spec"]').forEach(el => {
            const text = el.textContent.replace(/\\s+/g, ' ').trim();
            if (text.length > 10) lines.push(text);
        });
    }
    if (lines.length < 5) return document.body.innerText;
    return lines.join('\\n');
}
"""

# ─── スペック補完ヘルパー ──────────────────────────────────────────────────────

_SPEC_PATTERNS = {
    "tdp_w": [
        r"推奨PSU[:\s]+(\d+)\s*W",
        r"Recommended PSU[:\s]+(\d+)\s*W",
        r"最大消費電力[:\s]+(\d+)\s*W",
        r"Power Consumption[:\s]+(\d+)\s*W",
        r"TDP[:\s]+(\d+)\s*W",
        r"(\d+)\s*W\s+(?:or\s+above|以上)",
    ],
    "length_mm": [
        r"L\s*=?\s*(\d+)\s*(?:mm)?",
        r"サイズ[:\s]+(\d+)\s*x",
        r"Size[:\s]+(\d+(?:\.\d+)?)\s*x",
        r"Card\s+(?:Dimension|Length)[:\s]+(\d+(?:\.\d+)?)\s*mm",
        r"(\d{2,3})\s*mm\s*x\s*\d+",
    ],
    "slot_width": [
        r"([\d.]+)\s*[Ss]lot",
        r"Slots?[:\s]+([\d.]+)",
        r"スロット[:\s]+([\d.]+)",
        r"(\d(?:\.\d)?)\s*スロット",
    ],
    "power_connector": [
        r"電源コネクタ[:\s]+([^\n]+)",
        r"電源コネクター[:\s]+([^\n]+)",
        r"Power Connector[:\s]+([^\n]+)",
        r"補助電源[:\s]+([^\n]+)",
    ],
}


def _extract_specs_from_text(text: str) -> dict:
    """スペックテキストから null 補完候補を抽出する"""
    specs = {}
    for field, patterns in _SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                if field in ("tdp_w", "length_mm"):
                    try:
                        val = int(float(raw))
                        if field == "tdp_w" and 50 <= val <= 2000:
                            specs[field] = val
                        elif field == "length_mm" and 100 <= val <= 600:
                            specs[field] = val
                    except ValueError:
                        pass
                elif field == "slot_width":
                    try:
                        val = float(raw)
                        if 1.0 <= val <= 5.0:
                            specs[field] = val
                    except ValueError:
                        pass
                elif field == "power_connector":
                    if len(raw) < 80:
                        specs[field] = raw
                break

    # size_raw から slot_width の補完を試みる（"Dual Slot" パターン）
    if "slot_width" not in specs:
        size_raw_text = text
        if re.search(r"Dual\s+Slot", size_raw_text, re.IGNORECASE):
            specs["slot_width"] = 2.0
        elif re.search(r"Triple\s+Slot", size_raw_text, re.IGNORECASE):
            specs["slot_width"] = 3.0
        elif re.search(r"Quad\s+Slot", size_raw_text, re.IGNORECASE):
            specs["slot_width"] = 4.0

    return specs


# ─── メイン処理 ───────────────────────────────────────────────────────────────

def load_products() -> list[dict]:
    products = []
    with open(_JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def save_products(products: list[dict]) -> None:
    with open(_JSONL_PATH, "w", encoding="utf-8") as f:
        for rec in products:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def scrape_spec_text(page, product_url: str) -> str:
    """スペックページにアクセスしてテキストを取得する"""
    spec_url = _spec_url(product_url)
    print(f"  spec_url: {spec_url}", file=sys.stderr)

    try:
        # まずベースURLにアクセス（#kf はフラグメントなのでページロード後にJSで処理される）
        page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [goto error] {e}", file=sys.stderr)

    # ページのJS描画を待つ
    time.sleep(3)

    # #kf タブをクリックして切り替えを試みる
    try:
        kf_tab = page.query_selector('a[href="#kf"], [data-target="#kf"], .nav-link[href*="kf"]')
        if kf_tab:
            kf_tab.click()
            time.sleep(2)
            print("  [info] #kf タブをクリック", file=sys.stderr)
        else:
            # URL遷移で#kfを試す
            page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
    except Exception as e:
        print(f"  [tab click] {e}", file=sys.stderr)

    # JS でスペックテキストを抽出
    text = page.evaluate(JS_GIGABYTE_SPEC)

    # フォールバック: JS で取れなければ body テキスト全体
    if not text or len(text) < 100:
        print("  [info] JS抽出不十分、bodyテキストにフォールバック", file=sys.stderr)
        text = page.evaluate("() => document.body.innerText")

    return text or ""


def run(limit: int = 5, headless: bool = True) -> None:
    from datetime import datetime, timezone

    products = load_products()
    targets = products[:limit]
    print(f"\n[GIGABYTE] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = browser.new_context(
            user_agent=_UA,
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            extra_http_headers={
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['ja', 'en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            window.chrome = {runtime: {}};
        """)
        page = ctx.new_page()

        for i, prod in enumerate(targets, 1):
            model = _model_key(prod)
            name = prod.get("name", "")[:60]
            print(f"[{i}/{len(targets)}] {name}", file=sys.stderr)

            purl = prod.get("product_url", "")
            if not purl:
                print("  SKIP: product_url なし", file=sys.stderr)
                failed += 1
                continue

            try:
                text = scrape_spec_text(page, purl)
                if not text or len(text) < 50:
                    print("  WARN: テキスト取得なし", file=sys.stderr)
                    failed += 1
                    continue

                # テキスト保存
                safe = _safe_filename(model)
                out_path = _MANUAL_DIR / f"{safe}.txt"
                out_path.write_text(text, encoding="utf-8")

                # スペック抽出（ページテキスト + 既存 size_raw / slot_raw も合わせて検索）
                combined_text = text
                if prod.get("size_raw"):
                    combined_text += "\n" + str(prod["size_raw"])
                if prod.get("slot_raw"):
                    combined_text += "\n" + str(prod["slot_raw"])
                specs = _extract_specs_from_text(combined_text)

                # products.jsonl 更新
                prod["manual_path"] = str(out_path.relative_to(_ROOT))
                prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
                prod["manual_specs"] = specs

                # null フィールドを補完
                null_filled = []
                for field, val in specs.items():
                    if prod.get(field) is None and val is not None:
                        prod[field] = val
                        null_filled.append(f"{field}={val}")

                updated += 1
                print(
                    f"  OK: {len(text)} 文字 | specs={specs}"
                    + (f" | 補完={null_filled}" if null_filled else ""),
                    file=sys.stderr,
                )

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                failed += 1

            time.sleep(1.5)

        browser.close()

    save_products(products)
    print(
        f"\n[GIGABYTE] 完了: 成功={updated} 失敗={failed} | products.jsonl 更新済み",
        file=sys.stderr,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GIGABYTE GPU スペックテキスト収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit, headless=not args.no_headless)


if __name__ == "__main__":
    main()
