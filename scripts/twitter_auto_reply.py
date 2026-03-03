#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Auto Reply Bot
メンションに自動返信してエンゲージメントを高める

使い方:
  python twitter_auto_reply.py --dry-run  # テスト実行
  python twitter_auto_reply.py            # 本番実行
"""

import os
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# サイトURL
SITE_URL = 'https://pc-compat-engine-production.up.railway.app'

# 返信履歴ファイル
REPLY_HISTORY_FILE = Path(__file__).parent / 'twitter_reply_history.json'


def load_reply_history():
    """返信履歴を読み込み"""
    if not REPLY_HISTORY_FILE.exists():
        return {'replies': [], 'last_mention_id': None}
    with open(REPLY_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_reply_history(history):
    """返信履歴を保存"""
    with open(REPLY_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def extract_game_name(text):
    """テキストからゲーム名を抽出（簡易版）"""
    patterns = [
        r'(.+?)(?:は|が)?動く',
        r'(.+?)(?:の)?スペック',
        r'(.+?)(?:の)?推奨',
        r'(.+?)(?:を)?遊び',
        r'(.+?)(?:を)?プレイ',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            game_name = match.group(1).strip()
            game_name = game_name.replace('PC版', '').replace('Steam', '')
            game_name = re.sub(r'@\w+\s*', '', game_name).strip()
            if len(game_name) > 2:
                return game_name
    return None


def generate_reply(mention_text, author_username):
    """メンション内容に応じた返信を生成"""
    game_name = extract_game_name(mention_text)

    if game_name:
        slug = game_name.lower().replace(' ', '-')
        url = f"{SITE_URL}/game/{slug}"
        reply = (
            f"@{author_username} こんにちは！\n\n"
            f"{game_name}の推奨スペックと互換性診断はこちらから確認できます\n"
            f"{url}\n\n"
            f"予算別PC構成も提案しています！"
        )
    else:
        reply = (
            f"@{author_username} こんにちは！\n\n"
            f"PCゲームの推奨スペックや互換性診断はこちら\n"
            f"{SITE_URL}\n\n"
            f"443ゲームに対応しています！"
        )

    return reply


def main():
    import argparse
    import tweepy

    parser = argparse.ArgumentParser(description='Twitter Auto Reply Bot')
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

    # 返信履歴読み込み
    history = load_reply_history()
    last_mention_id = history.get('last_mention_id')

    # 自分のユーザーID取得
    try:
        me = client.get_me()
        my_id = me.data.id
        print(f"[OK] ログインユーザー: @{me.data.username} (ID: {my_id})")
    except Exception as e:
        print(f"[ERROR] ユーザー情報取得失敗: {e}")
        sys.exit(1)

    # メンション取得
    try:
        kwargs = {
            'id': my_id,
            'tweet_fields': ['author_id', 'created_at', 'text'],
            'expansions': ['author_id'],
            'max_results': 10,
        }
        if last_mention_id:
            kwargs['since_id'] = last_mention_id

        mentions = client.get_users_mentions(**kwargs)
    except Exception as e:
        print(f"[ERROR] メンション取得失敗: {e}")
        sys.exit(1)

    if not mentions.data:
        print("[INFO] 新しいメンションはありません")
        return

    # ユーザー情報をマッピング
    users_map = {}
    if mentions.includes and 'users' in mentions.includes:
        for user in mentions.includes['users']:
            users_map[str(user.id)] = user.username

    print(f"[INFO] {len(mentions.data)}件の新しいメンションを発見")

    # 返信済みID
    replied_ids = set(str(r['mention_id']) for r in history['replies'])
    reply_count = 0

    for mention in mentions.data:
        mention_id_str = str(mention.id)
        if mention_id_str in replied_ids:
            continue

        # 返信先ユーザー名
        author_username = users_map.get(str(mention.author_id), str(mention.author_id))
        reply_text = generate_reply(mention.text, author_username)

        if args.dry_run:
            print(f"\n[DRY RUN] メンション: {mention.text[:80]}...")
            print(f"[DRY RUN] 返信: {reply_text}")
            reply_count += 1
        else:
            try:
                client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=mention.id
                )
                print(f"  返信成功: @{author_username} - {mention.text[:50]}...")
                reply_count += 1
            except Exception as e:
                print(f"[ERROR] 返信失敗 (mention_id: {mention.id}): {e}")
                continue

        history['replies'].append({
            'mention_id': mention_id_str,
            'author_username': author_username,
            'timestamp': datetime.now().isoformat(),
        })

    # 最新のメンションIDを更新
    if mentions.data:
        newest_id = max(m.id for m in mentions.data)
        history['last_mention_id'] = str(newest_id)

    save_reply_history(history)
    print(f"\n[完了] {reply_count}件のメンションに{'返信候補を検出' if args.dry_run else '返信'}しました")


if __name__ == '__main__':
    main()
