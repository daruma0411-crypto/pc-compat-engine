# ダークテーマ UI 設計書

作成: 2026-02-25

## 概要

pc-compat-engine の `static/index.html` を Figma デザイン（Landing Template / Chat UI）に基づきダークテーマ化する。
レイアウトは現行のモバイルファースト 720px チャット形式を維持し、ビジュアルのみ刷新する（案B）。

## カラーパレット

| 用途 | 変数 | 値 |
|---|---|---|
| 背景（最外層） | `--bg-outer` | `#1D2229` |
| ヘッダー・フッター | `--bg-main` | `#232930` |
| カード・バブル | `--bg-card` | `#303740` |
| 入力欄・ビルドアイテム | `--bg-input` | `#3D454F` |
| アクティブ行 | `--bg-active` | `#444C57` |
| テキスト（主） | `--c-text` | `#EAECEF` |
| テキスト（副） | `--c-sub` | `#CDD2D8` |
| テキスト（補足） | `--c-muted` | `#BBC2CA` |
| アクセント | `--c-primary` | `#9ECFFF`（Action blue）|
| ボーダー | `--c-border` | `#606975` |
| OK | `--c-ok` | `#78FFCB`（Generated green）|
| WARNING | `--c-warn` | `#FFD978`（Danger yellow）|
| NG | `--c-ng` | `#FF9178`（Error orange）|
| 不明 | `--c-unk` | `#BBC2CA` |

## フォント

Inter（Google Fonts）を追加。フォールバック: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans"`

## コンポーネント別変更

### ヘッダー
- 背景: 紫グラデ → `#232930`
- 左端に ☰ ボタン（履歴ドロワー開閉）を追加
- ロゴアイコン（36px 丸角、`radial-gradient(#0059B2, #008AB0)`）を追加

### チャットエリア
- 背景: `#1D2229`
- AIバブル: `#303740` + border `#606975`
- ユーザーバブル: `#3D454F` + border `#606975`
- タイピングドット: `#9ECFFF`

### 入力フッター
- 背景: `#232930`, border-top `#606975`
- テキストエリア: `#3D454F`, border `#87909C`, placeholder `#BBC2CA`
- 送信ボタン: `#9ECFFF` 背景、暗色テキスト、角丸 10px

### モード選択カード
- 背景: `#303740`, border `#606975`
- ホバー: `#444C57` + `border-left: 3px solid #CDD2D8`

### 診断カード
- 背景: `#303740`, border `#606975`
- verdict-banner: 暗色 bg（OK=`#1a3d31` / WARN=`#3d3620` / NG=`#3d2420`）
- バッジ: 暗色バリアント（`badge-OK` 等）

### 推奨構成カード（ゲームモード）
- 背景: `#303740`, border `#606975`
- build-item: `#3D454F` + `border-left: 2px solid #9ECFFF`
- build-category: 半透明 `rgba(158,207,255,.2)` + border

### 履歴ドロワー（新機能）
- 実装: DOM にオーバーレイ追加（`position: fixed`、左からスライドイン）
- データ: localStorage `pc_compat_history`（最大20件）
- 保存内容: `{id, title(最初のユーザーメッセージ), date, mode}`
- 「＋ 新しいチャット」ボタンでページリロード
- 履歴行クリックは表示のみ（会話再開は今回スコープ外）

## 変更ファイル

- `static/index.html` のみ（バックエンド変更なし）

## 変更量の目安

- CSS: ~200行更新
- HTML: ドロワー部分 ~20行追加、ヘッダー ~3行追加
- JS: localStorage 関連 ~30行追加
