#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スペック補完スクリプト

マニュアルテキスト（manuals/*.txt）および size_raw フィールドから
products.jsonl の null フィールドを補完する。

補完ロジック（優先順）:
  1. マニュアルテキストから正規表現で抽出
  2. size_raw の寸法から slot_width を推定（厚み → スロット数換算）
  3. size_raw に "Dual Slot" / "Triple Slot" などのキーワードがあれば直接採用
  4. どれも取得できなければ null のまま

使い方:
  python scripts/spec_completion.py           # ドライラン（変更なし）
  python scripts/spec_completion.py --apply   # 実際に更新
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_ROOT = pathlib.Path(__file__).parent.parent

# ─── 定数 ───────────────────────────────────────────────────────────────────

MAKERS = ["msi", "gigabyte", "nzxt", "noctua", "asrock_mb", "asus"]

# PCIe スロットピッチ（mm）: 標準は 20.32mm
_SLOT_PITCH_MM = 20.32

# 厚み(mm) → slot_width 変換テーブル（上限, slot値）昇順
_THICKNESS_TO_SLOT: list[tuple[float, float]] = [
    (24.0, 1.0),
    (34.0, 1.5),
    (44.0, 2.0),
    (54.0, 2.5),
    (64.0, 3.0),
    (74.0, 3.5),
    (84.0, 4.0),
]

# ─── ユーティリティ ──────────────────────────────────────────────────────────


def _thickness_to_slot(thickness_mm: float) -> float | None:
    """厚み(mm) → スロット数（近似値）"""
    for upper, slot in _THICKNESS_TO_SLOT:
        if thickness_mm <= upper:
            return slot
    # 84mm超: 4.0
    return 4.0


def _extract_slot_from_keyword(text: str) -> float | None:
    """'Dual Slot', 'Triple Slot' などのキーワードから slot_width を返す"""
    t = text.lower()
    if "quad slot" in t or "4 slot" in t:
        return 4.0
    if "triple slot" in t or "3 slot" in t:
        return 3.0
    if "dual slot" in t or "2 slot" in t:
        return 2.0
    if "single slot" in t or "1 slot" in t:
        return 1.0
    return None


def _extract_thickness_from_size_raw(size_raw: str) -> float | None:
    """
    size_raw からカード厚みを抽出する。

    対応フォーマット:
      "260 x 151 x 61 mm"  → 61.0
      "Card: 260 x 151 x 61 mm / Radiator: ..."  → 61.0（Card部のみ）
      "L=330 W=145 H=65 mm"  → 65.0（H=が厚み）
      "H=40 L=267 W=111"     → 40.0
    """
    if not size_raw:
        return None

    # Card: ～ / Radiator: ～ → Card 部分のみ取り出す
    card_match = re.search(r"Card[:\s]+([^/\n]+)", size_raw, re.IGNORECASE)
    target = card_match.group(1) if card_match else size_raw

    # H=xxx 形式
    m = re.search(r"H\s*=\s*([\d.]+)", target, re.IGNORECASE)
    if m:
        return float(m.group(1))

    # "NNN x NNN x NNN" 形式 → 3番目（厚み）
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)",
        target,
    )
    if m:
        return float(m.group(3))

    return None


def _extract_slot_from_manual(text: str) -> float | None:
    """マニュアルテキストから slot_width を正規表現で抽出する"""
    if not text or "Access Denied" in text:
        return None

    # "3.9 slot" / "3.9 Slot" / "2.5 Slot"
    m = re.search(r"([\d.]+)\s*[Ss]lot", text)
    if m:
        val = float(m.group(1))
        if 1.0 <= val <= 5.0:
            return val

    # "Slot: 3.9" / "スロット: 3.0"
    m = re.search(r"[Ss]lot[:\s]+([\d.]+)", text)
    if m:
        val = float(m.group(1))
        if 1.0 <= val <= 5.0:
            return val

    return None


def _extract_tdp_from_manual(text: str) -> int | None:
    """マニュアルテキストから TDP を正規表現で抽出する"""
    if not text or "Access Denied" in text:
        return None

    for pat in [
        r"TDP[:\s]+([\d]+)\s*W",
        r"([\d]+)\s*W\s+TDP",
        r"最大消費電力[:\s]+([\d]+)\s*W",
        r"消費電力[:\s]+([\d]+)\s*W",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 10 <= val <= 1000:
                return val

    return None


# ─── メイン処理 ──────────────────────────────────────────────────────────────


def load_manual_text(manual_path: str | None) -> str:
    """manual_path が存在すればテキストを返す"""
    if not manual_path:
        return ""
    p = _ROOT / manual_path
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return ""


def process_product(prod: dict, manual_text: str) -> dict:
    """
    1製品のスペック補完を行い、補完ログ dict を返す。
    prod は in-place 更新。
    """
    specs = prod.get("specs")
    is_nested = isinstance(specs, dict)
    if not is_nested:
        specs = prod  # flat スキーマ（ASUS）

    filled: dict[str, tuple[str, object]] = {}  # field -> (source, value)

    # ── slot_width ──────────────────────────────────────────────────────
    if specs.get("slot_width") is None:
        # 1) マニュアルテキスト
        val = _extract_slot_from_manual(manual_text)
        if val is not None:
            source = "manual_text"
        else:
            # 2) size_raw キーワード（Dual Slot など）
            size_raw = prod.get("size_raw") or specs.get("size_raw") or ""
            val = _extract_slot_from_keyword(size_raw)
            if val is not None:
                source = "size_raw_keyword"
            else:
                # 3) size_raw 寸法推定
                thickness = _extract_thickness_from_size_raw(size_raw)
                if thickness is not None:
                    val = _thickness_to_slot(thickness)
                    source = f"size_raw_thickness({thickness:.0f}mm)"
                else:
                    val = None
                    source = "not_found"

        if val is not None:
            specs["slot_width"] = val
            filled["slot_width"] = (source, val)

    # ── tdp_w ────────────────────────────────────────────────────────────
    if specs.get("tdp_w") is None:
        val = _extract_tdp_from_manual(manual_text)
        if val is not None:
            specs["tdp_w"] = val
            filled["tdp_w"] = ("manual_text", val)

    # ── power_connector ──────────────────────────────────────────────────
    if specs.get("power_connector") is None:
        if manual_text and "Access Denied" not in manual_text:
            m = re.search(r"電源コネクタ[:\s]+([^\n]{3,60})", manual_text)
            if not m:
                m = re.search(r"Power Connector[:\s]+([^\n]{3,60})", manual_text, re.IGNORECASE)
            if m:
                specs["power_connector"] = m.group(1).strip()
                filled["power_connector"] = ("manual_text", specs["power_connector"])

    return filled


def run(apply: bool = False) -> None:
    total_null_before = 0
    total_null_after = 0
    total_filled = 0

    print(f"\n{'[DRY RUN]' if not apply else '[APPLY]'} スペック補完開始\n")

    for maker in MAKERS:
        jsonl_path = _ROOT / "workspace" / "data" / maker / "products.jsonl"
        if not jsonl_path.exists():
            continue

        products = []
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    products.append(json.loads(line))

        maker_filled = 0
        changed = False

        for prod in products:
            specs = prod.get("specs") if isinstance(prod.get("specs"), dict) else prod

            # 補完前の null 数カウント（対象フィールドのみ）
            target_fields = ["slot_width", "tdp_w", "power_connector", "tdp_rating_w"]
            null_before = sum(1 for f in target_fields if specs.get(f) is None)
            total_null_before += null_before

            if null_before == 0:
                total_null_after += 0
                continue

            manual_text = load_manual_text(prod.get("manual_path"))
            filled = process_product(prod, manual_text)

            null_after = sum(1 for f in target_fields if specs.get(f) is None)
            total_null_after += null_after

            if filled:
                maker_filled += len(filled)
                total_filled += len(filled)
                changed = True
                name = prod.get("name", "")[:40]
                for field, (source, val) in filled.items():
                    print(f"  [{maker}] {name} | {field}={val}  (源: {source})")

        if changed and apply:
            with jsonl_path.open("w", encoding="utf-8") as f:
                for rec in products:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  → {maker}/products.jsonl 更新済み ({maker_filled}件補完)")

    print(f"""
────────────────────────────────────────
補完結果:
  補完前 null フィールド数: {total_null_before}
  補完後 null フィールド数: {total_null_before - total_filled}
  補完成功数              : {total_filled}
  未補完数               : {total_null_before - total_filled}
────────────────────────────────────────
""")
    if not apply:
        print("※ ドライランのため products.jsonl は変更されていません。")
        print("   実際に更新するには: python scripts/spec_completion.py --apply")


def main():
    parser = argparse.ArgumentParser(description="スペック補完スクリプト")
    parser.add_argument("--apply", action="store_true", help="products.jsonl を実際に更新する")
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
