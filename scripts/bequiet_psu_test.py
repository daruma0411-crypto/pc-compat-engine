#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
be quiet! PSUスクレイパー（urllib + requests）

製品一覧: /en/powersupply のメインページから全製品IDを抽出
スペック:  /en/powersupply/{id} のtable-label/table-value から抽出

取得項目:
  wattage_w       - 定格電力 (W)
  efficiency_rating - 80 PLUS 認証
  modular_type    - フルモジュラー / セミモジュラー / 非モジュラー
  depth_mm        - 奥行き（L x W x H の L 値）
  connectors      - コネクター構成サマリー

出力:
  scripts/bequiet_psu_sample.jsonl   ← 生データ（デバッグ用）
  workspace/data/bequiet_psu/products.jsonl ← 診断エンジン用
"""

import html as html_lib
import io
import json
import pathlib
import re
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── 定数 ──────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

LISTING_URL = "https://www.bequiet.com/en/powersupply"
BASE_URL = "https://www.bequiet.com/en/powersupply"
MAX_PRODUCTS = 5

OUT_SCRIPT = pathlib.Path(__file__).parent / "bequiet_psu_sample.jsonl"
OUT_WORKSPACE = (
    pathlib.Path(__file__).parent.parent.parent
    / "workspace" / "data" / "bequiet_psu" / "products.jsonl"
)


# ─── ヘルパー ──────────────────────────────────────────────────────────────────

def _get(url: str) -> str:
    """URLを取得してUTF-8文字列を返す"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return raw.decode("utf-8", errors="replace")


def _clean(text: str) -> str:
    """HTMLタグ除去・ HTML エンティティデコード・空白正規化"""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_depth_mm(dim_str: str) -> str | None:
    """
    '175 x 150 x 86' → '175'
    be quiet! の Dimensions は L(奥行き) x W(幅) x H(高さ)
    """
    nums = re.findall(r"\d+(?:\.\d+)?", dim_str)
    return nums[0] if nums else None


def _build_connectors(spec: dict) -> str:
    """スペック辞書からコネクターサマリー文字列を生成"""
    parts = []
    check = "\u2713"  # ✓

    atx = spec.get("ATX -Motherboard ( 20+4-pin )", "").strip()
    if atx and atx not in ("-", ""):
        parts.append(f"{atx}x 24-pin")

    for label in ("P8  (CPU)", "P8 (CPU)"):
        val = spec.get(label, "").strip()
        if val and val not in ("-", ""):
            parts.append(f"{val}x 8-pin CPU")
            break

    for label in ("P4 +4 (CPU)", "P4+4 (CPU)"):
        val = spec.get(label, "").strip()
        if val and val not in ("-", ""):
            parts.append(f"{val}x 4+4-pin CPU")
            break

    pcie_8 = spec.get("12V-2x6 cables", "").strip()
    if pcie_8 and pcie_8 not in ("-", ""):
        parts.append(f"{pcie_8}x 12V-2x6(PCIe)")

    pcie_6p2 = spec.get("PCI-e 6+2-pin ( GPU )", "").strip()
    if pcie_6p2 and pcie_6p2 not in ("-", ""):
        parts.append(f"{pcie_6p2}x 6+2-pin PCIe")

    pcie_6 = spec.get("PCI-e 6-pin ( GPU )", "").strip()
    if pcie_6 and pcie_6 not in ("-", ""):
        parts.append(f"{pcie_6}x 6-pin PCIe")

    sata = spec.get("SATA", "").strip()
    if sata and sata not in ("-", ""):
        parts.append(f"{sata}x SATA")

    return ", ".join(parts) if parts else ""


def _parse_modular_type(spec: dict) -> str:
    """モジュラータイプを判定"""
    modular = spec.get("Modular cables", "").strip()
    # ✓ または &#10003; がデコードされた値
    if modular in ("\u2713", "✓", "True", "1", "yes", "Yes"):
        return "fully modular"
    # Semi-modular はラベルに直接記載がある場合
    semi = spec.get("Semi-modular cables", "").strip()
    if semi in ("\u2713", "✓", "True", "1"):
        return "semi modular"
    if modular in ("-", "", "0", "No", "no"):
        return "non modular"
    return modular  # そのまま返す


# ─── スクレイピング ────────────────────────────────────────────────────────────

def get_product_ids(limit: int = 5) -> list[tuple[str, str]]:
    """
    メインリスティングページから (product_id, wattage_label) のリストを返す
    例: [('5996', '1200W'), ('5995', '1000W'), ...]
    """
    html = _get(LISTING_URL)
    # ワット数つきの製品リンクを優先（より具体的なモデルの識別に使う）
    matches = re.findall(
        r'href="\./powersupply/(\d+)"[^>]*>\s*(\d+)W',
        html
    )
    seen = []
    seen_ids = set()
    for pid, watt in matches:
        if pid not in seen_ids:
            seen.append((pid, f"{watt}W"))
            seen_ids.add(pid)
    return seen[:limit]


def scrape_product(product_id: str) -> dict:
    """
    /en/powersupply/{product_id} から全スペックを取得
    返り値: 生スペック辞書（label → value）、モデル名も含む
    """
    url = f"{BASE_URL}/{product_id}"
    html = _get(url)

    # スペックテーブル全取得（モデル名より先に実行）
    rows = re.findall(
        r'<td class="table-label">(.*?)</td>\s*<td class="table-value">(.*?)</td>',
        html, re.DOTALL
    )
    spec_map = {}
    for label, value in rows:
        label_clean = _clean(label)
        value_clean = _clean(value)
        if label_clean:
            spec_map[label_clean] = value_clean

    # モデル名: spec_map の "Model" フィールドが最も正確
    # "DARK POWER 14 | 1200 W" → そのまま使用
    model_name = spec_map.get("Model", f"PSU-{product_id}")
    if not model_name or model_name == "-":
        model_name = f"PSU-{product_id}"

    return model_name, spec_map, url


def build_record(product_id: str, model_name: str, spec_map: dict, url: str) -> dict:
    """生スペック → workspace 用レコード"""
    # _clean() が空白を正規化するので単一スペースで参照
    wattage = spec_map.get("Continuous power (W)", "").strip()
    efficiency = spec_map.get("80 PLUS certification", "").strip()
    dim_str = spec_map.get("Dimensions without cable (L x W x H), (mm)", "")
    depth = _parse_depth_mm(dim_str)
    modular = _parse_modular_type(spec_map)
    connectors = _build_connectors(spec_map)

    specs = {}
    if wattage and wattage != "-":
        specs["wattage_w"] = wattage
    if efficiency and efficiency != "-":
        specs["efficiency_rating"] = efficiency
    if modular:
        specs["modular_type"] = modular
    if depth:
        specs["depth_mm"] = depth
    if connectors:
        specs["connectors"] = connectors

    # SKU: Article number からビルド
    article = spec_map.get("Article number", "").strip().lower().replace(" ", "-")

    return {
        "model_name": model_name,
        "manufacturer": "bequiet",
        "category": "psu",
        "sku": article or f"bequiet-psu-{product_id}",
        "source_url": url,
        "specs": specs,
        "_raw_specs": spec_map,
    }


# ─── メイン ───────────────────────────────────────────────────────────────────

def main():
    print("[1/2] be quiet! PSU 製品リスト取得中...", file=sys.stderr)
    product_ids = get_product_ids(MAX_PRODUCTS)
    print(f"  → {len(product_ids)} 件: {product_ids}", file=sys.stderr)

    print("[2/2] 各製品のスペックページをスクレイプ中...", file=sys.stderr)
    records = []

    for i, (pid, watt_label) in enumerate(product_ids, 1):
        print(f"\n[{i}/{len(product_ids)}] ID={pid} ({watt_label})", file=sys.stderr)
        try:
            model_name, spec_map, url = scrape_product(pid)
            print(f"  モデル: {model_name}", file=sys.stderr)
            print(f"  スペック取得: {len(spec_map)} items", file=sys.stderr)

            for lbl in ("Continuous power  (W)", "80 PLUS  certification",
                        "Dimensions without cable (L x W x H), (mm)", "Modular cables",
                        "PCI-e   6+2-pin ( GPU )"):
                if lbl in spec_map:
                    print(f"    {lbl}: {spec_map[lbl]}", file=sys.stderr)

            rec = build_record(pid, model_name, spec_map, url)
            records.append(rec)

        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            records.append({
                "model_name": f"PSU-{pid}",
                "manufacturer": "bequiet",
                "category": "psu",
                "sku": f"bequiet-psu-{pid}",
                "specs": {},
                "error": str(e),
            })
        time.sleep(1.0)

    # ─── ファイル保存 ────────────────────────────────────────────────────────
    # (a) scripts/bequiet_psu_sample.jsonl（_raw_specs 含む）
    OUT_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SCRIPT, "w", encoding="utf-8") as f:
        for rec in records:
            line = json.dumps(rec, ensure_ascii=False)
            f.write(line + "\n")
            print(line)

    # (b) workspace/data/bequiet_psu/products.jsonl（_raw_specs 除いたクリーン版）
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
                f"watt={s.get('wattage_w','?'):>5}W | "
                f"eff={s.get('efficiency_rating','?'):<12} | "
                f"mod={s.get('modular_type','?'):<15} | "
                f"depth={s.get('depth_mm','?')}mm",
                file=sys.stderr
            )
    print(f"\n  成功: {ok}  失敗: {ng}", file=sys.stderr)


if __name__ == "__main__":
    main()
