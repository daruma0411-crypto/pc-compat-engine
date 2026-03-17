#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
いいねしてくれた人にお礼リプライ + シェアお願い
岩下さんの成功パターン:「相手が好感 → ひろめてー → リポスト」を自動化

使い方:
  python twitter_like_thanker.py --dry-run  # テスト実行
  python twitter_like_thanker.py            # 本番実行
"""
import os
import sys
import json
import random
import time
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

SITE_URL = os.getenv('SITE_URL', 'https://pc-jisaku.com')
THANKED_FILE = Path(__file__).parent / 'twitter_thanked_users.json'
MY_USER_ID = os.getenv('TWITTER_USER_ID', '')  # 自分のユーザーID


def load_thanked():
    if not THANKED_FILE.exists():
        return {'users': {}, 'last_check': None}
    with open(THANKED_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_thanked(data):
    with open(THANKED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_recent_tweets(client, user_id, max_results=5):
    """自分の最近のツイートを取得"""
    try:
        response = client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            tweet_fields=['public_metrics', 'created_at']
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ ツイート取得エラー: {e}")
        return []


def get_liking_users(client, tweet_id):
    """ツイートにいいねしたユーザーを取得"""
    try:
        response = client.get_liking_users(
            id=tweet_id,
            user_fields=['username', 'name', 'public_metrics']
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ いいねユーザー取得エラー: {e}")
        return []


def generate_thank_reply(username):
    """お礼 + シェアお願いリプライを生成"""
    patterns = [
        f"@{username} ありがとうございます！🙏\n参考になったらシェアしてもらえると嬉しいです✨",
        f"@{username} いいねありがとう！\nPC仲間にも教えてあげてね🎮",
        f"@{username} ありがとう！広まれ〜🙏",
        f"@{username} 反応嬉しい！\n自作PC検討中の友達にもぜひ💪",
        f"@{username} ありがとうございます！\nスペック気になる人にRT頼みます🙏",
    ]
    return random.choice(patterns)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("❌ Twitter API認証情報が不足")
        sys.exit(1)

    import tweepy
    
    # v2 Client
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
        bearer_token=TWITTER_BEARER_TOKEN
    )

    # 自分のユーザーIDを取得
    me = client.get_me()
    if not me or not me.data:
        print("❌ 自分のユーザー情報を取得できません")
        sys.exit(1)
    my_id = me.data.id
    print(f"[INFO] ユーザー: @{me.data.username} (ID: {my_id})")

    thanked = load_thanked()
    
    # 最近のツイートを取得
    tweets = get_recent_tweets(client, my_id, max_results=5)
    if not tweets:
        print("[INFO] 最近のツイートがありません")
        return

    reply_count = 0
    max_replies = 3  # 1回の実行で最大3件

    for tweet in tweets:
        tweet_id = tweet.id
        metrics = tweet.public_metrics or {}
        like_count = metrics.get('like_count', 0)
        
        if like_count == 0:
            continue
        
        print(f"\n[ツイート] ID:{tweet_id} いいね:{like_count}")
        
        # いいねしたユーザーを取得
        liking_users = get_liking_users(client, tweet_id)
        
        for user in liking_users:
            user_key = f"{tweet_id}_{user.id}"
            
            # 既にお礼済みならスキップ
            if user_key in thanked['users']:
                continue
            
            # 自分自身はスキップ
            if user.id == my_id:
                continue
            
            # フォロワー数が少なすぎるBot的アカウントはスキップ
            followers = user.public_metrics.get('followers_count', 0) if user.public_metrics else 0
            if followers < 5:
                print(f"  [SKIP] @{user.username} (フォロワー{followers})")
                continue
            
            reply_text = generate_thank_reply(user.username)
            print(f"  [リプライ] @{user.username}: {reply_text}")
            
            if not args.dry_run:
                try:
                    client.create_tweet(
                        text=reply_text,
                        in_reply_to_tweet_id=tweet_id
                    )
                    print(f"  [OK] リプライ送信成功")
                    time.sleep(random.randint(30, 90))  # レート制限対策
                except Exception as e:
                    print(f"  [ERROR] リプライ失敗: {e}")
                    continue
            
            thanked['users'][user_key] = {
                'username': user.username,
                'thanked_at': datetime.now().isoformat()
            }
            reply_count += 1
            
            if reply_count >= max_replies:
                break
        
        if reply_count >= max_replies:
            break
    
    thanked['last_check'] = datetime.now().isoformat()
    save_thanked(thanked)
    print(f"\n✅ お礼リプライ: {reply_count}件")


if __name__ == '__main__':
    main()
