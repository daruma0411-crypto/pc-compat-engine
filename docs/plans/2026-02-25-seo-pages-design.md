# 設計書：SEOページ自動生成システム

**作成日**: 2026-02-25
**ステータス**: 承認済み・実装待ち

---

## 目的

「RTX 4070はLancool 216に入る？」系のロングテール検索クエリをGoogleから集客し、
アフィリエイト購入リンクへ誘導して収益化する。

---

## 実行タイミング

**ケーススクレイパー（kakaku_case）完了後** に実行する。

- 現状: GPU 158件 × ケース 30件 = 4,740ページ生成可能
- 目標: GPU 158件 × ケース 100件+ = 15,000ページ+

> SEOの評価には3〜6ヶ月かかるため、数日の遅延より初回のページ数を優先する。

スクレイパーの優先順位: `kakaku_mb`（進行中）→ **`kakaku_case`**（次）→ その他

---

## ファイル構成

```
pc-compat-engine/
├── scripts/
│   └── generate_seo_pages.py     ← 生成スクリプト（新規）
└── static/
    └── compat/
        ├── rtx-4070-vs-lancool-216.html    ← 個別ページ（GPU × ケース）
        ├── rtx-4070-vs-nzxt-h510.html
        ├── ...（全組み合わせ分）
        ├── gpu/
        │   ├── rtx-4070.html               ← GPU別インデックス
        │   └── ...
        └── case/
            ├── lancool-216.html            ← ケース別インデックス
            └── ...
```

既存の Flask ルート `/<path:filename>` が `static/` 以下を自動配信するため、
**app.py の変更は不要**。

---

## URL構造

| ページ種別 | URL例 |
|---|---|
| 個別ページ | `/compat/rtx-4070-vs-lancool-216.html` |
| GPU別インデックス | `/compat/gpu/rtx-4070.html` |
| ケース別インデックス | `/compat/case/lancool-216.html` |

**スラグ生成ルール**: 製品名を小文字に変換し、英数字以外をハイフンに置換
例: `"ASUS GeForce RTX 4070 TUF OC"` → `"asus-geforce-rtx-4070-tuf-oc"`

---

## 個別ページの構成

```html
タイトル: {GPU名}は{ケース名}に入る？互換性チェック結果

[判定バッジ: ✅ 入ります / ⚠️ 注意あり / ❌ 入りません]

## 互換性チェック結果

| 項目       | 値                        |
|------------|---------------------------|
| GPU全長    | 305mm                     |
| ケース最大 | 400mm                     |
| マージン   | 95mm（余裕あり）          |
| 判定       | ✅ OK                     |

[🛒 Amazonで{GPU名}を見る]  [🛍 楽天で探す]

---

## このGPUで他のケースを確認する
→ {GPU名}対応ケース一覧へ

## このケースに入る他のGPU
→ {ケース名}対応GPU一覧へ

---

[バナー] 複数パーツをまとめて互換性診断する → チャットUIへ
```

---

## GPU別・ケース別インデックスページの構成

**GPU別** (`/compat/gpu/rtx-4070.html`):
- タイトル: `RTX 4070が入るケース一覧`
- ✅ OK一覧 / ⚠️ WARNING一覧 / ❌ NG一覧（マージン昇順）
- 各ケースへの個別ページリンク + 購入ボタン

**ケース別** (`/compat/case/lancool-216.html`):
- タイトル: `Lancool 216に入るGPU一覧`
- ✅ OK一覧 / ⚠️ WARNING一覧 / ❌ NG一覧（マージン降順）
- 各GPUへの個別ページリンク + 購入ボタン

---

## 生成スクリプト仕様

**ファイル**: `scripts/generate_seo_pages.py`

**処理フロー**:
```
1. workspace/data/*/products.jsonl を全読み込み
2. category == 'gpu' かつ length_mm あり → GPU一覧
3. category == 'case' かつ max_gpu_length_mm あり → ケース一覧
4. GPU × ケース 全組み合わせでマージン計算
   - margin = case.max_gpu_length_mm - gpu.length_mm
   - margin <= 0  → NG
   - 0 < margin <= 20 → WARNING
   - margin > 20 → OK
5. 個別ページHTML生成 → static/compat/{gpu-slug}-vs-{case-slug}.html
6. GPU別インデックスHTML生成 → static/compat/gpu/{gpu-slug}.html
7. ケース別インデックスHTML生成 → static/compat/case/{case-slug}.html
8. 生成件数をコンソール出力
```

**再実行**: データ追加後にスクリプトを再実行するだけでHTML上書き生成。

---

## デプロイ手順

```bash
python scripts/generate_seo_pages.py
git add static/compat/
git commit -m "feat: SEOページ {N}件生成"
git push origin main
# → Render 自動デプロイ
```

---

## 将来の拡張（今回のスコープ外）

- `sitemap.xml` 自動生成（Googleへのインデックス申請を高速化）
- CPU × MB ソケット互換ページ
- PSU ワット数チェックページ
- 価格データ連携（リアルタイム価格表示）
