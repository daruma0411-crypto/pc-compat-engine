#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
トレンド便乗ツイート生成
- 曜日別テーマ投稿
- 定期コンテンツ（朝の挨拶、夜のまとめ）
"""
import sys
import random
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'


def generate_morning_tweet():
    """朝7時の投稿（通勤通学時間帯向け）"""
    patterns = [
        "おはようございます☀️\n\n今日もPCパーツの価格チェックしてます\n気になるGPUの値下がり情報は↓\n{url}",
        "おはよう👋\n\n朝イチでGPU価格確認したら\n面白い動きしてた\n\n詳しくはプロフから\n{url}",
        "☀️ 朝のPC自作ニュース\n\n今週のおすすめ構成を更新しました\n予算別にチェック↓\n{url}",
        "おはようございます\n\n今日のSteamセール情報と\nあなたのPCで動くかチェック↓\n{url}",
        "朝活PCパーツチェック☕\n\nRTX 4060が過去最安値に近づいてるかも\n価格推移はこちら↓\n{url}",
    ]
    text = random.choice(patterns).format(url=SITE_URL)
    
    hashtags = random.sample(['おはよう', 'PCゲーム', '自作PC', 'GPU'], 2)
    text += '\n\n' + ' '.join(f'#{t}' for t in hashtags)
    
    return text


def generate_weekday_theme_tweet():
    """曜日別テーマ投稿"""
    weekday = datetime.now().weekday()
    
    themes = {
        0: ("月曜日のPC構成相談", [  # 月曜
            "今週こそPC組むぞ！って人いる？\n\n予算と用途教えてくれたら\n最適構成を提案します\n\n{url}",
            "月曜日なので週間パーツ価格チェック\n先週からの値動きまとめ↓\n\n{url}",
        ]),
        1: ("火曜日のGPU比較", [  # 火曜
            "RTX 4060 vs RTX 4060 Ti\n差額1.5万円の価値はあるのか？\n\nデータで検証↓\n{url}",
            "GPU選びで迷ってる人へ\nゲーム別の推奨GPUを一覧にしました\n\n{url}",
        ]),
        2: ("水曜日のゲーム推奨スペック", [  # 水曜
            "水曜日なので新作ゲームのスペックチェック\n今週発売のタイトルは動くかな？\n\n{url}",
        ]),
        3: ("木曜日の予算別構成", [  # 木曜
            "予算別おすすめPC構成\n・5万円: 軽いゲーム向け\n・10万円: フルHD60fps\n・15万円: WQHD144fps\n\n詳細↓\n{url}",
        ]),
        4: ("金曜日のコスパ最強パーツ", [  # 金曜
            "週末に向けて！\n今買うべきコスパ最強パーツTOP3\n\nチェック↓\n{url}",
            "金曜の夜はPCいじりの時間\n今週のお買い得パーツまとめ\n\n{url}",
        ]),
        5: ("土曜日の自作PC挑戦", [  # 土曜
            "土曜日は自作PCの日！\n初心者でも組める構成を紹介してます\n\n{url}",
        ]),
        6: ("日曜日のまったりゲーム", [  # 日曜
            "日曜日のゲーム日和🎮\n新しいゲーム探してる人は\nスペック確認もお忘れなく\n\n{url}",
        ]),
    }
    
    theme_name, tweets = themes.get(weekday, ("その他", [f"PCパーツ情報更新中\n{SITE_URL}"]))
    text = random.choice(tweets).format(url=SITE_URL)
    
    hashtags = random.sample(['自作PC', 'PCパーツ', 'ゲーミングPC', 'GPU', 'コスパ'], 2)
    text += '\n\n' + ' '.join(f'#{t}' for t in hashtags)
    
    return text, theme_name


if __name__ == '__main__':
    print("=== 朝ツイート ===")
    print(generate_morning_tweet())
    print("\n=== 曜日テーマ ===")
    text, theme = generate_weekday_theme_tweet()
    print(f"[{theme}]")
    print(text)
