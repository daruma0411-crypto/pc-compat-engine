# scraper_asus.py 設計書

日付: 2026-02-24
ステータス: 承認済み

---

## 概要

ASUS 公式サイト（www.asus.com/jp / rog.asus.com）から GPU と MB のスペックを
Playwright で自動収集し、既存の products.jsonl 形式で保存するスクレイパー。

## 要件

- GPU: 20件以上、MB: 10件以上を収集
- 既存データ（GPU 15件・MB 10件）をスペック更新 + 新規追加
- asus_mb の一部 hex hash ID → `asus_{name-slug}` 形式に一括修正
- 単一ファイル `scripts/scraper_asus.py`

---

## アーキテクチャ

```
scraper_asus.py
├── _slugify()            IDスラグ生成（SCHEMA.md準拠）
├── _extract_gpu_specs()  スペックテキスト → GPU specs dict
├── _extract_mb_specs()   スペックテキスト → MB specs dict
├── AsusScraper           メインクラス
│   ├── scrape_gpu_urls() 一覧ページ → GPU URL リスト
│   ├── scrape_mb_urls()  一覧ページ → MB URL リスト
│   ├── scrape_spec()     製品スペックページ → record dict
│   ├── run_gpu()         GPU 全件処理
│   ├── run_mb()          MB 全件処理
│   └── run()             GPU + MB 両方実行
└── main()                CLI エントリポイント
```

出力先:
- GPU → `workspace/data/asus/products.jsonl`
- MB  → `workspace/data/asus_mb/products.jsonl`

---

## 一覧ページ

| カテゴリ | サイト | URL |
|---------|--------|-----|
| GPU | www.asus.com | `/jp/motherboards-components/graphics-cards/all-series/` |
| GPU | rog.asus.com | `/jp/graphics-cards/graphics-cards/all-series/` |
| MB  | www.asus.com | `/jp/motherboards-components/motherboards/all-series/` |
| MB  | rog.asus.com | `/jp/motherboards/all-series/` |

ページネーション: "もっと見る" ボタンを検出・クリック（最大 5 回）

---

## スペック抽出対象フィールド

### GPU
- `gpu_chip`, `vram`, `bus_interface`
- `length_mm`, `tdp_w`, `slot_width`, `power_connector`
- `boost_clock`, `display_output`, `size_raw`, `psu_raw`

### MB
- `socket`, `chipset`, `form_factor`
- `m2_slots`, `max_memory_gb`, `memory_type`, `memory_slots`
- `sata_ports`, `power_connector`

---

## マージ・保存ロジック

```
既存 products.jsonl 読み込み
→ source_url をキーに dict 作成
→ スクレイプした各製品:
    if source_url 既存: specs を上書き更新（created_at は保持）
    else: 新規レコードとして追記
→ ID が hex hash のレコードを正規スラグに変換
→ products.jsonl 全件上書き保存
```

---

## CLI

```bash
python scripts/scraper_asus.py            # GPU + MB 両方
python scripts/scraper_asus.py --gpu      # GPU のみ
python scripts/scraper_asus.py --mb       # MB のみ
python scripts/scraper_asus.py --limit 5  # 各カテゴリ上限 5 件
python scripts/scraper_asus.py --all      # ページネーション全件
python scripts/scraper_asus.py --no-headless
```
