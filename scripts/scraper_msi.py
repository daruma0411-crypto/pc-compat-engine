#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSI 公式サイト スクレイパー（本番データ保存版）
==============================================
対象:
  - GPU:  https://jp.msi.com/Graphics-Cards/Products  →  20 件以上
  - MB:   https://jp.msi.com/Motherboards/Products    →  10 件以上

出力:
  - workspace/data/msi/products.jsonl         （GPU）
  - workspace/data/msi_mb/products.jsonl      （MB）

既存 JSONL の id と照合して重複はスキップ。
Playwright headless=False（MSI は bot 検知回避のため）。

使い方:
  python scripts/scraper_msi.py
  python scripts/scraper_msi.py --gpu-limit 30 --mb-limit 15 --headless
"""

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

# Windows CP932 対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("playwright が未インストールです。pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

# ── パス設定 ──────────────────────────────────────────────────────────────────

SCRIPT_DIR  = pathlib.Path(__file__).parent
DATA_DIR    = SCRIPT_DIR.parent / "workspace" / "data"
GPU_OUT     = DATA_DIR / "msi" / "products.jsonl"
MB_OUT      = DATA_DIR / "msi_mb" / "products.jsonl"

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── スキーマ変換ヘルパー ──────────────────────────────────────────────────────

def make_id(maker: str, name: str) -> str:
    return hashlib.md5(f"{maker}:{name}".lower().encode()).hexdigest()[:12]


def load_existing_ids(path: pathlib.Path) -> set:
    ids = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["id"])
                    except Exception:
                        pass
    return ids


def append_record(path: pathlib.Path, rec: dict) -> bool:
    """ファイルに1レコード追記。成功で True を返す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return True


# ── 文字列パーサー ────────────────────────────────────────────────────────────

def _find(spec: dict, *keys: str) -> str:
    for k in keys:
        if k in spec:
            return spec[k].strip()
    return ""


def _parse_length(size_str: str) -> int | None:
    """'Card: 260 x 151 x 61 mm' → 260"""
    m = re.search(r"(?:Card:\s*)?(\d{2,3}(?:\.\d+)?)\s*x\s*\d", size_str, re.I)
    return int(float(m.group(1))) if m else None


def _parse_psu_w(psu_str: str) -> int | None:
    """'OC:800 W / EXtreme:1000W' → 800"""
    m = re.search(r"(\d{2,4})\s*W", psu_str, re.I)
    return int(m.group(1)) if m else None


def _parse_connector(conn_str: str) -> str:
    """'16-pin x 1 (ATX 3.1 PSU recommended)' → '16pinx1'"""
    if not conn_str:
        return ""
    s = conn_str.split("(")[0].strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("-", "").replace("×", "x").replace("ピン", "pin")
    return s


def _parse_slot_width(dim_str: str) -> float | None:
    """'3-slot' や 'Triple-slot' → 3.0"""
    m = re.search(r"(\d(?:\.\d+)?)\s*[-\s]?(?:slot|スロット)", dim_str, re.I)
    if m:
        return float(m.group(1))
    if re.search(r"triple|3", dim_str, re.I):
        return 3.0
    if re.search(r"dual|2", dim_str, re.I):
        return 2.0
    return None


def _parse_m2_count(storage_str: str) -> int | None:
    """'M.2 x 5' or '5 x M.2' or '5本のM.2' → 5"""
    # パターン1: 数字 x M.2 / M.2 x 数字
    m = re.search(r"M\.2\s*[xX×]\s*(\d)", storage_str)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d)\s*[xX×]\s*M\.2", storage_str)
    if m:
        return int(m.group(1))
    # パターン2: M.2スロットの出現数をカウント
    count = len(re.findall(r"M\.2", storage_str, re.I))
    return count if count > 0 else None


def _parse_max_mem(mem_str: str) -> int | None:
    """'最大容量: 192GB' or 'Max. 192GB' → 192"""
    m = re.search(r"(?:Max(?:\.|imum)?\.?\s*(?:capacity)?[: ]*|最大[容量]*[: ]*)(\d+)\s*GB", mem_str, re.I)
    return int(m.group(1)) if m else None


def _parse_mem_slots(mem_str: str) -> int | None:
    """'4 x DDR5 DIMM' → 4"""
    m = re.search(r"(\d)\s*[xX×]\s*(?:DDR\d|SO-DIMM|DIMM)", mem_str, re.I)
    return int(m.group(1)) if m else None


def _parse_mem_type(mem_str: str) -> str:
    if "DDR5" in mem_str.upper():
        return "DDR5"
    if "DDR4" in mem_str.upper():
        return "DDR4"
    return ""


def _parse_socket_mb(cpu_str: str) -> str:
    for token in ["LGA1851", "LGA1700", "LGA1200", "AM5", "AM4"]:
        if token in cpu_str.upper().replace(" ", ""):
            return token
    # LGA 1851 など空白あり
    m = re.search(r"LGA\s*(\d{3,4})", cpu_str, re.I)
    if m:
        return f"LGA{m.group(1)}"
    return ""


def _parse_chipset(chip_str: str) -> str:
    """'AMD X870E' or 'Intel® Z890' → 'X870E' / 'Z890'"""
    m = re.search(r"\b([A-Z][0-9]{3}[A-Z]?)\b", chip_str)
    return m.group(1) if m else chip_str.split()[-1] if chip_str else ""


def _parse_form_factor(ff_str: str) -> str:
    s = ff_str.upper().replace("-", "").replace(" ", "")
    for ff in ["EATX", "MIATX", "MINIATX", "MATX", "MICROATX", "ATX"]:
        if ff in s:
            mapping = {"EATX": "E-ATX", "MIATX": "Mini-ITX", "MINIATX": "Mini-ITX",
                       "MATX": "Micro-ATX", "MICROATX": "Micro-ATX", "ATX": "ATX"}
            return mapping[ff]
    return ff_str


def _parse_sata(storage_str: str) -> int | None:
    m = re.search(r"(\d)\s*[xX×]\s*SATA", storage_str, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"SATA\s*[xX×]\s*(\d)", storage_str, re.I)
    return int(m.group(1)) if m else None


# ── JavaScript ────────────────────────────────────────────────────────────────

JS_SPEC = """
() => {
    // MSI spec page: .pdtb .td > li.specName + テキストノード
    const tds = document.querySelectorAll('.pdtb .td');
    const result = {};
    tds.forEach(td => {
        const labelEl = td.querySelector('li.specName');
        if (!labelEl) return;
        const label = labelEl.textContent.trim().replace(/※\\d+/g, '').trim();
        const valueTexts = [];
        td.childNodes.forEach(node => {
            if (node.nodeType === 3 && node.textContent.trim()) {
                valueTexts.push(node.textContent.trim());
            }
        });
        // ul 内のテキストも収集（MB の場合 li にデータが入ることがある）
        td.querySelectorAll('ul li:not(.specName)').forEach(li => {
            const t = li.textContent.trim();
            if (t) valueTexts.push(t);
        });
        const value = [...new Set(valueTexts)].join(' / ');
        if (label && value) result[label] = value;
    });
    return result;
}
"""

JS_GPU_LIST = """
() => {
    const seen = new Set();
    const products = [];
    document.querySelectorAll('a[href*="/Graphics-Card/"]').forEach(a => {
        if (/\\/Graphics-Card\\/[^/]+$/.test(a.pathname)) {
            const link = a.pathname.replace('/Graphics-Card/', '');
            if (link && !seen.has(link)) {
                seen.add(link);
                const h2 = a.querySelector('h2');
                const name = (h2 ? h2.textContent.trim() : '')
                    || a.getAttribute('aria-label')
                    || a.querySelector('img')?.alt
                    || a.textContent.trim();
                if (name) products.push({ link, name });
            }
        }
    });
    return products;
}
"""

JS_MB_LIST = """
() => {
    const seen = new Set();
    const products = [];
    document.querySelectorAll('a[href*="/Motherboard/"]').forEach(a => {
        if (/\\/Motherboard\\/[^/]+$/.test(a.pathname)) {
            const link = a.pathname.replace('/Motherboard/', '');
            if (link && !seen.has(link)) {
                seen.add(link);
                const h2 = a.querySelector('h2');
                const name = (h2 ? h2.textContent.trim() : '')
                    || a.getAttribute('aria-label')
                    || a.querySelector('img')?.alt
                    || a.textContent.trim();
                if (name) products.push({ link, name });
            }
        }
    });
    return products;
}
"""

# ── GPU レコード構築 ──────────────────────────────────────────────────────────

def build_gpu_record(product: dict, spec: dict) -> dict:
    link = product["link"]
    name = product["name"]

    size_str = _find(spec, "サイズ", "Dimensions")
    psu_str  = _find(spec, "消費電力 (W)", "推奨電源ユニット容量 (W)", "TDP", "Power Consumption")
    conn_str = _find(spec, "補助電源コネクタ", "電源コネクタ", "Power Connector")
    vram_str = _find(spec, "メモリタイプ", "Memory Type", "Memory")
    chip_str = _find(spec, "搭載GPU", "GPU", "Graphics Processing Unit")
    bus_str  = _find(spec, "バスインターフェース", "Bus Interface", "PCI-E")

    # VRAM 容量を vram フィールドに統合
    vram_cap = _find(spec, "メモリ容量", "Memory Size", "VRAM")
    if vram_cap and "GB" in vram_cap and vram_str and "GB" not in vram_str:
        vram_str = f"{vram_cap} {vram_str}"

    return {
        "id":               make_id("msi", name),
        "name":             name,
        "maker":            "msi",
        "category":         "gpu",
        "source_url":       f"https://jp.msi.com/Graphics-Card/{link}",
        "manual_url":       "",
        "manual_path":      "",
        "manual_scraped_at": "",
        "created_at":       NOW,
        "specs": {
            "part_no":         link,
            "gpu_chip":        chip_str,
            "vram":            vram_str,
            "bus_interface":   bus_str,
            "length_mm":       _parse_length(size_str),
            "tdp_w":           _parse_psu_w(psu_str),
            "slot_width":      _parse_slot_width(size_str),
            "power_connector": _parse_connector(conn_str),
            "psu_raw":         psu_str,
        },
    }


# ── MB レコード構築 ───────────────────────────────────────────────────────────

def build_mb_record(product: dict, spec: dict) -> dict:
    link = product["link"]
    name = product["name"]

    cpu_str     = _find(spec, "CPU", "対応CPU", "Supported Processors")
    chip_str    = _find(spec, "チップセット", "Chipset")
    mem_str     = _find(spec, "メモリ", "メモリー", "Memory")
    storage_str = _find(spec, "ストレージ", "Storage", "M.2")
    ff_str      = _find(spec, "フォームファクター", "Form Factor", "サイズ")
    pwr_str     = _find(spec, "電源コネクタ", "Power Connector", "ATX電源")

    socket      = _parse_socket_mb(cpu_str)
    chipset     = _parse_chipset(chip_str)
    form_factor = _parse_form_factor(ff_str) if ff_str else "ATX"
    mem_type    = _parse_mem_type(mem_str)
    mem_slots   = _parse_mem_slots(mem_str)
    max_mem_gb  = _parse_max_mem(mem_str)
    m2_slots    = _parse_m2_count(storage_str)
    sata_ports  = _parse_sata(storage_str)

    return {
        "id":               make_id("msi", name),
        "name":             name,
        "maker":            "msi",
        "category":         "motherboard",
        "source_url":       f"https://jp.msi.com/Motherboard/{link}",
        "manual_url":       "",
        "manual_path":      "",
        "manual_scraped_at": "",
        "created_at":       NOW,
        "specs": {
            "socket":          socket,
            "chipset":         chipset,
            "form_factor":     form_factor,
            "m2_slots":        m2_slots,
            "max_memory_gb":   max_mem_gb,
            "memory_type":     mem_type,
            "memory_slots":    mem_slots,
            "sata_ports":      sata_ports,
            "power_connector": pwr_str,
        },
    }


# ── Playwright 操作 ───────────────────────────────────────────────────────────

def open_browser(pw, headless: bool):
    browser = pw.chromium.launch(
        headless=headless,
        args=["--window-position=-2000,-2000"] if not headless else [],
    )
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="ja-JP",
    )
    page = ctx.new_page()
    return browser, page


def fetch_product_list(page, list_url: str, js: str,
                        wait_sec: float = 6.0) -> list[dict]:
    """製品リストページを開いてJSで製品リストを返す"""
    print(f"  → {list_url}", file=sys.stderr)
    page.goto(list_url, wait_until="domcontentloaded", timeout=40000)
    time.sleep(wait_sec)
    return page.evaluate(js)


def fetch_spec(page, spec_url: str, wait_sec: float = 3.0) -> dict:
    page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
    time.sleep(wait_sec)
    return page.evaluate(JS_SPEC)


# ── GPU スクレイピング ─────────────────────────────────────────────────────────

def scrape_gpu(page, limit: int, out_path: pathlib.Path) -> int:
    print("\n[GPU] 製品リスト取得中...", file=sys.stderr)
    products = fetch_product_list(
        page,
        "https://jp.msi.com/Graphics-Cards/Products",
        JS_GPU_LIST,
        wait_sec=7.0,
    )
    print(f"  → リスト取得: {len(products)} 件", file=sys.stderr)

    existing_ids = load_existing_ids(out_path)
    print(f"  → 既存データ: {len(existing_ids)} 件（重複スキップ）", file=sys.stderr)

    saved = 0
    skipped = 0
    errors = 0

    for i, prod in enumerate(products, 1):
        if saved >= limit:
            break

        rid = make_id("msi", prod["name"])
        if rid in existing_ids:
            print(f"  [{i:2d}] SKIP（重複）: {prod['name'][:50]}", file=sys.stderr)
            skipped += 1
            continue

        spec_url = f"https://jp.msi.com/Graphics-Card/{prod['link']}/Specification"
        print(f"  [{i:2d}] {prod['name'][:55]}", file=sys.stderr)
        print(f"        {spec_url}", file=sys.stderr)

        try:
            spec = fetch_spec(page, spec_url, wait_sec=2.0)
            if not spec:
                print("        ⚠ スペックなし（スキップ）", file=sys.stderr)
                errors += 1
                continue

            rec = build_gpu_record(prod, spec)
            append_record(out_path, rec)
            existing_ids.add(rid)
            saved += 1

            s = rec["specs"]
            print(
                f"        ✅ length={s.get('length_mm')}mm  "
                f"tdp={s.get('tdp_w')}W  "
                f"conn={s.get('power_connector')}  "
                f"vram={s.get('vram')}",
                file=sys.stderr,
            )

        except PWTimeout:
            print(f"        ❌ タイムアウト", file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"        ❌ {e}", file=sys.stderr)
            errors += 1

        time.sleep(1.5)

    print(
        f"\n[GPU] 完了: 保存 {saved} 件  スキップ {skipped} 件  エラー {errors} 件",
        file=sys.stderr,
    )
    return saved


# ── MB スクレイピング ─────────────────────────────────────────────────────────

def scrape_mb(page, limit: int, out_path: pathlib.Path) -> int:
    print("\n[MB] 製品リスト取得中...", file=sys.stderr)
    products = fetch_product_list(
        page,
        "https://jp.msi.com/Motherboards/Products",
        JS_MB_LIST,
        wait_sec=7.0,
    )
    print(f"  → リスト取得: {len(products)} 件", file=sys.stderr)

    existing_ids = load_existing_ids(out_path)
    print(f"  → 既存データ: {len(existing_ids)} 件（重複スキップ）", file=sys.stderr)

    saved = 0
    skipped = 0
    errors = 0

    for i, prod in enumerate(products, 1):
        if saved >= limit:
            break

        rid = make_id("msi", prod["name"])
        if rid in existing_ids:
            print(f"  [{i:2d}] SKIP（重複）: {prod['name'][:50]}", file=sys.stderr)
            skipped += 1
            continue

        spec_url = f"https://jp.msi.com/Motherboard/{prod['link']}/Specification"
        print(f"  [{i:2d}] {prod['name'][:55]}", file=sys.stderr)
        print(f"        {spec_url}", file=sys.stderr)

        try:
            spec = fetch_spec(page, spec_url, wait_sec=2.5)

            # スペックが空の場合はリトライ（1回）
            if not spec:
                time.sleep(2)
                spec = page.evaluate(JS_SPEC)

            if not spec:
                print("        ⚠ スペックなし（スキップ）", file=sys.stderr)
                errors += 1
                continue

            rec = build_mb_record(prod, spec)

            # socket が取れなかった場合はデバッグ出力してスキップ
            if not rec["specs"].get("socket"):
                # スペックキーを出力して診断
                print(f"        ⚠ socket 未取得 - spec keys: {list(spec.keys())[:8]}", file=sys.stderr)
                # それでも保存（他フィールドは有用な可能性）

            append_record(out_path, rec)
            existing_ids.add(rid)
            saved += 1

            s = rec["specs"]
            print(
                f"        ✅ socket={s.get('socket')}  "
                f"chipset={s.get('chipset')}  "
                f"ff={s.get('form_factor')}  "
                f"mem={s.get('memory_type')}  "
                f"m2={s.get('m2_slots')}",
                file=sys.stderr,
            )

        except PWTimeout:
            print(f"        ❌ タイムアウト", file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"        ❌ {e}", file=sys.stderr)
            errors += 1

        time.sleep(1.5)

    print(
        f"\n[MB] 完了: 保存 {saved} 件  スキップ {skipped} 件  エラー {errors} 件",
        file=sys.stderr,
    )
    return saved


# ── 最終サマリー ──────────────────────────────────────────────────────────────

def print_summary(out_path: pathlib.Path, category: str):
    if not out_path.exists():
        return
    records = []
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"\n=== {category} 保存済み: {len(records)} 件 ({out_path}) ===", file=sys.stderr)
    for r in records[-5:]:  # 最新5件だけ表示
        s = r.get("specs", {})
        if category == "GPU":
            print(
                f"  {r['name'][:50]:<50} | "
                f"{s.get('length_mm')}mm | {s.get('tdp_w')}W | {s.get('power_connector')}",
                file=sys.stderr,
            )
        else:
            print(
                f"  {r['name'][:50]:<50} | "
                f"{s.get('socket')} {s.get('chipset')} | {s.get('memory_type')} | {s.get('form_factor')}",
                file=sys.stderr,
            )


# ── エントリポイント ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MSI GPU・MB スクレイパー")
    parser.add_argument("--gpu-limit", type=int, default=25, help="GPU 取得上限 (default: 25)")
    parser.add_argument("--mb-limit",  type=int, default=15, help="MB 取得上限 (default: 15)")
    parser.add_argument("--headless",  action="store_true", help="ヘッドレスモード（bot検知リスクあり）")
    parser.add_argument("--gpu-only",  action="store_true", help="GPU のみ取得")
    parser.add_argument("--mb-only",   action="store_true", help="MB のみ取得")
    args = parser.parse_args()

    print("=" * 60, file=sys.stderr)
    print("MSI スクレイパー 開始", file=sys.stderr)
    print(f"  GPU上限: {args.gpu_limit}  MB上限: {args.mb_limit}", file=sys.stderr)
    print(f"  headless: {args.headless}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    with sync_playwright() as pw:
        browser, page = open_browser(pw, args.headless)
        try:
            if not args.mb_only:
                scrape_gpu(page, args.gpu_limit, GPU_OUT)

            if not args.gpu_only:
                scrape_mb(page, args.mb_limit, MB_OUT)

        finally:
            browser.close()

    # サマリー
    if not args.mb_only:
        print_summary(GPU_OUT, "GPU")
    if not args.gpu_only:
        print_summary(MB_OUT, "MB")

    print("\n完了。", file=sys.stderr)


if __name__ == "__main__":
    main()
