#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Noctua CPUクーラー スペックテキスト収集スクレイパー

Noctua 製品の /specifications サブページからスペックテキストを収集して
products.jsonl の tdp_rating_w 等の null 値を補完する。

Noctua は Vercel Security Checkpoint で保護されているため、
headless=True で失敗した場合は headless=False にフォールバックする。

フロー:
  1. workspace/data/noctua_cooler/products.jsonl を読み込む
  2. product_url + /specifications からスペックページ URL を生成
  3. Playwright でページ取得・テキスト抽出
  4. manuals/{model}.txt に保存
  5. products.jsonl の null 値を補完して上書き

使い方:
  python noctua_manual.py             # 最初の5件（デフォルト）
  python noctua_manual.py --limit 3  # 3件
  python noctua_manual.py --all      # 全件
  python noctua_manual.py --no-headless  # ブラウザ表示（デバッグ用）
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

from manual_scraper.base import _UA, _ROOT

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

# --- 定数 -------------------------------------------------------------------

_JSONL_PATH = _ROOT / "workspace" / "data" / "noctua_cooler" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "noctua_cooler" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# --- ヘルパー ----------------------------------------------------------------


def _spec_url(product_url: str) -> str:
    """product_url から /specifications サブページ URL を返す"""
    return product_url.rstrip("/") + "/specifications"


def _model_key(product: dict) -> str:
    """製品の識別キーを返す（model > name の優先順）"""
    for key in ("model", "name"):
        val = product.get(key, "")
        if val:
            return re.sub(r"[<>/\\|?*\":]", "_", str(val))[:80]
    return "unknown"


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


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


# Noctua スペックページからテキストを抽出する JavaScript
JS_NOCTUA_TEXT = """
() => {
    const lines = [];
    // テーブル行
    document.querySelectorAll('table tr').forEach(tr => {
        const text = tr.textContent.replace(/\\s+/g, ' ').trim();
        if (text.length > 3) lines.push(text);
    });
    // dt/dd ペア
    const dts = document.querySelectorAll('dt');
    dts.forEach(dt => {
        const dd = dt.nextElementSibling;
        if (dd) lines.push(dt.textContent.trim() + ': ' + dd.textContent.trim());
    });
    if (lines.length < 3) return document.body.innerText;
    return lines.join('\\n');
}
"""

# --- TDP 抽出 ----------------------------------------------------------------

_TDP_PATTERNS = [
    r"TDP\s+rating[:\s]*(\d+)\s*W",
    r"[Rr]ecommended\s+TDP[:\s]*(\d+)\s*W",
    r"up\s+to\s+(\d+)\s*W",
    r"(\d+)\s*W\s+TDP",
]


def _extract_tdp_from_text(text: str) -> int | None:
    """テキストから TDP (W) を抽出する"""
    for pat in _TDP_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 30 <= val <= 500:
                return val
    return None


def _extract_nspr(text: str) -> int | None:
    """Noctua Standardised Performance Rating (NSPR) を抽出する"""
    m = re.search(r"NSPR\s*(\d+)", text)
    if m:
        val = int(m.group(1))
        if 10 <= val <= 500:
            return val
    return None


# --- スペック抽出（汎用フィールドも含む）------------------------------------
# Noctua のスペックページはラベルと値がスペース/コロンなしで連結されている:
#   "Total height168 mm"  "Fan configuration2x 140x140x25mm"
# これに対応するパターンを用意する。

_SPEC_PATTERNS = {
    "height_mm": [
        r"[Tt]otal\s+height\s*[:\s]*(\d+)\s*mm",
        r"Height\s+with\s+fan\(s\)\s*(\d+)\s*mm",
        r"[Hh]eight\s*[:\s]*(\d+)\s*mm",
    ],
    "fan_size_mm": [
        # "Fan configuration2x 140x140x25mm" -> 140
        r"[Ff]an\s+configuration\s*\d*x?\s*(\d+)\s*x\s*\d+\s*x",
        # "140x140x25mm" standalone
        r"(\d+)\s*x\s*\d+\s*x\s*\d+\s*mm",
        r"(\d+)\s*mm\s+(?:fan|fans)",
    ],
}


def _extract_specs_from_text(text: str) -> dict:
    """スペックテキストから補完候補を抽出する"""
    specs = {}

    tdp = _extract_tdp_from_text(text)
    if tdp is not None:
        specs["tdp_rating_w"] = tdp

    # NSPR を保存（TDP の代替指標）
    nspr = _extract_nspr(text)
    if nspr is not None:
        specs["nspr"] = nspr

    for field, patterns in _SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                except ValueError:
                    continue
                if field == "height_mm" and 20 <= val <= 200:
                    specs[field] = val
                elif field == "fan_size_mm" and val in (80, 92, 120, 140, 150, 200):
                    specs[field] = val
                break

    return specs


# --- メイン処理 ---------------------------------------------------------------

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

    # Vercel チャレンジ通過を待機
    passed = _wait_pass(page, 15)
    if not passed:
        print("  WARN: Vercel チャレンジ未通過", file=sys.stderr)
        return ""

    time.sleep(2)

    # JavaScript でスペックテキストを抽出
    text = page.evaluate(JS_NOCTUA_TEXT)

    # フォールバック: JS で取れなければ body テキスト全体
    if not text or len(text) < 50:
        text = page.evaluate("() => document.body.innerText")

    return text or ""


def run(limit: int = 5, headless: bool = True) -> None:
    from datetime import datetime, timezone

    products = load_products()
    targets = products[:limit]
    print(f"\n[Noctua] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0
    tdp_filled = 0

    def _try_scrape(headless_mode: bool) -> tuple[int, int, int]:
        """指定の headless モードでスクレイピングを実行"""
        nonlocal updated, failed, tdp_filled

        mode_label = "headless" if headless_mode else "headed"
        print(f"  [{mode_label}モードで実行]\n", file=sys.stderr)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless_mode,
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

                # 既にスクレイプ済みならスキップ
                if prod.get("manual_scraped_at"):
                    print("  SKIP: スクレイプ済み", file=sys.stderr)
                    continue

                try:
                    text = scrape_spec_text(page, purl)
                    if not text or len(text) < 50:
                        print("  WARN: テキスト取得なし / Vercel ブロック", file=sys.stderr)
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
                            if field == "tdp_rating_w":
                                tdp_filled += 1

                    updated += 1
                    print(
                        f"  OK: {len(text)} 文字 | specs={specs}"
                        + (f" | 補完={null_filled}" if null_filled else ""),
                        file=sys.stderr,
                    )

                except Exception as e:
                    print(f"  ERROR: {e}", file=sys.stderr)
                    failed += 1

                time.sleep(2)

            browser.close()

        return updated, failed, tdp_filled

    # まず headless=True で試行
    _try_scrape(headless)

    # headless で全件失敗した場合、headed モードで再試行
    if headless and updated == 0 and failed == len(targets):
        print(
            "\n[Noctua] headless で全件失敗 -> headed モードで再試行\n",
            file=sys.stderr,
        )
        # カウンターリセット
        updated = 0
        failed = 0
        tdp_filled = 0
        # manual_scraped_at をクリアして再試行可能にする
        for prod in targets:
            prod.pop("manual_scraped_at", None)
        _try_scrape(False)

    save_products(products)
    print(
        f"\n[Noctua] 完了: 成功={updated} 失敗={failed} | "
        f"tdp_rating_w 補完={tdp_filled} 件 | products.jsonl 更新済み",
        file=sys.stderr,
    )


# --- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Noctua CPUクーラー スペックテキスト収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit, headless=not args.no_headless)


if __name__ == "__main__":
    main()
