#!/usr/bin/env python3
"""
ゲームスペックDB スキーマ移行スクリプト

入力: workspace/data/steam/games.jsonl (現行スキーマ)
出力: workspace/data/steam/games.jsonl (新スキーマ)
バックアップ: workspace/data/steam/games_old.jsonl

処理:
  1. 全エントリ読み込み (エンコーディング破損行はスキップ)
  2. 同一appidの重複排除 (scraped_at最新を優先)
  3. 新スキーマに変換:
     - minimum/recommended を specs オブジェクト配下に移動
     - source フィールド追加
     - 各段階に label/target を自動付与
     - additional_notes → notes にリネーム
     - os/directx フィールドは specs 内から削除
  4. モンハンワイルズ (appid=2246340) はカプコン公式4段階データに置換
"""

import json
import os
import shutil
import sys

# Windows コンソール出力を UTF-8 に
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "workspace", "data", "steam")
INPUT_FILE = os.path.join(DATA_DIR, "games.jsonl")
BACKUP_FILE = os.path.join(DATA_DIR, "games_old.jsonl")
OUTPUT_FILE = os.path.join(DATA_DIR, "games.jsonl")

# モンハンワイルズ カプコン公式4段階データ
MHW_DATA = {
    "appid": 2246340,
    "name": "モンスターハンターワイルズ",
    "source": "steam_official",
    "scraped_at": "2026-02-25T04:47:25",
    "short_description": "荒々しく獰猛な自然が、襲い来る。刻一刻とダイナミックにその姿を変貌させるフィールド。",
    "genres": ["アクション", "アドベンチャー", "RPG"],
    "release_date": "2025年2月27日",
    "metacritic_score": None,
    "screenshot": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2246340/ss_31b5597fecf2d9a2904bc9bbf8011aacb18143db.600x338.jpg",
    "specs": {
        "minimum": {
            "label": "最低",
            "target": "FHD/30fps 最低設定",
            "gpu": ["NVIDIA GeForce GTX 1660", "AMD Radeon RX 5500 XT"],
            "gpu_vram_gb": 6,
            "cpu": ["Intel Core i5-10400", "Intel Core i3-12100", "AMD Ryzen 5 3600"],
            "ram_gb": 16,
            "storage_gb": 75,
            "storage_type": "SSD",
            "notes": "SSD必須、1080p(アップスケール使用、ネイティブ720p)/30fps",
        },
        "recommended": {
            "label": "推奨",
            "target": "FHD中設定/60fps",
            "gpu": ["NVIDIA GeForce RTX 2060 Super", "AMD Radeon RX 6600"],
            "gpu_vram_gb": 8,
            "cpu": ["Intel Core i5-10400", "Intel Core i3-12100", "AMD Ryzen 5 3600"],
            "ram_gb": 16,
            "storage_gb": 75,
            "storage_type": "SSD",
            "notes": "SSD必須、1080p/60fps(フレーム生成使用)",
        },
        "high": {
            "label": "高",
            "target": "1440p高設定/60fps",
            "gpu": [
                "NVIDIA GeForce RTX 4070 Ti",
                "NVIDIA GeForce RTX 4070 Ti SUPER",
                "AMD Radeon RX 7800 XT",
            ],
            "gpu_vram_gb": 12,
            "cpu": [
                "Intel Core i7-11700K",
                "Intel Core i5-12600K",
                "AMD Ryzen 7 5800X",
            ],
            "ram_gb": 16,
            "storage_gb": 75,
            "storage_type": "SSD",
            "notes": "SSD必須、1440p(アップスケール使用)/60fps(フレーム生成使用)",
        },
        "ultra": {
            "label": "ウルトラ",
            "target": "4K/60fps",
            "gpu": [
                "NVIDIA GeForce RTX 4080 SUPER",
                "AMD Radeon RX 7900 XTX",
            ],
            "gpu_vram_gb": 16,
            "cpu": ["Intel Core i7-12700K", "AMD Ryzen 7 5800X"],
            "ram_gb": 16,
            "storage_gb": 75,
            "storage_type": "SSD",
            "notes": "SSD必須、2160p(アップスケール使用)/60fps(フレーム生成使用)",
        },
    },
}


def convert_spec_tier(tier_data, tier_name):
    """旧スキーマの1段階データを新スキーマに変換"""
    if tier_data is None:
        return None

    labels = {
        "minimum": ("最低", "最低設定"),
        "recommended": ("推奨", "推奨設定"),
    }
    label, target = labels.get(tier_name, (tier_name, tier_name))

    new_tier = {
        "label": label,
        "target": target,
    }

    # フィールドをコピー (os, directx は除外)
    skip_fields = {"os", "directx"}
    for key, value in tier_data.items():
        if key in skip_fields:
            continue
        if key == "additional_notes":
            new_tier["notes"] = value
        else:
            new_tier[key] = value

    return new_tier


def convert_entry(entry):
    """旧スキーマのエントリを新スキーマに変換"""
    # source の決定
    source = "steam_official" if entry.get("scraped_at") else "manual"

    new_entry = {
        "appid": entry["appid"],
        "name": entry["name"],
        "source": source,
    }

    # scraped_at があればコピー
    if entry.get("scraped_at"):
        new_entry["scraped_at"] = entry["scraped_at"]

    # 基本情報コピー
    for field in [
        "short_description",
        "genres",
        "release_date",
        "metacritic_score",
        "screenshot",
    ]:
        if field in entry:
            new_entry[field] = entry[field]

    # specs 配下に移動
    specs = {}
    if entry.get("minimum") is not None:
        converted = convert_spec_tier(entry["minimum"], "minimum")
        if converted:
            specs["minimum"] = converted
    if entry.get("recommended") is not None:
        converted = convert_spec_tier(entry["recommended"], "recommended")
        if converted:
            specs["recommended"] = converted

    new_entry["specs"] = specs

    # notes (トップレベルの additional_notes があればコピー)
    if entry.get("additional_notes"):
        new_entry["notes"] = entry["additional_notes"]

    return new_entry


def main():
    print("=" * 60)
    print("ゲームスペックDB スキーマ移行")
    print("=" * 60)

    # 1. 読み込み
    print(f"\n[1] 読み込み: {INPUT_FILE}")
    with open(INPUT_FILE, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8", errors="replace")
    lines = text.strip().split("\n")
    print(f"    行数: {len(lines)}")

    entries = []
    parse_errors = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entries.append(entry)
        except (json.JSONDecodeError, Exception) as e:
            parse_errors += 1
            print(f"    [SKIP] 行 {i+1}: パースエラー ({str(e)[:60]})")

    print(f"    パース成功: {len(entries)} 件")
    print(f"    パースエラー: {parse_errors} 件")

    # 2. 重複排除 (scraped_at 最新を優先)
    print(f"\n[2] 重複排除")
    from collections import Counter

    appid_counts = Counter(e["appid"] for e in entries)
    duplicates = {k: v for k, v in appid_counts.items() if v > 1}

    if duplicates:
        print(f"    重複あり: {len(duplicates)} 組")
        for appid, count in duplicates.items():
            names = [e["name"] for e in entries if e["appid"] == appid]
            print(f"      appid={appid} ({names[0]}): {count} 件")
    else:
        print("    重複なし")

    # 最新の scraped_at を優先して重複排除
    unique = {}
    for entry in entries:
        appid = entry["appid"]
        if appid not in unique:
            unique[appid] = entry
        else:
            existing_ts = unique[appid].get("scraped_at", "")
            new_ts = entry.get("scraped_at", "")
            if new_ts > existing_ts:
                unique[appid] = entry

    dedup_count = len(entries) - len(unique)
    print(f"    排除: {dedup_count} 件 → 残: {len(unique)} 件")

    # 3. 新スキーマに変換
    print(f"\n[3] スキーマ変換")
    converted = {}
    for appid, entry in unique.items():
        if appid == 2246340:
            # モンハンワイルズはカプコン公式データに置換
            converted[appid] = MHW_DATA
            print(f"    MHW (appid=2246340): カプコン公式4段階データに置換")
        else:
            converted[appid] = convert_entry(entry)

    # appid でソート
    sorted_entries = sorted(converted.values(), key=lambda x: x["appid"])

    # MHW 4段階確認
    mhw = converted.get(2246340)
    if mhw:
        spec_tiers = list(mhw.get("specs", {}).keys())
        print(f"    MHW スペック段階: {spec_tiers} ({len(spec_tiers)}段階)")

    # 4. バックアップ & 書き出し
    print(f"\n[4] バックアップ & 書き出し")
    shutil.copy2(INPUT_FILE, BACKUP_FILE)
    print(f"    バックアップ: {BACKUP_FILE}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in sorted_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"    出力: {OUTPUT_FILE}")

    # 5. 統計
    print(f"\n{'=' * 60}")
    print("統計サマリー")
    print(f"{'=' * 60}")
    print(f"  入力行数:       {len(lines)}")
    print(f"  パース成功:     {len(entries)} 件")
    print(f"  パースエラー:   {parse_errors} 件")
    print(f"  重複排除:       {dedup_count} 件")
    print(f"  最終出力:       {len(sorted_entries)} 件")
    print(f"  MHW 4段階:      {'OK' if mhw and len(spec_tiers) == 4 else 'NG'}")

    # 検証: 出力ファイルの整合性チェック
    print(f"\n[検証] 出力ファイルの整合性チェック")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        check_lines = f.readlines()
    check_count = 0
    for line in check_lines:
        line = line.strip()
        if line:
            d = json.loads(line)
            assert "specs" in d, f"specs missing for appid={d['appid']}"
            assert "source" in d, f"source missing for appid={d['appid']}"
            # minimum/recommended がトップレベルにないことを確認
            assert "minimum" not in d, f"minimum at top level for appid={d['appid']}"
            assert "recommended" not in d, f"recommended at top level for appid={d['appid']}"
            check_count += 1
    print(f"    全 {check_count} 件: スキーマ検証 OK")
    print(f"\n完了！")


if __name__ == "__main__":
    main()
