# 設計書: 価格.comスクレイパー（全カテゴリデータ拡充）

作成日: 2026-02-25

---

## 目的

PC互換性チェックエンジンのデータベースを拡充する。
現状の各カテゴリデータが市場実態の10〜50%程度しか登録されていないため、
価格.comのスペック表をスクレイプして全件登録する。

## 対象カテゴリと優先順

| 優先 | カテゴリ | 現在 | 目標 | 保存先 |
|---|---|---|---|---|
| 1 | マザーボード | 51件 | ~1,000件 | workspace/data/kakaku_mb/ |
| 2 | CPU | 50件 | ~800件 | workspace/data/kakaku_cpu/ |
| 3 | ケース | 30件 | ~2,000件 | workspace/data/kakaku_case/ |
| 4 | PSU | 30件 | ~1,500件 | workspace/data/kakaku_psu/ |
| 5 | CPUクーラー | 20件 | ~1,200件 | workspace/data/kakaku_cooler/ |

## アーキテクチャ

### 方針: カテゴリ別スクレイパー×5本（案1）

```
scripts/
  kakaku_scraper_mb.py
  kakaku_scraper_cpu.py
  kakaku_scraper_case.py
  kakaku_scraper_psu.py
  kakaku_scraper_cooler.py
```

各スクリプトは独立して実行・中断・再開可能。

### 処理フロー

```
1. 一覧ページ走査
   https://kakaku.com/pc/{category}/itemlist.aspx?pdf_pg=N
   → ページネーション全走査（1ページ約20件）
   → 製品コード K0xxxxxxxxxx を収集

2. 詳細スペックページ取得
   https://kakaku.com/item/K0xxxxxxxxxx/spec/
   → <th>〜</th><td>〜</td> パターンでスペック表をパース

3. JSONL形式で保存
   既存IDはスキップ（重複防止）
   途中失敗時は再実行で続きから再開

4. レート制限: 0.5〜1秒間隔 + リトライ3回（指数バックオフ）
```

### 価格.com URL一覧

| カテゴリ | 一覧URL |
|---|---|
| MB | https://kakaku.com/pc/motherboard/itemlist.aspx |
| CPU | https://kakaku.com/pc/cpu/itemlist.aspx |
| ケース | https://kakaku.com/pc/pccase/itemlist.aspx |
| PSU | https://kakaku.com/pc/powersupply/itemlist.aspx |
| CPUクーラー | https://kakaku.com/pc/cpucooler/itemlist.aspx |

## データスキーマ

### マザーボード

```json
{
  "id": "kakaku_{K0xxxxxxxxxx}",
  "name": "製品名",
  "maker": "asus",
  "category": "motherboard",
  "source_url": "https://kakaku.com/item/K0xxxxxxxxxx/spec/",
  "created_at": "2026-02-25T00:00:00+00:00",
  "specs": {
    "chipset": "AMD B650",
    "socket": "AM5",
    "form_factor": "ATX",
    "memory_type": "DDR5",
    "memory_slots": 4,
    "max_memory_gb": 128,
    "m2_slots": 3,
    "sata_ports": 4,
    "pcie_x16_slots": 1,
    "size_mm": "305x244"
  }
}
```

### CPU

```json
{
  "specs": {
    "socket": "AM5",
    "cores": 16,
    "threads": 32,
    "base_clock_ghz": 4.3,
    "boost_clock_ghz": 5.7,
    "tdp_w": 170,
    "memory_type": "DDR5",
    "integrated_gpu": false
  }
}
```

### ケース

```json
{
  "specs": {
    "form_factor": "ATX",
    "supported_mb": ["E-ATX", "ATX", "Micro-ATX", "Mini-ITX"],
    "max_gpu_length_mm": 400,
    "max_cooler_height_mm": 170,
    "drive_bays_35": 2,
    "drive_bays_25": 3,
    "size_mm": "450x210x480"
  }
}
```

### PSU

```json
{
  "specs": {
    "wattage_w": 750,
    "efficiency": "80PLUS Gold",
    "modular": "フルモジュラー",
    "form_factor": "ATX",
    "pcie_connectors": "16-pin x1, 8-pin x2"
  }
}
```

### CPUクーラー

```json
{
  "specs": {
    "type": "空冷",
    "socket_support": ["AM5", "AM4", "LGA1700", "LGA1851"],
    "height_mm": 158,
    "tdp_rating_w": 250,
    "fan_size_mm": 140,
    "noise_db": 24.6
  }
}
```

## 実装上の注意

- User-Agent: Chrome/120 を使用
- リクエスト間隔: random.uniform(0.5, 1.0) 秒
- タイムアウト: 15秒
- リトライ: 最大3回（1秒→2秒→4秒 指数バックオフ）
- 文字コード: cp932でデコード
- 製品名からmaker（メーカー）を正規化（ASUS/MSI/GIGABYTE等→小文字スラグ）
- スペック値の正規化（「SocketAM5」→「AM5」、「MicroATX」→「Micro-ATX」等）

## 実行コマンド（予定）

```bash
python scripts/kakaku_scraper_mb.py      # 優先1: MB ~1時間
python scripts/kakaku_scraper_cpu.py     # 優先2: CPU ~40分
python scripts/kakaku_scraper_case.py    # 優先3: ケース ~2時間
python scripts/kakaku_scraper_psu.py     # 優先4: PSU ~1.5時間
python scripts/kakaku_scraper_cooler.py  # 優先5: クーラー ~1時間
```

## 成功基準

- 各カテゴリ: 既存データの3倍以上を登録
- スペック取得率: 80%以上（主要フィールドが埋まっている）
- app.py の `/api/diagnose` で新規登録製品が正しくマッチすること
