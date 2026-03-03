#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Auto Follow Bot
ゲーム関連アカウントを自動フォローしてフォロワーを増やす

使い方:
  python twitter_auto_follow.py --dry-run  # テスト実行
  python twitter_auto_follow.py            # 本番実行
"""

import os
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# フォロー履歴ファイル
FOLLOW_HISTORY_FILE = Path(__file__).parent / 'twitter_follow_history.json'

# 設定
MAX_FOLLOWS_PER_HOUR = 15
MAX_FOLLOWS_PER_DAY = 200
TARGET_HASHTAGS = [
    '#PCゲーム',
    '#自作PC',
    '#ゲーミングPC',
    '#GPU',
    '#ゲーミングノート',
    '#PCゲーマー',
]


def load_follow_history():
    """フォロー履歴を読み込み"""
    if not FOLLOW_HISTORY_FILE.exists():
        return {'follows': [], 'last_run': None}
    with open(FOLLOW_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_follow_history(history):
    """フォロー履歴を保存"""
    with open(FOLLOW_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def search_target_users(client, hashtag, max_results=20):
    """ハッシュタグでツイートを検索し、投稿者を抽出"""
    try:
        query = f"{hashtag} -is:retweet lang:ja"
        tweets = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['author_id'],
        )
        if not tweets.data:
            return []
        return list(set(tweet.author_id for tweet in tweets.data))
    except Exception as e:
        print(f"[ERROR] ツイート検索失敗 ({hashtag}): {e}")
        return []


def should_follow(user):
    """
    フォローすべきユーザーか判定

    基準:
    - フォロワー数: 50-10,000（スパム・大物を除外）
    - フォロー率: following/followers < 3（フォロバ期待）
    - アカウント作成: 30日以上前（新規スパム除外）
    """
    metrics = user.public_metrics
    followers = metrics['followers_count']
    following = metrics['following_count']

    if followers < 50 or followers > 10000:
        return False

    if followers > 0 and (following / followers) > 3:
        return False

    created_at = user.created_at
    if created_at and created_at > datetime.now(created_at.tzinfo) - timedelta(days=30):
        return False

    return True


def main():
    import argparse
    import tweepy

    parser = argparse.ArgumentParser(description='Twitter Auto Follow Bot')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行')
    args = parser.parse_args()

    # 環境変数チェック
    missing = [k for k, v in {
        'TWITTER_API_KEY': TWITTER_API_KEY,
        'TWITTER_API_SECRET': TWITTER_API_SECRET,
        'TWITTER_ACCESS_TOKEN': TWITTER_ACCESS_TOKEN,
        'TWITTER_ACCESS_SECRET': TWITTER_ACCESS_SECRET,
        'TWITTER_BEARER_TOKEN': TWITTER_BEARER_TOKEN,
    }.items() if not v]
    if missing:
        print(f"[ERROR] 環境変数が未設定: {', '.join(missing)}")
        sys.exit(1)

    # クライアント初期化
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )

    # フォロー履歴読み込み
    history = load_follow_history()
    today = datetime.now().date().isoformat()

    # 今日のフォロー数チェック
    today_follows = [f for f in history['follows'] if f.get('date') == today]
    if len(today_follows) >= MAX_FOLLOWS_PER_DAY:
        print(f"[INFO] 本日のフォロー上限に達しました: {len(today_follows)}/{MAX_FOLLOWS_PER_DAY}")
        return

    # 1時間以内のフォロー数チェック
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_follows = []
    for f in history['follows']:
        try:
            ts = datetime.fromisoformat(f['timestamp'])
            if ts > one_hour_ago:
                recent_follows.append(f)
        except (KeyError, ValueError):
            pass

    if len(recent_follows) >= MAX_FOLLOWS_PER_HOUR:
        print(f"[INFO] 1時間のフォロー上限に達しました: {len(recent_follows)}/{MAX_FOLLOWS_PER_HOUR}")
        return

    # フォロー済みID
    followed_ids = set(str(f['user_id']) for f in history['follows'])

    # ターゲット検索
    print("[INFO] ターゲットユーザーを検索中...")
    all_user_ids = []
    for hashtag in TARGET_HASHTAGS:
        print(f"  検索中: {hashtag}")
        user_ids = search_target_users(client, hashtag, max_results=20)
        all_user_ids.extend(user_ids)
        time.sleep(2)

    # 重複除去 + フォロー済み除外
    unique_ids = list(set(str(uid) for uid in all_user_ids) - followed_ids)
    if not unique_ids:
        print("[INFO] 新しいターゲットユーザーが見つかりませんでした")
        return

    print(f"[INFO] {len(unique_ids)}人の候補ユーザーを発見")

    # ユーザー情報取得（10件ずつ）
    max_follow = min(
        MAX_FOLLOWS_PER_HOUR - len(recent_follows),
        MAX_FOLLOWS_PER_DAY - len(today_follows)
    )
    follow_count = 0

    for i in range(0, len(unique_ids), 100):
        if follow_count >= max_follow:
            break

        batch = unique_ids[i:i + 100]
        try:
            users = client.get_users(
                ids=batch,
                user_fields=['public_metrics', 'description', 'created_at']
            )
            if not users.data:
                continue

            for user in users.data:
                if follow_count >= max_follow:
                    break

                if not should_follow(user):
                    continue

                if args.dry_run:
                    print(f"[DRY RUN] フォロー対象: @{user.username} "
                          f"(フォロワー: {user.public_metrics['followers_count']})")
                    follow_count += 1
                    continue

                try:
                    client.follow_user(user.id)
                    print(f"  フォロー成功: @{user.username} "
                          f"(フォロワー: {user.public_metrics['followers_count']})")

                    history['follows'].append({
                        'user_id': str(user.id),
                        'username': user.username,
                        'date': today,
                        'timestamp': datetime.now().isoformat(),
                    })
                    follow_count += 1
                    time.sleep(15)
                except Exception as e:
                    print(f"[ERROR] フォロー失敗 @{user.username}: {e}")

        except Exception as e:
            print(f"[ERROR] ユーザー情報取得失敗: {e}")

    # 履歴保存
    history['last_run'] = datetime.now().isoformat()
    save_follow_history(history)

    print(f"\n[完了] {follow_count}人を{'フォロー対象として検出' if args.dry_run else 'フォロー'}しました")
    print(f"本日の合計: {len(today_follows) + follow_count}/{MAX_FOLLOWS_PER_DAY}")


if __name__ == '__main__':
    main()
