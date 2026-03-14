#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マーケティング日次チェックスクリプト
HEARTBEATから呼び出されて、毎朝自動実行される

チェック項目:
1. Twitter投稿状況（7時・13時・18時）
2. ブログ記事生成状況
3. 前日のインプレッション・エンゲージメント
4. 異常検知（投稿失敗、PV急減など）
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

def check_twitter_posts():
    """Twitter投稿状況確認"""
    print("\n" + "=" * 60)
    print("1. Twitter投稿状況チェック")
    print("=" * 60)
    
    # GitHub Actions の実行履歴を確認
    try:
        result = subprocess.run(
            ['gh', 'run', 'list', '--workflow=twitter-bot.yml', '--limit', '3'],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent
        )
        
        lines = result.stdout.strip().split('\n')
        print(f"直近3回の投稿状況:")
        for line in lines:
            if 'completed' in line:
                status = "✅ 成功" if 'success' in line else "❌ 失敗"
                print(f"  {status} - {line}")
        
        # 失敗があればアラート
        if any('failure' in line for line in lines):
            print("\n⚠️ 警告: 投稿失敗が検出されました")
            return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False
    
    return True

def check_blog_generation():
    """ブログ記事生成状況確認"""
    print("\n" + "=" * 60)
    print("2. ブログ記事生成状況チェック")
    print("=" * 60)
    
    blog_dir = Path(__file__).parent.parent / 'static' / 'blog'
    history_file = blog_dir / 'generation_history.json'
    
    if not history_file.exists():
        print("❌ 生成履歴ファイルなし")
        return False
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    # 最新3記事を表示
    recent = history[-3:]
    print(f"最近の記事（{len(recent)}件）:")
    for article in recent:
        print(f"  ✅ {article['title']} ({article['filename']})")
    
    # 昨日の記事があるか確認
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    yesterday_articles = [a for a in history if a['filename'].startswith(yesterday)]
    
    if not yesterday_articles:
        print(f"\n⚠️ 警告: 昨日（{yesterday}）の記事が見つかりません")
        return False
    
    return True

def check_twitter_analytics():
    """Twitter Analyticsチェック"""
    print("\n" + "=" * 60)
    print("3. Twitter Analytics チェック")
    print("=" * 60)
    
    kpi_file = Path(__file__).parent / 'marketing_kpi.jsonl'
    
    if not kpi_file.exists():
        print("⚠️ KPIファイルなし → fetch_twitter_analytics.py を実行してください")
        return True
    
    # 最新のKPIを取得
    with open(kpi_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if lines:
            latest_kpi = json.loads(lines[-1])
            print(f"日付: {latest_kpi['date']}")
            print(f"投稿数: {latest_kpi['tweet_count']}件")
            print(f"総インプレッション: {latest_kpi['total_impressions']:,}回")
            print(f"総エンゲージメント: {latest_kpi['total_engagements']:,}回")
            print(f"平均エンゲージメント率: {latest_kpi['avg_engagement_rate']:.2f}%")
            
            # 異常検知: インプレッションが極端に低い
            if latest_kpi['total_impressions'] < 100 and latest_kpi['tweet_count'] > 0:
                print("\n⚠️ 警告: インプレッションが異常に低いです")
                return False
    
    return True

def generate_report():
    """日次レポート生成"""
    print("\n" + "=" * 60)
    print("日次マーケティングレポート")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        'twitter_posts': check_twitter_posts(),
        'blog_generation': check_blog_generation(),
        'twitter_analytics': check_twitter_analytics()
    }
    
    # 総合判定
    all_ok = all(results.values())
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ 全チェックOK")
    else:
        print("⚠️ 問題が検出されました。詳細を確認してください。")
    print("=" * 60)
    
    return all_ok

if __name__ == '__main__':
    all_ok = generate_report()
    sys.exit(0 if all_ok else 1)
