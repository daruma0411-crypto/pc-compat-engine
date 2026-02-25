#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_cases.py
ケース15件のスペック値を公式/価格.comで検証・修正する

戦略:
  - 価格.comにマッチする製品 → 価格.comの値 + kakaku URL をsource_urlに設定
  - 価格.comにない製品 → 手動定義した公式値を適用
"""

import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_ROOT = pathlib.Path(__file__).parent.parent.parent
_KAKAKU = _ROOT / "workspace" / "data" / "kakaku_case" / "products.jsonl"

# ─────────────────────────────────────────────────────────────────────────────
# 価格.comマッチング定義（製品ID → 価格.com製品名キーワード）
# ─────────────────────────────────────────────────────────────────────────────

KAKAKU_MATCH = {
    # NZXT (価格.comあり)
    "nzxt_nzxt-h9-flow": ["h9 flow cm-h91f"],
    "nzxt_nzxt-h3-flow": ["h3 flow cc-h31f"],
    # CoolerMaster (価格.comあり)
    "coolermaster_coolermaster-haf-500":       ["haf 500 h500-kgnn"],
    "coolermaster_coolermaster-td500-mesh-v2": ["td500 mesh v2 td500v2"],
    "coolermaster_coolermaster-masterbox-q300l": ["q300l"],
    "coolermaster_coolermaster-silencio-s600": ["silencio s600 mcs-s600"],
    # Fractal Design (価格.comあり)
    "fractal_fractal-design-define-7":    ["define 7 solid fd-c-def7a-01"],
    "fractal_fractal-design-define-7-xl": ["define 7 xl solid fd-c-def7x"],
    "fractal_fractal-design-north":       ["north fd-c-nor1c"],
    "fractal_fractal-design-torrent":     ["torrent tg clear tint fd-c-tor1a"],
    "fractal_fractal-design-meshify-2":   ["meshify 2 solid fd-c-mes2a"],
}

# ─────────────────────────────────────────────────────────────────────────────
# 手動定義（価格.comにない製品 / 公式スペック確認済み）
# ─────────────────────────────────────────────────────────────────────────────
# 出典:
#   NZXT H510:  https://www.bhphotovideo.com/c/product/1502891-REG/ (369mm公式)
#   NZXT H200i: https://www.nzxt.com/products/h200i (328mm → 実は325mm公式)
#   NZXT H2 Flow: https://nzxt.com/product/h2-flow (340mm公式)
#   CM H500: https://www.coolermaster.com/catalog/cases/mid-tower/mastercase-h500/ (413mm公式)

MANUAL_SPECS = {
    "nzxt_nzxt-h510": {
        "source_url": "https://nzxt.com/ja-JP/product/h510",
        "specs": {
            "max_gpu_length_mm": 369,        # 公式: 369mm (w/o HDD cage)
            "max_cpu_cooler_height_mm": 165,  # 公式: 165mm
            "form_factor": "ATX",
            "max_psu_length_mm": 200,
        },
        "data_dir": "cases",
    },
    "nzxt_nzxt-h200i": {
        "source_url": "https://nzxt.com/ja-JP/product/h200i",
        "specs": {
            "max_gpu_length_mm": 325,         # 公式: 325mm
            "max_cpu_cooler_height_mm": 167,  # 公式: 167mm
            "form_factor": "Mini-ITX",
            "max_psu_length_mm": 130,
        },
        "data_dir": "cases",
    },
    "nzxt_nzxt-h2-flow": {
        "source_url": "https://nzxt.com/ja-JP/product/h2-flow",
        "specs": {
            "max_gpu_length_mm": 340,         # 公式: 340mm
            "max_cpu_cooler_height_mm": 167,  # 公式: 167mm
            "form_factor": "Mini-ITX",
            "max_psu_length_mm": 130,
        },
        "data_dir": "cases",
    },
    "coolermaster_coolermaster-mastercase-h500": {
        "source_url": "https://www.coolermaster.com/jp/products/mastercase-h500/",
        "specs": {
            "max_gpu_length_mm": 413,         # 公式: 413mm (without HDD bracket)
            "max_cpu_cooler_height_mm": 167,  # 公式: 167mm
            "form_factor": "ATX",
            "max_psu_length_mm": 200,
        },
        "data_dir": "coolermaster_cases",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def load_kakaku() -> list[dict]:
    with open(_KAKAKU, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def kakaku_find(kakaku: list[dict], keywords: list[str]) -> dict | None:
    for kw in keywords:
        for p in kakaku:
            if kw.lower() in p.get('name', '').lower():
                return p
    return None

def load_jsonl(data_dir: str) -> list[dict]:
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def save_jsonl(data_dir: str, records: list[dict]) -> None:
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    with open(path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

def print_diff(field: str, old, new) -> str:
    if old == new:
        return f"  {field}: {old}  (変更なし)"
    else:
        return f"  {field}: {old} -> {new}  [DIFF]"


# ─────────────────────────────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────────────────────────────

def run(dry_run: bool = True):
    kakaku = load_kakaku()

    # data_dir ごとにレコードをまとめる
    all_records: dict[str, list[dict]] = {}

    # 処理結果
    results = []

    print("=" * 70)
    print(f"ケーススペック検証・修正  {'[DRY-RUN]' if dry_run else '[APPLY]'}")
    print("=" * 70)

    # ── A: 価格.comマッチング ──────────────────────────────────────────────────
    print("\n【A】価格.comマッチング対象")

    for pid, kws in KAKAKU_MATCH.items():
        match = kakaku_find(kakaku, kws)
        if not match:
            print(f"  {pid}: 価格.com NOT FOUND (キーワード: {kws})")
            results.append((pid, "kakaku_not_found"))
            continue

        kk_gpu = match.get('specs', {}).get('max_gpu_length_mm')
        kk_url = match.get('source_url', '')

        # data_dir を判定
        if pid.startswith('nzxt'):
            data_dir = 'cases'
        elif pid.startswith('coolermaster'):
            data_dir = 'coolermaster_cases'
        else:
            data_dir = 'fractal_cases'

        if data_dir not in all_records:
            all_records[data_dir] = load_jsonl(data_dir)

        records = all_records[data_dir]
        target = next((r for r in records if r.get('id') == pid), None)
        if not target:
            print(f"  {pid}: レコードが見つかりません")
            results.append((pid, "not_in_jsonl"))
            continue

        old_gpu = target.get('specs', {}).get('max_gpu_length_mm')
        old_url = target.get('source_url')

        print(f"\n  {target.get('name')}")
        print(print_diff('max_gpu_length_mm', old_gpu, kk_gpu))
        print(f"  source_url: {old_url} -> {kk_url}")

        if not dry_run:
            if kk_gpu is not None:
                target.setdefault('specs', {})['max_gpu_length_mm'] = kk_gpu
            target['source_url'] = kk_url

        results.append((pid, "kakaku_ok" if old_gpu == kk_gpu else "kakaku_diff"))

    # ── B: 手動定義 ────────────────────────────────────────────────────────────
    print("\n【B】手動定義（価格.comなし）")

    for pid, cfg in MANUAL_SPECS.items():
        data_dir = cfg['data_dir']
        if data_dir not in all_records:
            all_records[data_dir] = load_jsonl(data_dir)

        records = all_records[data_dir]
        target = next((r for r in records if r.get('id') == pid), None)
        if not target:
            print(f"  {pid}: レコードが見つかりません")
            results.append((pid, "not_in_jsonl"))
            continue

        print(f"\n  {target.get('name')}")
        has_diff = False
        for field, new_val in cfg['specs'].items():
            old_val = target.get('specs', {}).get(field)
            line = print_diff(field, old_val, new_val)
            print(line)
            if old_val != new_val:
                has_diff = True

        old_url = target.get('source_url')
        new_url = cfg['source_url']
        print(f"  source_url: {old_url} -> {new_url}")

        if not dry_run:
            target['specs'] = cfg['specs']
            target['source_url'] = new_url

        results.append((pid, "manual_diff" if has_diff else "manual_ok"))

    # ── 保存 ─────────────────────────────────────────────────────────────────
    if not dry_run:
        for data_dir, records in all_records.items():
            save_jsonl(data_dir, records)
            print(f"\n  -> {data_dir}/products.jsonl を保存しました")

    # ── サマリー ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"【サマリー】{'DRY-RUN' if dry_run else 'APPLY完了'}")
    for pid, status in results:
        print(f"  {pid:50s}  {status}")

    if dry_run:
        print("\n  --apply を付けて再実行すると実際に更新されます")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    run(dry_run=not args.apply)
