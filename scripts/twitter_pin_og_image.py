#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter固定ツイート投稿スクリプト
OG画像を添付してツイート → ピン留め
"""
import sys
import os
import tweepy
from pathlib import Path
from dotenv import load_dotenv

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# .env読み込み
load_dotenv(Path(__file__).parent.parent / '.env')

# Twitter API認証
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')

# 画像パス
IMAGE_PATH = Path(__file__).parent.parent / "og-image.png"

def pin_og_image_tweet():
    """OG画像をツイートしてピン留め"""
    
    # v2 client (ツイート投稿用)
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
        wait_on_rate_limit=True
    )
    
    # v1.1 API (メディアアップロード用)
    auth = tweepy.OAuth1UserHandler(
        API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)
    
    print("=" * 60)
    print("Twitter固定ツイート投稿")
    print("=" * 60)
    
    # 1. メディアアップロード
    print(f"\n[1/3] 画像アップロード中... ({IMAGE_PATH.name})")
    media = api.media_upload(filename=str(IMAGE_PATH))
    print(f"✅ メディアID: {media.media_id}")
    
    # 2. ツイート投稿（画像付き）
    tweet_text = """🎮 PC自作、もう迷わない。

💬 予算とやりたいゲームを伝えるだけ
🔍 14,000件のパーツDBから最適構成を即提案
⚡ 互換性チェック自動完了

👉 https://pc-compat-engine-production.up.railway.app

#PC自作 #ゲーミングPC #RTX50 #AIショップ店員"""
    
    print(f"\n[2/3] ツイート投稿中...")
    response = client.create_tweet(
        text=tweet_text,
        media_ids=[media.media_id]
    )
    tweet_id = response.data['id']
    print(f"✅ ツイートID: {tweet_id}")
    print(f"   URL: https://twitter.com/syoyutarou/status/{tweet_id}")
    
    # 3. ピン留め
    print(f"\n[3/3] ピン留め中...")
    client.pin(tweet_id)
    print(f"✅ 固定ツイートに設定完了")
    
    print("\n" + "=" * 60)
    print("🎉 完了！プロフィールを確認してください")
    print("=" * 60)
    
    return tweet_id

if __name__ == "__main__":
    try:
        pin_og_image_tweet()
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
