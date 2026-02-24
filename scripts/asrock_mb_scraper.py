#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASRock AM5マザーボード スクレイパー
  - httpx + BeautifulSoup（Playwrightなし）
  - specification.asp は静的HTML → サーバーサイドレンダリング
出力: pc-compat-engine/workspace/data/asrock_mb/products.jsonl
"""

import httpx
import json
import pathlib
import re
import sys
import time

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install beautifulsoup4 httpx", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://www.asrock.com"
LIST_URL  = f"{BASE_URL}/mb/"
OUTPUT_PATH = (
    pathlib.Path(__file__).parent.parent
    / "workspace" / "data" / "asrock_mb" / "products.jsonl"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# AM5ソケット判定用チップセット名
AM5_CHIPSETS = {
    "X870E", "X870", "B850E", "B850", "B840",
    "X670E", "X670", "B650E", "B650", "A620",
    "X600", "W790",
}


def get_amd_product_urls() -> list[dict]:
    """製品一覧ページから全AMD製品URLと名前を取得"""
    print("製品リスト取得中 ...", file=sys.stderr)
    r = httpx.get(LIST_URL, headers=HEADERS, timeout=30, follow_redirects=True, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    urls = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"/mb/AMD/")):
        href: str = a["href"]
        full_url = BASE_URL + href if href.startswith("/") else href
        if full_url in seen:
            continue
        seen.add(full_url)
        h6 = a.find("h6")
        name = h6.get_text(strip=True) if h6 else ""
        if name:
            urls.append({"name": name, "url": full_url})

    print(f"  AMD製品URL: {len(urls)}件", file=sys.stderr)
    return urls


def get_spec_html(product_url: str) -> str:
    """specification.asp を取得"""
    spec_url = product_url.replace("index.asp", "specification.asp")
    r = httpx.get(spec_url, headers=HEADERS, timeout=30, follow_redirects=True, verify=False)
    r.raise_for_status()
    return r.text


def parse_spec_dict(html: str) -> dict[str, str]:
    """SpecForm > SpecItem / SpecData のペアを辞書化"""
    soup = BeautifulSoup(html, "html.parser")
    spec_form = soup.find(class_="SpecForm")
    if not spec_form:
        return {}
    items = spec_form.find_all(class_="SpecItem")
    datas = spec_form.find_all(class_="SpecData")
    return {
        item.get_text(strip=True): data.get_text(" ", strip=True)
        for item, data in zip(items, datas)
    }


def extract_fields(spec: dict[str, str], name: str, product_url: str) -> dict | None:
    """スペック辞書から必要フィールドを抽出"""
    cpu_text      = spec.get("CPU", "")
    chipset_text  = spec.get("Chipset", "")
    memory_text   = spec.get("Memory", "")
    storage_text  = spec.get("Storage", "")
    form_text     = spec.get("Form Factor", "")

    # ── Socket ──
    socket = None
    if "AM5" in cpu_text:
        socket = "AM5"
    elif "AM4" in cpu_text:
        socket = "AM4"

    if socket != "AM5":
        return None  # AM5以外は除外

    # ── Chipset ──
    chipset = None
    m = re.search(r"AMD\s+([A-Z][A-Z0-9]+)", chipset_text)
    if m:
        chipset = m.group(1)

    # ── Form Factor ──
    form_factor = None
    for ff in ["Thin mITX", "mITX", "EATX", "mATX", "ATX", "STX"]:
        if ff.lower().replace(" ", "") in form_text.lower().replace(" ", ""):
            form_factor = ff
            break

    # ── M.2スロット数（"M.2 Socket" の出現回数）──
    m2_slots = len(re.findall(r"M\.2 Socket", storage_text, re.IGNORECASE))
    if m2_slots == 0:
        m2_slots = None

    # ── 最大メモリGB ──
    max_memory_gb = None
    mm = re.search(r"Max\.\s*capacity[^:]*:\s*(\d+)\s*GB", memory_text, re.IGNORECASE)
    if mm:
        max_memory_gb = int(mm.group(1))

    # ── メモリタイプ ──
    memory_type = None
    if "DDR5" in memory_text:
        memory_type = "DDR5"
    elif "DDR4" in memory_text:
        memory_type = "DDR4"

    # ── モデル名（URLデコード）──
    model_m = re.search(r"/mb/AMD/([^/]+)/(?:index|specification)\.asp", product_url)
    model = model_m.group(1).replace("%20", " ") if model_m else name

    return {
        "source":         "asrock",
        "category":       "motherboard",
        "name":           name,
        "model":          model,
        "product_url":    product_url.replace("specification.asp", "index.asp"),
        "socket":         socket,
        "chipset":        chipset,
        "form_factor":    form_factor,
        "m2_slots":       m2_slots,
        "max_memory_gb":  max_memory_gb,
        "memory_type":    memory_type,
    }


# ── メイン ─────────────────────────────────────────────────────────
def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_products = get_amd_product_urls()

    # AM5チップセット搭載製品を優先（名前から推測）
    am5_candidates = [
        p for p in all_products
        if any(cs in p["name"] for cs in AM5_CHIPSETS)
           or re.search(r"\b[XBA][0-9]{3}[EM]?\b", p["name"])
    ]
    # フォールバック: 全製品から5件
    targets = (am5_candidates if am5_candidates else all_products)[:5]

    print(f"\n対象製品: {len(targets)}件", file=sys.stderr)

    results = []
    for i, prod in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {prod['name']} ...", file=sys.stderr)
        try:
            html = get_spec_html(prod["url"])
            spec = parse_spec_dict(html)
            rec  = extract_fields(spec, prod["name"], prod["url"])
            if rec:
                results.append(rec)
                print(
                    f"  ✅ socket={rec['socket']} chipset={rec['chipset']} "
                    f"ff={rec['form_factor']} m2={rec['m2_slots']} "
                    f"mem={rec['max_memory_gb']}GB {rec['memory_type']}",
                    file=sys.stderr,
                )
            else:
                print("  ⏭  AM5以外 → スキップ", file=sys.stderr)
        except Exception as e:
            print(f"  ❌ ERROR: {e}", file=sys.stderr)
        time.sleep(1.5)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in results:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n保存: {OUTPUT_PATH}  ({len(results)}件)", file=sys.stderr)

    # ── コンソールサマリー ──
    print(f"\n{'モデル':<35} {'ソケット':^6} {'チップセット':^8} {'FF':^8} {'M.2':^4} {'最大メモリ':^10} {'メモリ種':^6}", file=sys.stderr)
    print("-" * 85, file=sys.stderr)
    for r in results:
        print(
            f"  {r['model']:<33} {str(r['socket']):^6} {str(r['chipset']):^8} "
            f"{str(r['form_factor']):^8} {str(r['m2_slots']):^4} "
            f"{str(r['max_memory_gb'])+'GB':^10} {str(r['memory_type']):^6}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
