#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter営業モニター（OpenClaw Heartbeat連携）
見込み客のツイートを検索 → 分析 → リプライ送信

使い方:
  python twitter_sales_monitor.py           # 本番実行
  python twitter_sales_monitor.py --dry-run # テスト実行
"""
import os
import sys
import json
import random
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

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

SITE_URL = 'https://pc-jisaku.com'
HISTORY_FILE = Path(__file__).parent / 'twitter_sales_history.json'

# 検索キーワード（見込み客発見用）
SEARCH_QUERIES = [
    "自作PC 構成 相談",
    "ゲーミングPC 予算",
    "グラボ 買い替え 迷う",
    "PC 延命 買い替え",
    "BTO 検討",
    "スペック 足りる",
    "GPU おすすめ 2026",
    "RTX 4060 4070 どっち",
    "PC 組みたい",
    "自作PC 初めて",
]


def load_history():
    if not HISTORY_FILE.exists():
        return {'replied': [], 'last_run': None}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def search_prospects(client, query, max_results=10):
    """見込み客のツイートを検索"""
    try:
        response = client.search_recent_tweets(
            query=f'{query} -is:retweet -is:reply lang:ja',
            max_results=max_results,
            tweet_fields=['author_id', 'text', 'created_at', 'public_metrics'],
            user_fields=['username', 'name', 'public_metrics'],
            expansions=['author_id']
        )
        if not response.data:
            return []
        
        users = {u.id: u for u in (response.includes.get('users', []) or [])}
        results = []
        for tweet in response.data:
            user = users.get(tweet.author_id)
            results.append({
                'tweet_id': str(tweet.id),
                'text': tweet.text,
                'username': user.username if user else 'unknown',
                'name': user.name if user else 'unknown',
                'followers': user.public_metrics.get('followers_count', 0) if user and user.public_metrics else 0,
                'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                'created_at': str(tweet.created_at),
            })
        return results
    except Exception as e:
        print(f"  ⚠️ 検索エラー ({query}): {e}")
        return []


def generate_reply(prospect):
    """見込み客の投稿内容に合わせたリプライを生成"""
    text = prospect['text'].lower()
    username = prospect['username']
    
    # キーワードマッチでリプライパターンを選択
    if any(w in text for w in ['予算', '万円', '万で']):
        replies = [
            f"@{username} 予算に合わせた最適構成、こちらで診断できますよ！\n14,000件以上のパーツDBから提案します\n\n{SITE_URL}",
            f"@{username} 予算内で最大パフォーマンスの構成、気になりませんか？\nAIが最適パーツを提案↓\n\n{SITE_URL}",
        ]
    elif any(w in text for w in ['延命', '買い替え', '交換', '新調']):
        replies = [
            f"@{username} 今のPCでどこまで戦えるか、こちらで診断できますよ！\nパーツ交換の優先順位もわかります\n\n{SITE_URL}",
            f"@{username} 延命 vs 買い替え、迷いますよね\nまず今の構成で何が動くかチェック↓\n\n{SITE_URL}",
        ]
    elif any(w in text for w in ['スペック', '動く', '足りる', '推奨']):
        replies = [
            f"@{username} そのゲームが動くか、こちらで即チェックできますよ！\n推奨スペックとの比較も一目瞭然\n\n{SITE_URL}",
        ]
    elif any(w in text for w in ['おすすめ', 'どっち', '迷う', '悩む']):
        replies = [
            f"@{username} パーツ選びで迷ったら、こちらで互換性チェックしてみてください！\n14,000件のDBから最適解を提案します\n\n{SITE_URL}",
        ]
    elif any(w in text for w in ['初めて', '初心者', '組みたい']):
        replies = [
            f"@{username} 初自作PC、ワクワクしますね！\n予算と用途を入れるだけで最適構成を提案してくれるツールありますよ↓\n\n{SITE_URL}",
        ]
    else:
        replies = [
            f"@{username} PC構成の互換性チェック、こちらでできますよ！\nAIショップ店員が最適構成を提案します\n\n{SITE_URL}",
        ]
    
    return random.choice(replies)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    import tweepy
    
    # Bearer TokenのURLエンコードを解除
    bearer = os.environ.get('TWITTER_BEARER_TOKEN', '')
    if '%3D' in bearer or '%2F' in bearer:
        import urllib.parse
        bearer = urllib.parse.unquote(bearer)
    
    client = tweepy.Client(
        consumer_key=os.environ.get('TWITTER_API_KEY'),
        consumer_secret=os.environ.get('TWITTER_API_SECRET'),
        access_token=os.environ.get('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.environ.get('TWITTER_ACCESS_SECRET'),
        bearer_token=bearer if bearer else None
    )

    # SSL証明書エラー回避（企業プロキシ環境対策）
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    os.environ['CURL_CA_BUNDLE'] = ''
    
    import requests
    old_request = requests.Session.request
    def patched_request(self, *args, **kwargs):
        kwargs['verify'] = False
        return old_request(self, *args, **kwargs)
    requests.Session.request = patched_request
    
    # 自分のユーザーID取得
    my_username = 'syoyutarou'  # 固定（API呼び出し節約）
    print(f"🤖 @{my_username} で営業開始")

    history = load_history()
    replied_ids = set(history.get('replied', []))

    # ランダムに3つのクエリを選択（レート制限対策）
    queries = random.sample(SEARCH_QUERIES, min(3, len(SEARCH_QUERIES)))
    
    all_prospects = []
    for query in queries:
        print(f"\n🔍 検索: {query}")
        prospects = search_prospects(client, query, max_results=10)
        print(f"  → {len(prospects)}件発見")
        all_prospects.extend(prospects)
        time.sleep(1)

    # フィルタリング
    filtered = []
    for p in all_prospects:
        # 既にリプライ済み
        if p['tweet_id'] in replied_ids:
            continue
        # 自分自身
        if p['username'] == my_username:
            continue
        # フォロワー少なすぎ（Bot排除）
        if p['followers'] < 5:
            continue
        # 企業・宣伝系排除
        if any(w in p['text'].lower() for w in ['pr', '広告', 'プレゼント', 'キャンペーン', 'airdrop', '円から購入', 'セール開催', '開催中', '❣']):
            continue
        # PC無関係のBTO排除（不動産等）
        text_lower = p['text'].lower()
        if 'bto' in text_lower and not any(w in text_lower for w in ['pc', 'パソコン', 'ゲーミング', '自作', 'gpu', 'グラボ']):
            continue
        filtered.append(p)

    print(f"\n📋 フィルタ後: {len(filtered)}件")

    # 最大3件リプライ
    reply_count = 0
    max_replies = 3

    for prospect in filtered[:max_replies * 2]:  # 余裕を持って候補を確保
        if reply_count >= max_replies:
            break

        reply_text = generate_reply(prospect)
        
        print(f"\n👤 @{prospect['username']} (フォロワー{prospect['followers']})")
        print(f"   投稿: {prospect['text'][:80]}...")
        print(f"   リプライ: {reply_text[:80]}...")

        if not args.dry_run:
            # Step 1: いいね（接点作り）
            try:
                client.like(prospect['tweet_id'])
                print(f"   ❤️ いいね成功")
            except Exception as e:
                print(f"   ⚠️ いいね失敗: {e}")
            
            time.sleep(random.randint(5, 15))
            
            # Step 2: リプライ試行（403なら引用RTにフォールバック）
            try:
                client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=prospect['tweet_id']
                )
                print(f"   ✅ リプライ成功！")
            except Exception as e:
                if '403' in str(e):
                    # 引用RTにフォールバック
                    try:
                        tweet_url = f"https://x.com/i/status/{prospect['tweet_id']}"
                        quote_text = reply_text.replace(f"@{prospect['username']} ", "")
                        if len(quote_text) > 240:
                            quote_text = quote_text[:237] + "..."
                        client.create_tweet(
                            text=quote_text,
                            quote_tweet_id=prospect['tweet_id']
                        )
                        print(f"   🔄 引用RT成功！（リプライ403のためフォールバック）")
                    except Exception as e2:
                        print(f"   ❌ 引用RTも失敗: {e2}")
                        continue
                else:
                    print(f"   ❌ 送信失敗: {e}")
                    continue
            
            time.sleep(random.randint(30, 90))
        else:
            print(f"   🔍 [DRY RUN]")

        replied_ids.add(prospect['tweet_id'])
        reply_count += 1

    history['replied'] = list(replied_ids)[-500:]  # 直近500件保持
    history['last_run'] = datetime.now().isoformat()
    save_history(history)

    print(f"\n✅ 営業完了: {reply_count}件リプライ")


if __name__ == '__main__':
    main()
