# PC互換チェッカー 本番デプロイ手順書

## 📋 目次
1. [環境変数一覧](#環境変数一覧)
2. [必要なパッケージとバージョン](#必要なパッケージとバージョン)
3. [ポート設定](#ポート設定)
4. [デプロイ手順（Render.com）](#デプロイ手順rendercom)
5. [動作確認方法](#動作確認方法)
6. [トラブルシューティング](#トラブルシューティング)

---

## 🔑 環境変数一覧

### 必須環境変数

| 変数名 | 説明 | 取得方法 |
|--------|------|----------|
| `ANTHROPIC_API_KEY` | Claude APIキー（必須） | https://console.anthropic.com/settings/keys |
| `REPLICATE_API_TOKEN` | Replicate APIキー（画像生成に必須） | https://replicate.com/account/api-tokens |

### オプション環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `PORT` | サーバーのリスニングポート | `10000` |
| `AMAZON_TAG` | Amazonアフィリエイトタグ | `pccompat-22` |
| `RAKUTEN_A_ID` | 楽天アフィリエイトID | (空) |
| `RAKUTEN_L_ID` | 楽天アフィリエイトリンクID | (空) |

### ローカル開発用 .env ファイル

```bash
# .env ファイル（プロジェクトルートに配置）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REPLICATE_API_TOKEN=r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT=10000
AMAZON_TAG=pccompat-22
```

⚠️ **重要**: `.env` ファイルは `.gitignore` に含まれており、Gitにコミットされません。本番環境では Render の Environment Variables で設定します。

---

## 📦 必要なパッケージとバージョン

`requirements.txt` に記載されている依存関係：

```txt
# Web Framework
flask>=3.0.0
gunicorn>=22.0.0

# LLM Provider
anthropic>=0.40.0

# AI Image Generation
replicate>=1.0.0

# HTML Parser
beautifulsoup4>=4.12.0

# Utilities
python-dotenv>=1.0.0
requests>=2.32.0
```

### Python バージョン

- **推奨**: Python 3.11 (固定)
- **最小要件**: Python 3.9 以上
- **重要**: `runtime.txt` で `python-3.11.0` を指定済み（Replicate パッケージの互換性のため）

⚠️ **Python 3.14+ を使用すると、`replicate` パッケージが Pydantic v1 互換性エラーで起動失敗します。**

---

## 🔌 ポート設定

### ローカル開発

```bash
# デフォルトポート
PORT=10000

# アクセスURL
http://127.0.0.1:10000
```

### 本番環境（Render）

- Render は自動的に `PORT` 環境変数を設定します
- `gunicorn` が `$PORT` を読み取ってバインドします
- 外部からは `https://your-app.onrender.com` でアクセス可能

---

## 🚀 デプロイ手順（Render.com）

### Step 1: GitHubリポジトリの準備

```bash
# 1. プロジェクトディレクトリに移動
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# 2. 必要なファイルが揃っていることを確認:
# ✅ app.py
# ✅ requirements.txt
# ✅ runtime.txt (Python 3.11.0 指定)
# ✅ .env.example
# ✅ workspace/data/ (パーツデータ)
# ✅ static/ (フロントエンド)

# 3. 最新の変更をコミット
git add .
git commit -m "feat: 本番デプロイ準備完了 (Python 3.11固定)"

# 4. GitHubにプッシュ
git push origin main
```

### Step 2: Render.com でプロジェクトを作成

1. **Render Dashboard にアクセス**
   - https://dashboard.render.com/ にログイン

2. **New Web Service を作成**
   - 「New +」→「Web Service」をクリック
   - GitHub リポジトリ `daruma0411-crypto/pc-compat-engine` を選択

3. **基本設定を入力**

   | 項目 | 設定値 |
   |------|--------|
   | **Name** | `pc-compat-engine` (任意) |
   | **Region** | `Singapore` (Asia最寄り) |
   | **Branch** | `main` |
   | **Root Directory** | (空欄) |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app` |

### Step 3: 環境変数を設定

Render Dashboard の **Environment** タブで以下を追加：

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
REPLICATE_API_TOKEN=r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AMAZON_TAG=pccompat-22
```

⚠️ **注意**: `PORT` は Render が自動設定するため、手動で追加不要です。

### Step 4: デプロイ実行

```bash
# Render が自動的に以下を実行:
# 1. リポジトリをクローン
# 2. pip install -r requirements.txt
# 3. gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app

# デプロイログを確認:
# Render Dashboard → 該当サービス → Logs タブ
```

### Step 5: カスタムドメイン設定（オプション）

```bash
# 1. Render Dashboard → Settings → Custom Domains
# 2. 独自ドメインを追加（例: pc-compat.example.com）
# 3. DNSレコードを追加:
#    - Type: CNAME
#    - Name: pc-compat
#    - Value: your-app.onrender.com
```

---

## ✅ 動作確認方法

### 1. ヘルスチェック

```bash
# ローカル環境
curl http://127.0.0.1:10000/api/health

# 本番環境
curl https://your-app.onrender.com/api/health

# 期待されるレスポンス:
# {"status": "ok", "message": "PC互換チェッカーは正常に動作しています"}
```

### 2. トップページアクセス

```bash
# ブラウザで開く:
# ローカル: http://127.0.0.1:10000
# 本番: https://your-app.onrender.com

# 期待される画面:
# - PC互換チェッカーのUIが表示される
# - 左側にチャット入力欄
# - 右側にパーツ選択パネル
```

### 3. チャット機能テスト

```bash
# ブラウザで以下を試す:
# 1. 「モンハンワイルドを快適にプレイしたい」と入力
# 2. Claude がレスポンスを返すことを確認
# 3. パーツ提案が表示されることを確認
```

### 4. 画像生成テスト

```bash
# 前提: 構成が確定している状態

# 1. 「完成イメージを見る」ボタンをクリック
# 2. Replicate API が画像を生成することを確認
# 3. 生成された画像が表示されることを確認
```

### 5. APIエンドポイント確認

```bash
# /api/chat エンドポイント
curl -X POST https://your-app.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "モンハンワイルドをプレイしたい",
    "session_id": "test-session"
  }'

# 期待されるレスポンス:
# {
#   "response": "...",
#   "phase": "hearing",
#   "hearing_questions": [...],
#   "confirmed_parts": {...}
# }
```

---

## 🔧 トラブルシューティング

### 問題 1: Render でビルドが失敗する

**症状**: `pip install` でエラー

**解決策**:
```bash
# 1. requirements.txt のバージョン指定を確認
# 2. Python バージョンを 3.11 に固定:
#    Render Dashboard → Settings → Environment → Python Version: 3.11.0
```

### 問題 2: APIキーエラー

**症状**: `ANTHROPIC_API_KEY is not set`

**解決策**:
```bash
# 1. Render Dashboard → Environment で環境変数を確認
# 2. APIキーの形式を確認（sk-ant- で始まる）
# 3. 環境変数の Save を忘れずにクリック
# 4. サービスを再起動: Manual Deploy → Deploy latest commit
```

### 問題 3: タイムアウトエラー

**症状**: `Worker timeout (pid:xxx)`

**解決策**:
```bash
# Start Command に --timeout を追加:
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app

# または、より長いタイムアウトを設定:
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 app:app
```

### 問題 4: メモリ不足

**症状**: `MemoryError` または OOM Killed

**解決策**:
```bash
# 1. Render のプランをアップグレード（Free → Starter 以上）
# 2. Worker数を減らす:
gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app
```

### 問題 5: 静的ファイルが404

**症状**: CSS/JS が読み込まれない

**解決策**:
```bash
# app.py の static_folder 設定を確認:
app = Flask(__name__, static_folder='static')

# ディレクトリ構造を確認:
# pc-compat-engine/
# ├── app.py
# ├── static/
# │   ├── index.html
# │   ├── app.js
# │   └── style.css
```

### 問題 6: Pydantic v1 互換性エラー（Python 3.14+）

**症状**: `Error: unable to infer type for attribute "previous"` / `Pydantic V1 functionality isn't compatible with Python 3.14`

**原因**: `replicate` パッケージが Pydantic v1 を使用しており、Python 3.14 以降と互換性がない

**解決策**:
```bash
# 1. runtime.txt を作成してPython 3.11 に固定:
echo "python-3.11.0" > runtime.txt

# 2. GitHubにプッシュ:
git add runtime.txt
git commit -m "fix: Python 3.11に固定してReplicate互換性を確保"
git push origin main

# 3. Renderが自動的に再デプロイ
```

---

## 🎯 チェックリスト

デプロイ前に確認:

- [ ] `.env` ファイルにAPIキーを設定（ローカル開発用）
- [ ] `requirements.txt` が最新
- [ ] GitHub に最新コードをプッシュ済み
- [ ] Render の環境変数を設定済み
- [ ] `workspace/data/` ディレクトリが存在する
- [ ] ヘルスチェックが成功する

デプロイ後に確認:

- [ ] Render のログにエラーがない
- [ ] トップページが表示される
- [ ] チャット機能が動作する
- [ ] パーツ提案が表示される
- [ ] 画像生成機能が動作する（Replicate APIキー必須）

---

## 📚 参考リンク

- **Render Docs**: https://docs.render.com/
- **Flask Docs**: https://flask.palletsprojects.com/
- **Gunicorn Docs**: https://docs.gunicorn.org/
- **Anthropic API**: https://docs.anthropic.com/
- **Replicate API**: https://replicate.com/docs

---

_最終更新: 2026-02-27 00:00 JST_
