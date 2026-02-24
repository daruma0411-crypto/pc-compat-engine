#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NZXT ケーススクレイパー（httpx不要・urllib のみ）

製品一覧: Shopify collections/cases/products.json
スペック:  /products/{handle} の SSR HTML から
          tech-specs__cell--label / tech-specs__cell--value で抽出

出力:
  scripts/nzxt_case_sample.jsonl   ← 生データ（デバッグ用）
  workspace/data/cases/products.jsonl ← 診断エンジン用（specs辞書形式）
"""

import io
import json
import pathlib
import re
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── 定数 ─────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

OUT_SCRIPT    = pathlib.Path(__file__).parent / "nzxt_case_sample.jsonl"
OUT_WORKSPACE = pathlib.Path(__file__).parent.parent.parent / "workspace" / "data" / "cases" / "products.jsonl"

# NZXTスペックラベル → 共通キー マッピング
SPEC_KEY_MAP = {
    "GPU Length":               "max_gpu_length_mm",
    "CPU Cooler Height":        "max_cpu_cooler_height_mm",
    "PSU Length":               "max_psu_length_mm",
    "Motherboard Compatibility":"mb_form_factor_support",
    "Power Supply Type":        "psu_form_factor",
}

# ─── ヘルパー ─────────────────────────────────────────────────────────────────

def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def _parse_first_mm(value_str: str):
    """'Up to 331 mm' or 'Up to 185 mm (7.3 in)' → '331'"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*mm", value_str, re.IGNORECASE)
    return str(int(float(m.group(1)))) if m else None


# ─── スクレイピング ────────────────────────────────────────────────────────────

def get_product_list(limit: int = 10) -> list:
    """collections/cases/products.json から製品リストを取得"""
    url = f"https://nzxt.com/collections/cases/products.json?limit={limit}"
    data = json.loads(_get(url))
    products = data.get("products", [])
    # "Refurbished" を除外（念のため）
    return [p for p in products if "efurbish" not in p.get("title", "")][:5]


def scrape_specs(handle: str) -> tuple[dict, str]:
    """
    /products/{handle} の HTML から tech-specs を抽出。
    返り値: (spec_map, sku)
    """
    html = _get(f"https://nzxt.com/products/{handle}").decode("utf-8", errors="replace")

    # スペックテーブル抽出
    rows = re.findall(
        r'tech-specs__cell--label">(.*?)</div>.*?'
        r'tech-specs__cell--value">(.*?)</div>',
        html, re.DOTALL
    )
    spec_map = {}
    for label, value in rows:
        label = re.sub(r"<[^>]+>|\s+", " ", label).strip()
        value = re.sub(r"<[^>]+>|\s+", " ", value).strip()
        if label:
            spec_map[label] = value

    # SKU を .json エンドポイントから取得
    try:
        pdata = json.loads(_get(f"https://nzxt.com/products/{handle}.json"))
        variants = pdata.get("product", {}).get("variants", [])
        sku = variants[0].get("sku", "").strip().lower() if variants else ""
    except Exception:
        sku = ""

    return spec_map, sku


def build_record(product: dict, spec_map: dict, sku: str) -> dict:
    """Shopify 製品エントリ + スペックマップ → workspace 用レコード"""
    specs = {}
    for nzxt_label, common_key in SPEC_KEY_MAP.items():
        raw = spec_map.get(nzxt_label, "")
        if not raw:
            continue
        if common_key in ("max_gpu_length_mm", "max_cpu_cooler_height_mm", "max_psu_length_mm"):
            parsed = _parse_first_mm(raw)
            specs[common_key] = parsed if parsed else raw
        else:
            specs[common_key] = raw

    return {
        "model_name":  product["title"],
        "manufacturer": "nzxt",
        "category":    "case",
        "sku":         sku or product["handle"],
        "source_url":  f"https://nzxt.com/products/{product['handle']}",
        "specs":       specs,
        # デバッグ用: 生スペックマップ
        "_raw_specs":  spec_map,
    }


# ─── メイン ───────────────────────────────────────────────────────────────────

def main():
    print("[1/2] NZXT ケース製品リスト取得中...", file=sys.stderr)
    products = get_product_list()
    print(f"  → {len(products)} 件", file=sys.stderr)

    print("[2/2] 各製品のスペックページをスクレイプ中...", file=sys.stderr)
    records = []

    for i, prod in enumerate(products, 1):
        handle = prod["handle"]
        print(f"\n[{i}/{len(products)}] {prod['title']} (handle={handle})", file=sys.stderr)
        try:
            spec_map, sku = scrape_specs(handle)
            print(f"  スペック取得: {len(spec_map)} items | SKU={sku}", file=sys.stderr)
            for lbl in ("GPU Length", "CPU Cooler Height", "PSU Length",
                        "Motherboard Compatibility", "Power Supply Type"):
                if lbl in spec_map:
                    print(f"    {lbl}: {spec_map[lbl]}", file=sys.stderr)

            rec = build_record(prod, spec_map, sku)
            records.append(rec)

        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            records.append({
                "model_name":   prod["title"],
                "manufacturer": "nzxt",
                "category":     "case",
                "sku":          prod["handle"],
                "specs":        {},
                "error":        str(e),
            })
        time.sleep(1.0)

    # ─── ファイル保存 ───────────────────────────────────────────────────────
    # (a) scripts/nzxt_case_sample.jsonl（_raw_specs 含む）
    OUT_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(json.dumps(rec, ensure_ascii=False))

    # (b) workspace/data/cases/products.jsonl（_raw_specs 除いたクリーン版）
    OUT_WORKSPACE.parent.mkdir(parents=True, exist_ok=True)
    clean_records = []
    for rec in records:
        if "error" not in rec:
            clean = {k: v for k, v in rec.items() if not k.startswith("_")}
            clean_records.append(clean)
    with open(OUT_WORKSPACE, "w", encoding="utf-8") as f:
        for rec in clean_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ─── サマリー ────────────────────────────────────────────────────────────
    print(f"\n[保存完了]", file=sys.stderr)
    print(f"  {OUT_SCRIPT}  ({len(records)} 件)", file=sys.stderr)
    print(f"  {OUT_WORKSPACE}  ({len(clean_records)} 件)", file=sys.stderr)

    print("\n[スペックサマリー]", file=sys.stderr)
    ok, ng = 0, 0
    for rec in records:
        s = rec.get("specs", {})
        if "error" in rec:
            print(f"  ERROR: {rec['model_name'][:50]}", file=sys.stderr)
            ng += 1
        else:
            ok += 1
            print(
                f"  {rec['model_name'][:45]:<45} | "
                f"gpu={s.get('max_gpu_length_mm','?'):>4}mm | "
                f"cpu={s.get('max_cpu_cooler_height_mm','?'):>4}mm | "
                f"psu={s.get('max_psu_length_mm','?'):>4}mm | "
                f"mb={s.get('mb_form_factor_support','?')}",
                file=sys.stderr
            )
    print(f"\n  成功: {ok}  失敗: {ng}", file=sys.stderr)


if __name__ == "__main__":
    main()
