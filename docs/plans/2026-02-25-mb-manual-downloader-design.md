# MBマニュアルPDFダウンローダー 設計ドキュメント

作成日: 2026-02-25

## 目的

マザーボードの公式マニュアルPDFをダウンロードしてテキスト化し、
後フェーズのPageIndex投入のための中間ファイルを生成する。

## 背景・差別化根拠

マザーボードはIF（条件分岐）的要素が多く、スペック表だけでは診断できない
制限事項がマニュアルに記載されている：

- M.2スロット使用時のSATAポート無効化
- PCIeスロット帯域がx16→x8/x4に低下する条件
- メモリスロット推奨構成
- CPU TDP上限（VRM設計起因）

これらをPageIndexで検索可能にすることが差別化ポイント。

## パイプライン

```
【今回実装】
PDFダウンロード → PyMuPDFでテキスト抽出 → .txt保存 → products.jsonl更新

【後フェーズ】
.txt → PageIndex投入（全文検索・RAG）
```

.txtを中間成果物として保持することで、PageIndex実装時に再ダウンロード不要。

## 対象・実装順序

| 優先度 | メーカー | JSONL | 件数 | 難易度 |
|---|---|---|---|---|
| 済 | ASRock | `asrock_mb/products.jsonl` | 5件 | ◎ 固定URLパターン（完了） |
| 1 | GIGABYTE | `gigabyte_mb/products.jsonl` | 10件 | ○ サポートページ経由 |
| 2 | ASUS | `asus_mb/products.jsonl` | 14件 | △ ROGドメイン、Playwright必要 |
| 3 | MSI | `msi_mb/products.jsonl` | 22件 | ✕ Akamai bot検知対策必要 |

## 処理フロー（全メーカー共通）

```
products.jsonl 読み込み
    ↓
source_url からサポートページURL生成
    ↓
Playwright でページ取得
    ↓
PDFリンク抽出（"Manual" / "User Guide" / "ユーザーズマニュアル" を含む href）
    ↓
httpx でPDFダウンロード
    ↓
PyMuPDF (fitz) でテキスト抽出
    ↓
{maker}_mb/manuals/{model}.txt に保存
    ↓
products.jsonl の manual_url / manual_path / manual_scraped_at を更新
```

## 各メーカーのURLパターン

### GIGABYTE
- 製品URL: `https://www.gigabyte.com/Motherboard/{model}`
- サポートURL: `https://www.gigabyte.com/Motherboard/{model}/support#support-manual`
- PDFホスト: `download.gigabyte.com`

### ASUS
- 製品URL: `https://rog.asus.com/motherboards/.../` （ROGライン）
- サポートURL: `{product_url}helpdesk_manual/`
- PDFホスト: `dlcdnets.asus.com`

### MSI
- 製品URL: `https://www.msi.com/Motherboard/{model}`
- サポートURL: `https://www.msi.com/Motherboard/{model}/support#manual`
- 対策: トップページCookie取得 → UA偽装

## 出力ファイル

```
workspace/data/gigabyte_mb/manuals/{model}.txt
workspace/data/asus_mb/manuals/{model}.txt
workspace/data/msi_mb/manuals/{model}.txt
```

## スクリプト構成

```
scripts/manual_scraper/
  base.py                  ← 既存（共通基底）
  asrock_manual.py         ← 既存（動作済み）
  gigabyte_mb_manual.py    ← 新規（Phase 1）
  asus_mb_manual.py        ← 新規（Phase 2）
  msi_mb_manual.py         ← 新規（Phase 3）
```

## 実装方針

- 既存 `asrock_manual.py` の構造を基本として横展開
- Playwright headless=False（bot検知回避）
- 失敗はスキップしてログ記録、取得できたものだけ保存
- `--limit N` / `--all` オプションで件数制御

## 成功基準

- GIGABYTE MB 10件中 7件以上のtxt取得（70%以上）
- ASUS MB 14件中 10件以上のtxt取得（70%以上）
- MSI MB 22件中 15件以上のtxt取得（70%以上）
