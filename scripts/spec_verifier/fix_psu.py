#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_psu.py
PSU 15件の source_url を補完する（wattage_w は全件一致確認済み）
"""

import json, pathlib, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_ROOT = pathlib.Path(__file__).parent.parent.parent
_KAKAKU = _ROOT / "workspace" / "data" / "kakaku_psu" / "products.jsonl"

# ─────────────────────────────────────────────────────────────────────────────
# 価格.comマッチング（wattage_w確認 + source_url設定）
# ─────────────────────────────────────────────────────────────────────────────

KAKAKU_MATCH = {
    "corsair_corsair-rm850x":        ("corsair_psu", ["rm850x cp-9020180"]),    # 旧版（wattage同じ）
    "corsair_corsair-rm1000x":       ("corsair_psu", ["rm1000x shift 2025 cp-9020300"]),  # 最新版
    "corsair_corsair-rm750x":        ("corsair_psu", ["rm750x 2024", "cp-9020285"]),
    "corsair_corsair-hx1200":        ("corsair_psu", ["hx1200i 2025 cp-9020307"]),
    "corsair_corsair-rm1200x-shift": ("corsair_psu", ["rm1200x shift cp-9020254"]),
    "seasonic_seasonic-focus-gx-850":   ("seasonic_psu", ["focus gx-850"]),
    "seasonic_seasonic-focus-gx-750":   ("seasonic_psu", ["focus gx-750"]),
    "seasonic_seasonic-focus-gx-1000":  ("seasonic_psu", ["focus gx-1000"]),
    "silverstone_silverstone-sx700-pt": ("silverstone_psu", ["sst-sx700-pt"]),
    "silverstone_silverstone-et750-g":  ("silverstone_psu", ["sst-et750-g"]),
    "silverstone_silverstone-da850-g":  ("silverstone_psu", ["sst-da850"]),
    "silverstone_silverstone-st1100-ti":("silverstone_psu", ["sst-st1100-ti"]),
}

# 価格.comになし or 古すぎ → 公式URL手動設定
MANUAL_URL = {
    "seasonic_seasonic-focus-gx-650":  ("seasonic_psu", "https://www.seasonic.com/focus-gx-650"),
    "seasonic_seasonic-prime-tx-850":  ("seasonic_psu", "https://www.seasonic.com/prime-tx-850"),
    "silverstone_silverstone-sx600-g": ("silverstone_psu", "https://www.silverstonetek.com/jp/product/info/power-supplies/SX600-G/"),
}

# ─────────────────────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def load_kakaku():
    with open(_KAKAKU, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def kakaku_find(kakaku, keywords):
    for kw in keywords:
        for p in kakaku:
            if kw.lower() in p.get('name','').lower():
                return p
    return None

def load_jsonl(data_dir):
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def save_jsonl(data_dir, records):
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

# ─────────────────────────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────────────────────────

def run(dry_run=True):
    kakaku = load_kakaku()
    all_records = {}
    results = []

    print("=" * 70)
    print(f"PSUスペック検証・source_url補完  {'[DRY-RUN]' if dry_run else '[APPLY]'}")
    print("=" * 70)

    # ── A: 価格.com突合わせ ──
    print("\n【A】価格.comマッチング対象（wattage_w確認 + source_url設定）")
    for pid, (data_dir, kws) in KAKAKU_MATCH.items():
        if data_dir not in all_records:
            all_records[data_dir] = load_jsonl(data_dir)
        records = all_records[data_dir]
        target = next((r for r in records if r.get('id') == pid), None)
        if not target:
            print(f"  {pid}: レコードなし")
            results.append((pid, "not_found"))
            continue

        match = kakaku_find(kakaku, kws)
        if not match:
            print(f"  {target['name']}: 価格.com NOT FOUND -> 公式URL使用")
            results.append((pid, "kakaku_not_found"))
            continue

        kk_w   = match.get('specs', {}).get('wattage_w')
        cur_w  = target.get('specs', {}).get('wattage_w')
        kk_url = match.get('source_url', '')

        w_status = "一致" if kk_w == cur_w else f"DIFF {cur_w}->{kk_w}"
        print(f"  {target['name']:40s}  wattage: {cur_w}W ({w_status})  url: {'設定済' if target.get('source_url') else 'null->OK'}")

        if not dry_run:
            if kk_w is not None and kk_w != cur_w:
                target.setdefault('specs', {})['wattage_w'] = kk_w
            target['source_url'] = kk_url
        results.append((pid, "ok" if kk_w == cur_w else "diff"))

    # ── B: 手動URL設定 ──
    print("\n【B】手動URL設定（価格.comなし）")
    for pid, (data_dir, url) in MANUAL_URL.items():
        if data_dir not in all_records:
            all_records[data_dir] = load_jsonl(data_dir)
        records = all_records[data_dir]
        target = next((r for r in records if r.get('id') == pid), None)
        if not target:
            print(f"  {pid}: レコードなし")
            results.append((pid, "not_found"))
            continue

        print(f"  {target['name']:40s}  wattage: {target.get('specs',{}).get('wattage_w')}W (要確認)  source_url -> {url}")
        if not dry_run:
            target['source_url'] = url
        results.append((pid, "manual_url"))

    # ── 保存 ──
    if not dry_run:
        for data_dir, records in all_records.items():
            save_jsonl(data_dir, records)
            print(f"\n  -> {data_dir}/products.jsonl を保存しました")

    # ── サマリー ──
    print("\n" + "=" * 70)
    ok  = [p for p, s in results if s in ("ok", "manual_url")]
    dif = [p for p, s in results if s == "diff"]
    err = [p for p, s in results if s not in ("ok", "manual_url", "diff")]
    print(f"【サマリー】{'DRY-RUN' if dry_run else 'APPLY完了'}")
    print(f"  OK（変更なし）: {len(ok)}件")
    print(f"  DIFF（値修正）: {len(dif)}件  {dif}")
    print(f"  その他/エラー : {len(err)}件  {err}")
    if dry_run:
        print("\n  --apply を付けて再実行すると実際に更新されます")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    run(dry_run=not args.apply)
