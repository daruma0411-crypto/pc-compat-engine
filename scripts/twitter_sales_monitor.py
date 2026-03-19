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

# 猛者アカウント（PC自作系インフルエンサー）
# これらのアカウントの投稿にいいね → フォロワーへの露出
INFLUENCER_ACCOUNTS = [
    'storm_btopc',       # STORM BTO (119K)
    'Tsukumo_eX',        # ツクモ秋葉原 (92K)
    'dospara_sapporo',   # ドスパラ札幌 (16K)
    'dospara_kago',      # ドスパラ鹿児島 (19K)
    'PK_itami',          # パソコン工房 (1K)
    'PK_Kashii',         # パソコン工房 (2K)
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
                'author_id': str(tweet.author_id),
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
    """見込み客の投稿内容に合わせた人間らしいリプライを生成"""
    text = prospect['text'].lower()
    username = prospect['username']
    
    # URLは3回に1回だけ（営業感を消す）
    add_url = random.random() < 0.33
    url_suffix = f"\n\n{SITE_URL}" if add_url else ""
    
    if any(w in text for w in ['予算', '万円', '万で']):
        replies = [
            f"@{username} その予算なら意外といい構成組めますよ👍\nGPUに全振りするのがコツです{url_suffix}",
            f"@{username} 予算内で最大限のパフォーマンス出したいですよね\n電源とケースで節約してGPUに回すのが正解{url_suffix}",
            f"@{username} いい予算感ですね！\nその金額ならRTX 4060が狙えるので、大体のゲーム快適にいけますよ{url_suffix}",
        ]
    elif any(w in text for w in ['延命', '買い替え', '交換', '新調']):
        replies = [
            f"@{username} 延命か買い替えか悩みますよね...\n個人的にはまずSSD+電源交換で様子見がコスパ良いと思います{url_suffix}",
            f"@{username} 同じ悩み抱えてる人多いですよね\nグラボだけ変えてもう2年戦うのもアリですよ{url_suffix}",
        ]
    elif any(w in text for w in ['スペック', '動く', '足りる', '推奨']):
        replies = [
            f"@{username} 推奨スペック満たしてても実際カクつくことありますよね...\n設定下げれば意外と快適になることも多いです{url_suffix}",
            f"@{username} スペック気になりますよね\n公式の推奨って結構盛ってるので、実際はもう少し低くても動きますよ{url_suffix}",
        ]
    elif any(w in text for w in ['おすすめ', 'どっち', '迷う', '悩む']):
        replies = [
            f"@{username} 迷いますよね〜\n正直どっち選んでも後悔しないレベルだと思います\n予算で決めちゃうのもアリ{url_suffix}",
            f"@{username} その2つで迷うの、めちゃくちゃわかります\n用途次第ですけど、コスパなら下位モデルで十分かと{url_suffix}",
        ]
    elif any(w in text for w in ['初めて', '初心者', '組みたい']):
        replies = [
            f"@{username} 初自作！楽しみですね🎮\nぶっちゃけプラモ感覚で組めるので思ったより簡単ですよ{url_suffix}",
            f"@{username} 自作PC沼へようこそw\n最初は不安だけど、一回組むとハマりますよ{url_suffix}",
        ]
    elif any(w in text for w in ['重い', 'カクつく', 'フレームレート', 'fps']):
        replies = [
            f"@{username} カクつくのストレスですよね...\nまず画質設定を「中」にしてみてください。意外と見た目変わらずfps倍になったりします{url_suffix}",
            f"@{username} 重いの辛いですよね\nグラボのドライバ更新で改善することもあるので試してみてください{url_suffix}",
        ]
    else:
        replies = [
            f"@{username} PC周りって奥が深いですよね\n何か困ったことあればお気軽にどうぞ👍{url_suffix}",
            f"@{username} わかります〜\nPCの悩みって尽きないですよねw{url_suffix}",
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
    liked_influencer_ids = set(history.get('liked_influencer', []))

    # === Phase 0: 猛者の投稿にいいね（露出戦略）===
    print("\n--- 猛者いいね ---")
    influencer_like_count = 0
    for account in random.sample(INFLUENCER_ACCOUNTS, min(2, len(INFLUENCER_ACCOUNTS))):
        try:
            user_result = client.get_user(username=account, user_fields=['id'])
            if not user_result.data:
                continue
            user_id = user_result.data.id
            tweets_result = client.get_users_tweets(user_id, max_results=5, tweet_fields=['public_metrics'])
            if not tweets_result.data:
                continue
            for tweet in tweets_result.data[:2]:
                tweet_key = f"inf_{tweet.id}"
                if tweet_key in liked_influencer_ids:
                    continue
                try:
                    client.like(tweet.id)
                    print(f"  ❤️ @{account} の投稿にいいね")
                    liked_influencer_ids.add(tweet_key)
                    influencer_like_count += 1
                    time.sleep(random.randint(3, 8))
                except Exception:
                    pass
        except Exception as e:
            print(f"  ⚠️ @{account}: {e}")
        time.sleep(1)
    print(f"  猛者いいね: {influencer_like_count}件")

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
        # PC無関係の投稿を除外
        text_lower = p['text'].lower()
        if 'bto' in text_lower and not any(w in text_lower for w in ['pc', 'パソコン', 'ゲーミング', '自作', 'gpu', 'グラボ']):
            continue
        # PC関連キーワードが1つもない投稿を除外
        pc_keywords = ['pc', 'パソコン', 'グラボ', 'gpu', 'cpu', 'メモリ', 'ゲーミング', '自作', 'rtx', 'geforce', 'radeon', 'steam', 'ゲーム', 'スペック']
        if not any(w in text_lower for w in pc_keywords):
            continue
        # 創作・恋愛系を除外
        exclude_keywords = ['キャラ', '推し活', 'イラスト', '漫画', '小説', '恋愛', 'cp', 'うちよそ', '夢女子', '片想い']
        if any(w in text_lower for w in exclude_keywords):
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
                    # リプライ不可 → フォローで接点作り
                    try:
                        client.follow_user(prospect.get('author_id', ''))
                        print(f"   👤 フォロー成功（リプライ403のため）")
                    except Exception:
                        print(f"   ℹ️ いいねのみ（リプライ・フォロー不可）")
                else:
                    print(f"   ❌ 送信失敗: {e}")
                    continue
            
            time.sleep(random.randint(30, 90))
        else:
            print(f"   🔍 [DRY RUN]")

        replied_ids.add(prospect['tweet_id'])
        reply_count += 1

    history['replied'] = list(replied_ids)[-500:]  # 直近500件保持
    history['liked_influencer'] = list(liked_influencer_ids)[-200:]
    history['last_run'] = datetime.now().isoformat()
    save_history(history)

    print(f"\n✅ 営業完了: {reply_count}件リプライ")


if __name__ == '__main__':
    main()
