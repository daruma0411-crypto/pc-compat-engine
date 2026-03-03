#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Bot for PC Compatibility Checker
ゲーム互換性情報を自動投稿するTwitterボット

使い方:
  python twitter_bot.py --dry-run  # テスト実行（実際に投稿しない）
  python twitter_bot.py            # 本番投稿
"""

import json
import random
import os
import sys
from datetime import datetime
from pathlib import Path

# Twitter API設定（環境変数から取得）
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# サイトURL
SITE_URL = 'https://pc-compat-engine-production.up.railway.app'

# ゲームデータパス
GAMES_DATA_PATH = Path(__file__).parent.parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'

# 投稿履歴ファイル（同じゲームを連続投稿しない）
HISTORY_FILE = Path(__file__).parent / 'twitter_post_history.json'


def load_games():
    """ゲームデータを読み込み"""
    games = []
    with open(GAMES_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                games.append(json.loads(line))
    return games


def load_history():
    """投稿履歴を読み込み"""
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_history(history):
    """投稿履歴を保存"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def select_game(games, history, max_history=50):
    """
    投稿するゲームを選択
    - 推奨スペックが記載されているゲームを優先
    - 最近投稿したゲームは除外
    - メタスコアが高いゲームを優先
    """
    # 有効なゲーム（推奨スペックあり）を抽出
    valid_games = [
        g for g in games
        if g.get('specs', {}).get('recommended', {}).get('gpu')
    ]

    # 最近投稿したゲームを除外
    recent_names = set(h['name'] for h in history[-max_history:])
    candidates = [g for g in valid_games if g['name'] not in recent_names]

    if not candidates:
        # 全ゲーム投稿済みの場合は履歴をリセット
        candidates = valid_games

    # メタスコアでソート（高い順）
    candidates_with_score = [
        g for g in candidates
        if g.get('metacritic_score') and g['metacritic_score'] > 0
    ]
    candidates_with_score.sort(key=lambda x: x.get('metacritic_score', 0), reverse=True)

    # 上位30%からランダム選択（多様性のため）
    top_count = max(1, len(candidates_with_score) // 3)
    return random.choice(candidates_with_score[:top_count])


def game_slug(game_name):
    """ゲーム名からURL用スラッグを生成（sitemapのパターンに合わせる）"""
    slug = game_name.lower()
    slug = slug.replace(' ', '-').replace(':', '').replace('™', '')
    slug = slug.replace('®', '').replace('(', '').replace(')', '')
    slug = slug.replace('[', '').replace(']', '').replace('/', '')
    slug = slug.replace('\'', '').replace('"', '').replace(',', '')
    slug = slug.replace('--', '-').replace('--', '-')  # 連続ハイフン除去
    return slug.strip('-')


def format_spec(spec):
    """スペック情報を整形"""
    if isinstance(spec, list):
        return spec[0].replace('™', '').replace('®', '').replace('(R)', '').strip()
    return str(spec).replace('™', '').replace('®', '').replace('(R)', '').strip()


def generate_tweet_patterns(game):
    """ツイート文のパターンを生成（複数パターンからランダム選択）"""
    name = game['name']
    slug = game_slug(name)
    url = f"{SITE_URL}/game/{slug}"

    rec = game.get('specs', {}).get('recommended', {})
    gpu = format_spec(rec.get('gpu', ['不明'])) if rec.get('gpu') else '不明'
    cpu = format_spec(rec.get('cpu', ['不明'])) if rec.get('cpu') else '不明'
    ram = rec.get('ram_gb', '不明')

    # メタスコア
    meta_score = game.get('metacritic_score')
    meta_text = f"（メタスコア: {meta_score}）" if meta_score and meta_score > 0 else ""

    patterns = [
        # パターン1: GPU互換性強調
        f"【GPU互換性チェック】\n"
        f"{name}{meta_text}\n\n"
        f"推奨GPU: {gpu}\n"
        f"推奨CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"あなたのPCで動く？→ {url}\n"
        f"#PCゲーム #GPU互換性",

        # パターン2: 質問形式
        f"「{name}」やりたいけど、自分のPCで動くか不安...\n\n"
        f"推奨スペック:\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"無料で互換性チェック！→ {url}\n"
        f"#PCゲーム #スペック確認",

        # パターン3: シンプル紹介
        f"{name}\n"
        f"推奨スペック一覧\n\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"詳細 → {url}\n"
        f"#PCゲーム #自作PC",

        # パターン4: トラブルシューティング風
        f"「{name}がカクつく...」\n\n"
        f"推奨スペックをチェック！\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"互換性診断ツール→ {url}\n"
        f"#PCゲーム #動作環境",
    ]

    return random.choice(patterns)


def post_tweet(text, dry_run=True):
    """ツイートを投稿（DRY RUNモードではコンソール出力のみ）"""
    if dry_run:
        print("=" * 60)
        print("[DRY RUN] 以下のツイートを投稿します:")
        print("=" * 60)
        print(text)
        print("=" * 60)
        print(f"文字数: {len(text)}")
        return True

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
        return False

    # Twitter API v2での投稿
    try:
        import tweepy
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
        response = client.create_tweet(text=text)
        tweet_id = response.data['id']
        print(f"[SUCCESS] ツイート投稿成功! ID: {tweet_id}")
        print(f"[SUCCESS] URL: https://twitter.com/i/web/status/{tweet_id}")
        return True
    except tweepy.errors.Forbidden as e:
        print(f"[ERROR] 403 Forbidden: App permissions が Read Only の可能性")
        print(f"        対処: Developer Portal で Read and Write に変更後、Access Token を再生成")
        print(f"        詳細: {e}")
        return False
    except tweepy.errors.Unauthorized as e:
        print(f"[ERROR] 401 Unauthorized: Access Token が無効")
        print(f"        対処: Developer Portal で Access Token を再生成")
        print(f"        詳細: {e}")
        return False
    except Exception as e:
        error_str = str(e)
        if '402' in error_str:
            print(f"[ERROR] 402 Payment Required: Twitter API のクレジット不足")
            print(f"        対処: https://developer.twitter.com/en/portal/subscription でプランを確認")
            print(f"        Free Tier の月間500ツイート上限に達した可能性があります")
        else:
            print(f"[ERROR] ツイート投稿失敗: {type(e).__name__}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='PC Compatibility Checker Twitter Bot')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行（実際に投稿しない）')
    args = parser.parse_args()

    # ゲームデータ読み込み
    print("ゲームデータ読み込み中...")
    games = load_games()
    print(f"[OK] {len(games)}ゲームを読み込みました")

    # 投稿履歴読み込み
    history = load_history()
    print(f"[履歴] 投稿履歴: {len(history)}件")

    # ゲーム選択
    selected_game = select_game(games, history)
    print(f"[選択] 選択ゲーム: {selected_game['name']}")

    # ツイート文生成
    tweet_text = generate_tweet_patterns(selected_game)

    # 投稿
    success = post_tweet(tweet_text, dry_run=args.dry_run)

    if success and not args.dry_run:
        # 履歴に追加
        history.append({
            'name': selected_game['name'],
            'posted_at': datetime.now().isoformat(),
            'tweet_text': tweet_text
        })
        save_history(history)
        print("[OK] 投稿履歴を更新しました")

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
