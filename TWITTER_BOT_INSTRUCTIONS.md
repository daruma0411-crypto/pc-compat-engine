# Twitter Bot トラブルシューティング・修正指示書

## 📌 現状の問題

Twitter Bot（自動投稿システム）が動作していない。

### 症状
- GitHub Actionsは成功（✅）
- しかし実際にはツイートされていない
- 投稿履歴（`scripts/twitter_post_history.json`）が空

### 発生しているエラー
```
[失敗] ツイート投稿失敗: 403 Forbidden
または
[失敗] ツイート投稿失敗: 401 Unauthorized
```

---

## 🔍 問題の原因（推定）

### 1. **App Permissions が Read Only**
- Twitter Developer Portal で権限が「Read」のみになっている
- 「Read and Write」に変更が必要

### 2. **Access Token が古い**
- 権限変更前に生成されたトークンは古い権限のまま
- 権限変更後に再生成が必要

### 3. **User Authentication Settings が未設定**
- OAuth 1.0a の設定が不完全
- Callback URL等が未設定の可能性

---

## 🎯 解決手順

### ステップ1: Twitter Developer Portal で権限確認

#### 1.1 アプリ設定を開く

```
https://developer.twitter.com/en/portal/projects-and-apps
```

1. 作成したアプリ（PC Compatibility Checker）を選択
2. **「Settings」タブ** をクリック

#### 1.2 User Authentication Settings を確認

**「User authentication settings」セクションを探す**

- **✅ 既に設定済みの場合:**
  - 「App permissions」を確認
  - ❌ **Read** のみ → 修正が必要
  - ✅ **Read and Write** → OK

- **❌ 未設定の場合:**
  - 「Set up」ボタンをクリック
  - 以下の設定を実施:
    - **App permissions**: `Read and Write`
    - **Type of App**: `Web App, Automated App or Bot`
    - **Callback URI**: `https://pc-jisaku.com`
    - **Website URL**: `https://pc-jisaku.com`

#### 1.3 Access Token を再生成

**重要: 権限変更後は必ずトークン再生成！**

1. **「Keys and tokens」タブ** に移動
2. **「Access Token and Secret」セクション**
3. **「Regenerate」ボタン** をクリック
4. 新しいトークンをメモ帳に保存:
   ```
   Access Token: ...
   Access Token Secret: ...
   ```

---

### ステップ2: GitHub Secrets を更新

新しいトークンで更新:

```
https://github.com/daruma0411-crypto/pc-compat-engine/settings/secrets/actions
```

1. **TWITTER_ACCESS_TOKEN** の右側の鉛筆アイコンをクリック
   - 新しい Access Token に置き換え
   - **Update secret**

2. **TWITTER_ACCESS_SECRET** の右側の鉛筆アイコンをクリック
   - 新しい Access Token Secret に置き換え
   - **Update secret**

**注意:** 他のSecrets（API_KEY, API_SECRET, BEARER_TOKEN）は変更不要

---

### ステップ3: ローカルでテスト

#### 3.1 診断スクリプト実行

**ファイル:** `scripts/twitter_debug.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter API 権限診断スクリプト
"""

import os
import sys

try:
    import tweepy
    print(f"[INFO] tweepy version: {tweepy.__version__}")
except ImportError:
    print("[ERROR] tweepy not installed. Run: pip install tweepy")
    sys.exit(1)

# 環境変数から取得
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

print("\n=== 1. 環境変数確認 ===")
for name, value in [
    ('TWITTER_API_KEY', API_KEY),
    ('TWITTER_API_SECRET', API_SECRET),
    ('TWITTER_ACCESS_TOKEN', ACCESS_TOKEN),
    ('TWITTER_ACCESS_SECRET', ACCESS_SECRET),
    ('TWITTER_BEARER_TOKEN', BEARER_TOKEN)
]:
    print(f"{name}: {'✅ OK' if value else '❌ Missing'}")

if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, BEARER_TOKEN]):
    print("\n[ERROR] Some credentials are missing")
    sys.exit(1)

print("\n=== 2. Twitter API接続テスト ===")

try:
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )
    
    me = client.get_me()
    print(f"✅ 接続成功!")
    print(f"   アカウント: @{me.data.username}")
    print(f"   名前: {me.data.name}")
    print(f"   ID: {me.data.id}")
    
    print("\n=== 3. 権限テスト ===")
    
    # タイムライン取得（Read権限）
    try:
        tweets = client.get_users_tweets(me.data.id, max_results=5)
        print("✅ Read権限: OK")
    except Exception as e:
        print(f"❌ Read権限: Failed - {e}")
    
    # Write権限は実際に投稿しないと確認できない
    print("⚠️  Write権限: 実際の投稿で確認")
    print("   → python scripts/twitter_bot.py --dry-run で確認")
    
    print("\n=== 診断完了 ===")
    print("✅ 認証は正常です。--dry-run なしで実行してください。")
    
except tweepy.errors.Forbidden as e:
    print(f"\n❌ 403 Forbidden エラー")
    print(f"   原因: App permissions が Read Only の可能性")
    print(f"   対処: Developer Portal で Read and Write に変更")
    print(f"   詳細: {e}")
    sys.exit(1)
    
except tweepy.errors.Unauthorized as e:
    print(f"\n❌ 401 Unauthorized エラー")
    print(f"   原因: Access Token が無効")
    print(f"   対処: Access Token を再生成")
    print(f"   詳細: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ 予期しないエラー: {type(e).__name__}")
    print(f"   詳細: {e}")
    sys.exit(1)
```

**実行:**
```powershell
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# 環境変数設定（PowerShell）
$env:TWITTER_API_KEY = "..."
$env:TWITTER_API_SECRET = "..."
$env:TWITTER_ACCESS_TOKEN = "..."
$env:TWITTER_ACCESS_SECRET = "..."
$env:TWITTER_BEARER_TOKEN = "..."

# 診断実行
python scripts\twitter_debug.py
```

---

#### 3.2 DRY RUN テスト

```powershell
python scripts\twitter_bot.py --dry-run
```

**期待される出力:**
```
[INFO] tweepy version: 4.14.0
[OK] All credentials present
[INFO] Loading games data...
[OK] Loaded 445 games
[INFO] Loaded 0 history entries
[SELECTED] Elden Ring (Score: 96)
[TWEET] Generated (245 chars)
============================================================
[DRY RUN] Would post this tweet:
============================================================
【GPU互換性チェック】
Elden Ring（メタスコア: 96）

推奨GPU: NVIDIA GeForce GTX 1070
推奨CPU: Intel Core i7-8700K
RAM: 16GB

あなたのPCで動く？→ https://...
#PCゲーム #GPU互換性
============================================================
Length: 245 chars
```

---

#### 3.3 本番投稿テスト

**DRY RUNが成功したら:**

```powershell
python scripts\twitter_bot.py
```

**期待される出力:**
```
[ATTEMPT 1/3] Posting tweet...
[SUCCESS] Tweet posted! ID: 1234567890
[SUCCESS] URL: https://twitter.com/i/web/status/1234567890
[OK] History updated
```

---

### ステップ4: GitHub Actions 再実行

#### 4.1 手動実行

```
https://github.com/daruma0411-crypto/pc-compat-engine/actions
```

1. **「Twitter Bot - Auto Post」** を選択
2. **「Run workflow」** をクリック
3. **「Run workflow」** を再度クリック（確認）

#### 4.2 ログ確認

実行が完了したら、ログを確認:

1. 実行中のワークフローをクリック
2. **「Post to Twitter」** ステップを展開
3. **最後の行を確認**:
   - ✅ `[SUCCESS] Tweet posted! ID: ...` → 成功！
   - ❌ `[ERROR] 403 Forbidden...` → まだ権限問題

---

## 📋 チェックリスト

### ✅ 完了確認

- [ ] Twitter Developer Portal で App permissions = `Read and Write`
- [ ] User Authentication Settings が設定済み
- [ ] Access Token を再生成済み
- [ ] GitHub Secrets を新しいトークンで更新済み
- [ ] `python scripts/twitter_debug.py` が成功
- [ ] `python scripts/twitter_bot.py --dry-run` が成功
- [ ] `python scripts/twitter_bot.py` が成功（実際に投稿される）
- [ ] Twitter（https://twitter.com/syoyutarou）でツイート確認
- [ ] GitHub Actions 手動実行が成功
- [ ] `scripts/twitter_post_history.json` に履歴が記録される

---

## 🔧 よくあるエラーと対処法

### エラー1: 403 Forbidden

**原因:**
- App permissions が `Read` のみ
- または権限変更後にトークン再生成していない

**対処:**
1. Developer Portal → Settings → User authentication settings
2. App permissions → `Read and Write` に変更
3. Keys and tokens → Access Token を **Regenerate**
4. GitHub Secrets を更新

---

### エラー2: 401 Unauthorized

**原因:**
- Access Token が無効
- API Key が間違っている

**対処:**
1. Developer Portal → Keys and tokens
2. 全てのキーを再生成:
   - API Key & Secret → Regenerate
   - Bearer Token → Regenerate
   - Access Token & Secret → Regenerate
3. GitHub Secrets を全て更新

---

### エラー3: tweepy が古い

**症状:**
```
AttributeError: module 'tweepy' has no attribute 'Client'
```

**対処:**
```bash
pip install --upgrade tweepy
# tweepy 4.14.0 以降が必要
```

---

### エラー4: 環境変数が設定されていない

**症状:**
```
[ERROR] Missing environment variables: TWITTER_API_KEY, ...
```

**対処（ローカル）:**
```powershell
# PowerShell
$env:TWITTER_API_KEY = "your_key_here"
$env:TWITTER_API_SECRET = "your_secret_here"
# ... 他も同様
```

**対処（GitHub Actions）:**
- GitHub Secrets が正しく設定されているか確認
- Secretの名前が正確か確認（大文字小文字も含めて）

---

## 🚀 実装コマンド（Claude Code用）

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# 診断スクリプト作成
claude "TWITTER_BOT_INSTRUCTIONS.md の twitter_debug.py を作成してください"

# 既存スクリプト改善（必要な場合）
claude "scripts/twitter_bot.py を TWITTER_BOT_INSTRUCTIONS.md の twitter_bot_v2.py の内容で改善してください。
エラーハンドリングとログ出力を強化してください。"
```

---

## 📊 成功基準

### ✅ 完全成功の状態

1. **ローカルテスト:**
   ```
   python scripts/twitter_bot.py
   → [SUCCESS] Tweet posted! ID: ...
   ```

2. **Twitter確認:**
   ```
   https://twitter.com/syoyutarou
   → 新しいツイートが表示される
   ```

3. **履歴ファイル:**
   ```json
   [
     {
       "name": "Elden Ring",
       "posted_at": "2026-03-03T12:00:00",
       "tweet_text": "..."
     }
   ]
   ```

4. **GitHub Actions:**
   - ✅ 全ステップ成功
   - ✅ `Post to Twitter` ステップに `[SUCCESS]` が表示

5. **自動投稿:**
   - 12:00, 18:00, 21:00 (JST) に自動実行
   - 毎回新しいツイートが投稿される

---

## 🔐 セキュリティ注意事項

### 秘密情報の管理

- **絶対にGitにコミットしない:**
  - Access Token
  - API Key
  - Bearer Token

- **.gitignore に追加済みか確認:**
  ```
  .env
  *.json
  !package.json
  !workspace/data/**/*.json
  ```

- **ローカルテスト後:**
  ```powershell
  # 環境変数クリア
  Remove-Item Env:\TWITTER_*
  ```

---

## 📝 次のステップ（成功後）

### 1. モニタリング設定

**週1回確認:**
- GitHub Actions の実行ログ
- Twitter Analytics（インプレッション数）

### 2. 投稿内容の最適化

- 反応が良いパターンを分析
- ハッシュタグの効果測定
- 投稿時間の調整

### 3. 機能拡張（オプション）

- 画像付きツイート（ゲームスクリーンショット）
- スレッド投稿（詳細スペック解説）
- リプライ自動応答

---

以上です。トラブルシューティング頑張ってください！ 🐦
