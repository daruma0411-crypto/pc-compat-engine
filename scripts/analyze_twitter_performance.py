#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter投稿パフォーマンス分析スクリプト
- 投稿タイプ別の分布
- 画像付き投稿の割合
- 投稿時間帯の分布
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# Windows コンソールのUTF-8出力
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_history():
    history_file = Path(__file__).parent / 'twitter_post_history.json'
    with open(history_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze():
    history = load_history()
    
    # 最近30件を分析
    recent = history[-30:]
    
    print("=" * 60)
    print("Twitter投稿分析レポート（最近30件）")
    print("=" * 60)
    
    # 投稿タイプ別の分布
    post_types = Counter(h.get('post_type', h.get('name', 'unknown')) for h in recent)
    print("\n投稿タイプ別分布:")
    for ptype, count in post_types.most_common():
        pct = count / len(recent) * 100
        print(f"  {ptype:15s}: {count:2d}件 ({pct:5.1f}%)")
    
    # 画像付き投稿の割合
    with_image = sum(1 for h in recent if h.get('has_image'))
    print(f"\n画像付き投稿: {with_image}/{len(recent)} ({with_image/len(recent)*100:.1f}%)")
    
    # 投稿時間帯の分布
    hours = []
    for h in recent:
        try:
            dt = datetime.fromisoformat(h['posted_at'])
            hours.append(dt.hour)
        except:
            pass
    
    if hours:
        hour_dist = Counter(hours)
        print("\n投稿時間帯:")
        for hour in sorted(hour_dist.keys()):
            count = hour_dist[hour]
            bar = "█" * count
            print(f"  {hour:02d}時: {bar} ({count})")
    
    # ハッシュタグ数の分布
    hashtag_counts = [h.get('hashtag_count', 0) for h in recent if 'hashtag_count' in h]
    if hashtag_counts:
        avg_hashtags = sum(hashtag_counts) / len(hashtag_counts)
        print(f"\n平均ハッシュタグ数: {avg_hashtags:.1f}個")
    
    print("\n" + "=" * 60)
    print("推奨アクション:")
    print("=" * 60)
    
    # ブログ投稿が多い場合
    blog_pct = post_types.get('blog', 0) / len(recent) * 100
    if blog_pct > 40:
        print(f"⚠ ブログ投稿が{blog_pct:.0f}%と多い → ゲーム投稿を増やす")
    
    # 画像付き投稿が少ない場合
    if with_image / len(recent) < 0.5:
        print(f"⚠ 画像付き投稿が{with_image/len(recent)*100:.0f}%と少ない → 画像付きを増やす")
    
    # 投稿時間が偏っている場合
    if hours and len(set(hours)) < 3:
        print(f"⚠ 投稿時間が{len(set(hours))}時間帯に偏っている → 朝・昼・夜に分散")
    
    print("\n次のステップ:")
    print("1. 投稿頻度を1日3回に変更（朝7時、昼13時、夜18時）")
    print("2. 画像付き投稿を80%以上に")
    print("3. 人気ゲームタイトル（Cyberpunk, Elden Ring等）を優先")

if __name__ == '__main__':
    analyze()
