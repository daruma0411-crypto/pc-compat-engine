#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw営業Bot - Twitter直接リプライ
相手の投稿を分析して個別アドバイスをリプライする

使い方:
  python twitter_reply_direct.py --tweet-url "https://x.com/user/status/123" --message "リプライ内容"
  python twitter_reply_direct.py --tweet-id 123456789 --message "リプライ内容"
  python twitter_reply_direct.py --dry-run --tweet-id 123 --message "テスト"
"""
import os
import sys
import argparse
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# .envから読み込み
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

# SSL証明書エラー回避（企業プロキシ対策）
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
_old_request = requests.Session.request
def _patched_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return _old_request(self, *args, **kwargs)
requests.Session.request = _patched_request

TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')


def extract_tweet_id(url_or_id):
    """URLまたはIDからツイートIDを抽出"""
    if url_or_id.isdigit():
        return url_or_id
    match = re.search(r'/status/(\d+)', url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def send_reply(tweet_id, message, dry_run=False):
    """ツイートにリプライを送信"""
    import tweepy
    
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    print(f"📝 リプライ内容:")
    print(f"   対象ツイート: {tweet_id}")
    print(f"   メッセージ: {message}")
    print(f"   文字数: {len(message)}")
    
    if len(message) > 280:
        print(f"⚠️ 280文字を超えています（{len(message)}文字）")
        return False
    
    if dry_run:
        print("🔍 [DRY RUN] 実際には送信しません")
        return True
    
    try:
        response = client.create_tweet(
            text=message,
            in_reply_to_tweet_id=tweet_id
        )
        print(f"✅ リプライ送信成功！")
        print(f"   Tweet ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"❌ リプライ送信失敗: {e}")
        return False


def get_tweet_info(tweet_id):
    """ツイートの情報を取得"""
    import tweepy
    
    client = tweepy.Client(
        bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
    )
    
    try:
        response = client.get_tweet(
            tweet_id,
            tweet_fields=['author_id', 'text', 'created_at', 'public_metrics'],
            user_fields=['username', 'name'],
            expansions=['author_id']
        )
        if response.data:
            tweet = response.data
            user = response.includes['users'][0] if response.includes else None
            print(f"📌 ツイート情報:")
            print(f"   ユーザー: @{user.username if user else '不明'}")
            print(f"   内容: {tweet.text[:100]}...")
            print(f"   いいね: {tweet.public_metrics.get('like_count', 0)}")
            return tweet, user
    except Exception as e:
        print(f"⚠️ ツイート情報取得失敗: {e}")
    return None, None


def main():
    parser = argparse.ArgumentParser(description='Twitter直接リプライ')
    parser.add_argument('--tweet-url', type=str, help='ツイートURL')
    parser.add_argument('--tweet-id', type=str, help='ツイートID')
    parser.add_argument('--message', type=str, required=True, help='リプライメッセージ')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行')
    args = parser.parse_args()
    
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        print("❌ Twitter API認証情報が不足しています")
        print("   .envファイルを確認してください")
        sys.exit(1)
    
    tweet_ref = args.tweet_url or args.tweet_id
    if not tweet_ref:
        print("❌ --tweet-url または --tweet-id を指定してください")
        sys.exit(1)
    
    tweet_id = extract_tweet_id(tweet_ref)
    
    # ツイート情報を取得
    get_tweet_info(tweet_id)
    
    # リプライ送信
    success = send_reply(tweet_id, args.message, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
