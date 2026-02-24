#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASUS GPU スペックテキスト収集スクレイパー

ASUS GPU 製品にはマニュアル PDF が存在しないため、
公式スペックページ（/techspec/ または /spec/）の全テキストを収集して
products.jsonl の null 値を補完する。

フロー:
  1. workspace/data/asus/products.jsonl を読み込む
  2. product_url から techspec/spec URL を生成
  3. Playwright でページ取得・テキスト抽出
  4. manuals/{model}.txt に保存
  5. products.jsonl の null 値を補完して上書き

使い方:
  python asus_manual.py             # 最初の5件（デフォルト）
  python asus_manual.py --limit 3  # 3件
  python asus_manual.py --all      # 全件
  python asus_manual.py --no-headless  # ブラウザ表示（デバッグ用）
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

_JSONL_PATH = _ROOT / "workspace" / "data" / "asus" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "asus" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# ─── ヘルパー ─────────────────────────────────────────────────────────────────

def _spec_url(product_url: str) -> str:
    """
    product_url からスペックページ URL を返す。
    - rog.asus.com  → {url}/spec/
    - www.asus.com  → {url}/techspec/
    """
    base = product_url.rstrip("/")
    if "rog.asus.com" in base:
        return base + "/spec/"
    return base + "/techspec/"


def _model_key(product: dict) -> str:
    """製品の識別キーを返す（model > part_no > name の優先順）"""
    # URL末尾パスをモデルIDとして使用
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


JS_ROG_TEXT = """
() => {
    // ROG spec ページ: h2 を見出しとして直後の値を取得
    const lines = [];
    document.querySelectorAll('h2').forEach(h => {
        const label = h.textContent.trim();
        if (!label) return;
        const parent = h.parentElement;
        let valueEl = parent ? parent.nextElementSibling : null;
        if (!valueEl || !valueEl.textContent.trim()) valueEl = h.nextElementSibling;
        if (valueEl) lines.push(label + ': ' + valueEl.textContent.replace(/\\s+/g, ' ').trim());
    });
    return lines.join('\\n');
}
"""

JS_WWW_TEXT = """
() => {
    const lines = [];
    document.querySelectorAll('[class*="TechSpec__rowTable__"]').forEach(row => {
        const titleEl = row.querySelector('[class*="TechSpec__specTitle__"]')
                     || row.querySelector('[class*="rowTableTitle"]');
        const valueEl = row.querySelector('[class*="TechSpec__specContent__"]')
                     || row.querySelector('[class*="rowTableItem"]');
        if (titleEl && valueEl) {
            const label = titleEl.textContent.trim();
            const value = valueEl.textContent.replace(/\\s+/g, ' ').trim();
            if (label) lines.push(label + ': ' + value);
        }
    });
    return lines.join('\\n');
}
"""

# ─── スペック補完ヘルパー ──────────────────────────────────────────────────────

_SPEC_PATTERNS = {
    "tdp_w": [
        r"推奨PSU[:\s]+(\d+)\s*W",
        r"Recommended PSU[:\s]+(\d+)\s*W",
        r"最大消費電力[:\s]+(\d+)\s*W",
        r"TDP[:\s]+(\d+)\s*W",
    ],
    "length_mm": [
        r"サイズ[:\s]+(\d+)\s*x",
        r"Size[:\s]+(\d+(?:\.\d+)?)\s*x",
        r"Card\s+Dimension[:\s]+(\d+(?:\.\d+)?)\s*mm",
    ],
    "slot_width": [
        r"([\d.]+)\s*[Ss]lot",
        r"Slots[:\s]+([\d.]+)",
        r"スロット[:\s]+([\d.]+)",
    ],
    "power_connector": [
        r"電源コネクタ[:\s]+([^\n]+)",
        r"電源コネクター[:\s]+([^\n]+)",
        r"Power Connector[:\s]+([^\n]+)",
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
        page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [goto error] {e}", file=sys.stderr)
    time.sleep(2)

    if "rog.asus.com" in product_url:
        text = page.evaluate(JS_ROG_TEXT)
    else:
        text = page.evaluate(JS_WWW_TEXT)

    # フォールバック: JS で取れなければ body テキスト全体
    if not text or len(text) < 100:
        text = page.evaluate("() => document.body.innerText")

    return text or ""


def run(limit: int = 5, headless: bool = True) -> None:
    from datetime import datetime, timezone

    products = load_products()
    targets = products[:limit]
    print(f"\n[ASUS] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent=_UA,
            viewport={"width": 1280, "height": 900},
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
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

                # スペック抽出
                specs = _extract_specs_from_text(text)

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
        f"\n[ASUS] 完了: 成功={updated} 失敗={failed} | products.jsonl 更新済み",
        file=sys.stderr,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ASUS GPU スペックテキスト収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit, headless=not args.no_headless)


if __name__ == "__main__":
    main()
