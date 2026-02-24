#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIGABYTE GPU スペック スクレイピング テスト
製品リストページのDOMから最初の5製品URLを取得し、
各スペックページ (/{id}/sp) を Playwright でスクレイピングして JSONL を出力する。

DOM構造:
  - 製品リスト: a[href*="/jp/Graphics-Card/GV-"] → 製品URL (重複あり → set で除去)
  - スペックページ: .spec-item-list ul → li.spec-title (ラベル) + li.spec-desc (値)
  - サイズ形式: "L=330 W=145 H=65 mm" → L値を length_mm として使用
  - スロット情報: スペックページに記載なし → null

注意: GIGABYTE は headless Playwright を bot 検知するため headless=False を使用
"""

import io
import json
import re
import sys
import time
from playwright.sync_api import sync_playwright

# Windows CP932 対策: stdout/stderr を UTF-8 に強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Spec parsing helpers ─────────────────────────────────────────────────────

def _find_spec(spec_map: dict, *keys: str) -> str:
    """複数のキー候補を試してスペック値を返す（なければ空文字）"""
    for k in keys:
        if k in spec_map:
            return spec_map[k].strip()
    return ""


def _parse_length_mm(size_str: str) -> int | None:
    """'L=330 W=145 H=65 mm' → 330"""
    # GIGABYTE形式: L=XXX
    m = re.search(r"L=(\d+(?:\.\d+)?)", size_str, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    # フォールバック: 先頭の数値
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]?\s*\d", size_str)
    return int(float(m2.group(1))) if m2 else None


def _parse_psu_w(psu_str: str) -> int | None:
    """'1000W' → 1000"""
    m = re.search(r"(\d+)\s*W", psu_str, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_connector(conn_str: str) -> str:
    """電源コネクタ文字列を正規化 ('16 Pin*1' → '16Pin*1')"""
    return (conn_str
            .replace(" ", "")
            .replace("×", "x")
            .replace("-", "")
            .replace("ピン", "pin"))


# ─── JavaScript for DOM extraction ───────────────────────────────────────────

JS_PRODUCT_LIST = """
() => {
    // 製品リストページ: href に /jp/Graphics-Card/GV- を含むリンクを収集
    const links = Array.from(document.querySelectorAll('a[href*="/jp/Graphics-Card/GV-"]'));
    const seen = new Set();
    const products = [];
    links.forEach(a => {
        const href = a.href;
        // IDを抽出: /jp/Graphics-Card/{id} のパス最終部分
        const match = href.match(/\\/Graphics-Card\\/(GV-[^/]+?)(?:\\/|$)/);
        if (!match) return;
        const id = match[1];
        // 製品名: h2要素が最も信頼性高い (名前チェックをseen重複チェックより先に行う)
        const nameEl = a.querySelector('h2');
        const name = nameEl ? nameEl.textContent.trim() : a.textContent.trim();
        if (!name || name.length <= 3) return;  // 画像のみリンクをスキップ
        if (seen.has(id)) return;
        seen.add(id);
        products.push({ id, name, href });
    });
    return products;
}
"""

JS_GIGABYTE_SPEC = """
() => {
    // GIGABYTE spページ: .spec-item-list ul → li.spec-title + li.spec-desc
    const result = {};
    const lists = document.querySelectorAll('.spec-item-list');
    lists.forEach(ul => {
        const titleEls = ul.querySelectorAll('.spec-title');
        const descEls = ul.querySelectorAll('.spec-desc');
        if (titleEls.length === 1 && descEls.length === 1) {
            const label = titleEls[0].textContent.trim();
            const value = descEls[0].textContent.trim();
            if (label) result[label] = value;
        } else {
            titleEls.forEach((t, i) => {
                if (descEls[i]) {
                    const label = t.textContent.trim();
                    const value = descEls[i].textContent.trim();
                    if (label) result[label] = value;
                }
            });
        }
    });
    return result;
}
"""


def scrape_product_list(page) -> list:
    """製品リストページから最初の5製品を取得"""
    page.goto(
        "https://www.gigabyte.com/jp/Graphics-Card",
        wait_until="domcontentloaded",
        timeout=30000
    )
    time.sleep(3)  # JS レンダリング待ち
    products = page.evaluate(JS_PRODUCT_LIST)
    return products


def scrape_spec_page(page, product_id: str) -> dict:
    """GIGABYTEスペックページ（/sp）のスペックマップを返す"""
    url = f"https://www.gigabyte.com/jp/Graphics-Card/{product_id}/sp"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)  # Nuxt.js レンダリング待ち
    spec_map = page.evaluate(JS_GIGABYTE_SPEC)
    return spec_map


def build_record(product: dict, spec_map: dict) -> dict:
    """製品情報 + スペックマップ → JSONL レコード"""
    size_str = _find_spec(spec_map, "カード寸法")
    psu_str  = _find_spec(spec_map, "必要電源容量", "推奨電源容量")
    conn_str = _find_spec(spec_map, "電源端子", "電源コネクタ")
    vram_str = (
        _find_spec(spec_map, "メモリ容量") + " " +
        _find_spec(spec_map, "メモリ種類")
    ).strip()
    core_str = _find_spec(spec_map, "GPU 名", "GPU")
    clock_str= _find_spec(spec_map, "コア周波数")
    bus_str  = _find_spec(spec_map, "カード・バス")
    disp_str = _find_spec(spec_map, "映像出力端子")

    rec = {
        "source":          "gigabyte",
        "category":        "gpu",
        "part_no":         product.get("id", "").replace("-", "_"),
        "product_id":      product.get("id"),
        "name":            product.get("name", ""),
        "product_url":     f"https://www.gigabyte.com/jp/Graphics-Card/{product.get('id', '')}",
        "gpu_chip":        core_str,
        "vram":            vram_str,
        "bus_interface":   bus_str,
        "boost_clock":     clock_str,
        "display_output":  disp_str,
        "length_mm":       _parse_length_mm(size_str),
        "tdp_w":           _parse_psu_w(psu_str),
        "slot_width":      None,  # GIGABYTEスペックページに記載なし
        "power_connector": _parse_connector(conn_str) if conn_str else "",
        "size_raw":        size_str,
        "psu_raw":         psu_str,
        "connector_raw":   conn_str,
        "slot_raw":        "",
    }
    return rec


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--window-position=-2000,-2000"]  # 画面外配置 (bot検知回避)
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        # 1. 製品リスト取得
        print("[1/2] GIGABYTE製品リストページから5製品取得中...", file=sys.stderr)
        products = scrape_product_list(page)
        products = products[:5]
        print(f"  → {len(products)} 件取得", file=sys.stderr)
        for p in products:
            print(f"    - {p.get('name', '')} (id={p.get('id', '')})", file=sys.stderr)

        # 2. 各製品のスペックを取得
        records = []
        for i, prod in enumerate(products, 1):
            pid = prod.get("id", "")
            name = prod.get("name", "")

            print(f"[{i}/5] {name[:60]}", file=sys.stderr)
            print(f"       spec_url: https://www.gigabyte.com/jp/Graphics-Card/{pid}/sp", file=sys.stderr)

            if not pid:
                print("  SKIP: id が空", file=sys.stderr)
                continue

            try:
                spec_map = scrape_spec_page(page, pid)
                print(f"  取得キー数: {len(spec_map)}", file=sys.stderr)

                # デバッグ: 主要キー
                for k in ("カード寸法", "必要電源容量", "電源端子", "GPU 名"):
                    if k in spec_map:
                        print(f"    {k}: {spec_map[k][:60]}", file=sys.stderr)

                rec = build_record(prod, spec_map)
                records.append(rec)

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                records.append({
                    "source": "gigabyte", "category": "gpu",
                    "name": name,
                    "product_url": f"https://www.gigabyte.com/jp/Graphics-Card/{pid}",
                    "error": str(e),
                })

            time.sleep(1)

        browser.close()

    # 3. JSONL ファイル保存
    import pathlib
    out_path = pathlib.Path(__file__).parent / "gigabyte_gpu_sample.jsonl"
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
                f"tdp={rec.get('tdp_w')} W | "
                f"slot={rec.get('slot_width')} | "
                f"conn={rec.get('power_connector')}",
                file=sys.stderr
            )
        else:
            print(f"  ERROR: {rec.get('name','')[:50]} → {rec['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
