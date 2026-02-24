# マニュアルPDF収集スクレイパー 設計ドキュメント

作成日: 2026-02-24

## 目的

各メーカーの公式サポートページからマニュアル・仕様書PDFを収集し、以下の3用途に活用する：

1. **スペック補完**（即効性）- products.jsonl の null 値をPDFから補完
2. **互換性判定補強** - 注意事項・例外ルールの追加
3. **RAGナレッジベース** - OpenClaw 24時間営業用の回答品質向上

## 対象メーカー

| メーカー | カテゴリ | データファイル |
|--------|---------|--------------|
| ASUS | GPU | workspace/data/asus/products.jsonl |
| MSI | GPU | workspace/data/msi/products.jsonl |
| GIGABYTE | GPU | workspace/data/gigabyte/products.jsonl |
| NZXT | ケース | workspace/data/cases/products.jsonl |
| Noctua | CPUクーラー | workspace/data/noctua_cooler/products.jsonl |
| ASRock | マザーボード | workspace/data/asrock_mb/products.jsonl |
| be quiet! | 電源 | workspace/data/bequiet_psu/products.jsonl |

## ディレクトリ構成

```
pc-compat-engine/scripts/manual_scraper/
  __init__.py
  base.py           <- 共通基底クラス
  asus_manual.py    <- ASUS GPU（Phase 1）
  msi_manual.py
  gigabyte_manual.py
  nzxt_manual.py
  noctua_manual.py
  asrock_manual.py
  bequiet_manual.py
  run_all.py        <- 全メーカー一括実行

pc-compat-engine/workspace/data/{maker}/manuals/
  {model}.txt       <- PDF全文テキスト
```

## products.jsonl 追加フィールド

```json
{
  "manual_url": "https://...manual.pdf",
  "manual_path": "workspace/data/asus/manuals/TUF-RTX3080.txt",
  "manual_scraped_at": "2026-02-24T10:00:00",
  "manual_specs": {
    "tdp_w": 320,
    "pcie_slot": "x16",
    "power_connector": "1x16pin"
  }
}
```

`manual_specs` の値は既存フィールドが null の場合のみ補完に使用する。

## アーキテクチャ

### ManualScraperBase（base.py）

```
ManualScraperBase
  load_products(jsonl_path) -> list[dict]
  get_support_page_url(product) -> str      <- サブクラスが実装
  find_pdf_links(page) -> list[str]          <- Playwright
  download_pdf(url) -> bytes                 <- httpx
  extract_text(pdf_bytes) -> str             <- PyMuPDF
  extract_manual_specs(text) -> dict         <- 正規表現
  save_manual_txt(model, text)
  update_products_jsonl(records)
```

### ASUS サポートURL構築ルール

product_url の末尾パス要素をモデル名として利用：

```
https://www.asus.com/jp/.../TUF-RX9070XT-O16G/
                         ->
https://www.asus.com/jp/support/download-center/?model=TUF-RX9070XT-O16G
```

## 実行フロー（Phase 1: ASUS）

1. asus/products.jsonl 読み込み
2. 各製品のサポートページへ Playwright でアクセス
3. "User Manual" / "マニュアル" を含む PDF リンク抽出
4. httpx で PDF ダウンロード -> manuals/{model}.txt に保存
5. TDP・PCIe・電源コネクタを正規表現で抽出
6. products.jsonl の null フィールドを補完して上書き保存
7. 処理件数・取得成功率をログ出力

## 実装方針

- Playwright: Vercel 等のセキュリティチェックに対応
- PyMuPDF (fitz): テキスト抽出（pdfplumber をフォールバック）
- スタイル: 既存 noctua_cooler_scraper.py に準拠
- エラー処理: 取得できたものだけ保存（失敗はログに記録してスキップ）

## 展開計画

- Phase 1: ASUS GPU -> 動作確認
- Phase 2: エージェントチームで残り6メーカーを並列展開
