# X Monitor Scraper 設計書

作成: 2026-02-24  
ステータス: 承認済み

## 概要

Playwright で X（旧Twitter）を検索し、自作PC関連ツイートから型番を抽出して  
`/api/diagnose` に診断リクエストを送り、結果をログファイルに保存するスクリプト。

## ファイル構成

```
pc-compat-engine/
├── scripts/
│   └── x_monitor_scraper.py    # ← 新規作成（メインスクリプト）
└── logs/                        # ← 自動生成
    ├── x_monitor_YYYY-MM-DD.jsonl   # 診断結果ログ
    ├── seen_ids.txt                  # 処理済みツイートID（重複防止）
    └── x_session.json               # Xログインセッション（初回後再利用）
```

## 実行方法

```bash
# 手動実行
python scripts/x_monitor_scraper.py

# cronまたはWindowsタスクスケジューラで15分ごと
python C:\Users\iwashita.AKGNET\pc-compat-engine\scripts\x_monitor_scraper.py
```

## 処理フロー

```
seen_ids.txt 読み込み
    ↓
X にログイン（x_session.json が有効なら再利用、期限切れなら再ログイン）
    ↓
「グラボ 入らない」で検索（&f=live: 最新タブ）
    ↓
ツイートを最大 MAX_TWEETS 件スクロール収集
    ↓
各ツイートに対して:
  ├─ ID が seen_ids に存在 → スキップ
  ├─ 型番抽出（PART_PATTERNS 正規表現）
  ├─ 型番が 0 件 → スキップ
  ├─ POST /api/diagnose {parts: [...]}
  ├─ 結果を x_monitor_YYYY-MM-DD.jsonl に追記
  └─ ID を seen_ids.txt に追記
    ↓
完了ログ出力
```

## 環境変数（.env に記載）

| 変数名          | 必須 | デフォルト                                                      |
|-----------------|------|------------------------------------------------------------------|
| X_USERNAME      | ✅   | —                                                                |
| X_PASSWORD      | ✅   | —                                                                |
| COMPAT_API_URL  |      | https://pc-compat-engine.onrender.com/api/diagnose               |
| X_SEARCH_QUERY  |      | グラボ 入らない                                                  |
| MAX_TWEETS      |      | 20                                                               |

## ログ形式（JSONL）

1行1レコード（追記形式）：

```json
{
  "timestamp": "2026-02-24T10:30:00",
  "tweet_id": "1234567890123456789",
  "tweet_url": "https://x.com/i/status/1234567890123456789",
  "tweet_text": "RTX 4090がNZXT H510に入らない...",
  "parts": ["RTX 4090", "H510"],
  "verdict": "NG",
  "summary": "GPU長336mmがケース最大310mmを超えています",
  "checks": []
}
```

スキップ時：

```json
{
  "timestamp": "2026-02-24T10:30:00",
  "tweet_id": "...",
  "skipped": true,
  "reason": "no_parts_found"
}
```

## 型番抽出パターン

`PART_NUMBER_PATTERNS`（domain_rules.py）から抽出した正規表現を inline で定義。  
スタンドアロンスクリプトのため、インポートではなく定数として展開。

カバー対象：NVIDIA GPU / AMD GPU / Intel CPU / AMD CPU / Noctua クーラー /
PCケース / 電源 / メモリ（DDR表記）

## 依存パッケージ

```
playwright>=1.40
python-dotenv
requests
```

インストール：
```bash
pip install playwright python-dotenv requests
playwright install chromium
```

## セッション管理

- 初回実行時：フルログイン → `logs/x_session.json` に保存
- 以降の実行：セッションファイルを `browser_context.storage_state` でロード
- セッション期限切れ時：自動的に再ログイン

## cron 登録例（Windows タスクスケジューラ）

```
タスク名: pc-compat-x-monitor
実行間隔: 15分
コマンド: python C:\Users\iwashita.AKGNET\pc-compat-engine\scripts\x_monitor_scraper.py
開始ディレクトリ: C:\Users\iwashita.AKGNET\pc-compat-engine
```
