#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter API 権限診断スクリプト

使い方:
1. 環境変数設定:
   $env:TWITTER_API_KEY = "..."
   $env:TWITTER_API_SECRET = "..."
   $env:TWITTER_ACCESS_TOKEN = "..."
   $env:TWITTER_ACCESS_SECRET = "..."
   $env:TWITTER_BEARER_TOKEN = "..."

2. 実行:
   python scripts\twitter_debug.py
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
credentials = {
    'TWITTER_API_KEY': API_KEY,
    'TWITTER_API_SECRET': API_SECRET,
    'TWITTER_ACCESS_TOKEN': ACCESS_TOKEN,
    'TWITTER_ACCESS_SECRET': ACCESS_SECRET,
    'TWITTER_BEARER_TOKEN': BEARER_TOKEN
}

all_present = True
for name, value in credentials.items():
    status = '[OK]' if value else '[MISSING]'
    print(f"{status} {name}")
    if not value:
        all_present = False

if not all_present:
    print("\n[ERROR] Some credentials are missing")
    print("Set them with: $env:VARIABLE_NAME = \"value\"")
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
    print(f"[SUCCESS] 接続成功!")
    print(f"   アカウント: @{me.data.username}")
    print(f"   名前: {me.data.name}")
    print(f"   ID: {me.data.id}")
    
    print("\n=== 3. 権限テスト ===")
    
    # タイムライン取得（Read権限）
    try:
        tweets = client.get_users_tweets(me.data.id, max_results=5)
        print("[OK] Read権限: 正常")
        if tweets.data:
            print(f"   最新ツイート: {len(tweets.data)}件取得")
    except Exception as e:
        print(f"[ERROR] Read権限: 失敗 - {e}")
    
    # Write権限は実際に投稿しないと確認できない
    print("[INFO] Write権限: 実際の投稿で確認が必要")
    print("   → python scripts\\twitter_bot.py --dry-run で確認")
    
    print("\n=== 診断完了 ===")
    print("[SUCCESS] 認証は正常です")
    print("次のステップ: python scripts\\twitter_bot.py --dry-run")
    
except tweepy.errors.Forbidden as e:
    print(f"\n[ERROR] 403 Forbidden エラー")
    print(f"原因: App permissions が Read Only の可能性")
    print(f"対処法:")
    print(f"  1. https://developer.twitter.com/en/portal/projects-and-apps")
    print(f"  2. アプリを選択 → Settings → User authentication settings")
    print(f"  3. App permissions を 'Read and Write' に変更")
    print(f"  4. Keys and tokens → Access Token → Regenerate")
    print(f"  5. GitHub Secrets を新しいトークンで更新")
    print(f"\nエラー詳細: {e}")
    sys.exit(1)
    
except tweepy.errors.Unauthorized as e:
    print(f"\n[ERROR] 401 Unauthorized エラー")
    print(f"原因: Access Token が無効")
    print(f"対処法:")
    print(f"  1. https://developer.twitter.com/en/portal/projects-and-apps")
    print(f"  2. アプリを選択 → Keys and tokens")
    print(f"  3. Access Token → Regenerate")
    print(f"  4. GitHub Secrets を新しいトークンで更新")
    print(f"\nエラー詳細: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n[ERROR] 予期しないエラー: {type(e).__name__}")
    print(f"詳細: {e}")
    sys.exit(1)
