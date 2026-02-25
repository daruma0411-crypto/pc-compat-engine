# Steam スクレイパー設計書

**日付**: 2026-02-25
**フェーズ**: Phase 1（スクレイパー実装のみ）

## 目的

pc-compat-engine を AIパフォーマンスアドバイザーにピボットするため、Steam ゲームの PC 必要スペック・推奨スペックを収集し RAG 用データベースを構築する。

## ファイル構成

```
pc-compat-engine/
├── scripts/
│   ├── steam_top_games.py     # Step 1: appidリスト取得
│   ├── steam_scraper.py       # Step 2: 詳細スクレイピング
│   └── steam_parser.py        # Step 3: HTMLパーサー（モジュール）
└── workspace/data/steam/
    ├── raw/                   # appidごとのJSON（.gitignore対象）
    ├── games.jsonl            # パース済みデータ（git管理）
    └── top_games.json         # appidリスト（git管理）
```

## データフロー

```
Steam検索API
  → top_games.json（300〜500 appid）
      → appdetails API（1.5秒間隔）
          → raw/{appid}.json（チェックポイント）
              → steam_parser.py（日英両対応）
                  → games.jsonl
```

## 各スクリプトの仕様

### steam_top_games.py

- エンドポイント: `https://store.steampowered.com/search/results/`
- カテゴリ: `topsellers` × 10ページ、`popularnew` × 10ページ（各25件）
- `hidef2p=1`（無料ゲーム除外）
- `type: "game"` のみ残す、重複排除
- 出力: `workspace/data/steam/top_games.json`
- 目標: 300〜500 appid

### steam_scraper.py

- エンドポイント: `https://store.steampowered.com/api/appdetails?appids={appid}&l=japanese`
- `raw/{appid}.json` が存在するappidはスキップ（途中再開対応）
- レート制限: 1.5秒/リクエスト
- エラーハンドリング: 3回リトライ（指数バックオフ）、429エラー時60秒待機
- 200件ごとにチェックポイント → `games.jsonl` に追記
- 取得フィールド: name, steam_appid, type, short_description, genres, categories, release_date, pc_requirements, platforms, metacritic, screenshots[0]

### steam_parser.py

- BeautifulSoup（html.parser）でHTML → 構造化JSON
- **日英両対応ラベル**: `Processor|プロセッサー`、`Memory|メモリ`、`Graphics|グラフィックス`、`Storage|ストレージ` 等
- CPU/GPU は `or` / `／` で分割して配列化
- RAM/Storage は数値抽出して int 化
- パース失敗項目は `null`（スキップせず記録）

## 出力形式（games.jsonl）

```json
{
  "appid": 2246340,
  "name": "Monster Hunter Wilds",
  "genres": ["Action", "RPG"],
  "release_date": "2025-02-28",
  "metacritic_score": 85,
  "minimum": {
    "os": "Windows 10 (64-bit)",
    "cpu": ["Intel Core i5-10400", "AMD Ryzen 5 3600"],
    "gpu": ["NVIDIA GeForce GTX 1660", "AMD Radeon RX 5500 XT"],
    "ram_gb": 16,
    "storage_gb": 75,
    "storage_type": "SSD",
    "directx": "12"
  },
  "recommended": { "..." },
  "scraped_at": "2026-02-25T12:00:00Z"
}
```

## 完了基準

- [ ] 300タイトル以上が `games.jsonl` に格納
- [ ] パース成功率 90% 以上（minimum/recommended の主要項目）
- [ ] Steam API の BAN なし
- [ ] `steam_scraper.py` が途中再開できる
- [ ] git commit 済み

## 決定事項

| 項目 | 決定 |
|------|------|
| 実装スコープ | Phase 1のみ（Phase 2は別セッション） |
| データ保存先 | `workspace/data/steam/`（既存データと統一） |
| API言語 | `l=japanese`（日本語） |
| ファイル構成 | 3ファイル分離（疎結合） |
