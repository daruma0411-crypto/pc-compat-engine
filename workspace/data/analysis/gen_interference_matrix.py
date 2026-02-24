#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU × ケース 干渉マージン行列生成スクリプト
  margin = case.max_gpu_length_mm - gpu.length_mm
  NG      : margin <= 0
  WARNING : 0 < margin <= 20
  OK      : margin > 20
出力: interference_matrix.csv（ワイドフォーマット）
"""
import csv
import json
import pathlib
import sys
import io

# Windows CP932 対策
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DATA_DIR = pathlib.Path(__file__).parent.parent  # workspace/data/

# ── データ読み込み ──────────────────────────────────────────────
GPU_DIRS   = ["asus", "msi", "gigabyte"]
CASE_DIR   = DATA_DIR / "cases" / "products.jsonl"
OUTPUT_CSV = pathlib.Path(__file__).parent / "interference_matrix.csv"


def load_gpus():
    gpus = []
    for d in GPU_DIRS:
        p = DATA_DIR / d / "products.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("length_mm") is not None:
                    gpus.append({
                        "maker":      rec.get("source", d),
                        "name":       rec.get("name", ""),
                        "length_mm":  int(rec["length_mm"]),
                        "tdp_w":      rec.get("tdp_w"),
                        "connector":  rec.get("power_connector", ""),
                    })
    return gpus


def load_cases():
    cases = []
    if not CASE_DIR.exists():
        return cases
    with open(CASE_DIR, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            specs = rec.get("specs", {})
            max_mm = specs.get("max_gpu_length_mm")
            if max_mm is not None:
                cases.append({
                    "model":           rec.get("model", ""),
                    "max_gpu_mm":      int(max_mm),
                    "form_factor":     specs.get("form_factor", ""),
                })
    return cases


def status(margin: int) -> str:
    if margin <= 0:
        return "NG"
    elif margin <= 20:
        return "WARNING"
    else:
        return "OK"


# ── 行列生成 ────────────────────────────────────────────────────
gpus  = load_gpus()
cases = load_cases()

print(f"GPU: {len(gpus)}件, ケース: {len(cases)}件", file=sys.stderr)

# ── CSV出力 (ワイドフォーマット) ────────────────────────────────
# ヘッダ: maker | GPU名 | length_mm | Case1(mm) | Case1_status | Case2(mm) | Case2_status | ...
with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)

    # ヘッダ行
    header = ["maker", "GPU名", "length_mm"]
    for c in cases:
        label = f"{c['model']} (max {c['max_gpu_mm']}mm)"
        header += [f"マージン_{c['model']}", f"判定_{c['model']}"]
    writer.writerow(header)

    # データ行（GPU length_mm 降順でソート）
    for gpu in sorted(gpus, key=lambda g: g["length_mm"], reverse=True):
        row = [gpu["maker"], gpu["name"], gpu["length_mm"]]
        for c in cases:
            margin = c["max_gpu_mm"] - gpu["length_mm"]
            row += [margin, status(margin)]
        writer.writerow(row)

print(f"保存: {OUTPUT_CSV}", file=sys.stderr)

# ── コンソール確認用サマリー ────────────────────────────────────
print(f"\n{'GPU名':<52} {'length':>6} | " +
      " | ".join(f"{c['model'][:12]:<12}" for c in cases), file=sys.stderr)
print("-" * (60 + 20 * len(cases)), file=sys.stderr)

ng_cnt = warn_cnt = ok_cnt = 0
for gpu in sorted(gpus, key=lambda g: g["length_mm"], reverse=True):
    parts = []
    for c in cases:
        margin = c["max_gpu_mm"] - gpu["length_mm"]
        s = status(margin)
        mark = {"NG": "❌NG", "WARNING": "⚠ WARN", "OK": "✅OK"}[s]
        parts.append(f"{margin:+4d}mm {mark}")
        if s == "NG": ng_cnt += 1
        elif s == "WARNING": warn_cnt += 1
        else: ok_cnt += 1
    print(f"  {gpu['name'][:50]:<50} {gpu['length_mm']:>6}mm | " +
          " | ".join(parts), file=sys.stderr)

total = len(gpus) * len(cases)
print(f"\n合計 {total}件: ❌NG={ng_cnt}  ⚠WARNING={warn_cnt}  ✅OK={ok_cnt}", file=sys.stderr)
print(f"\n【干渉トラップ候補】", file=sys.stderr)
for gpu in sorted(gpus, key=lambda g: g["length_mm"], reverse=True):
    for c in cases:
        margin = c["max_gpu_mm"] - gpu["length_mm"]
        s = status(margin)
        if s in ("NG", "WARNING"):
            print(f"  {s:7s}  {gpu['name'][:45]} ({gpu['length_mm']}mm) × {c['model']} (max {c['max_gpu_mm']}mm)  →  マージン {margin:+d}mm",
                  file=sys.stderr)
