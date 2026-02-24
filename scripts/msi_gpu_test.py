#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSI GPU スペック スクレイピング テスト
最初の5製品を製品リストページ DOM から取得し、
各スペックページ (/Specification) を Playwright でスクレイピングして JSONL を出力する。

DOM構造:
  - 製品リスト: a[href*="/Graphics-Card/"] (pathname が /Graphics-Card/{link} で終わるもの)
  - ラベル: .pdtb .td > ul > li.specName
  - 値:     .pdtb .td 内のテキストノード (ul要素の後)
  - スロット情報: スペックページに記載なし → null

注意: MSI は headless Playwright を bot 検知するため headless=False を使用
      Vue.js レンダリングに 5 秒程度必要
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
    """'Card: 260 x 151 x 61 mm ...' → 260"""
    # MSI形式: "Card: XXX x YYY x ZZZ mm" または "XXX x YYY x ZZZ mm"
    m = re.search(r"(?:Card:\s*)?(\d+(?:\.\d+)?)\s*x\s*\d", size_str, re.IGNORECASE)
    return int(float(m.group(1))) if m else None


def _parse_psu_w(psu_str: str) -> int | None:
    """'OC:800 W / EXtreme:1000W' → 最初に出てくるW数値を返す"""
    m = re.search(r"(\d+)\s*W", psu_str, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_connector(conn_str: str) -> str:
    """電源コネクタ文字列を正規化 ('16-pin x 2' → '16pinx2')"""
    return (conn_str
            .replace(" ", "")
            .replace("×", "x")
            .replace("-", "")
            .replace("ピン", "pin")
            .split("(")[0]  # 括弧以降を除去
            .strip())


# ─── JavaScript for DOM extraction ───────────────────────────────────────────

JS_MSI_SPEC = """
() => {
    // MSI Specificationページ: .pdtb .td > li.specName(ラベル) + テキストノード(値)
    const tds = document.querySelectorAll('.pdtb .td');
    const result = {};
    tds.forEach(td => {
        const labelEl = td.querySelector('li.specName');
        if (!labelEl) return;
        const label = labelEl.textContent.trim().replace(/※\\d+/g, '').trim();
        // テキストノードのみを値として収集 (ul要素は除く)
        const valueTexts = [];
        td.childNodes.forEach(node => {
            if (node.nodeType === 3 && node.textContent.trim()) {
                valueTexts.push(node.textContent.trim());
            }
        });
        const value = valueTexts.join(' / ');
        if (label) result[label] = value;
    });
    return result;
}
"""

JS_PRODUCT_LIST = """
() => {
    // MSI製品リストページから製品リンクを収集
    // URLパターン: /Graphics-Card/{link} (Overview, Gallery等のサブページを除外)
    const seen = new Set();
    const products = [];
    document.querySelectorAll('a[href*="/Graphics-Card/"]').forEach(a => {
        const href = a.href;
        // /Specification, /Gallery などのサブページを除外
        if (/\\/Graphics-Card\\/[^/]+$/.test(a.pathname)) {
            const link = a.pathname.replace('/Graphics-Card/', '');
            if (link && !seen.has(link)) {
                seen.add(link);
                // 製品名: h2 → aria-label → img alt → テキスト
                const h2 = a.querySelector('h2');
                const name = (h2 ? h2.textContent.trim() : '')
                    || a.getAttribute('aria-label')
                    || a.querySelector('img')?.alt
                    || a.textContent.trim();
                if (name) products.push({ link, name, href });
            }
        }
    });
    return products;
}
"""


def scrape_spec_page(page, url: str) -> dict:
    """MSIスペックページに移動してスペックマップを返す"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(1.5)  # JS 描画待ち
    spec_map = page.evaluate(JS_MSI_SPEC)
    return spec_map


def build_record(product: dict, spec_map: dict) -> dict:
    """製品APIエントリ + スペックマップ → JSONL レコード"""
    size_str = _find_spec(spec_map, "サイズ")
    psu_str  = _find_spec(spec_map, "消費電力 (W)", "推奨電源ユニット容量 (W)")
    # 消費電力がない場合は推奨電源容量を使用
    if not _parse_psu_w(psu_str):
        psu_str = _find_spec(spec_map, "推奨電源ユニット容量 (W)", "消費電力 (W)")
    conn_str = _find_spec(spec_map, "補助電源コネクタ", "電源コネクタ")
    vram_str = _find_spec(spec_map, "メモリタイプ", "Memory")
    core_str = _find_spec(spec_map, "搭載GPU", "GPU")
    clock_str= _find_spec(spec_map, "コアクロック（MHz）", "Core Clock")
    bus_str  = _find_spec(spec_map, "バスインターフェース", "Bus Interface", "PCI-E")
    disp_str = _find_spec(spec_map, "映像出力端子")

    name = product.get("name", "")

    rec = {
        "source":          "msi",
        "category":        "gpu",
        "part_no":         product.get("link", ""),
        "product_id":      product.get("link"),
        "name":            name,
        "product_url":     f"https://jp.msi.com/Graphics-Card/{product.get('link', '')}",
        "gpu_chip":        core_str,
        "vram":            vram_str,
        "bus_interface":   bus_str,
        "boost_clock":     clock_str,
        "display_output":  disp_str,
        "length_mm":       _parse_length_mm(size_str),
        "tdp_w":           _parse_psu_w(psu_str),
        "slot_width":      None,  # MSIスペックページに記載なし
        "power_connector": _parse_connector(conn_str) if conn_str else "",
        "size_raw":        size_str,
        "psu_raw":         psu_str,
        "connector_raw":   conn_str,
        "slot_raw":        "",
    }
    return rec


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("[1/2] MSI製品リストから5製品取得中（Playwright経由）...", file=sys.stderr)

    records = []
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

        # 製品リストページを開いてDOMから製品リンクを収集
        page.goto("https://jp.msi.com/Graphics-Cards/Products", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)  # Vue.js レンダリング待ち（5秒必要）

        products = page.evaluate(JS_PRODUCT_LIST)
        products = products[:5]
        print(f"  → {len(products)} 件取得", file=sys.stderr)
        for p in products:
            print(f"    - {p.get('name', '')} (link={p.get('link', '')})", file=sys.stderr)

        for i, prod in enumerate(products, 1):
            link = prod.get("link", "")
            name = prod.get("name", "")
            spec_url = f"https://jp.msi.com/Graphics-Card/{link}/Specification"

            print(f"[{i}/5] {name[:60]}", file=sys.stderr)
            print(f"       spec_url: {spec_url}", file=sys.stderr)

            if not link:
                print("  SKIP: link が空", file=sys.stderr)
                continue

            try:
                spec_map = scrape_spec_page(page, spec_url)
                print(f"  取得キー数: {len(spec_map)}", file=sys.stderr)

                # デバッグ: 主要キー
                for k in ("サイズ", "消費電力 (W)", "補助電源コネクタ", "推奨電源ユニット容量 (W)"):
                    if k in spec_map:
                        print(f"    {k}: {spec_map[k][:60]}", file=sys.stderr)

                rec = build_record(prod, spec_map)
                records.append(rec)

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                records.append({
                    "source": "msi", "category": "gpu",
                    "name": name,
                    "product_url": f"https://jp.msi.com/Graphics-Card/{link}",
                    "error": str(e),
                })

            time.sleep(1)

        browser.close()

    # 3. JSONL ファイル保存
    import pathlib
    out_path = pathlib.Path(__file__).parent / "msi_gpu_sample.jsonl"
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
