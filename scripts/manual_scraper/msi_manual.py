#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSI GPU スペックテキスト収集スクレイパー

MSI GPU 製品の公式スペックページ（/Specification）のテキストを収集して
products.jsonl の null 値を補完する。

MSI はAkamai CDNによるbot検知が厳しいため、以下の対策を実施:
  - まずトップページにアクセスして Cookie を取得
  - リアルなブラウザフィンガープリントを模倣
  - ブロック時は products.jsonl 内の既存 raw データから補完

フロー:
  1. workspace/data/msi/products.jsonl を読み込む
  2. product_url + /Specification でスペック URL を生成
  3. Playwright でページ取得・テキスト抽出
  4. manuals/{model}.txt に保存
  5. products.jsonl の null 値を補完して上書き

使い方:
  python msi_manual.py             # 最初の5件（デフォルト）
  python msi_manual.py --limit 3  # 3件
  python msi_manual.py --all      # 全件
  python msi_manual.py --no-headless  # ブラウザ表示（デバッグ用）
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

_JSONL_PATH = _ROOT / "workspace" / "data" / "msi" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "msi" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# よりリアルな User-Agent
_MSI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ─── ヘルパー ─────────────────────────────────────────────────────────────────

def _spec_url(product_url: str) -> str:
    """product_url からスペックページ URL を返す（末尾に /Specification を追加）"""
    base = product_url.rstrip("/")
    return base + "/Specification"


def _model_key(product: dict) -> str:
    """製品の識別キーを返す（product_id > part_no > name の優先順）"""
    for key in ("product_id", "part_no", "name"):
        val = product.get(key, "")
        if val:
            return re.sub(r"[<>/\\|?*\":]", "_", str(val))[:80]
    return "unknown"


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


# MSI スペックページ用 JS 抽出
JS_MSI_TEXT = """
() => {
    const lines = [];
    document.querySelectorAll('.main-specifications tr, .specificationsItem, dl').forEach(el => {
        const text = el.textContent.replace(/\\s+/g, ' ').trim();
        if (text) lines.push(text);
    });
    if (lines.length === 0) return document.body.innerText;
    return lines.join('\\n');
}
"""

# Bot検知バイパス用 初期化スクリプト
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['ja-JP','ja','en-US','en']});
window.chrome = {runtime: {}};
"""

# ─── スペック補完ヘルパー ──────────────────────────────────────────────────────

_SPEC_PATTERNS = {
    "tdp_w": [
        r"推奨PSU[:\s]+(\d+)\s*W",
        r"Recommended PSU[:\s]+(\d+)\s*W",
        r"最大消費電力[:\s]+(\d+)\s*W",
        r"TDP[:\s]+(\d+)\s*W",
        r"Power\s+Consumption[:\s]+(\d+)\s*W",
        r"(\d+)\s*W\s+TDP",
    ],
    "length_mm": [
        r"Card\s+Dimension[:\s]+(\d+(?:\.\d+)?)\s*(?:x|X|×)",
        r"サイズ[:\s]+(\d+)\s*(?:x|X|×)",
        r"Size[:\s]+(\d+(?:\.\d+)?)\s*(?:x|X|×)",
        r"Card\s+Length[:\s]+(\d+(?:\.\d+)?)\s*mm",
        r"(\d{2,3})\s*x\s*\d+\s*x\s*\d+\s*mm",
    ],
    "slot_width": [
        r"([\d.]+)\s*[Ss]lot",
        r"Slots?[:\s]+([\d.]+)",
        r"スロット[:\s]+([\d.]+)",
    ],
    "power_connector": [
        r"電源コネクタ[:\s]+([^\n]+)",
        r"電源コネクター[:\s]+([^\n]+)",
        r"Power Connector[:\s]+([^\n]+)",
        r"(?:16|12VHPWR|12V-2x6)[- ]?pin\s*(?:x\s*\d+)?",
        r"(\d+-pin\s*x\s*\d+)",
    ],
}


def _extract_specs_from_text(text: str) -> dict:
    """スペックテキストから null 補完候補を抽出する"""
    specs = {}
    for field, patterns in _SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw = m.group(1).strip() if m.lastindex else m.group(0).strip()
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


def _estimate_slot_width_from_size(size_raw: str) -> float | None:
    """
    size_raw（例: "303 x 121 x 49 mm"）から厚さ(mm)を取得し slot_width を推定する。
    PCIe 1スロット = 約 20mm。2スロット=40mm, 2.5=50mm, 3=60mm, 3.5=70mm
    """
    if not size_raw:
        return None
    # "W x H x D mm" パターン（3番目の数値が厚さ）
    m = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm", size_raw, re.IGNORECASE)
    if not m:
        return None
    thickness = float(m.group(3))
    if thickness < 15 or thickness > 120:
        return None
    # 20mm = 1slot として推定、0.5刻みに丸め
    raw_slots = thickness / 20.0
    rounded = round(raw_slots * 2) / 2  # 0.5刻み
    if 1.0 <= rounded <= 5.0:
        return rounded
    return None


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


def _warm_up_session(page) -> None:
    """MSI トップページにアクセスして Cookie/セッションを確立する"""
    print("  [warm-up] jp.msi.com トップページ...", file=sys.stderr)
    try:
        page.goto("https://jp.msi.com/", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)
    except Exception as e:
        print(f"  [warm-up error] {e}", file=sys.stderr)


def scrape_spec_text(page, product_url: str, retried: bool = False) -> str:
    """スペックページにアクセスしてテキストを取得する"""
    spec_url = _spec_url(product_url)
    print(f"  spec_url: {spec_url}", file=sys.stderr)

    try:
        page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [goto error] {e}", file=sys.stderr)
    time.sleep(4)

    # Access Denied チェック
    body_text = page.evaluate("() => document.body.innerText") or ""
    if "Access Denied" in body_text:
        if not retried:
            print("  [blocked] Access Denied - product_url を直接試行", file=sys.stderr)
            try:
                page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(4)
                body_text = page.evaluate("() => document.body.innerText") or ""
                if "Access Denied" in body_text:
                    print("  [blocked] product_url もブロック", file=sys.stderr)
                    return ""
            except Exception as e:
                print(f"  [goto error] {e}", file=sys.stderr)
                return ""
        else:
            return ""

    # MSI 固有の JS でスペックテーブルからテキストを抽出
    text = page.evaluate(JS_MSI_TEXT)

    # フォールバック: JS で取れなければ body テキスト全体
    if not text or len(text) < 100:
        print("  [fallback] body.innerText を使用", file=sys.stderr)
        text = body_text

    return text or ""


def run(limit: int = 5, headless: bool = True) -> None:
    from datetime import datetime, timezone

    products = load_products()
    targets = products[:limit]
    print(f"\n[MSI] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0
    blocked_count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
            ],
        )
        ctx = browser.new_context(
            user_agent=_MSI_UA,
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            extra_http_headers={
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        ctx.add_init_script(_STEALTH_JS)
        page = ctx.new_page()

        # MSI トップページで Cookie を取得
        _warm_up_session(page)

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

                scraped_ok = bool(text and len(text) >= 50 and "Access Denied" not in text)

                if scraped_ok:
                    # テキスト保存
                    safe = _safe_filename(model)
                    out_path = _MANUAL_DIR / f"{safe}.txt"
                    out_path.write_text(text, encoding="utf-8")

                    # スペック抽出（ローカルパターン + base共通の両方）
                    specs_local = _extract_specs_from_text(text)
                    specs_base = extract_manual_specs(text)
                    specs = {**specs_base, **specs_local}

                    prod["manual_path"] = str(out_path.relative_to(_ROOT))
                    prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
                    prod["manual_specs"] = specs
                else:
                    blocked_count += 1
                    print("  [blocked] スクレイピング不可 - raw データで補完", file=sys.stderr)
                    specs = {}

                # null フィールドを補完（スクレイプ成功・失敗どちらでも既存rawデータから補完試行）
                null_filled = []

                # specs から補完
                for field, val in specs.items():
                    if prod.get(field) is None and val is not None:
                        prod[field] = val
                        null_filled.append(f"{field}={val}")

                # slot_width が未取得の場合、size_raw から推定
                if prod.get("slot_width") is None:
                    size_raw = prod.get("size_raw", "")
                    est = _estimate_slot_width_from_size(size_raw)
                    if est is not None:
                        prod["slot_width"] = est
                        null_filled.append(f"slot_width={est}(推定)")

                if scraped_ok:
                    updated += 1
                    print(
                        f"  OK: {len(text)} 文字 | specs={specs}"
                        + (f" | 補完={null_filled}" if null_filled else ""),
                        file=sys.stderr,
                    )
                else:
                    if null_filled:
                        updated += 1
                        print(f"  PARTIAL: raw データ補完={null_filled}", file=sys.stderr)
                    else:
                        failed += 1

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                failed += 1

            time.sleep(2)

        browser.close()

    save_products(products)
    print(
        f"\n[MSI] 完了: 成功={updated} 失敗={failed} blocked={blocked_count} | products.jsonl 更新済み",
        file=sys.stderr,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MSI GPU スペックテキスト収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit, headless=not args.no_headless)


if __name__ == "__main__":
    main()
