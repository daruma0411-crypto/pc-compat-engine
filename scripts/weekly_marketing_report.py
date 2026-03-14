#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週次マーケティングレポート生成スクリプト
毎週月曜日に自動実行

出力内容:
1. 週間Twitter統計（インプレッション、エンゲージメント、フォロワー増減）
2. ブログ記事一覧
3. 施策の効果測定
4. 次週のアクション
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def load_weekly_kpi():
    """週次KPIを読み込み"""
    kpi_file = Path(__file__).parent / 'marketing_kpi.jsonl'
    
    if not kpi_file.exists():
        return []
    
    # 過去7日分のKPIを取得
    week_ago = datetime.now() - timedelta(days=7)
    
    weekly_kpi = []
    with open(kpi_file, 'r', encoding='utf-8') as f:
        for line in f:
            kpi = json.loads(line)
            kpi_date = datetime.strptime(kpi['date'], '%Y-%m-%d')
            if kpi_date >= week_ago:
                weekly_kpi.append(kpi)
    
    return weekly_kpi

def analyze_weekly_performance():
    """週次パフォーマンス分析"""
    weekly_kpi = load_weekly_kpi()
    
    if not weekly_kpi:
        print("⚠️ データ不足: KPIデータがありません")
        return None
    
    # 集計
    total_impressions = sum(kpi['total_impressions'] for kpi in weekly_kpi)
    total_engagements = sum(kpi['total_engagements'] for kpi in weekly_kpi)
    total_tweets = sum(kpi['tweet_count'] for kpi in weekly_kpi)
    avg_engagement_rate = sum(kpi['avg_engagement_rate'] for kpi in weekly_kpi) / len(weekly_kpi)
    
    # 日別トレンド
    daily_impressions = {kpi['date']: kpi['total_impressions'] for kpi in weekly_kpi}
    
    # トップパフォーマンス投稿
    all_tweets = []
    for kpi in weekly_kpi:
        all_tweets.extend(kpi['tweets'])
    
    top_tweets = sorted(all_tweets, key=lambda t: t['impressions'], reverse=True)[:5]
    
    return {
        'total_impressions': total_impressions,
        'total_engagements': total_engagements,
        'total_tweets': total_tweets,
        'avg_engagement_rate': avg_engagement_rate,
        'daily_impressions': daily_impressions,
        'top_tweets': top_tweets
    }

def generate_weekly_report():
    """週次レポート生成"""
    print("=" * 70)
    print(f"週次マーケティングレポート（{datetime.now().strftime('%Y年%m月%d日')}）")
    print("=" * 70)
    
    perf = analyze_weekly_performance()
    
    if not perf:
        return
    
    print("\n## 1. Twitter パフォーマンス（過去7日間）\n")
    print(f"総投稿数: {perf['total_tweets']}件")
    print(f"総インプレッション: {perf['total_impressions']:,}回")
    print(f"総エンゲージメント: {perf['total_engagements']:,}回")
    print(f"平均エンゲージメント率: {perf['avg_engagement_rate']:.2f}%")
    
    print("\n## 2. 日別インプレッション推移\n")
    for date, impressions in perf['daily_impressions'].items():
        bar = "█" * (impressions // 100)
        print(f"{date}: {bar} ({impressions:,})")
    
    print("\n## 3. トップパフォーマンス投稿（TOP5）\n")
    for i, tweet in enumerate(perf['top_tweets'], 1):
        print(f"{i}. {tweet['text']}")
        print(f"   インプレッション: {tweet['impressions']:,} | エンゲージメント率: {tweet['engagement_rate']:.2f}%")
    
    # ブログ記事一覧
    print("\n## 4. 今週のブログ記事\n")
    blog_dir = Path(__file__).parent.parent / 'static' / 'blog'
    history_file = blog_dir / 'generation_history.json'
    
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        recent_articles = [a for a in history if a['filename'] >= week_ago]
        
        for article in recent_articles:
            print(f"- {article['title']} ({article['filename']})")
    
    # 改善提案
    print("\n## 5. 改善提案\n")
    
    if perf['avg_engagement_rate'] < 2.0:
        print("⚠️ エンゲージメント率が低い（<2%）")
        print("   → 投稿内容の見直し、質問形式の増加、画像付き投稿の増加")
    
    if perf['total_impressions'] < 5000:
        print("⚠️ インプレッションが目標未達（<5,000/週）")
        print("   → ハッシュタグ最適化、投稿時間の調整、リプライ活動の強化")
    
    if perf['total_tweets'] < 14:
        print("⚠️ 投稿頻度が低い（<2回/日）")
        print("   → GitHub Actionsの設定確認")
    
    print("\n## 6. 次週のアクション\n")
    print("- [ ] エンゲージメント率向上施策の実施")
    print("- [ ] トップパフォーマンス投稿パターンの分析・再現")
    print("- [ ] SEO対策の強化（内部リンク、メタディスクリプション）")
    
    print("\n" + "=" * 70)
    
    # レポートをファイルに保存
    report_file = Path(__file__).parent / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.txt"
    # （省略: ファイル保存処理）

if __name__ == '__main__':
    generate_weekly_report()
