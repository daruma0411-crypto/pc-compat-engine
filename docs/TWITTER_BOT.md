# Twitter Bot - PC互換チェッカー自動投稿

## 概要

PC互換チェッカーのゲーム情報を自動的にTwitterへ投稿するボットです。

### 機能

- 📊 **メタスコア優先選択**: 高評価ゲームを優先的に投稿
- 🔄 **投稿履歴管理**: 同じゲームを短期間で重複投稿しない（最大50件履歴）
- 🎲 **ランダムパターン**: 4種類のツイート文パターンからランダム選択
- ✅ **DRY RUN対応**: 本番投稿前にテスト可能

---

## セットアップ

### 1. Twitter Developer Accountの取得

1. **Twitter Developer Portal**にアクセス: https://developer.twitter.com/
2. **Create App**でアプリケーション作成
3. **User Authentication Settings**で以下を設定:
   - App permissions: **Read and Write**
   - Type of App: **Web App, Automated App or Bot**
4. **Keys and Tokens**タブで以下を取得:
   - API Key（Consumer Key）
   - API Secret（Consumer Secret）
   - Access Token
   - Access Token Secret
   - Bearer Token

### 2. 環境変数の設定

#### Windows（PowerShell）

```powershell
# 一時的な設定（現在のセッションのみ）
$env:TWITTER_API_KEY = "your_api_key_here"
$env:TWITTER_API_SECRET = "your_api_secret_here"
$env:TWITTER_ACCESS_TOKEN = "your_access_token_here"
$env:TWITTER_ACCESS_SECRET = "your_access_secret_here"
$env:TWITTER_BEARER_TOKEN = "your_bearer_token_here"
```

#### 永続的な設定（システム環境変数）

1. **システムのプロパティ** → **環境変数**を開く
2. **ユーザー環境変数**に以下を追加:
   - `TWITTER_API_KEY`
   - `TWITTER_API_SECRET`
   - `TWITTER_ACCESS_TOKEN`
   - `TWITTER_ACCESS_SECRET`
   - `TWITTER_BEARER_TOKEN`

### 3. Pythonライブラリのインストール

```bash
pip install tweepy
```

---

## 使い方

### テスト実行（DRY RUN）

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine
python scripts\twitter_bot.py --dry-run
```

**出力例:**
```
ゲームデータ読み込み中...
[OK] 445ゲームを読み込みました
[履歴] 投稿履歴: 0件
[選択] 選択ゲーム: Baldur's Gate 3
============================================================
[DRY RUN] 以下のツイートを投稿します:
============================================================
「Baldur's Gate 3」やりたいけど、自分のPCで動くか不安...

推奨スペック:
GPU: Nvidia 2060 Super
CPU: Intel i7 8700K
RAM: 16GB

無料で互換性チェック！→ https://pc-compat-engine-production.up.railway.app/game/baldurs-gate-3
#PCゲーム #スペック確認
============================================================
文字数: 200
```

### 本番投稿

```bash
python scripts\twitter_bot.py
```

投稿が成功すると、`scripts/twitter_post_history.json`に履歴が保存されます。

---

## 自動化（定期投稿）

### 方法1: Windows タスクスケジューラ

1. **タスクスケジューラ**を起動
2. **基本タスクの作成**を選択
3. 設定:
   - **名前**: PC互換チェッカー Twitter Bot
   - **トリガー**: 毎日 12:00, 18:00, 21:00
   - **操作**: プログラムの開始
   - **プログラム**: `python`
   - **引数**: `C:\Users\iwashita.AKGNET\pc-compat-engine\scripts\twitter_bot.py`
   - **開始**: `C:\Users\iwashita.AKGNET\pc-compat-engine`

### 方法2: GitHub Actions（推奨）

Railway.appで動いているアプリとは別に、GitHub Actionsで定期実行する方法です。

#### `.github/workflows/twitter-bot.yml`

```yaml
name: Twitter Bot - Auto Post

on:
  schedule:
    # 日本時間 12:00, 18:00, 21:00 (UTC+9)
    - cron: '0 3,9,12 * * *'  # UTC 3:00, 9:00, 12:00
  workflow_dispatch:  # 手動実行も可能

jobs:
  post:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install tweepy
    
    - name: Post to Twitter
      env:
        TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
        TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
        TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
        TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
        TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
      run: |
        python scripts/twitter_bot.py
    
    - name: Commit history
      run: |
        git config user.name "GitHub Actions"
        git config user.email "actions@github.com"
        git add scripts/twitter_post_history.json
        git commit -m "Update Twitter post history [skip ci]" || echo "No changes"
        git push
```

#### GitHub Secretsの設定

1. GitHubリポジトリ → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**で以下を追加:
   - `TWITTER_API_KEY`
   - `TWITTER_API_SECRET`
   - `TWITTER_ACCESS_TOKEN`
   - `TWITTER_ACCESS_SECRET`
   - `TWITTER_BEARER_TOKEN`

### 方法3: Railway.app Cron（将来）

Railway.appにCron機能が追加された場合、アプリ内でスケジュール実行も可能です。

---

## ツイートパターン

4種類のパターンからランダムに選択されます:

### パターン1: GPU互換性強調
```
【GPU互換性チェック】
Elden Ring（メタスコア: 96）

推奨GPU: Nvidia GeForce GTX 1070
推奨CPU: Intel Core i7-8700K
RAM: 16GB

あなたのPCで動く？→ https://...
#PCゲーム #GPU互換性
```

### パターン2: 質問形式
```
「Elden Ring」やりたいけど、自分のPCで動くか不安...

推奨スペック:
GPU: Nvidia GeForce GTX 1070
CPU: Intel Core i7-8700K
RAM: 16GB

無料で互換性チェック！→ https://...
#PCゲーム #スペック確認
```

### パターン3: シンプル紹介
```
Elden Ring
推奨スペック一覧

GPU: Nvidia GeForce GTX 1070
CPU: Intel Core i7-8700K
RAM: 16GB

詳細 → https://...
#PCゲーム #自作PC
```

### パターン4: トラブルシューティング風
```
「Elden Ringがカクつく...」

推奨スペックをチェック！
GPU: Nvidia GeForce GTX 1070
CPU: Intel Core i7-8700K
RAM: 16GB

互換性診断ツール→ https://...
#PCゲーム #動作環境
```

---

## 投稿履歴

履歴は`scripts/twitter_post_history.json`に保存されます。

```json
[
  {
    "name": "Baldur's Gate 3",
    "posted_at": "2026-03-01T14:00:00.123456",
    "tweet_text": "「Baldur's Gate 3」やりたいけど..."
  },
  {
    "name": "Elden Ring",
    "posted_at": "2026-03-01T18:00:00.123456",
    "tweet_text": "【GPU互換性チェック】Elden Ring..."
  }
]
```

最大50件の履歴を保持し、重複投稿を防ぎます。

---

## トラブルシューティング

### エラー: `tweepy module not found`

```bash
pip install tweepy
```

### エラー: `401 Unauthorized`

- Twitter API Keyが正しく設定されているか確認
- App permissionsが「Read and Write」になっているか確認

### エラー: `403 Forbidden`

- Access TokenとSecretが正しいか確認
- Bearer Tokenが正しいか確認

### 文字化け（Windows）

スクリプト内で絵文字を使用していません。文字化けする場合は、PowerShellのエンコーディング設定を確認してください。

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## カスタマイズ

### 投稿頻度の調整

`select_game()`関数の`max_history`パラメータで調整:

```python
# 履歴を100件に拡大（重複期間を延長）
select_game(games, history, max_history=100)
```

### メタスコアフィルタ

メタスコアの閾値を設定:

```python
candidates_with_score = [
    g for g in candidates
    if g.get('metacritic_score') and g['metacritic_score'] >= 80  # 80点以上のみ
]
```

### ハッシュタグのカスタマイズ

各パターン内のハッシュタグを編集:

```python
f"#PCゲーム #GPU互換性 #自作PC"
```

---

## ライセンス

このスクリプトはPC互換チェッカープロジェクトの一部です。
