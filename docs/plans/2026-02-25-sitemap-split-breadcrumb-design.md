# 設計書: サイトマップ分割 + パンくずナビゲーション実装

**日付**: 2026-02-25
**対象リポジトリ**: pc-compat-engine
**ステータス**: 承認済み

---

## 概要

現在の `sitemap.xml` は172,229 URLを含み、Googleの50,000件/ファイル上限を超過している。
また172,228件のSEOページ（個別・GPUインデックス・ケースインデックス）にパンくずナビゲーションが存在せず、
Googlebotのクロール効率が低い。

本設計では以下を実装する:

1. **サイトマップ分割**: sitemap-1.xml〜sitemap-4.xml + sitemap-index.xml（Google仕様準拠）
2. **パンくずHTML**: 全ページにナビゲーション追加
3. **JSON-LD BreadcrumbList**: Schema.org準拠の構造化データ

---

## セクション1: サイトマップ分割

### 現状
- `static/sitemap.xml`: 172,229 URL（1ファイル）→ Google上限50,000件超過

### 設計

**分割方針**:
| ファイル | 内容 | URL数（概算） |
|---|---|---|
| sitemap-1.xml | 個別ページ #1〜50,000 | 50,000 |
| sitemap-2.xml | 個別ページ #50,001〜100,000 | 50,000 |
| sitemap-3.xml | 個別ページ #100,001〜150,000 | 50,000 |
| sitemap-4.xml | 個別ページ #150,001〜 + インデックスページ（GPU/ケース） | 〜22,229 |
| sitemap-index.xml | 上記4ファイルへの参照 | 4エントリ |

**sitemap-index.xml 形式**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://pc-jisaku.com/sitemap-1.xml</loc>
    <lastmod>2026-02-25</lastmod>
  </sitemap>
  ...
</sitemapindex>
```

**変更ファイル**:
- `scripts/generate_seo_pages.py`: `_generate_sitemap()` を修正
- `static/robots.txt`: `Sitemap:` 行を `sitemap-index.xml` に変更

---

## セクション2: パンくずナビゲーション + JSON-LD

### パンくず構造

| ページ種別 | パンくず |
|---|---|
| 個別ページ（GPU×ケース） | ホーム > GPUインデックス > 個別ページ |
| GPUインデックス | ホーム > GPUインデックス |
| ケースインデックス | ホーム > ケースインデックス |

### HTML パンくず（全ページ）

```html
<nav aria-label="breadcrumb" style="padding:8px 16px;background:#f5f5f5;border-bottom:1px solid #ddd;font-size:14px;">
  <a href="/">ホーム</a>
  &rsaquo;
  <a href="/compat/gpu/{gpu_slug}.html">{gpu_name}</a>  <!-- 個別ページのみ -->
  &rsaquo;
  <span>{current_page_name}</span>
</nav>
```

### JSON-LD BreadcrumbList（全ページ `<head>` 内）

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "ホーム", "item": "https://pc-jisaku.com/" },
    { "@type": "ListItem", "position": 2, "name": "{gpu_name}", "item": "https://.../compat/gpu/{slug}.html" },
    { "@type": "ListItem", "position": 3, "name": "{gpu_name} vs {case_name}" }
  ]
}
```

### 変更ファイル

`scripts/generate_seo_pages.py` 内の3関数を修正:
- `individual_page()`: パンくず3階層（ホーム > GPU > 個別）
- `gpu_index_page()`: パンくず2階層（ホーム > GPU）
- `case_index_page()`: パンくず2階層（ホーム > ケース）

---

## 実装スコープ

| 変更対象 | 変更内容 |
|---|---|
| `scripts/generate_seo_pages.py` | `_generate_sitemap()` 分割ロジック + 3ページ関数にbreadcrumb追加 |
| `static/robots.txt` | `Sitemap:` 行更新 |
| `static/sitemap.xml` | 削除（sitemap-1〜4.xml + sitemap-index.xml に置換） |

## 非スコープ（今回対象外）

- GPU/ケース以外のカテゴリ
- サイトマップへの `<priority>` / `<changefreq>` 追加
- ページネーション（rel=next/prev）
- hreflang（多言語なし）

---

## 期待効果

- Google Search Consoleでサイトマップエラー解消
- Googlebotがパンくずリンク経由でGPU/ケースインデックスページを効率的に発見
- SERP でパンくずリッチスニペット表示（JSON-LD効果）
