#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Analytics取得スクリプト
- 最近の投稿のインプレッション・エンゲージメントを取得
- 日次でKPIを記録
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Twitter API設定
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

def get_recent_tweets_analytics():
    """最近の投稿の分析データを取得"""
    try:
        import tweepy
        
        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
        
        # 自分のユーザーIDを取得
        me = client.get_me()
        user_id = me.data.id
        
        # 最近24時間の投稿を取得（公開メトリクス付き）
        start_time = datetime.utcnow() - timedelta(days=1)
        tweets = client.get_users_tweets(
            user_id,
            start_time=start_time.isoformat() + 'Z',
            tweet_fields=['created_at', 'public_metrics'],
            max_results=10
        )
        
        if not tweets.data:
            print("過去24時間の投稿なし")
            return []
        
        analytics = []
        for tweet in tweets.data:
            metrics = tweet.public_metrics
            analytics.append({
                'id': tweet.id,
                'text': tweet.text[:50] + '...' if len(tweet.text) > 50 else tweet.text,
                'created_at': tweet.created_at.isoformat(),
                'impressions': metrics.get('impression_count', 0),
                'likes': metrics['like_count'],
                'retweets': metrics['retweet_count'],
                'replies': metrics['reply_count'],
                'engagement_rate': (
                    (metrics['like_count'] + metrics['retweet_count'] + metrics['reply_count']) / 
                    max(metrics.get('impression_count', 1), 1) * 100
                )
            })
        
        return analytics
    
    except Exception as e:
        print(f"エラー: {e}")
        return []

def save_daily_kpi(analytics):
    """日次KPIを保存"""
    kpi_file = Path(__file__).parent / 'marketing_kpi.jsonl'
    
    today_kpi = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_impressions': sum(a['impressions'] for a in analytics),
        'total_engagements': sum(a['likes'] + a['retweets'] + a['replies'] for a in analytics),
        'tweet_count': len(analytics),
        'avg_engagement_rate': sum(a['engagement_rate'] for a in analytics) / len(analytics) if analytics else 0,
        'tweets': analytics
    }
    
    with open(kpi_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(today_kpi, ensure_ascii=False) + '\n')
    
    print(f"[OK] 日次KPI保存: {kpi_file}")
    return today_kpi

def print_report(kpi):
    """レポート出力"""
    print("\n" + "=" * 60)
    print(f"Twitter Analytics レポート（{kpi['date']}）")
    print("=" * 60)
    print(f"投稿数: {kpi['tweet_count']}件")
    print(f"総インプレッション: {kpi['total_impressions']:,}回")
    print(f"総エンゲージメント: {kpi['total_engagements']:,}回")
    print(f"平均エンゲージメント率: {kpi['avg_engagement_rate']:.2f}%")
    print("\n投稿詳細:")
    for tweet in kpi['tweets']:
        print(f"  - {tweet['text']}")
        print(f"    インプレッション: {tweet['impressions']:,} | いいね: {tweet['likes']} | RT: {tweet['retweets']} | 返信: {tweet['replies']}")
        print(f"    エンゲージメント率: {tweet['engagement_rate']:.2f}%")
    print("=" * 60)

def main():
    if not TWITTER_BEARER_TOKEN:
        print("[ERROR] TWITTER_BEARER_TOKEN が設定されていません")
        sys.exit(1)
    
    print("Twitter Analytics取得中...")
    analytics = get_recent_tweets_analytics()
    
    if analytics:
        kpi = save_daily_kpi(analytics)
        print_report(kpi)
    else:
        print("データ取得失敗")

if __name__ == '__main__':
    main()
