# 設計ドキュメント：Amazonアソシエイト審査対策コンテンツページ

日付: 2026-02-24

## 目的
Amazonアソシエイト審査通過に必要な10ページ以上のコンテンツを static/ フォルダに追加する。

## 採用案：A（共通CSS + ワイルドカードルート）

### ファイル構成
```
static/
  css/common.css
  guides/beginner.html / gpu-guide.html / cpu-guide.html / case-guide.html / psu-guide.html
  builds/gaming-50k.html / gaming-100k.html / gaming-200k.html
  blog/index.html
  about.html
```

### app.py 変更
- `@app.route('/<path:filename>')` ワイルドカードルートを追加
- `.html` ファイルを読み込み `__AMAZON_TAG__` を環境変数で置換して返す

### 共通ナビゲーション
- ヘッダー：ロゴ + ドロップダウンナビ（ガイド/構成例）+ CTAボタン（互換性チェックを試す）
- フッター：コピーライト + リンク集
- カラー：`#4f46e5`（インディゴ）、既存 index.html と統一

### Amazonリンク形式
`https://www.amazon.co.jp/s?k=<keyword>&tag=__AMAZON_TAG__`
