#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter API 権限自動チェックスクリプト

実際のAPI呼び出しで権限を確認
"""

import os
import sys
import tweepy

# 環境変数から取得
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

def check_permissions():
    """実際のAPI呼び出しで権限を確認"""
    
    print("=== Twitter API 権限チェック ===\n")
    
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, BEARER_TOKEN]):
        print("[ERROR] 環境変数が不足しています")
        return False
    
    try:
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_SECRET
        )
        
        # 1. Read権限チェック
        print("[TEST 1] Read権限テスト...")
        me = client.get_me()
        print(f"[OK] Read権限: 正常")
        print(f"    アカウント: @{me.data.username}\n")
        
        # 2. Write権限チェック（実際には投稿しないダミーテスト）
        print("[TEST 2] Write権限テスト...")
        print("[INFO] ※実際に短いテストツイートを投稿します")
        
        # テストツイート（すぐ削除）
        test_text = "🔧 API権限テスト - このツイートは自動削除されます"
        
        try:
            response = client.create_tweet(text=test_text)
            tweet_id = response.data['id']
            print(f"[OK] Write権限: 正常")
            print(f"    テストツイートID: {tweet_id}")
            
            # すぐ削除
            print("[INFO] テストツイートを削除中...")
            client.delete_tweet(tweet_id)
            print("[OK] テストツイート削除完了\n")
            
            print("=== 結果 ===")
            print("[SUCCESS] Read and Write 権限が正常に機能しています！")
            return True
            
        except tweepy.errors.Forbidden as e:
            print(f"[ERROR] Write権限なし（403 Forbidden）")
            print(f"\n原因:")
            print(f"  App permissions が 'Read' のみになっています")
            print(f"\n対処法:")
            print(f"  1. https://developer.twitter.com/en/portal/projects-and-apps")
            print(f"  2. アプリ選択 → Settings → User authentication settings")
            print(f"  3. App permissions を 'Read and Write' に変更")
            print(f"  4. Keys and tokens → Access Token → Regenerate")
            print(f"  5. 新しいトークンでGitHub Secretsを更新")
            return False
            
    except tweepy.errors.Unauthorized as e:
        print(f"[ERROR] 401 Unauthorized")
        print(f"原因: Access Token が無効です")
        return False
        
    except Exception as e:
        print(f"[ERROR] 予期しないエラー: {e}")
        return False


if __name__ == "__main__":
    success = check_permissions()
    sys.exit(0 if success else 1)
