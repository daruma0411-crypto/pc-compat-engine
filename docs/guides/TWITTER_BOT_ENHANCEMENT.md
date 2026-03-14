# Twitter Bot 強化版実装指示書

## 📌 プロジェクト概要

現在のTwitter Bot（`scripts/twitter_bot.py`）を強化して、エンゲージメント率とフォロワー増加を自動化する。

### 現状
- ✅ 1日3回自動投稿（12:00, 18:00, 21:00 JST）
- ✅ 4種類の投稿パターン
- ✅ メタスコア優先選択
- ✅ 投稿履歴管理

### 目標
- 🎯 インプレッション: 現在の2-3倍
- 🎯 エンゲージメント率: 1-3%
- 🎯 フォロワー増加: 月100-500人

---

## 🎨 Phase A: メタスコア画像の自動生成・添付

### 目標
ツイートにメタスコア画像を添付してビジュアルインパクトを高める。

### 実装内容

#### タスクA.1: 画像生成モジュール作成

**ファイル:** `scripts/generate_metacritic_image.py`

**機能:**
- メタスコアを視覚的に表示する画像を動的生成
- 色分け: 緑（75-100）、黄（50-74）、赤（0-49）
- サイズ: 1200x628px（Twitter推奨サイズ）

**実装例:**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metacritic Score画像生成モジュール
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

def generate_metacritic_image(game_name, score, output_path):
    """
    メタスコア画像を生成
    
    Args:
        game_name (str): ゲーム名
        score (int): メタスコア（0-100）
        output_path (str): 出力パス
    
    Returns:
        str: 生成した画像のパス
    """
    
    # 画像サイズ（Twitter推奨: 1200x628）
    width, height = 1200, 628
    
    # スコアに応じた色設定
    if score >= 75:
        score_color = (102, 204, 0)  # 緑
        bg_color = (20, 30, 20)
    elif score >= 50:
        score_color = (255, 204, 0)  # 黄
        bg_color = (30, 25, 10)
    else:
        score_color = (255, 0, 0)  # 赤
        bg_color = (30, 10, 10)
    
    # 画像作成
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # フォント設定（システムフォントを使用）
    # Windowsの場合
    font_paths = [
        r'C:\Windows\Fonts\msgothic.ttc',  # MS ゴシック
        r'C:\Windows\Fonts\meiryo.ttc',     # メイリオ
        '/System/Library/Fonts/Hiragino Sans GB.ttc',  # macOS
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Linux
    ]
    
    font_large = None
    font_medium = None
    font_small = None
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_large = ImageFont.truetype(font_path, 180)
                font_medium = ImageFont.truetype(font_path, 60)
                font_small = ImageFont.truetype(font_path, 40)
                break
            except:
                pass
    
    # フォントが見つからない場合はデフォルト
    if not font_large:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # メタスコア表示（中央）
    score_text = str(score)
    # スコアのバウンディングボックスを取得
    bbox = draw.textbbox((0, 0), score_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    score_x = (width - text_width) // 2
    score_y = (height - text_height) // 2 - 50
    
    # スコア背景（丸）
    circle_radius = 150
    circle_center = (width // 2, height // 2 - 20)
    draw.ellipse(
        [circle_center[0] - circle_radius, circle_center[1] - circle_radius,
         circle_center[0] + circle_radius, circle_center[1] + circle_radius],
        fill=score_color
    )
    
    # スコアテキスト
    draw.text((score_x, score_y), score_text, fill='white', font=font_large)
    
    # 「Metacritic Score」ラベル（上部）
    label_text = "METACRITIC SCORE"
    bbox = draw.textbbox((0, 0), label_text, font=font_small)
    label_width = bbox[2] - bbox[0]
    label_x = (width - label_width) // 2
    draw.text((label_x, 50), label_text, fill=(200, 200, 200), font=font_small)
    
    # ゲーム名（下部）
    # 長いゲーム名は改行
    max_chars = 40
    if len(game_name) > max_chars:
        game_name_short = game_name[:max_chars] + '...'
    else:
        game_name_short = game_name
    
    bbox = draw.textbbox((0, 0), game_name_short, font=font_medium)
    name_width = bbox[2] - bbox[0]
    name_x = (width - name_width) // 2
    draw.text((name_x, height - 120), game_name_short, fill='white', font=font_medium)
    
    # 評価テキスト
    if score >= 75:
        rating_text = "Universal Acclaim"
    elif score >= 50:
        rating_text = "Generally Favorable"
    else:
        rating_text = "Mixed or Average"
    
    bbox = draw.textbbox((0, 0), rating_text, font=font_small)
    rating_width = bbox[2] - bbox[0]
    rating_x = (width - rating_width) // 2
    draw.text((rating_x, height - 60), rating_text, fill=(180, 180, 180), font=font_small)
    
    # 保存
    img.save(output_path)
    return output_path


if __name__ == '__main__':
    # テスト実行
    test_dir = Path(__file__).parent / 'test_images'
    test_dir.mkdir(exist_ok=True)
    
    # 高スコア
    generate_metacritic_image("Baldur's Gate 3", 96, test_dir / 'test_high.png')
    # 中スコア
    generate_metacritic_image("Example Game", 68, test_dir / 'test_mid.png')
    # 低スコア
    generate_metacritic_image("Another Game", 45, test_dir / 'test_low.png')
    
    print("✅ テスト画像を生成しました: scripts/test_images/")
```

---

#### タスクA.2: Twitter Bot に画像添付機能を追加

**ファイル:** `scripts/twitter_bot.py`

**変更点:**

```python
# 1. インポート追加
from generate_metacritic_image import generate_metacritic_image

# 2. post_tweet 関数を修正
def post_tweet(text, dry_run=True, image_path=None):
    """ツイートを投稿（画像添付対応）"""
    if dry_run:
        print("=" * 60)
        print("[DRY RUN] 以下のツイートを投稿します:")
        print("=" * 60)
        print(text)
        if image_path:
            print(f"\n[画像添付] {image_path}")
        print("=" * 60)
        print(f"文字数: {len(text)}")
        return True

    # 環境変数チェック（既存のコード）
    # ...

    # Twitter API v2での投稿（画像対応）
    try:
        import tweepy
        
        # OAuth 1.0a認証（画像アップロードに必要）
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET
        )
        api_v1 = tweepy.API(auth)
        
        # v2クライアント
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
        
        # 画像がある場合はアップロード
        media_id = None
        if image_path and os.path.exists(image_path):
            media = api_v1.media_upload(image_path)
            media_id = media.media_id
        
        # ツイート投稿
        if media_id:
            response = client.create_tweet(text=text, media_ids=[media_id])
        else:
            response = client.create_tweet(text=text)
        
        print(f"✅ ツイート投稿成功: https://twitter.com/user/status/{response.data['id']}")
        
        # 画像ファイルを削除（一時ファイル）
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        
        return True
    except Exception as e:
        print(f"[ERROR] ツイート投稿失敗: {e}")
        return False

# 3. main() 関数を修正
def main():
    """メイン処理"""
    # 既存のコード...
    
    # ゲーム選択
    selected_game = select_game(games, history)
    
    # ツイート生成
    tweet_text = generate_tweet_patterns(selected_game)
    
    # メタスコア画像生成（スコアがある場合）
    image_path = None
    meta_score = selected_game.get('metacritic_score')
    if meta_score and meta_score > 0:
        image_dir = Path(__file__).parent / 'temp_images'
        image_dir.mkdir(exist_ok=True)
        image_path = image_dir / f"meta_{selected_game['name'].replace(' ', '_')}.png"
        generate_metacritic_image(selected_game['name'], meta_score, str(image_path))
    
    # ツイート投稿
    success = post_tweet(tweet_text, dry_run=args.dry_run, image_path=image_path)
    
    # 履歴更新（既存のコード）
    # ...
```

---

## 📝 Phase B: 投稿パターンを10種類に拡張

### 目標
現在の4パターン → 10パターンに増やして、投稿内容に多様性を持たせる。

### 実装内容

#### タスクB.1: `generate_tweet_patterns()` を拡張

**ファイル:** `scripts/twitter_bot.py`

```python
def generate_tweet_patterns(game):
    """ツイート文のパターンを生成（10パターン）"""
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
        # パターン1: GPU互換性強調（既存）
        f"【GPU互換性チェック】\n"
        f"{name}{meta_text}\n\n"
        f"推奨GPU: {gpu}\n"
        f"推奨CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"あなたのPCで動く？→ {url}\n"
        f"#PCゲーム #GPU互換性",

        # パターン2: 質問形式（既存）
        f"「{name}」やりたいけど、自分のPCで動くか不安...\n\n"
        f"推奨スペック:\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"無料で互換性チェック！→ {url}\n"
        f"#PCゲーム #スペック確認",

        # パターン3: シンプル紹介（既存）
        f"{name}\n"
        f"推奨スペック一覧\n\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"詳細 → {url}\n"
        f"#PCゲーム #自作PC",

        # パターン4: トラブルシューティング風（既存）
        f"「{name}がカクつく...」\n\n"
        f"推奨スペックをチェック！\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"互換性診断ツール→ {url}\n"
        f"#PCゲーム #動作環境",

        # パターン5: 重い原因はGPU？
        f"「{name}が重い！原因はGPU？」\n\n"
        f"推奨スペック:\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"スペック不足ならアップグレードを検討\n"
        f"→ {url}\n"
        f"#PCゲーム #GPU",

        # パターン6: 予算別PC構成
        f"「予算15万円で{name}を快適プレイ」\n\n"
        f"推奨スペック:\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"予算別PC構成を提案！\n"
        f"→ {url}\n"
        f"#ゲーミングPC #予算",

        # パターン7: ノートPC対応
        f"「ノートPCで{name}は動く？」\n\n"
        f"推奨GPU: {gpu}\n"
        f"推奨CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"ゲーミングノート選びの参考に\n"
        f"→ {url}\n"
        f"#ゲーミングノート #PCゲーム",

        # パターン8: GPU別対応ゲーム
        f"「RTX 4060で{name}は遊べる？」\n\n"
        f"推奨GPU: {gpu}\n"
        f"推奨CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"GPU別対応ゲーム一覧\n"
        f"→ {url}\n"
        f"#RTX4060 #GPU互換性",

        # パターン9: 最低スペック vs 推奨スペック
        f"「{name}の最低スペックと推奨スペックの違いは？」\n\n"
        f"推奨スペック:\n"
        f"GPU: {gpu}\n"
        f"CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"詳細な比較はこちら\n"
        f"→ {url}\n"
        f"#PCゲーム #スペック",

        # パターン10: FPS目標
        f"「{name}を144fpsで遊ぶには？」\n\n"
        f"推奨GPU: {gpu}\n"
        f"推奨CPU: {cpu}\n"
        f"RAM: {ram}GB\n\n"
        f"FPS目標別のPC構成を提案\n"
        f"→ {url}\n"
        f"#144fps #ゲーミングPC",
    ]

    return random.choice(patterns)
```

---

## 🤝 Phase C: フォロワー獲得施策の自動化

### 目標
ゲーム関連アカウントを自動フォロー・エンゲージメント強化してフォロワーを増やす。

### 実装内容

#### タスクC.1: 自動フォロースクリプト作成

**ファイル:** `scripts/twitter_auto_follow.py`

**機能:**
- 「#PCゲーム」「#自作PC」「#ゲーミングPC」等のハッシュタグで検索
- アクティブなアカウントを自動フォロー
- フォローバック率を追跡

**注意:**
- Twitter APIの制限に注意（1日最大400フォロー）
- スパム判定を避けるため、1時間あたり10-20アカウント程度に制限

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Auto Follow Bot
ゲーム関連アカウントを自動フォローしてフォロワーを増やす
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# フォロー履歴ファイル
FOLLOW_HISTORY_FILE = Path(__file__).parent / 'twitter_follow_history.json'

# 設定
MAX_FOLLOWS_PER_HOUR = 15  # 1時間あたりの最大フォロー数
MAX_FOLLOWS_PER_DAY = 200  # 1日あたりの最大フォロー数
TARGET_HASHTAGS = [
    '#PCゲーム',
    '#自作PC',
    '#ゲーミングPC',
    '#GPU',
    '#ゲーミングノート',
    '#144fps',
    '#PCゲーマー',
]


def load_follow_history():
    """フォロー履歴を読み込み"""
    if not FOLLOW_HISTORY_FILE.exists():
        return {'follows': [], 'last_run': None}
    with open(FOLLOW_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_follow_history(history):
    """フォロー履歴を保存"""
    with open(FOLLOW_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def search_target_users(client, hashtag, max_results=20):
    """
    ハッシュタグでツイートを検索し、投稿者を抽出
    
    Args:
        client: Tweepy Client
        hashtag: 検索ハッシュタグ
        max_results: 最大取得数
    
    Returns:
        list: ユーザーIDリスト
    """
    try:
        # 過去24時間のツイートを検索
        query = f"{hashtag} -is:retweet"
        tweets = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['author_id'],
        )
        
        if not tweets.data:
            return []
        
        # ユーザーIDを抽出
        user_ids = list(set([tweet.author_id for tweet in tweets.data]))
        return user_ids
    
    except Exception as e:
        print(f"[ERROR] ツイート検索失敗: {e}")
        return []


def get_user_info(client, user_ids):
    """
    ユーザー情報を取得
    
    Args:
        client: Tweepy Client
        user_ids: ユーザーIDリスト
    
    Returns:
        list: ユーザー情報のリスト
    """
    try:
        users = client.get_users(
            ids=user_ids,
            user_fields=['public_metrics', 'description', 'created_at']
        )
        
        if not users.data:
            return []
        
        return users.data
    
    except Exception as e:
        print(f"[ERROR] ユーザー情報取得失敗: {e}")
        return []


def should_follow(user):
    """
    フォローすべきユーザーか判定
    
    基準:
    - フォロワー数: 100-10,000（スパムアカウントを除外）
    - フォロー数 / フォロワー数 < 3（フォロバ期待）
    - 最近のツイート: 過去30日以内
    """
    metrics = user.public_metrics
    followers = metrics['followers_count']
    following = metrics['following_count']
    
    # フォロワー数チェック
    if followers < 100 or followers > 10000:
        return False
    
    # フォロー率チェック
    if followers > 0 and (following / followers) > 3:
        return False
    
    # アカウント作成日チェック（新しすぎるアカウントは除外）
    created_at = user.created_at
    if created_at > datetime.now(created_at.tzinfo) - timedelta(days=30):
        return False
    
    return True


def follow_user(client, user_id):
    """
    ユーザーをフォロー
    
    Args:
        client: Tweepy Client
        user_id: ユーザーID
    
    Returns:
        bool: 成功/失敗
    """
    try:
        client.follow_user(user_id)
        return True
    except Exception as e:
        print(f"[ERROR] フォロー失敗 (user_id: {user_id}): {e}")
        return False


def main():
    """メイン処理"""
    import tweepy
    
    # クライアント初期化
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    # フォロー履歴読み込み
    history = load_follow_history()
    
    # 今日のフォロー数をカウント
    today = datetime.now().date().isoformat()
    today_follows = [f for f in history['follows'] if f.get('date') == today]
    
    if len(today_follows) >= MAX_FOLLOWS_PER_DAY:
        print(f"[INFO] 本日のフォロー上限に達しました: {len(today_follows)}/{MAX_FOLLOWS_PER_DAY}")
        return
    
    # 1時間以内のフォロー数をカウント
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_follows = [
        f for f in history['follows']
        if datetime.fromisoformat(f['timestamp']) > one_hour_ago
    ]
    
    if len(recent_follows) >= MAX_FOLLOWS_PER_HOUR:
        print(f"[INFO] 1時間のフォロー上限に達しました: {len(recent_follows)}/{MAX_FOLLOWS_PER_HOUR}")
        return
    
    # フォロー済みユーザーIDリスト
    followed_user_ids = set(f['user_id'] for f in history['follows'])
    
    # ターゲットユーザーを検索
    print(f"[INFO] ターゲットユーザーを検索中...")
    target_user_ids = []
    
    for hashtag in TARGET_HASHTAGS:
        print(f"  検索中: {hashtag}")
        user_ids = search_target_users(client, hashtag, max_results=20)
        target_user_ids.extend(user_ids)
        time.sleep(2)  # レート制限対策
    
    # 重複除去 + フォロー済み除外
    target_user_ids = list(set(target_user_ids) - followed_user_ids)
    
    if not target_user_ids:
        print("[INFO] 新しいターゲットユーザーが見つかりませんでした")
        return
    
    print(f"[INFO] {len(target_user_ids)}人の候補ユーザーを発見")
    
    # ユーザー情報を取得
    users = get_user_info(client, target_user_ids)
    
    # フォロー実行
    follow_count = 0
    max_follow = min(
        MAX_FOLLOWS_PER_HOUR - len(recent_follows),
        MAX_FOLLOWS_PER_DAY - len(today_follows)
    )
    
    for user in users:
        if follow_count >= max_follow:
            break
        
        if not should_follow(user):
            continue
        
        # フォロー実行
        if follow_user(client, user.id):
            print(f"✅ フォロー成功: @{user.username} (フォロワー: {user.public_metrics['followers_count']})")
            
            # 履歴に追加
            history['follows'].append({
                'user_id': user.id,
                'username': user.username,
                'date': today,
                'timestamp': datetime.now().isoformat(),
            })
            
            follow_count += 1
            
            # レート制限対策（15秒待機）
            time.sleep(15)
    
    # 履歴更新
    history['last_run'] = datetime.now().isoformat()
    save_follow_history(history)
    
    print(f"\n[完了] {follow_count}人をフォローしました")
    print(f"本日の合計: {len(today_follows) + follow_count}/{MAX_FOLLOWS_PER_DAY}")


if __name__ == '__main__':
    main()
```

---

#### タスクC.2: 自動リプライスクリプト作成

**ファイル:** `scripts/twitter_auto_reply.py`

**機能:**
- メンションをチェック
- ゲーム関連の質問に自動回答
- スペック診断リンクを送信

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Auto Reply Bot
メンションに自動返信
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

# Twitter API設定
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# サイトURL
SITE_URL = 'https://pc-jisaku.com'

# 返信履歴ファイル
REPLY_HISTORY_FILE = Path(__file__).parent / 'twitter_reply_history.json'


def load_reply_history():
    """返信履歴を読み込み"""
    if not REPLY_HISTORY_FILE.exists():
        return {'replies': []}
    with open(REPLY_HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_reply_history(history):
    """返信履歴を保存"""
    with open(REPLY_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def extract_game_name(text):
    """
    テキストからゲーム名を抽出（簡易版）
    
    キーワード: "〇〇 動く？", "〇〇 スペック", "〇〇 推奨"
    """
    # パターンマッチング
    patterns = [
        r'(.+?)(?:は|が)?動く',
        r'(.+?)(?:の)?スペック',
        r'(.+?)(?:の)?推奨',
        r'(.+?)(?:を)?遊び',
        r'(.+?)(?:を)?プレイ',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            game_name = match.group(1).strip()
            # 不要な単語を除去
            game_name = game_name.replace('PC版', '').replace('Steam', '')
            game_name = game_name.strip()
            if len(game_name) > 2:
                return game_name
    
    return None


def generate_reply(mention_text, author_username):
    """
    メンション内容に応じた返信を生成
    """
    # ゲーム名を抽出
    game_name = extract_game_name(mention_text)
    
    if game_name:
        # ゲーム名が含まれている場合
        slug = game_name.lower().replace(' ', '-')
        url = f"{SITE_URL}/game/{slug}"
        
        reply = (
            f"@{author_username} こんにちは！\n\n"
            f"{game_name}の推奨スペックと互換性診断はこちらから確認できます👇\n"
            f"{url}\n\n"
            f"予算別PC構成も提案しています！"
        )
    else:
        # 一般的な返信
        reply = (
            f"@{author_username} こんにちは！\n\n"
            f"PCゲームの推奨スペックや互換性診断はこちら👇\n"
            f"{SITE_URL}\n\n"
            f"443ゲームに対応しています！"
        )
    
    return reply


def get_mentions(client, since_id=None):
    """
    メンションを取得
    
    Args:
        client: Tweepy Client
        since_id: 前回チェック以降のメンションのみ取得
    
    Returns:
        list: メンションのリスト
    """
    try:
        mentions = client.get_users_mentions(
            id=client.get_me().data.id,
            since_id=since_id,
            tweet_fields=['author_id', 'created_at'],
            expansions=['author_id'],
            max_results=10
        )
        
        if not mentions.data:
            return []
        
        return mentions.data
    
    except Exception as e:
        print(f"[ERROR] メンション取得失敗: {e}")
        return []


def reply_to_mention(client, mention_id, reply_text):
    """
    メンションに返信
    
    Args:
        client: Tweepy Client
        mention_id: メンションのツイートID
        reply_text: 返信テキスト
    
    Returns:
        bool: 成功/失敗
    """
    try:
        client.create_tweet(
            text=reply_text,
            in_reply_to_tweet_id=mention_id
        )
        return True
    except Exception as e:
        print(f"[ERROR] 返信失敗: {e}")
        return False


def main():
    """メイン処理"""
    import tweepy
    
    # クライアント初期化
    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    # 返信履歴読み込み
    history = load_reply_history()
    
    # 前回チェックしたツイートID
    last_mention_id = history.get('last_mention_id')
    
    # メンション取得
    mentions = get_mentions(client, since_id=last_mention_id)
    
    if not mentions:
        print("[INFO] 新しいメンションはありません")
        return
    
    print(f"[INFO] {len(mentions)}件の新しいメンションを発見")
    
    # 返信実行
    reply_count = 0
    
    for mention in mentions:
        # 既に返信済みか確認
        replied_ids = set(r['mention_id'] for r in history['replies'])
        if mention.id in replied_ids:
            continue
        
        # 返信テキスト生成
        reply_text = generate_reply(mention.text, mention.author_id)
        
        # 返信実行
        if reply_to_mention(client, mention.id, reply_text):
            print(f"✅ 返信成功: {mention.text[:50]}...")
            
            # 履歴に追加
            history['replies'].append({
                'mention_id': mention.id,
                'author_id': mention.author_id,
                'timestamp': datetime.now().isoformat(),
            })
            
            reply_count += 1
    
    # 最新のメンションIDを更新
    if mentions:
        history['last_mention_id'] = mentions[0].id
    
    # 履歴保存
    save_reply_history(history)
    
    print(f"\n[完了] {reply_count}件のメンションに返信しました")


if __name__ == '__main__':
    main()
```

---

#### タスクC.3: GitHub Actions に自動化ワークフローを追加

**ファイル:** `.github/workflows/twitter-engagement.yml`

```yaml
name: Twitter Engagement Bot

on:
  schedule:
    # 自動フォロー: 1日2回（9:00, 21:00 JST）
    - cron: '0 0,12 * * *'  # UTC 0:00 (JST 9:00), UTC 12:00 (JST 21:00)
  workflow_dispatch:  # 手動実行も可能

jobs:
  auto-follow:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install tweepy Pillow
      
      - name: Run Auto Follow Bot
        env:
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
          TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
        run: |
          python scripts/twitter_auto_follow.py
      
      - name: Commit follow history
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add scripts/twitter_follow_history.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update: Twitter follow history"
          git push

  auto-reply:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install tweepy
      
      - name: Run Auto Reply Bot
        env:
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
          TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
        run: |
          python scripts/twitter_auto_reply.py
      
      - name: Commit reply history
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add scripts/twitter_reply_history.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update: Twitter reply history"
          git push
```

---

## ✅ 実装チェックリスト

### Phase A: メタスコア画像
- [ ] `scripts/generate_metacritic_image.py` 作成
- [ ] テスト画像生成（3種類）
- [ ] `twitter_bot.py` に画像添付機能追加
- [ ] ローカルテスト（DRY RUN）
- [ ] 本番テスト（1回投稿）

### Phase B: 投稿パターン拡張
- [ ] `generate_tweet_patterns()` を10パターンに拡張
- [ ] ローカルテスト（全パターン確認）
- [ ] 本番デプロイ

### Phase C: フォロワー獲得
- [ ] `scripts/twitter_auto_follow.py` 作成
- [ ] `scripts/twitter_auto_reply.py` 作成
- [ ] `.github/workflows/twitter-engagement.yml` 作成
- [ ] ローカルテスト
- [ ] GitHub Actions設定
- [ ] 1週間モニタリング

---

## 📈 期待効果

| 指標 | 現在 | 1ヶ月後（予測） |
|------|------|----------------|
| インプレッション/ツイート | 10-50 | 100-500 |
| エンゲージメント率 | 0.5% | 2-3% |
| フォロワー数 | 48 | 100-200 |
| サイトクリック/週 | 不明 | 50-200 |

---

## 🚨 注意事項

### Twitter API制限
- **フォロー**: 1日最大400件（実装では200件に制限）
- **ツイート**: 1日最大300件（実装では3件）
- **リプライ**: 無制限（スパム判定に注意）

### スパム対策
- フォローは1時間15件まで
- 同じツイートに複数回返信しない
- ボットであることを隠さない（プロフィールに記載）

---

## 📞 実装サポート

この指示書を Claude Code に渡して実装を進めてください。

**実装順序（推奨）:**
1. Phase A（画像生成）→ 効果が最も高い
2. Phase B（投稿パターン）→ 簡単
3. Phase C（フォロワー獲得）→ 慎重に

---

**作成日:** 2026年3月3日  
**最終更新:** 2026年3月3日  
**作成者:** OpenClaw AI  
**対象読者:** Claude Code（コーディングエージェント）
