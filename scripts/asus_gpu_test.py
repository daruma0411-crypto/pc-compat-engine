#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASUS GPU スペック スクレイピング テスト
最初の5製品を SeriesFilterResult API で取得し、各スペックページを
Playwright でスクレイピングして JSONL を出力する。

スペックページURL規則:
  - rog.asus.com 製品  → {ProductURL}spec/
  - www.asus.com 製品  → {ProductURL}techspec/
"""

import io
import json
import re
import sys
import time
import httpx
from playwright.sync_api import sync_playwright

# Windows CP932 対策: stdout/stderr を UTF-8 に強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── API ─────────────────────────────────────────────────────────────────────

SERIES_FILTER_URL = (
    "https://odinapi.asus.com/recent-data/apiv2/SeriesFilterResult"
    "?SystemCode=asus&WebsiteCode=jp"
    "&ProductLevel1Code=motherboards-components"
    "&ProductLevel2Code=graphics-cards"
    "&PageSize=5&PageIndex=1"
    "&Sort=Newsest&siteID=www&sitelang="
)

# ─── Spec parsing helpers ─────────────────────────────────────────────────────

def _find_spec(spec_map: dict, *keys: str) -> str:
    """複数のキー候補を試してスペック値を返す（なければ空文字）"""
    for k in keys:
        if k in spec_map:
            return spec_map[k].strip()
    return ""


def _parse_length_mm(size_str: str) -> int | None:
    """'332 x 147.3 x 64 mm ...' → 332"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*x\s*\d", size_str)
    return int(float(m.group(1))) if m else None


def _parse_psu_w(psu_str: str) -> int | None:
    """'750W' → 750"""
    m = re.search(r"(\d+)\s*W", psu_str, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_slot(slot_str: str) -> float | None:
    """'3.2 Slot' → 3.2"""
    m = re.search(r"(\d+(?:\.\d+)?)", slot_str)
    return float(m.group(1)) if m else None


def _parse_connector(conn_str: str) -> str:
    """電源コネクタ文字列を正規化"""
    return conn_str.replace(" ", "").replace("×", "x").replace("ピン", "pin")


# ─── Playwright scraping ──────────────────────────────────────────────────────

SPEC_HEADING_SELECTORS = [
    # www.asus.com (techspec) / rog.asus.com (spec) 共通パターン
    "h2",                           # heading level 2
]

JS_ROG_SPEC = """
() => {
    // ROG spec ページ: h2 → 直後の sibling div が値
    const result = {};
    const headings = document.querySelectorAll('h2');
    headings.forEach(h => {
        const label = h.textContent.trim();
        if (!label) return;
        // parent.nextElementSibling パターン
        const parent = h.parentElement;
        let valueEl = parent ? parent.nextElementSibling : null;
        if (!valueEl || !valueEl.textContent.trim()) {
            valueEl = h.nextElementSibling;
        }
        if (valueEl) {
            result[label] = valueEl.textContent.replace(/\\s+/g, ' ').trim();
        }
    });
    return result;
}
"""

JS_WWW_SPEC = """
() => {
    // www.asus.com techspec ページ: TechSpec__rowTable__ クラスの行から取得
    const rows = document.querySelectorAll('[class*="TechSpec__rowTable__"]');
    const result = {};
    rows.forEach(row => {
        const titleEl = row.querySelector('[class*="TechSpec__specTitle__"]')
                     || row.querySelector('[class*="rowTableTitle"]');
        const valueEl = row.querySelector('[class*="TechSpec__specContent__"]')
                     || row.querySelector('[class*="rowTableItem"]');
        if (titleEl && valueEl) {
            const label = titleEl.textContent.trim();
            const value = valueEl.textContent.replace(/\\s+/g, ' ').trim();
            if (label) result[label] = value;
        }
    });
    return result;
}
"""


def scrape_spec_page(page, url: str) -> dict:
    """
    スペックページに移動し、見出し→値のマップを返す。
    - rog.asus.com → JS_ROG_SPEC (h2ベース)
    - www.asus.com → JS_WWW_SPEC (TechSpec__クラスベース)
    """
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(1.5)  # JS 描画待ち

    if "rog.asus.com" in url:
        js = JS_ROG_SPEC
    else:
        js = JS_WWW_SPEC

    spec_map = page.evaluate(js)
    return spec_map


def build_record(product: dict, spec_map: dict) -> dict:
    """SeriesFilterResult エントリ + スペックマップ → JSONL レコード"""
    size_str   = _find_spec(spec_map, "サイズ")
    psu_str    = _find_spec(spec_map, "推奨PSU", "Recommended PSU")
    conn_str   = _find_spec(spec_map, "電源コネクタ", "電源コネクター", "Power Connector")
    slot_str   = _find_spec(spec_map, "Slot", "スロット", "Slots", "Slot数")
    vram_str   = _find_spec(spec_map, "ビデオメモリ", "Memory")
    core_str   = _find_spec(spec_map, "グラフィックスエンジン", "Graphic Engine")
    clock_str  = _find_spec(spec_map, "コアクロック", "Core Clock")
    bus_str    = _find_spec(spec_map, "バスインターフェース", "Bus Interface")
    display_str= _find_spec(spec_map, "インターフェース", "Interface")

    name_raw = product.get("Name", "")
    # Name に HTML タグが含まれる場合は除去
    name_clean = re.sub(r"<[^>]+>", "", name_raw).strip()

    rec = {
        "source":           "asus",
        "category":         "gpu",
        "part_no":          product.get("PartNo", ""),
        "m1_id":            product.get("M1Id") or product.get("ProductID"),
        "name":             name_clean,
        "product_url":      product.get("ProductURL", ""),
        "gpu_chip":         core_str,
        "vram":             vram_str,
        "bus_interface":    bus_str,
        "boost_clock":      clock_str,
        "display_output":   display_str,
        "length_mm":        _parse_length_mm(size_str),
        "tdp_w":            _parse_psu_w(psu_str),   # 推奨PSU (実TDP≠PSU だが代替値)
        "slot_width":       _parse_slot(slot_str),
        "power_connector":  _parse_connector(conn_str) if conn_str else "",
        "size_raw":         size_str,
        "psu_raw":          psu_str,
        "connector_raw":    conn_str,
        "slot_raw":         slot_str,
    }
    return rec


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # 1. 製品リスト取得
    print("[1/2] SeriesFilterResult API から5製品取得中...", file=sys.stderr)
    resp = httpx.get(SERIES_FILTER_URL, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    products = data.get("Result", {}).get("ProductList", [])
    if not products:
        # キー構造が異なる場合のフォールバック
        products = data.get("ProductList", [])
    products = products[:5]
    print(f"  → {len(products)} 件取得", file=sys.stderr)

    # 2. 各製品のスペックを取得
    records = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        for i, prod in enumerate(products, 1):
            url_base = prod.get("ProductURL", "")
            name_raw = re.sub(r"<[^>]+>", "", prod.get("Name", "")).strip()
            print(f"[{i}/5] {name_raw[:60]}...", file=sys.stderr)
            print(f"       URL: {url_base}", file=sys.stderr)

            if not url_base:
                print("  SKIP: ProductURL が空", file=sys.stderr)
                continue

            # スペックページURL
            if "rog.asus.com" in url_base:
                spec_url = url_base.rstrip("/") + "/spec/"
            else:
                spec_url = url_base.rstrip("/") + "/techspec/"

            print(f"  spec_url: {spec_url}", file=sys.stderr)

            try:
                spec_map = scrape_spec_page(page, spec_url)
                print(f"  取得キー数: {len(spec_map)}", file=sys.stderr)

                # デバッグ: 主要キーを表示
                for k in ("サイズ", "推奨PSU", "電源コネクタ", "Slot", "スロット"):
                    if k in spec_map:
                        print(f"    {k}: {spec_map[k][:60]}", file=sys.stderr)

                rec = build_record(prod, spec_map)
                records.append(rec)

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                records.append({
                    "source": "asus", "category": "gpu",
                    "name": name_raw,
                    "product_url": url_base,
                    "error": str(e),
                })

            time.sleep(1)  # リクエスト間隔

        browser.close()

    # 3. JSONL ファイル保存 + コンソール出力
    import pathlib
    out_path = pathlib.Path(__file__).parent / "asus_gpu_sample.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            line = json.dumps(rec, ensure_ascii=False)
            f.write(line + "\n")
            print(line)

    print(f"\n[保存完了] {out_path}  ({len(records)} 件)", file=sys.stderr)

    # サマリー
    print("\n[サマリー]", file=sys.stderr)
    for rec in records:
        if "error" not in rec:
            print(
                f"  {rec.get('name','')[:50]:<50} | "
                f"length={rec.get('length_mm')} mm | "
                f"psu={rec.get('tdp_w')} W | "
                f"slot={rec.get('slot_width')} | "
                f"conn={rec.get('power_connector')}",
                file=sys.stderr
            )
        else:
            print(f"  ERROR: {rec.get('name','')[:50]} → {rec['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
