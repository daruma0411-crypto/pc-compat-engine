#!/usr/bin/env python3
"""
スキーマ統一スクリプト
全products.jsonlを統一スキーマに変換する

統一スキーマ:
{
  "id": str,              # maker_model-slug
  "name": str,            # 製品名
  "maker": str,           # メーカー名
  "category": str,        # カテゴリ
  "source_url": str|null, # 製品ページURL
  "manual_url": str|null,
  "manual_path": str|null,
  "manual_scraped_at": str|null,
  "created_at": str,      # ISO8601
  "specs": {}             # カテゴリ固有スペック
}
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent / "workspace" / "data"
CREATED_AT = "2026-02-24T00:00:00+00:00"


def slugify(text: str) -> str:
    """文字列をIDに使えるslugに変換"""
    text = text.lower()
    text = re.sub(r'[™®©]', '', text)
    text = re.sub(r'[\s/\\]+', '-', text)
    text = re.sub(r'[^a-z0-9\-_]', '', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


def make_id(maker: str, name: str) -> str:
    return f"{slugify(maker)}_{slugify(name)}"


# ── カテゴリ別スペックフィールド定義 ──────────────────────────────────────

CPU_SPEC_FIELDS = [
    "model", "socket", "cores", "p_cores", "e_cores", "threads",
    "base_clock_ghz", "boost_clock_ghz", "tdp_w", "max_turbo_power_w",
    "memory_type", "max_memory_speed_mhz", "max_memory_gb",
    "integrated_gpu", "igpu_model", "pcie_version", "l3_cache_mb",
]

MB_SPEC_FIELDS = [
    "model", "socket", "chipset", "form_factor", "m2_slots",
    "max_memory_gb", "memory_type",
]

GPU_SPEC_FIELDS = [
    "part_no", "product_id", "m1_id",
    "gpu_chip", "vram", "bus_interface", "boost_clock",
    "display_output", "length_mm", "tdp_w", "slot_width",
    "power_connector", "size_raw", "psu_raw", "connector_raw", "slot_raw",
    "manual_specs",
]

RAM_SPEC_FIELDS = [
    "model", "memory_type", "capacity_gb", "kit_count", "per_stick_gb",
    "speed_mhz", "cas_latency", "timings", "voltage_v",
    "form_factor", "xmp", "expo", "color", "note",
]

COOLER_SPEC_FIELDS = [
    "model", "height_mm", "socket_support", "fan_size_mm", "tdp_rating_w",
]

CASE_SPEC_FIELDS = [
    "max_gpu_length_mm", "max_cpu_cooler_height_mm",
    "form_factor", "max_psu_length_mm",
]

CATEGORY_SPECS = {
    "cpu": CPU_SPEC_FIELDS,
    "motherboard": MB_SPEC_FIELDS,
    "gpu": GPU_SPEC_FIELDS,
    "ram": RAM_SPEC_FIELDS,
    "cpu_cooler": COOLER_SPEC_FIELDS,
    "case": CASE_SPEC_FIELDS,
}


def convert_record(raw: dict) -> dict:
    """1レコードを統一スキーマに変換"""
    # maker取得（sourceまたはmaker）
    maker = raw.get("source") or raw.get("maker") or "unknown"

    # name取得（nameまたはmodel）
    name = raw.get("name") or raw.get("model") or ""

    # category取得
    category = raw.get("category", "unknown")

    # source_url取得（product_urlを統一）
    source_url = raw.get("product_url") or raw.get("source_url") or None

    # manual系フィールド
    manual_url = raw.get("manual_url") or None
    manual_path = raw.get("manual_path") or None
    manual_scraped_at = raw.get("manual_scraped_at") or None

    # specsを構築
    spec_fields = CATEGORY_SPECS.get(category, [])
    specs = {}

    if category == "case":
        # casesは既にspecs{}を持っている場合
        if "specs" in raw:
            raw_specs = raw["specs"]
        else:
            raw_specs = raw
        for field in spec_fields:
            val = raw_specs.get(field)
            if val is not None:
                # 数値文字列を数値に変換（max_gpu_length_mm等）
                if field.endswith("_mm") and isinstance(val, str):
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        pass
                specs[field] = val
    else:
        for field in spec_fields:
            val = raw.get(field)
            if val is not None:
                specs[field] = val

    unified = {
        "id": make_id(maker, name),
        "name": name,
        "maker": maker,
        "category": category,
        "source_url": source_url,
        "manual_url": manual_url,
        "manual_path": manual_path,
        "manual_scraped_at": manual_scraped_at,
        "created_at": CREATED_AT,
        "specs": specs,
    }
    return unified


def validate_record(record: dict, idx: int, filepath: Path) -> list[str]:
    """レコードをバリデーション。エラーリストを返す"""
    errors = []
    required_fields = ["id", "name", "maker", "category", "created_at", "specs"]
    for f in required_fields:
        if f not in record:
            errors.append(f"[{filepath.parent.name}#{idx}] 必須フィールド欠損: {f}")
        elif record[f] is None or record[f] == "":
            errors.append(f"[{filepath.parent.name}#{idx}] 必須フィールドが空: {f}")
    if "specs" in record and not isinstance(record["specs"], dict):
        errors.append(f"[{filepath.parent.name}#{idx}] specs が dict でない")
    return errors


def process_file(jsonl_path: Path) -> tuple[int, int, list[str]]:
    """
    1ファイルを変換して上書き保存。
    戻り値: (変換件数, エラー件数, エラーメッセージリスト)
    """
    # バックアップ
    backup_path = jsonl_path.with_suffix(".jsonl.bak")
    shutil.copy2(jsonl_path, backup_path)
    print(f"  バックアップ: {backup_path.name}")

    # 読み込み
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    # 変換
    converted = []
    all_errors = []
    for i, raw in enumerate(records):
        unified = convert_record(raw)
        errs = validate_record(unified, i, jsonl_path)
        all_errors.extend(errs)
        converted.append(unified)

    # 上書き保存
    with open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for rec in converted:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return len(converted), len(all_errors), all_errors


def main():
    print("=" * 60)
    print("スキーマ統一スクリプト 開始")
    print("=" * 60)

    # 全products.jsonlを収集
    jsonl_files = sorted(BASE_DIR.rglob("products.jsonl"))
    print(f"\n対象ファイル数: {len(jsonl_files)}")
    for f in jsonl_files:
        print(f"  {f.relative_to(BASE_DIR)}")

    total_records = 0
    total_errors = 0
    all_error_messages = []

    print("\n" + "─" * 60)
    for jsonl_path in jsonl_files:
        dir_name = jsonl_path.parent.name
        print(f"\n[{dir_name}] 処理中...")
        count, err_count, errs = process_file(jsonl_path)
        print(f"  変換: {count}件, エラー: {err_count}件")
        total_records += count
        total_errors += err_count
        all_error_messages.extend(errs)

    print("\n" + "=" * 60)
    print("バリデーション結果")
    print("=" * 60)
    print(f"総変換件数: {total_records}")
    print(f"総エラー件数: {total_errors}")

    if all_error_messages:
        print("\nエラー詳細:")
        for msg in all_error_messages:
            print(f"  ✗ {msg}")
    else:
        print("\n✓ 全件バリデーション PASS")

    # バリデーション結果をファイルに保存
    result_path = BASE_DIR / "migration_result.txt"
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(f"実行日時: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"総変換件数: {total_records}\n")
        f.write(f"総エラー件数: {total_errors}\n")
        if all_error_messages:
            f.write("\nエラー詳細:\n")
            for msg in all_error_messages:
                f.write(f"  {msg}\n")
        else:
            f.write("\n全件バリデーション PASS\n")
    print(f"\n結果保存: {result_path}")


if __name__ == "__main__":
    main()
