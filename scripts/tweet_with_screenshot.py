#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サイトのスクショを撮ってツイートに添付する
"""
import os
import sys
import subprocess
import argparse
import tempfile
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# .envから読み込み
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

import urllib3
urllib3.disable_warnings()
import requests
_old = requests.Session.request
def _patched(self, *a, **kw):
    kw['verify'] = False
    return _old(self, *a, **kw)
requests.Session.request = _patched

CHROME_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
SITE_URL = 'https://pc-jisaku.com'


def take_screenshot(url, output_path, width=1280, height=800):
    """ヘッドレスChromeでスクショ"""
    subprocess.run(
        [CHROME_PATH, '--headless', f'--screenshot={output_path}',
         f'--window-size={width},{height}', url],
        capture_output=True, timeout=30
    )
    return Path(output_path).exists()


def tweet_with_image(text, image_path):
    """画像付きツイート"""
    import tweepy
    
    auth = tweepy.OAuth1UserHandler(
        os.environ['TWITTER_API_KEY'],
        os.environ['TWITTER_API_SECRET'],
        os.environ['TWITTER_ACCESS_TOKEN'],
        os.environ['TWITTER_ACCESS_SECRET']
    )
    api_v1 = tweepy.API(auth)
    
    media = api_v1.media_upload(str(image_path))
    
    client = tweepy.Client(
        consumer_key=os.environ['TWITTER_API_KEY'],
        consumer_secret=os.environ['TWITTER_API_SECRET'],
        access_token=os.environ['TWITTER_ACCESS_TOKEN'],
        access_token_secret=os.environ['TWITTER_ACCESS_SECRET']
    )
    
    result = client.create_tweet(text=text, media_ids=[media.media_id])
    return result.data['id']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=SITE_URL, help='スクショするURL')
    parser.add_argument('--message', required=True, help='ツイート本文')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    # スクショ撮影
    ss_path = tempfile.mktemp(suffix='.png')
    print(f"📸 スクショ撮影: {args.url}")
    if not take_screenshot(args.url, ss_path):
        print("❌ スクショ撮影失敗")
        sys.exit(1)
    
    size = os.path.getsize(ss_path)
    print(f"✅ スクショOK ({size:,} bytes)")
    
    if args.dry_run:
        print(f"🔍 [DRY RUN] {args.message[:80]}...")
        return
    
    tweet_id = tweet_with_image(args.message, ss_path)
    print(f"✅ 投稿完了! ID: {tweet_id}")
    
    os.unlink(ss_path)


if __name__ == '__main__':
    main()
