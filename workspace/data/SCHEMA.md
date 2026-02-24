# products.jsonl 統一スキーマ

バージョン: 1.0  
更新日: 2026-02-24  
対象ファイル: workspace/data/*/products.jsonl（10ファイル・50件）

---

## 共通フィールド

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `id` | string | ✓ | `{maker}_{name-slug}` 形式の一意ID |
| `name` | string | ✓ | 製品名（公式表記のまま） |
| `maker` | string | ✓ | メーカー名（小文字） |
| `category` | string | ✓ | カテゴリ（下表参照） |
| `source_url` | string\|null | | 製品ページURL |
| `manual_url` | string\|null | | マニュアルのダウンロードURL |
| `manual_path` | string\|null | | ローカル保存済みマニュアルのパス |
| `manual_scraped_at` | string\|null | | マニュアル収集日時（ISO 8601） |
| `created_at` | string | ✓ | レコード作成日時（ISO 8601） |
| `specs` | object | ✓ | カテゴリ固有スペック（下表参照） |

### カテゴリ一覧

| category 値 | 説明 | データソース |
|---|---|---|
| `cpu` | CPU | amd_cpu, intel_cpu |
| `motherboard` | マザーボード | asrock_mb |
| `gpu` | グラフィックカード | asus, gigabyte, msi |
| `ram` | メモリ | corsair_ram, gskill_ram |
| `cpu_cooler` | CPUクーラー | noctua_cooler |
| `case` | PCケース | cases |

---

## category別 specs フィールド

### cpu

| フィールド | 型 | 説明 |
|---|---|---|
| `model` | string | モデル名（短縮形） |
| `socket` | string | ソケット形状（例: AM5, LGA1851） |
| `cores` | int | 総コア数 |
| `p_cores` | int | Pコア数 |
| `e_cores` | int | Eコア数 |
| `threads` | int | スレッド数 |
| `base_clock_ghz` | float | ベースクロック (GHz) |
| `boost_clock_ghz` | float | ブーストクロック (GHz) |
| `tdp_w` | int | TDP (W) |
| `max_turbo_power_w` | int | 最大ターボパワー (W) |
| `memory_type` | array[string] | 対応メモリ種別（例: ["DDR5"]） |
| `max_memory_speed_mhz` | int | 最大メモリクロック (MHz) |
| `max_memory_gb` | int | 最大メモリ容量 (GB) |
| `integrated_gpu` | bool | 内蔵GPU有無 |
| `igpu_model` | string\|null | 内蔵GPUモデル名 |
| `pcie_version` | string | PCIeバージョン（例: "5.0"） |
| `l3_cache_mb` | int | L3キャッシュ (MB) |

### motherboard

| フィールド | 型 | 説明 |
|---|---|---|
| `model` | string | モデル名 |
| `socket` | string | CPUソケット（例: AM5） |
| `chipset` | string | チップセット（例: X870E） |
| `form_factor` | string | フォームファクター（ATX, EATX, Mini-ITX等） |
| `m2_slots` | int | M.2スロット数 |
| `max_memory_gb` | int | 最大メモリ容量 (GB) |
| `memory_type` | string | 対応メモリ種別（例: "DDR5"） |

### gpu

| フィールド | 型 | 説明 |
|---|---|---|
| `part_no` | string | パーツ番号 |
| `product_id` | string | 製品ID（一部メーカー） |
| `m1_id` | int | ASUS内部ID（ASUS製品のみ） |
| `gpu_chip` | string | GPUチップ名 |
| `vram` | string | VRAMサイズ・種別（例: "16GB GDDR7"） |
| `bus_interface` | string | バスインターフェース（例: "PCI Express 5.0"） |
| `boost_clock` | string | ブーストクロック（テキスト形式） |
| `display_output` | string | 映像出力端子（テキスト形式） |
| `length_mm` | int | カード長 (mm) |
| `tdp_w` | int\|null | TDP / 推奨PSW (W) |
| `slot_width` | float\|null | スロット幅 |
| `power_connector` | string | 電源コネクタ形式 |
| `size_raw` | string | サイズ原文 |
| `psu_raw` | string | PSW要件原文 |
| `connector_raw` | string | コネクタ原文 |
| `slot_raw` | string | スロット原文 |
| `manual_specs` | object | マニュアルから抽出したスペック（収集済み製品のみ） |

### ram

| フィールド | 型 | 説明 |
|---|---|---|
| `model` | string | 型番 |
| `memory_type` | string | メモリ規格（例: "DDR5"） |
| `capacity_gb` | int | キット総容量 (GB) |
| `kit_count` | int | キット枚数 |
| `per_stick_gb` | int | 1枚あたり容量 (GB) |
| `speed_mhz` | int | 動作周波数 (MHz) |
| `cas_latency` | int | CASレイテンシ |
| `timings` | string | タイミング（例: "30-36-36-76"） |
| `voltage_v` | float | 動作電圧 (V) |
| `form_factor` | string | フォームファクター（例: "DIMM"） |
| `xmp` | bool | XMP対応 |
| `expo` | bool | AMD EXPO対応 |
| `color` | string | カラー |
| `note` | string | 補足情報（任意） |

### cpu_cooler

| フィールド | 型 | 説明 |
|---|---|---|
| `model` | string | 型番 |
| `height_mm` | int | クーラー高さ (mm) |
| `socket_support` | array[string] | 対応ソケット一覧 |
| `fan_size_mm` | int | ファン径 (mm) |
| `tdp_rating_w` | int\|null | 対応TDP目安 (W) |

### case

| フィールド | 型 | 説明 |
|---|---|---|
| `max_gpu_length_mm` | int | GPU最大搭載長 (mm) |
| `max_cpu_cooler_height_mm` | int | CPUクーラー最大高さ (mm) |
| `form_factor` | string | 対応マザーボードフォームファクター |
| `max_psu_length_mm` | int | PSU最大長 (mm) |

---

## IDスラグ生成規則

```
id = {maker}_{slugify(name)}

slugify:
  1. 小文字化
  2. ™®© を除去
  3. スペース・/・\ を - に置換
  4. 英数字・ハイフン・アンダースコア以外を除去
  5. 連続ハイフンを1つに圧縮
```

例:
- `"AMD Ryzen 9 9950X"` → `amd_amd-ryzen-9-9950x`
- `"NH-D15 G2"` → `noctua_nh-d15-g2`
- `"AORUS GeForce RTX™ 5090 INFINITY 32G"` → `gigabyte_aorus-geforce-rtx-5090-infinity-32g`

---

## 変換履歴

| 日付 | 変更内容 |
|---|---|
| 2026-02-24 | v1.0 初版。旧3形式（直置きスペック+source、直置きスペック+maker+specs{}）を統一スキーマに移行 |

### 旧フォーマットとの対応

| 旧フィールド | 新フィールド | 備考 |
|---|---|---|
| `source` | `maker` | 統一 |
| `maker` | `maker` | そのまま |
| `product_url` | `source_url` | 名称変更 |
| 直置きスペック | `specs.{field}` | specs内に移動 |
| `specs.{field}` (cases) | `specs.{field}` | そのまま（数値文字列→int変換） |
