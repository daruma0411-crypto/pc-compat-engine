# ブログ×Twitter連動 + 週次価格レポート実装指示書

## 📋 実装概要

**目的**: ブログとTwitterを連動させてBOT感を軽減 + 週次価格レポートでリピーター獲得

**追加機能**:
1. **週1定点観測記事**: 価格.com価格推移レポート（毎週月曜9時）
2. **Twitter連動**: ブログ記事を自動ツイート（BOT感軽減）

**実装時間**: 1時間10分

---

## 🎯 施策4: 週1定点観測記事（40分）

### 目的

**週次レポートでリピーター獲得 + SEO強化**

```
毎週月曜9時に定点観測記事を自動生成:
- GPU価格推移（今週の最安値）
- CPU価格推移
- BTO製品の値下げ情報
- 「今買い時」判定
```

**SEO効果**:
- 「RTX 4060 価格推移」
- 「GPU 今買い時」
- 「ゲーミングPC 値下げ」

---

### 実装内容

#### 4-1. 価格データ取得モジュール

**新規ファイル**: `scripts/price_tracker.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
価格追跡モジュール
価格.com API（非公式）またはスクレイピングで価格取得
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
PRICE_HISTORY_FILE = WORKSPACE_DIR / "workspace" / "data" / "price_history.jsonl"

def fetch_gpu_prices():
    """
    GPU価格を取得（価格.com等）
    
    Returns:
        List[dict]: GPU価格データ
    """
    # 簡易実装: BTOデータベースから価格取得
    # 本番実装: 価格.com API or スクレイピング
    
    bto_file = WORKSPACE_DIR / "workspace" / "data" / "bto" / "products.jsonl"
    
    gpu_prices = {}
    
    with open(bto_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                product = json.loads(line)
                gpu_name = product['specs']['gpu']['name']
                price = product['price_jpy']
                
                if gpu_name not in gpu_prices or price < gpu_prices[gpu_name]:
                    gpu_prices[gpu_name] = price
    
    # JSONL形式で保存（履歴蓄積）
    record = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'prices': gpu_prices,
    }
    
    with open(PRICE_HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    return gpu_prices

def get_price_trends(weeks=4):
    """
    過去N週間の価格推移を取得
    
    Args:
        weeks: 過去何週間分
    
    Returns:
        dict: GPU別価格推移
    """
    if not PRICE_HISTORY_FILE.exists():
        return {}
    
    cutoff_date = datetime.now() - timedelta(weeks=weeks)
    
    trends = {}
    
    with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                record_date = datetime.strptime(record['date'], '%Y-%m-%d')
                
                if record_date >= cutoff_date:
                    for gpu, price in record['prices'].items():
                        if gpu not in trends:
                            trends[gpu] = []
                        trends[gpu].append({
                            'date': record['date'],
                            'price': price,
                        })
    
    return trends

def analyze_price_trends(trends):
    """
    価格トレンド分析
    
    Returns:
        dict: 今買い時かどうかの判定
    """
    analysis = {}
    
    for gpu, history in trends.items():
        if len(history) < 2:
            continue
        
        # 最新価格
        latest = history[-1]['price']
        
        # 過去平均
        avg_price = sum(h['price'] for h in history) / len(history)
        
        # 最安値
        min_price = min(h['price'] for h in history)
        
        # 判定
        if latest <= min_price:
            verdict = "今買い時！（過去最安値）"
        elif latest < avg_price * 0.95:
            verdict = "買い時（平均より5%安い）"
        elif latest > avg_price * 1.1:
            verdict = "待った方が良い（平均より10%高い）"
        else:
            verdict = "通常価格"
        
        analysis[gpu] = {
            'latest': latest,
            'avg': int(avg_price),
            'min': min_price,
            'verdict': verdict,
            'change_pct': ((latest - avg_price) / avg_price) * 100,
        }
    
    return analysis

if __name__ == '__main__':
    # テスト実行
    prices = fetch_gpu_prices()
    print(f"✅ {len(prices)} 件のGPU価格取得")
    
    trends = get_price_trends(weeks=4)
    print(f"✅ {len(trends)} 件のトレンドデータ")
    
    analysis = analyze_price_trends(trends)
    for gpu, data in analysis.items():
        print(f"{gpu}: ¥{data['latest']:,} ({data['verdict']})")
```

---

#### 4-2. 週次レポート生成スクリプト

**新規ファイル**: `scripts/weekly_price_report.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
週次価格レポート生成
毎週月曜9時に自動実行
"""

import os
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic

from price_tracker import fetch_gpu_prices, get_price_trends, analyze_price_trends
from blog_generator import generate_html, save_blog_post

# 環境変数
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Anthropic クライアント
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_weekly_report():
    """
    週次価格レポート生成
    """
    print("📊 週次価格レポート生成開始")
    
    # 1. 最新価格取得
    print("  1/4 価格データ取得中...")
    current_prices = fetch_gpu_prices()
    
    # 2. 過去4週間のトレンド取得
    print("  2/4 トレンド分析中...")
    trends = get_price_trends(weeks=4)
    analysis = analyze_price_trends(trends)
    
    # 3. レポート本文生成（Claude Opus）
    print("  3/4 レポート本文生成中...")
    content = generate_report_content(analysis)
    
    # 4. HTML生成・保存
    print("  4/4 HTML生成・保存中...")
    title = f"【{datetime.now().strftime('%Y年%m月第%W週')}】GPU・CPU価格推移レポート - 今買い時は？"
    keywords = [
        "GPU 価格推移",
        "RTX 価格",
        "ゲーミングPC 今買い時",
        "価格コム GPU",
    ]
    
    html = generate_html(title, content, keywords)
    
    # ファイル名生成
    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f"{timestamp}_weekly_price_report.html"
    
    save_blog_post(filename, html)
    
    print(f"✅ 週次レポート生成完了: {filename}")
    
    return filename

def generate_report_content(analysis):
    """
    レポート本文をClaude Opusで生成
    """
    # 今買い時のGPU
    buy_now = {gpu: data for gpu, data in analysis.items() if "買い時" in data['verdict']}
    
    # 値上がりしているGPU
    overpriced = {gpu: data for gpu, data in analysis.items() if "待った方が" in data['verdict']}
    
    # プロンプト作成
    prompt = f"""
以下のデータを元に、週次GPU価格レポート記事を執筆してください。

【今買い時のGPU】
{format_gpu_list(buy_now)}

【値上がり中のGPU（待った方が良い）】
{format_gpu_list(overpriced)}

【要件】
- タイトル: 【今週の買い時GPU】価格推移レポート
- 構成:
  1. 今週のサマリー（100字）
  2. 今買い時のGPU 3選（各200字）
  3. 値上がり中のGPU（注意喚起）
  4. 来週の予測
  5. まとめ
- 1,500文字程度
- 価格は実データを使用（推測禁止）
- 最後に「AI診断チャットで相談」へ誘導
"""
    
    # Claude Opus 呼び出し
    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    return message.content[0].text

def format_gpu_list(gpu_dict):
    """
    GPU辞書を読みやすい文字列に変換
    """
    lines = []
    for gpu, data in gpu_dict.items():
        lines.append(f"- {gpu}: ¥{data['latest']:,} (平均比 {data['change_pct']:+.1f}%)")
    return "\n".join(lines)

if __name__ == '__main__':
    generate_weekly_report()
```

---

#### 4-3. GitHub Actions 週次実行

**新規ファイル**: `.github/workflows/weekly-price-report.yml`

```yaml
name: Weekly Price Report

on:
  schedule:
    - cron: '0 0 * * 1'  # 毎週月曜0時（UTC = 日本時間9時）
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install anthropic requests
    
    - name: Generate weekly price report
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        python scripts/weekly_price_report.py
    
    - name: Commit new report
      run: |
        git config user.name "GitHub Actions Bot"
        git config user.email "actions@github.com"
        git add static/blog/ workspace/data/price_history.jsonl
        git diff --staged --quiet || git commit -m "chore: 週次価格レポート自動生成 [skip ci]"
        git push
```

---

## 🎯 施策5: Twitter連動（30分）

### 目的

**ブログ記事を自動ツイート → BOT感軽減 + トラフィック誘導**

```
Before（BOT感満載）:
「Elden Ring」やりたいけど、自分のPCで動くか不安...
推奨スペック:
GPU: RTX 3060
...

After（人間らしい）:
今日の記事書きました📝

「Elden Ring」が重い時の対処法7選

グラフィック設定の最適化から
ドライバ更新まで詳しく解説👇
https://bit.ly/xxx

#PCゲーム #エルデンリング
```

---

### 実装内容

#### 5-1. ブログ記事自動ツイート機能

**ファイル**: `scripts/blog_generator.py` に追加

```python
import tweepy

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')

def post_blog_to_twitter(title, url, game_name):
    """
    ブログ記事をTwitterに投稿
    
    Args:
        title: 記事タイトル
        url: 記事URL
        game_name: ゲーム名
    """
    # Twitter API v2 クライアント
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    # ツイート文生成（パターン化）
    tweet_patterns = [
        f"今日の記事書きました📝\n\n{title}\n\n{url}\n\n#{game_name.replace(' ', '')} #PCゲーム",
        
        f"新しい記事公開しました！\n\n{title}\n\n詳しく解説してます👇\n{url}\n\n#PCスペック #{game_name.replace(' ', '')}",
        
        f"📝 ブログ更新\n\n{title}\n\n参考になれば嬉しいです！\n{url}\n\n#ゲーミングPC #{game_name.replace(' ', '')}",
        
        f"{game_name}について記事書きました\n\n{title}\n\n{url}\n\n#PCゲーム #推奨スペック",
    ]
    
    # ランダムに1つ選択
    import random
    tweet_text = random.choice(tweet_patterns)
    
    # 投稿
    try:
        response = client.create_tweet(text=tweet_text)
        print(f"✅ Twitter投稿成功: {response.data['id']}")
        return response.data['id']
    except Exception as e:
        print(f"❌ Twitter投稿エラー: {e}")
        return None

def generate_daily_post():
    """
    毎日1本の記事生成 + Twitter投稿
    """
    # 旬のゲームを取得
    trending_game = get_trending_game()
    
    # テンプレート選択
    template = select_best_template(trending_game)
    
    # 変数設定
    variables = {
        'game': trending_game,
        'gpu_model': random.choice(["4060", "4070", "4080"]),
        'budget': random.choice(["10", "12", "15", "18", "20"]),
    }
    
    print(f"\n🎯 本日の記事テーマ:")
    print(f"  - ゲーム: {trending_game}")
    print(f"  - テンプレート: {template['title']}")
    
    # 記事生成
    html = generate_blog_post(template, variables)
    
    if html:
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d')
        slug = trending_game.lower().replace(' ', '-').replace(':', '')
        filename = f"{timestamp}_{slug}_{template['id']}.html"
        
        # 保存
        save_blog_post(filename, html)
        
        # 記事URLを生成
        article_url = f"https://pc-compat-engine-production.up.railway.app/blog/{filename}"
        
        # Twitterに投稿
        print(f"\n🐦 Twitter投稿中...")
        post_blog_to_twitter(
            title=template['title'].format(**variables),
            url=article_url,
            game_name=trending_game
        )
        
        print(f"\n✅ 本日の記事生成+投稿完了: {filename}")
        return filename
    else:
        print(f"\n❌ 記事生成失敗")
        return None
```

---

#### 5-2. 週次レポートもTwitter投稿

**ファイル**: `scripts/weekly_price_report.py` に追加

```python
from blog_generator import post_blog_to_twitter

def generate_weekly_report():
    """
    週次価格レポート生成 + Twitter投稿
    """
    # ... 既存のレポート生成コード ...
    
    # HTML生成・保存
    html = generate_html(title, content, keywords)
    filename = f"{timestamp}_weekly_price_report.html"
    save_blog_post(filename, html)
    
    # 記事URL生成
    article_url = f"https://pc-compat-engine-production.up.railway.app/blog/{filename}"
    
    # Twitter投稿（週次レポート専用文面）
    tweet_text = f"""
📊 今週の価格レポート公開！

{title}

今買い時のGPUは？
値上がり中のパーツは？

詳しくはこちら👇
{article_url}

#GPU価格 #今買い時 #ゲーミングPC
    """.strip()
    
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    try:
        client.create_tweet(text=tweet_text)
        print(f"✅ 週次レポートをTwitter投稿")
    except Exception as e:
        print(f"❌ Twitter投稿エラー: {e}")
    
    print(f"✅ 週次レポート生成完了: {filename}")
    return filename
```

---

#### 5-3. Twitter投稿パターンの多様化

**既存の `scripts/twitter_bot.py` に追加**

```python
# 既存のゲーム情報ツイートに加えて、ブログ記事も混ぜる

def should_post_blog_article():
    """
    ブログ記事を投稿するかどうか判定
    
    確率:
    - 通常ゲーム情報: 70%
    - ブログ記事: 30%
    """
    import random
    return random.random() < 0.3  # 30%の確率でブログ記事

# メイン処理
if should_post_blog_article():
    # 最新のブログ記事を取得してツイート
    latest_article = get_latest_blog_article()
    post_blog_to_twitter(latest_article['title'], latest_article['url'], latest_article['game'])
else:
    # 通常のゲーム情報ツイート（既存コード）
    post_game_info()
```

---

## ✅ 実装完了チェックリスト

### 施策4: 週1定点観測記事
- [ ] `scripts/price_tracker.py` 作成
- [ ] `scripts/weekly_price_report.py` 作成
- [ ] `.github/workflows/weekly-price-report.yml` 作成
- [ ] `workspace/data/price_history.jsonl` 初期化
- [ ] テスト実行（手動で1回実行）
- [ ] 週次スケジュール確認（毎週月曜9時JST）

### 施策5: Twitter連動
- [ ] `blog_generator.py` に `post_blog_to_twitter()` 追加
- [ ] `weekly_price_report.py` に Twitter投稿機能追加
- [ ] `twitter_bot.py` にブログ記事投稿パターン追加
- [ ] GitHub Actions ワークフローに Twitter投稿処理追加
- [ ] テスト投稿（dry-run）

---

## 📊 期待効果

### 週次価格レポート

| 指標 | 効果 |
|------|------|
| **リピーター獲得** | 毎週チェックしに来る固定読者+50% |
| **SEO効果** | 「GPU 価格推移」で上位表示 |
| **成約率向上** | 「今買い時！」→ 購買意欲↑ → 成約率+15% |
| **PV/記事** | 500-1,000（通常記事の2倍） |

### Twitter連動

| 指標 | Before | After |
|------|--------|-------|
| **BOT感** | 100%（ゲーム情報のみ） | 50%（ブログ記事も混在） |
| **エンゲージメント率** | 0.5% | 2-3%（+300%） |
| **クリック率** | 0.1% | 1-2%（+1,000%） |
| **ブログ流入** | 0 | 100-300/月 |

---

## 🚀 実装手順

### Phase 4: 週次価格レポート（40分）
1. `scripts/price_tracker.py` 作成
2. `scripts/weekly_price_report.py` 作成
3. `.github/workflows/weekly-price-report.yml` 作成
4. テスト実行: `python scripts/weekly_price_report.py`
5. Git commit & push

### Phase 5: Twitter連動（30分）
1. `blog_generator.py` 修正（Twitter投稿機能追加）
2. `weekly_price_report.py` 修正（Twitter投稿追加）
3. `twitter_bot.py` 修正（ブログ記事パターン追加）
4. テスト投稿: `python scripts/blog_generator.py --dry-run`
5. Git commit & push

---

## 💰 ROI試算

### 週次価格レポート

```
制作コスト:
- Claude Opus: 1記事 $0.06
- 月4記事 = $0.24
- 年間 = $2.88

収益（保守的）:
- 月4記事 × 平均700PV × 5%成約率 × ¥5,000 = 月¥7,000
- 年間 = ¥84,000

ROI = ¥84,000 / $2.88 (≒¥432) = 約194倍
```

### Twitter連動

```
コスト: $0（既存機能の拡張）

収益:
- Twitter流入 200PV/月 × 3%成約率 × ¥5,000 = 月¥30,000
- 年間 = ¥360,000

ROI = 無限大
```

---

**実装時間目安**: 1時間10分

**Co-Authored-By**: Claude Opus 4.6 <noreply@anthropic.com>
