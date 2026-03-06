#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter 削除&再投稿スクリプト
指定ツイートを削除し、同じゲームを正しいURLで再投稿する
"""

import json
import os
import sys
import random
from pathlib import Path
from datetime import datetime

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

SITE_URL = 'https://pc-compat-engine-production.up.railway.app'
GAMES_DATA_PATH = Path(__file__).parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'
HISTORY_FILE = Path(__file__).parent / 'twitter_post_history.json'


def get_twitter_client():
    """Twitter APIクライアントを取得"""
    import tweepy
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    return client


def delete_tweet(tweet_id, dry_run=False):
    """ツイートを削除"""
    if dry_run:
        print(f"[DRY RUN] ツイート削除: {tweet_id}")
        return True

    client = get_twitter_client()
    try:
        client.delete_tweet(tweet_id)
        print(f"[SUCCESS] ツイート削除成功: {tweet_id}")
        return True
    except Exception as e:
        print(f"[ERROR] ツイート削除失敗: {e}")
        return False


def find_game(appid):
    """appidでゲームを検索"""
    with open(GAMES_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                game = json.loads(line)
                game_appid = game.get('steam_appid') or game.get('appid')
                if str(game_appid) == str(appid):
                    return game
    return None


def format_spec(spec):
    """スペック情報を整形"""
    if isinstance(spec, list):
        return spec[0].replace('™', '').replace('®', '').replace('(R)', '').strip()
    return str(spec).replace('™', '').replace('®', '').replace('(R)', '').strip()


def game_slug(game_name):
    """ゲーム名からURL用スラッグを生成"""
    slug = game_name.lower()
    slug = slug.replace(' ', '-').replace(':', '').replace('™', '')
    slug = slug.replace('®', '').replace('(', '').replace(')', '')
    slug = slug.replace('[', '').replace(']', '').replace('/', '')
    slug = slug.replace('\'', '').replace('"', '').replace(',', '')
    slug = slug.replace('・', '').replace('·', '').replace('‐', '-')
    slug = slug.replace('--', '-').replace('--', '-')
    return slug.strip('-')


def generate_repost_tweet(game):
    """再投稿用ツイート文を生成"""
    import urllib.parse
    name = game['name']
    slug = game_slug(name)
    encoded_slug = urllib.parse.quote(slug)
    url = f"{SITE_URL}/game/{encoded_slug}"

    rec = game.get('specs', {}).get('recommended', {})
    gpu = format_spec(rec.get('gpu', ['不明'])) if rec.get('gpu') else '不明'
    cpu = format_spec(rec.get('cpu', ['不明'])) if rec.get('cpu') else '不明'
    ram = rec.get('ram_gb', '不明')
    gpu_short = gpu.replace('GeForce ', '').replace('NVIDIA ', '').replace('Radeon ', '')

    patterns = [
        (
            f"{name}、薄型ノートじゃキツイよな\n"
            f"最低でも{gpu_short}相当は欲しい\n\n"
            f"{url}\n\n"
            f"#ペルソナ5ロイヤル #ゲーミングノート #PCゲーム",
            'notebook'
        ),
        (
            f"{name}やりてぇんだけど\n"
            f"{gpu_short}あれば動くかな？\n\n"
            f"とりあえず調べてみた↓\n{url}\n\n"
            f"#ペルソナ5ロイヤル #PCゲーム #Steam",
            'casual'
        ),
        (
            f"「{name}」自分のPCで動くか不安...\n\n"
            f"推奨スペック:\n"
            f"GPU: {gpu_short}\n"
            f"CPU: {cpu}\n"
            f"RAM: {ram}GB\n\n"
            f"無料で互換性チェック！→ {url}\n\n"
            f"#ペルソナ5ロイヤル #PCゲーム #スペック確認",
            'question'
        ),
    ]

    text, pattern_type = random.choice(patterns)
    return text


def post_tweet(text, dry_run=False, image_path=None):
    """ツイート投稿"""
    if dry_run:
        print(f"[DRY RUN] 投稿内容:\n{text}")
        if image_path:
            print(f"[DRY RUN] 画像: {image_path}")
        return True

    import tweepy
    client = get_twitter_client()

    try:
        media_ids = None
        if image_path and os.path.exists(str(image_path)):
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY, TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
            )
            api_v1 = tweepy.API(auth)
            media = api_v1.media_upload(str(image_path))
            media_ids = [media.media_id]
            print(f"[OK] 画像アップロード成功: media_id={media.media_id}")

        if media_ids:
            response = client.create_tweet(text=text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=text)

        tweet_id = response.data['id']
        print(f"[SUCCESS] ツイート投稿成功! ID: {tweet_id}")
        print(f"[SUCCESS] URL: https://twitter.com/i/web/status/{tweet_id}")
        return True
    except Exception as e:
        print(f"[ERROR] ツイート投稿失敗: {e}")
        return False


def update_history(game, tweet_text):
    """投稿履歴を更新（古いエントリを削除して新しいエントリを追加）"""
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

    # 同じゲームの最新エントリを削除
    game_name = game['name']
    new_history = [h for h in history if h['name'] != game_name]
    # 新しいエントリを追加
    new_history.append({
        'name': game_name,
        'posted_at': datetime.now().isoformat(),
        'tweet_text': tweet_text,
        'has_image': True,
    })

    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
    print("[OK] 投稿履歴を更新しました")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Twitter Delete & Repost')
    parser.add_argument('--delete-id', required=True, help='削除するツイートのID')
    parser.add_argument('--game-appid', required=True, help='再投稿するゲームのappid')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行')
    args = parser.parse_args()

    # 1. ゲーム情報取得
    game = find_game(args.game_appid)
    if not game:
        print(f"[ERROR] appid {args.game_appid} のゲームが見つかりません")
        sys.exit(1)
    print(f"[OK] ゲーム: {game['name']} (appid: {args.game_appid})")

    # 2. ツイート削除
    print(f"\n--- ツイート削除 ---")
    if not delete_tweet(args.delete_id, dry_run=args.dry_run):
        sys.exit(1)

    # 3. メタスコア画像生成
    image_path = None
    meta_score = game.get('metacritic_score')
    if meta_score and meta_score > 0:
        try:
            from generate_metacritic_image import generate_metacritic_image
            image_dir = Path(__file__).parent / 'temp_images'
            image_dir.mkdir(exist_ok=True)
            safe_name = game['name'].replace(' ', '_').replace('/', '_')
            image_path = str(image_dir / f"meta_{safe_name}.png")
            generate_metacritic_image(game['name'], meta_score, image_path)
            print(f"[OK] メタスコア画像生成: {image_path}")
        except Exception as e:
            print(f"[WARN] 画像生成スキップ: {e}")
            image_path = None

    # 4. 再投稿
    print(f"\n--- 再投稿 ---")
    tweet_text = generate_repost_tweet(game)
    if not post_tweet(tweet_text, dry_run=args.dry_run, image_path=image_path):
        sys.exit(1)

    # 5. 履歴更新
    if not args.dry_run:
        update_history(game, tweet_text)

    print("\n[DONE] 削除&再投稿完了!")


if __name__ == '__main__':
    main()
