#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全カテゴリ 干渉マージン行列生成スクリプト
3マトリクスを一括計算して CSV 出力

  1. GPU × ケース      : length_mm      vs max_gpu_length_mm
  2. CPUクーラー × ケース : height_mm      vs max_cpu_cooler_height_mm
  3. 電源 × ケース     : depth_mm       vs max_psu_length_mm

判定基準（実測値マージン = case_limit - component_size）:
  GPU:       NG if margin < 0 | WARNING if 0 <= margin <= 30 | OK otherwise
  CPUクーラー: NG if margin < 0 | WARNING if 0 <= margin <= 20 | OK otherwise
  PSU:       NG if margin < 0 | WARNING if 0 <= margin <= 20 | OK otherwise

出力:
  full_interference_matrix.csv   全125件（ロング形式）
  interference_traps.csv         NG/WARNING のみ抽出
"""

import csv
import io
import json
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── パス定義 ────────────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).parent.parent  # pc-compat-engine/workspace/data/
REPO_ROOT = ROOT.parent.parent.parent         # C:\Users\iwashita.AKGNET\
PSU_PATH = REPO_ROOT / "workspace" / "data" / "bequiet_psu" / "products.jsonl"

OUT_DIR = pathlib.Path(__file__).parent
OUT_FULL   = OUT_DIR / "full_interference_matrix.csv"
OUT_TRAPS  = OUT_DIR / "interference_traps.csv"

# ─── 判定閾値 ────────────────────────────────────────────────────────────────

WARN_THRESH = {
    "gpu":        30,   # GPU は大型のため 30mm まで WARNING
    "cpu_cooler": 20,
    "psu":        20,
}


def verdict(margin: int, category: str) -> str:
    if margin < 0:
        return "NG"
    elif margin <= WARN_THRESH.get(category, 20):
        return "WARNING"
    return "OK"


# ─── データ読み込み ──────────────────────────────────────────────────────────

def load_gpus() -> list[dict]:
    gpus = []
    for sub in ["asus", "msi", "gigabyte"]:
        path = ROOT / sub / "products.jsonl"
        if not path.exists():
            print(f"  [SKIP] {path}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("length_mm") is None:
                    continue
                gpus.append({
                    "category": "gpu",
                    "maker":    r.get("source", sub),
                    "name":     r.get("name", ""),
                    "value_mm": int(r["length_mm"]),
                    "extra":    f"TDP:{r.get('tdp_w','?')}W conn:{r.get('power_connector','')}",
                })
    return gpus


def load_coolers() -> list[dict]:
    path = ROOT / "noctua_cooler" / "products.jsonl"
    coolers = []
    if not path.exists():
        print(f"  [SKIP] {path}", file=sys.stderr)
        return coolers
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("height_mm") is None:
                continue
            coolers.append({
                "category": "cpu_cooler",
                "maker":    r.get("source", "noctua"),
                "name":     r.get("name", ""),
                "value_mm": int(r["height_mm"]),
                "extra":    f"fan:{r.get('fan_size_mm','?')}mm",
            })
    return coolers


def load_psus() -> list[dict]:
    psus = []
    if not PSU_PATH.exists():
        print(f"  [SKIP] {PSU_PATH}", file=sys.stderr)
        return psus
    with open(PSU_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            specs = r.get("specs", {})
            depth = specs.get("depth_mm")
            if depth is None:
                continue
            psus.append({
                "category": "psu",
                "maker":    r.get("manufacturer", "bequiet"),
                "name":     r.get("model_name", ""),
                "value_mm": int(depth),
                "extra":    f"{specs.get('wattage_w','?')}W {specs.get('efficiency_rating','')}",
            })
    return psus


def load_cases() -> list[dict]:
    path = ROOT / "cases" / "products.jsonl"
    cases = []
    if not path.exists():
        print(f"  [SKIP] {path}", file=sys.stderr)
        return cases
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            specs = r.get("specs", {})
            cases.append({
                "model":         r.get("model", ""),
                "maker":         r.get("maker", "nzxt"),
                "form_factor":   specs.get("form_factor", ""),
                "max_gpu_mm":    int(specs["max_gpu_length_mm"])       if specs.get("max_gpu_length_mm")       else None,
                "max_cooler_mm": int(specs["max_cpu_cooler_height_mm"]) if specs.get("max_cpu_cooler_height_mm") else None,
                "max_psu_mm":    int(specs["max_psu_length_mm"])       if specs.get("max_psu_length_mm")       else None,
            })
    return cases


# ─── メイン ──────────────────────────────────────────────────────────────────

def main():
    print("[1/4] データ読み込み中...", file=sys.stderr)
    gpus    = load_gpus()
    coolers = load_coolers()
    psus    = load_psus()
    cases   = load_cases()

    print(f"  GPU: {len(gpus)}件", file=sys.stderr)
    print(f"  CPUクーラー: {len(coolers)}件", file=sys.stderr)
    print(f"  PSU: {len(psus)}件", file=sys.stderr)
    print(f"  ケース: {len(cases)}件", file=sys.stderr)

    # ── 全ペアの計算 ────────────────────────────────────────────────
    print("\n[2/4] 干渉マージン計算中...", file=sys.stderr)

    rows = []   # 全行

    CASE_KEY = {
        "gpu":        "max_gpu_mm",
        "cpu_cooler": "max_cooler_mm",
        "psu":        "max_psu_mm",
    }
    MATRIX_LABEL = {
        "gpu":        "GPU×ケース",
        "cpu_cooler": "CPUクーラー×ケース",
        "psu":        "電源×ケース",
    }

    for components, limit_key in [
        (gpus,    "max_gpu_mm"),
        (coolers, "max_cooler_mm"),
        (psus,    "max_psu_mm"),
    ]:
        for comp in sorted(components, key=lambda x: x["value_mm"], reverse=True):
            for case in cases:
                limit = case.get(limit_key)
                if limit is None:
                    continue
                margin = limit - comp["value_mm"]
                v = verdict(margin, comp["category"])
                rows.append({
                    "matrix_type":      MATRIX_LABEL[comp["category"]],
                    "component_category": comp["category"],
                    "component_maker":  comp["maker"],
                    "component_name":   comp["name"],
                    "component_mm":     comp["value_mm"],
                    "component_extra":  comp.get("extra", ""),
                    "case_model":       case["model"],
                    "case_maker":       case["maker"],
                    "case_form_factor": case["form_factor"],
                    "case_limit_mm":    limit,
                    "margin_mm":        margin,
                    "verdict":          v,
                })

    total = len(rows)
    ng    = sum(1 for r in rows if r["verdict"] == "NG")
    warn  = sum(1 for r in rows if r["verdict"] == "WARNING")
    ok    = total - ng - warn

    print(f"  合計 {total} 件: NG={ng}  WARNING={warn}  OK={ok}", file=sys.stderr)

    # ── full_interference_matrix.csv 出力 ─────────────────────────
    print("\n[3/4] CSV出力中...", file=sys.stderr)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    FIELDNAMES = [
        "matrix_type", "component_category", "component_maker",
        "component_name", "component_mm", "component_extra",
        "case_model", "case_maker", "case_form_factor",
        "case_limit_mm", "margin_mm", "verdict",
    ]

    with open(OUT_FULL, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {OUT_FULL}  ({total} 行)", file=sys.stderr)

    # ── interference_traps.csv 出力（NG/WARNING のみ） ─────────────
    trap_rows = [r for r in rows if r["verdict"] in ("NG", "WARNING")]
    trap_rows.sort(key=lambda r: (r["verdict"], r["matrix_type"], r["margin_mm"]))

    with open(OUT_TRAPS, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(trap_rows)
    print(f"  → {OUT_TRAPS}  ({len(trap_rows)} 行)", file=sys.stderr)

    # ── コンソールサマリー ──────────────────────────────────────────
    print("\n[4/4] 干渉トラップ一覧 (NG/WARNING)", file=sys.stderr)
    print("=" * 110, file=sys.stderr)

    for mtype in ["GPU×ケース", "CPUクーラー×ケース", "電源×ケース"]:
        traps = [r for r in trap_rows if r["matrix_type"] == mtype]
        if not traps:
            print(f"\n【{mtype}】問題なし", file=sys.stderr)
            continue
        print(f"\n【{mtype}】", file=sys.stderr)
        print(f"  {'判定':<8} {'コンポーネント':<48} {'mm':>5} {'ケース':<20} {'制限':>5}  マージン", file=sys.stderr)
        print(f"  {'-'*8} {'-'*48} {'-'*5} {'-'*20} {'-'*5}  {'-'*8}", file=sys.stderr)
        for r in sorted(traps, key=lambda x: x["margin_mm"]):
            mark = "❌NG     " if r["verdict"] == "NG" else "⚠ WARNING"
            print(f"  {mark} {r['component_name'][:47]:<48} {r['component_mm']:>5} "
                  f"{r['case_model'][:19]:<20} {r['case_limit_mm']:>5}mm  {r['margin_mm']:+d}mm",
                  file=sys.stderr)

    print("\n" + "=" * 110, file=sys.stderr)
    print(f"\n合計 {total} 件: ❌NG={ng}  ⚠WARNING={warn}  ✅OK={ok}", file=sys.stderr)
    print(f"\n保存完了:", file=sys.stderr)
    print(f"  {OUT_FULL}", file=sys.stderr)
    print(f"  {OUT_TRAPS}", file=sys.stderr)


if __name__ == "__main__":
    main()
