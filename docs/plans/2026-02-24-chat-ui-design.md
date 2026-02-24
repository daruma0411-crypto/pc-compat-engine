# /compat チャットUI設計書

**作成**: 2026-02-24
**対象**: pc-compat-engine `/compat` ページ刷新

---

## 概要

現行のフォーム入力UIをチャット形式に刷新する。
自然言語で「RTX 4070をLancool 216に入れたい」と書くだけで型番抽出→互換性診断→代替品提案まで完結する。

---

## アーキテクチャ

```
ブラウザ (static/index.html)
  ↓ POST /api/chat  { message, history[] }
app.py
  ├─ Claude Haiku で型番抽出
  ├─ _lookup_pc_specs() でDB照合（既存）
  ├─ _compute_prechecks() で事前計算（既存）
  └─ _run_pc_diagnosis_with_claude() で診断（既存）
  ↓ { type, parts, diagnosis, reply }

ブラウザ（代替品ボタン押下時）
  ↓ GET /api/alternatives?category=gpu&case_name=...
app.py
  └─ products.jsonl をフィルタリング（長さ・ソケット等）
  ↓ { alternatives: [{name, specs, amazon_url, rakuten_url}] }
```

**変更ファイル**:
- `app.py` → `/api/chat` と `/api/alternatives` を追加
- `static/index.html` → チャットUI形式に全面刷新
- 既存 `/api/diagnose` はそのまま維持（下位互換）

---

## バックエンド API

### POST /api/chat

**リクエスト**:
```json
{
  "message": "RTX 4070をLancool 216に入れたい",
  "history": []
}
```

**レスポンス type: "diagnosis"**（型番2件以上揃った場合）:
```json
{
  "type": "diagnosis",
  "reply": "RTX 4070 と Lancool 216 の組み合わせを診断しました。",
  "parts": ["GeForce RTX 4070 GAMING X TRIO", "Lian Li Lancool 216"],
  "diagnosis": {
    "verdict": "OK",
    "checks": [...],
    "summary": "..."
  }
}
```

**レスポンス type: "clarify"**（型番不足の場合）:
```json
{
  "type": "clarify",
  "reply": "GPUはRTX 4070ですね。ケースの型番も教えてください。",
  "parts": ["GeForce RTX 4070 GAMING X TRIO"]
}
```

**レスポンス type: "message"**（型番ゼロの場合）:
```json
{
  "type": "message",
  "reply": "どのパーツの組み合わせを確認したいですか？..."
}
```

### GET /api/alternatives

**パラメータ**:
- `category`: `gpu` or `case`
- `case_name`: ケース名（GPU代替品検索時）
- `gpu_name`: GPU名（ケース代替品検索時）

**レスポンス**:
```json
{
  "alternatives": [
    {
      "name": "MSI GeForce RTX 4070 VENTUS 3X",
      "maker": "msi",
      "specs": { "length_mm": 285, "tdp_w": 200, "power_connector": "16pinx1" },
      "amazon_url": "https://www.amazon.co.jp/s?k=MSI+RTX+4070+VENTUS+3X&tag=pccompat-22",
      "rakuten_url": "https://search.rakuten.co.jp/search/mall/MSI+RTX+4070+VENTUS+3X/"
    }
  ]
}
```

---

## フロントエンド UI

### レイアウト

```
┌─────────────────────────────────────┐
│  🖥️ PC互換性チェッカー               │  ← ヘッダー
├─────────────────────────────────────┤
│ （スクロール可能チャット欄）          │
│  [AI] どんな組み合わせを確認したいですか？  │
│       RTX 4070をケースに入れたい ▶  │
│  [AI] ケースの型番も教えてください    │
│       Lancool 216です ▶             │
│  [AI] 診断結果カード                 │
│       NG/WARNING時: 代替ボタン       │
│       商品カードグリッド             │
├─────────────────────────────────────┤
│ [入力欄                    ] [送信]  │  ← 固定フッター
└─────────────────────────────────────┘
```

### 診断結果カード構造

```
┌─────────────────────────────────────┐
│ ✅/⚠️/❌ 互換性OK/WARNING/NG        │  ← verdict banner
│ サマリー1行                          │
├─────────────────────────────────────┤
│ ✅ GPU干渉  OK 75mm余裕             │  ← checks list
│ ✅ ソケット OK LGA1700一致          │
│ ⚠️ 電源    WARNING 使用率85%       │
└─────────────────────────────────────┘
│ [GPUを変える] [ケースを変える]       │  ← NG/WARNING時のみ
```

### 商品カード構造

```
┌────────────────────────────┐
│ MSI RTX 4070 VENTUS 3X    │
│ 285mm / 200W / 16pin       │
│ 価格目安: ¥55,000〜        │
│ [🛒 Amazon] [🛒 楽天]     │
└────────────────────────────┘
```

---

## 状態管理

- ブラウザJS配列で会話履歴を保持（サーバーステートレス）
- リロードで状態はリセット
- `history` 配列を `/api/chat` に毎回送信

---

## アフィリエイト

- Amazon: `tag=pccompat-22`（サーバー側 `__AMAZON_TAG__` 置換で注入）
- 楽天: `RAKUTEN_A_ID` / `RAKUTEN_L_ID` 環境変数で注入
- 価格.com: アフィリエイトなし（単純検索URL）
