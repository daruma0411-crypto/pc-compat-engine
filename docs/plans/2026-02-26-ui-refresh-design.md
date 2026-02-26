# PC互換チェッカー UI刷新 設計書

作成: 2026-02-26

## 概要

`index.html` を CSS / JS / HTML に分割し、チームで並列実装する。
修正1〜5 + モバイル対応を実施。

## ファイル分割設計

### 分割前
```
static/index.html  （CSS + HTML + JS が混在、~1220行）
```

### 分割後
```
static/index.html     HTML構造 + アフィリエイト設定インライン小スクリプト
static/style.css      全CSS（~580行 → 修正追加後 ~700行想定）
static/app.js         全JS（~600行 → 修正追加後 ~700行想定）
```

### アフィリエイトタグの扱い
`app.py` が `index.html` を読み込んで `__AMAZON_TAG__` 等を置換して返す。
JS分離後も `index.html` 内の小スクリプトに変数定義を残すことで、
`app.py` の修正不要。

```html
<!-- index.html 内に残す小スクリプト -->
<script>
  const AMAZON_TAG   = '__AMAZON_TAG__';
  const RAKUTEN_A_ID = '__RAKUTEN_A_ID__';
  const RAKUTEN_L_ID = '__RAKUTEN_L_ID__';
</script>
<script src="/static/app.js"></script>
```

## チーム構成

| エージェント | 担当 | ファイル |
|---|---|---|
| team-lead | Phase0分割 + Phase2 QA | index.html |
| agent-css | 全CSS変更 | style.css |
| agent-js | 全JS変更 | app.js |

## 実装内容

### agent-css（style.css）

#### 修正4: 購入ボタンのトーンダウン
```css
/* 変更前 */
.buy-btn-amazon  { background: #FF9900; }
.buy-btn-rakuten { background: #BF0000; }

/* 変更後: ゴーストボタン */
.buy-btn {
  background: transparent;
  border: 1px solid var(--c-border);
  color: var(--c-sub);
}
.buy-btn:hover { background: var(--bg-active); color: var(--c-text); }
.buy-btn-amazon, .buy-btn-rakuten { /* 色は削除 */ }
```

#### 修正3B: カテゴリラベル色分け
```css
.build-category[data-cat="GPU"]  { color: #4CAF50; border-color: rgba(76,175,80,.3); background: rgba(76,175,80,.12); }
.build-category[data-cat="CPU"]  { color: #2196F3; border-color: rgba(33,150,243,.3); background: rgba(33,150,243,.12); }
.build-category[data-cat="RAM"]  { color: #9C27B0; border-color: rgba(156,39,176,.3); background: rgba(156,39,176,.12); }
.build-category[data-cat="MB"]   { color: #FF9800; border-color: rgba(255,152,0,.3);  background: rgba(255,152,0,.12); }
.build-category[data-cat="PSU"]  { color: #607D8B; border-color: rgba(96,125,139,.3); background: rgba(96,125,139,.12); }
.build-category[data-cat="CASE"] { color: #009688; border-color: rgba(0,150,136,.3);  background: rgba(0,150,136,.12); }
```

#### 修正2-CSS: レーダーチャート改善
- `.radar-wrap` の width を 280px に拡大（現在 260px）
- `.radar-title` に軸説明テキストのスタイル追加

#### 修正1-CSS: 構成サマリーカード
- `.summary-card` 新規追加
- `.summary-row` `.summary-status` `.summary-total` 追加

#### 修正5-CSS: パーツサムネイル
- `.build-thumb` 48×48px サムネスタイル
- `.build-thumb-default` デフォルトアイコン

#### 修正3A-CSS: カードサイズ傾斜
- `.build-item--lg` `.build-item--md` `.build-item--sm` 追加

#### モバイル CSS
- `@media (max-width: 600px)` でサマリーカード・レーダーの縦積み対応

### agent-js（app.js）

#### 修正2-JS: レーダーチャート改善
- `renderRadarChart` の `label: 'ゲーム推奨'` → `label: '{gameName} 高設定60fps推奨ライン'` に動的生成
- 互換チェックモード時はレーダー非表示（`gameMode === false` で skip）

#### 修正1-JS: 構成サマリーカード
- `renderSummaryCard(build)` 関数を新規追加
- `appendRecommendationMessage` の冒頭で呼び出す
- 全カテゴリを常に表示（未選択は「—」グレーアウト）
- 合計金額リアルタイム表示

#### 修正5-JS: パーツ画像
- `renderAlternatives` / `appendRecommendationMessage` に `image_url` フィールド対応追加
- 画像なし → カテゴリ別デフォルトアイコン（GPU: 🎮 CPU: ⚡ RAM: 💾 MB: 🔌 PSU: 🔋 CASE: 🖥️）

#### 修正3A-JS: カードサイズクラス
- `build-item` に `data-cat` + サイズクラス付与
  - GPU, CPU, CASE → `build-item--lg`
  - RAM, MB → `build-item--md`
  - PSU → `build-item--sm`

## 実装優先度（agent-css / agent-js 内の順番）

```
1. 修正4 + 修正3B  ← CSS変更のみ、最優先
2. 修正5           ← 画像UI
3. 修正1           ← サマリーカード（CSS+JS）
4. 修正2           ← レーダー改善
5. 修正3A          ← カードサイズ
6. モバイル対応     ← 最後
```

## 検証方法

```bash
# ローカルサーバー起動確認
# Chrome headless スクリーンショット
chrome --headless --screenshot=out.png http://localhost:5000
```

確認項目:
- 購入ボタンが控えめになっている
- カテゴリラベルが色分けされている
- サマリーカードが表示される
- モバイル幅（375px）で崩れていない
