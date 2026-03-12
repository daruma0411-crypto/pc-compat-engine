#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Bot for PC Compatibility Checker
ゲーム互換性情報を自動投稿するTwitterボット（人間化版 v3）

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

from url_shortener import shorten_url

# Twitter API設定（環境変数から取得）
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# サイトURL
SITE_URL = os.getenv('SITE_URL', 'https://pc-compat-engine-production.up.railway.app')

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
    slug = slug.replace('・', '').replace('·', '').replace('‐', '-')
    slug = slug.replace('--', '-').replace('--', '-')  # 連続ハイフン除去
    return slug.strip('-')


def format_spec(spec):
    """スペック情報を整形"""
    if isinstance(spec, list):
        return spec[0].replace('™', '').replace('®', '').replace('(R)', '').strip()
    return str(spec).replace('™', '').replace('®', '').replace('(R)', '').strip()


def generate_hashtags(game, pattern_type, max_tags=2):
    """
    ツイート内容に応じて適切なハッシュタグを生成
    最大2つ（BOT感軽減）
    
    Args:
        game: ゲーム情報辞書
        pattern_type: ツイートパターンタイプ
        max_tags: 最大タグ数（デフォルト2）
    """
    game_tag = game['name'].replace(' ', '').replace(':', '').replace("'", '')

    type_tags = {
        'question': ['GPU相談', 'スペック相談', '動作環境'],
        'review': ['レビュー', 'おすすめゲーム', 'プレイ日記'],
        'troubleshoot': ['トラブルシューティング', 'PC不具合', '動作不良'],
        'casual': ['PCゲーム雑談', 'ゲーム好き', 'Steam'],
        'budget': ['予算PC', '自作PC', 'コスパPC'],
        'notebook': ['ゲーミングノート', 'ノートPC', 'モバイルゲーミング'],
        'report': ['ベンチマーク', 'PCスペック', '動作報告'],
        'compare': ['GPU比較', '自作PC', 'パーツ選び'],
        'negative': ['動作環境', 'PCゲーム', 'スペック不足'],
        'positive': ['おすすめゲーム', '神ゲー', 'PCゲーム'],
        'short': ['PCゲーム', 'Steam'],
        'blog': ['自作PC', 'PCパーツ', 'ブログ更新'],
        'opinion': ['PCゲーム', '自作PC'],
        'data': ['GPU価格', 'PCパーツ'],
    }

    extra_tags = type_tags.get(pattern_type, ['PCゲーム'])
    
    # max_tags=2の場合、ゲームタグ1つ + 追加タグ1つ = 合計2つ
    num_extra = min(max_tags - 1, len(extra_tags))
    selected = random.sample(extra_tags, num_extra) if num_extra > 0 else []
    all_tags = [game_tag] + selected
    
    # 念のため最大数チェック
    all_tags = all_tags[:max_tags]

    return ' '.join(f"#{tag}" for tag in all_tags)


def count_hashtags(text):
    """ツイート内のハッシュタグ数をカウント"""
    return text.count('#')


def ensure_max_hashtags(text, max_tags=2):
    """
    ツイート内のハッシュタグが上限を超えないように制限
    
    Args:
        text: ツイート文
        max_tags: 最大タグ数
    Returns:
        調整後のツイート文
    """
    current_count = count_hashtags(text)
    if current_count <= max_tags:
        return text
    
    # タグを抽出して上限数に制限
    lines = text.split('\n')
    result_lines = []
    tags_count = 0
    
    for line in lines:
        if '#' not in line:
            result_lines.append(line)
        else:
            # この行のタグを処理
            words = line.split()
            new_words = []
            for word in words:
                if word.startswith('#'):
                    if tags_count < max_tags:
                        new_words.append(word)
                        tags_count += 1
                else:
                    new_words.append(word)
            if new_words:
                result_lines.append(' '.join(new_words))
    
    return '\n'.join(result_lines)


def generate_tweet_patterns(game):
    """
    人間らしいツイート文を生成（30パターン）

    特徴:
    - 口語調・スラング混在
    - 感情表現豊か
    - 質問形・雑談風・報告風など多様
    - URLは短縮版を使用
    - ハッシュタグは最大2つまで
    """
    import urllib.parse
    name = game['name']
    steam_appid = game.get('steam_appid')
    
    if not steam_appid:
        # AppIDがない場合はスラッグを使用（レガシー対応）
        slug = game_slug(name)
        encoded_slug = urllib.parse.quote(slug)
        full_url = f"{SITE_URL}/game/{encoded_slug}"
    else:
        # 短縮URL形式（200文字超過エラー対策）
        full_url = f"{SITE_URL}/g/{steam_appid}"
    
    short_url = shorten_url(full_url)

    rec = game.get('specs', {}).get('recommended', {})
    gpu = format_spec(rec.get('gpu', ['不明'])) if rec.get('gpu') else '不明'
    cpu = format_spec(rec.get('cpu', ['不明'])) if rec.get('cpu') else '不明'
    ram = rec.get('ram_gb', '不明')

    # GPU名を略称化（人間らしく）
    gpu_short = gpu.replace('GeForce ', '').replace('NVIDIA ', '').replace('Radeon ', '')

    # (pattern_text, pattern_type) のタプルリスト
    patterns = [
        # === 雑談風 (casual) ===
        (
            f"{name}やりてぇんだけど\n"
            f"{gpu_short}あれば動くかな？\n\n"
            f"とりあえず調べてみた↓\n{short_url}",
            'casual'
        ),
        (
            f"{name}、クソ重いって聞いたけど\n"
            f"{gpu_short}なら余裕らしい\n\n"
            f"うちのPCで動くか確認→ {short_url}",
            'casual'
        ),
        (
            f"{name}買ったけど重すぎワロタ\n"
            f"推奨スペック詐欺やんけ\n\n"
            f"GPU: {gpu_short}\n"
            f"CPU: {cpu}\n"
            f"RAM: {ram}GB\n\n"
            f"{short_url}",
            'casual'
        ),

        # === 質問風 (question) ===
        (
            f"{gpu_short}で{name}って60fps出る？\n\n"
            f"推奨スペック見る限りギリギリっぽいけど...\n\n"
            f"詳細→ {short_url}",
            'question'
        ),
        (
            f"質問\n"
            f"{name}を快適に遊びたいんだけど\n"
            f"{gpu_short}と{cpu}ならいける？\n\n"
            f"スペック確認ツール↓\n{short_url}",
            'question'
        ),
        (
            f"{name}ってRAM {ram}GBないとキツイ？\n"
            f"うち16GBしかないんだけど\n\n"
            f"推奨スペック→ {short_url}",
            'question'
        ),

        # === 報告風 (report) ===
        (
            f"{name}、{gpu_short}でも普通に遊べたわ\n\n"
            f"推奨スペック:\n"
            f"・GPU: {gpu_short}\n"
            f"・CPU: {cpu}\n"
            f"・RAM: {ram}GB\n\n"
            f"{short_url}",
            'report'
        ),
        (
            f"{name}ベンチマーク結果\n"
            f"{gpu_short} / {cpu}\n"
            f"→ 1080p60fps安定\n\n"
            f"詳しいスペック→ {short_url}",
            'report'
        ),
        (
            f"【動作確認済み】\n"
            f"{name}\n"
            f"GPU: {gpu_short}\n"
            f"CPU: {cpu}\n"
            f"RAM: {ram}GB\n\n"
            f"{short_url}",
            'report'
        ),

        # === ネガティブ風 (negative) ===
        (
            f"{name}カクつきすぎて萎えた\n"
            f"{gpu_short}じゃ足りんのか？\n\n"
            f"推奨スペック確認→ {short_url}",
            'negative'
        ),
        (
            f"{name}、設定下げても重い...\n"
            f"やっぱりGPU買い替え時か\n\n"
            f"推奨: {gpu_short}\n"
            f"詳細→ {short_url}",
            'negative'
        ),
        (
            f"{name}ロード長すぎ問題\n"
            f"SSDに入れても遅い\n"
            f"これCPUが原因？\n\n"
            f"推奨CPU: {cpu}\n"
            f"{short_url}",
            'negative'
        ),

        # === ポジティブ風 (positive) ===
        (
            f"{name}めっちゃ面白い！\n"
            f"{gpu_short}でヌルヌル動いてる\n\n"
            f"推奨スペック→ {short_url}",
            'positive'
        ),
        (
            f"{name}神ゲーすぎる\n"
            f"グラフィック最高設定で快適\n\n"
            f"GPU: {gpu_short}\n"
            f"詳細→ {short_url}",
            'positive'
        ),
        (
            f"{name}、想像以上に最適化されてるわ\n"
            f"{gpu_short}でも余裕で遊べる\n\n"
            f"{short_url}",
            'positive'
        ),

        # === 比較風 (compare) ===
        (
            f"{name}、{gpu_short}とRTX 4060どっちがいい？\n\n"
            f"推奨スペック見る限り\n"
            f"{gpu_short}で十分っぽい\n\n"
            f"{short_url}",
            'compare'
        ),
        (
            f"{name}を1080pと1440pで比較\n"
            f"1080p: {gpu_short}で余裕\n"
            f"1440p: RTX 4070推奨\n\n"
            f"詳細→ {short_url}",
            'compare'
        ),
        (
            f"{name}、最低スペックと推奨スペックの差エグい\n\n"
            f"推奨: {gpu_short} / {cpu}\n"
            f"最低: GTX 1660 / Core i5\n\n"
            f"{short_url}",
            'compare'
        ),

        # === 予算風 (budget) ===
        (
            f"予算15万円で{name}を快適に遊びたい\n\n"
            f"推奨構成:\n"
            f"・GPU: {gpu_short}\n"
            f"・CPU: {cpu}\n"
            f"・RAM: {ram}GB\n\n"
            f"{short_url}",
            'budget'
        ),
        (
            f"{name}用にPC組むなら\n"
            f"{gpu_short} + {cpu}で20万くらい？\n\n"
            f"詳しいスペック→ {short_url}",
            'budget'
        ),
        (
            f"コスパ重視で{name}遊びたい人向け\n"
            f"{gpu_short}（3万円台）で十分いける\n\n"
            f"{short_url}",
            'budget'
        ),

        # === トラブルシューティング風 (troubleshoot) ===
        (
            f"{name}が起動しない...\n"
            f"GPUドライバ更新したら直った\n\n"
            f"推奨: {gpu_short}\n"
            f"{short_url}",
            'troubleshoot'
        ),
        (
            f"{name}クラッシュ多発する人\n"
            f"RAM {ram}GB以上にしたら安定したわ\n\n"
            f"詳細→ {short_url}",
            'troubleshoot'
        ),
        (
            f"{name}のフレームレート出ない問題\n"
            f"VSync切ったら改善した\n\n"
            f"推奨GPU: {gpu_short}\n"
            f"{short_url}",
            'troubleshoot'
        ),

        # === ノートPC風 (notebook) ===
        (
            f"ゲーミングノートで{name}動く？\n\n"
            f"推奨: {gpu_short}\n"
            f"→ RTX 4060 Laptop以上なら余裕\n\n"
            f"{short_url}",
            'notebook'
        ),
        (
            f"{name}、薄型ノートじゃキツイよな\n"
            f"最低でも{gpu_short}相当は欲しい\n\n"
            f"{short_url}",
            'notebook'
        ),

        # === 短文・キャッチー (short) ===
        (
            f"{name}\n"
            f"{gpu_short}あれば余裕\n\n"
            f"{short_url}",
            'short'
        ),
        (
            f"{name}推奨スペック\n"
            f"GPU: {gpu_short}\n"
            f"CPU: {cpu}\n\n"
            f"{short_url}",
            'short'
        ),
        (
            f"{name}動作環境まとめ\n{short_url}",
            'short'
        ),
        (
            f"{name}\n"
            f"重いけど面白い\n\n"
            f"推奨→ {short_url}",
            'short'
        ),
    ]

    # ランダム選択
    text, pattern_type = random.choice(patterns)

    # ハッシュタグ付与（ツイート文にまだタグがなければ追加）
    current_tag_count = count_hashtags(text)
    if current_tag_count == 0:
        # タグが無い場合は追加
        hashtags = generate_hashtags(game, pattern_type, max_tags=2)
        text = text + f"\n\n{hashtags}"
    elif current_tag_count > 2:
        # タグが3個以上ある場合は2個に制限
        text = ensure_max_hashtags(text, max_tags=2)

    return text


def generate_question_tweet():
    """質問・意見型ツイート（BOT感脱却）"""
    patterns = [
        "みんなGPU何使ってる？\n筆者はRTX 4070だけどそろそろ5070気になる",
        "ゲーミングPC組むとき一番金かけるパーツどこ？\n個人的にはGPU>CPU>メモリの順",
        "正直RTX 4060で十分じゃね？って思ってるんだけど\n4070にする価値ある場面って何",
        "PC自作で一番やらかした失敗教えて\n自分は電源ケチって不安定になった",
        "ゲーミングモニター、144Hzと240Hzの違いって体感できる？\nFPS系やる人教えて",
        "メモリ16GBと32GB、ゲーム用途ならどっち？\n最近のゲーム32GB推奨増えてきたよね",
        "中古GPUって買う？買わない？\nマイニング落ちは避けるべき？",
        "BTOと自作、初心者にはどっちを勧める？\n自作の達成感は代えがたいけど",
        "SSD、NVMe Gen4とGen3って体感差ある？\nゲームのロード時間変わるのかな",
        "空冷vs簡易水冷\n見た目は水冷がカッコいいけどメンテ考えると空冷かなあ",
        "PCゲーマーの皆さん、電気代月いくらくらい？\nハイエンドPC+モニター2枚だとヤバそう",
        "今からPC組むならIntelとAMDどっち選ぶ？\nRyzen 7 7800X3Dが鉄板って聞くけど",
        "Steamのウィッシュリストに入れっぱなしのゲーム何本ある？\n自分は47本...",
        "PCケースのエアフロー気にする派？見た目重視派？\n最近のケースはどっちも優秀だけど",
        "GPUの最適な買い替えサイクルって何年？\n2年で変える人いる？",
        "ゲーム中にタスクマネージャー開く癖ある人いない？\nGPU使用率つい気になる",
        "PCパーツの価格チェック、毎日してる人いる？\n底値狙いは疲れるけどやめられない",
        "フルHDで十分って人、WQHD試したことある？\n一度体験すると戻れなくなるよ",
        "PC自作始めたきっかけ何だった？\n自分はBTOの電源が壊れて交換したのが最初",
        "最近のゲーム、推奨スペック上がりすぎじゃない？\nRTX 4070が「推奨」はキツイ",
    ]
    text = random.choice(patterns)
    
    # ハッシュタグは最大2個まで
    hashtags_list = random.sample(['自作PC', 'PCゲーム', 'GPU'], min(2, 2))
    hashtags = ' '.join(f"#{tag}" for tag in hashtags_list)
    text += f"\n\n{hashtags}"
    
    # 念のためタグ数チェック
    text = ensure_max_hashtags(text, max_tags=2)
    
    return text, 'opinion'


def generate_data_tweet():
    """データ分析型ツイート（独自DB活用）"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from blog_data_loader import load_gpu_prices, load_performance_scores
        gpu_prices = load_gpu_prices()
        perf = load_performance_scores()
    except Exception:
        return None, 'data'

    patterns = []

    # GPU最安値パターン
    target_chips = ['RTX 4060', 'RTX 4070', 'RTX 5070', 'RTX 4060 Ti']
    for chip_name in target_chips:
        for key, data in gpu_prices.items():
            if chip_name.lower() in key.lower():
                price = data['min_price']
                patterns.append(
                    f"{key}の最安値 今{price:,}円\n"
                    f"VRAM {data.get('vram_gb', '?')}GB / {data['count']}製品比較\n"
                    f"価格.com調べ\n\n"
                    f"{SITE_URL}"
                )
                break

    # 性能比較パターン
    if perf.get('gpu') and len(perf['gpu']) >= 5:
        top5 = perf['gpu'][:5]
        lines = "GPU性能ランキング TOP5\n\n"
        for i, g in enumerate(top5, 1):
            lines += f"{i}. {g['name']}: {g['score']}点\n"
        lines += f"\n14,000件の価格DBから算出\n{SITE_URL}"
        patterns.append(lines)

    if not patterns:
        return None, 'data'

    text = random.choice(patterns)
    
    # ハッシュタグ追加（最大2個）
    current_count = count_hashtags(text)
    if current_count < 2:
        remaining_tags = 2 - current_count
        possible_tags = ['GPU価格', 'PCパーツ']
        tags_to_add = random.sample(possible_tags, min(remaining_tags, len(possible_tags)))
        hashtags = ' '.join(f"#{tag}" for tag in tags_to_add)
        text += f"\n\n{hashtags}"
    
    # 念のためタグ数チェック
    text = ensure_max_hashtags(text, max_tags=2)
    
    return text, 'data'


def post_tweet(text, dry_run=True, image_path=None):
    """ツイートを投稿（画像添付対応、DRY RUNモードではコンソール出力のみ）"""
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

    # Twitter API v2での投稿（画像添付対応）
    try:
        import tweepy

        # v2クライアント
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )

        # 画像がある場合はv1 APIでアップロード
        media_ids = None
        if image_path and os.path.exists(str(image_path)):
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY,
                TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN,
                TWITTER_ACCESS_SECRET
            )
            api_v1 = tweepy.API(auth)
            media = api_v1.media_upload(str(image_path))
            media_ids = [media.media_id]
            print(f"[OK] 画像アップロード成功: media_id={media.media_id}")

        # ツイート投稿
        if media_ids:
            response = client.create_tweet(text=text, media_ids=media_ids)
        else:
            response = client.create_tweet(text=text)

        tweet_id = response.data['id']
        print(f"[SUCCESS] ツイート投稿成功! ID: {tweet_id}")
        print(f"[SUCCESS] URL: https://twitter.com/i/web/status/{tweet_id}")

        # 一時画像ファイルを削除
        if image_path and os.path.exists(str(image_path)):
            os.remove(str(image_path))
            print(f"[OK] 一時画像を削除: {image_path}")

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


def post_thread(tweets, dry_run=True):
    """スレッド投稿（3連投）"""
    if dry_run:
        print("=" * 60)
        print("[DRY RUN] スレッド投稿:")
        for i, t in enumerate(tweets, 1):
            print(f"--- {i}/{len(tweets)} ---")
            print(t)
        print("=" * 60)
        return True

    try:
        import tweepy
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )

        prev_id = None
        for i, text in enumerate(tweets):
            if prev_id:
                response = client.create_tweet(text=text, in_reply_to_tweet_id=prev_id)
            else:
                response = client.create_tweet(text=text)
            prev_id = response.data['id']
            print(f"[SUCCESS] スレッド {i+1}/{len(tweets)} 投稿: ID={prev_id}")

        return True
    except Exception as e:
        print(f"[ERROR] スレッド投稿失敗: {e}")
        return False


def generate_thread_tweets(game):
    """スレッド用3連投を生成"""
    import urllib.parse
    name = game['name']
    steam_appid = game.get('steam_appid')
    
    if not steam_appid:
        slug = game_slug(name)
        encoded_slug = urllib.parse.quote(slug)
        full_url = f"{SITE_URL}/game/{encoded_slug}"
    else:
        full_url = f"{SITE_URL}/g/{steam_appid}"
    
    short_url = shorten_url(full_url)

    rec = game.get('specs', {}).get('recommended', {})
    gpu = format_spec(rec.get('gpu', ['不明'])) if rec.get('gpu') else '不明'
    gpu_short = gpu.replace('GeForce ', '').replace('NVIDIA ', '').replace('Radeon ', '')
    ram = rec.get('ram_gb', '不明')

    tweets = [
        f"【{name}の推奨スペック解説】\n\n"
        f"推奨GPU: {gpu_short}\n"
        f"推奨RAM: {ram}GB\n\n"
        f"このゲームを快適に遊ぶために必要な構成を3ツイートで解説します",

        f"GPU選びのポイント\n\n"
        f"1080p60fpsなら{gpu_short}で十分\n"
        f"WQHD以上ならRTX 4070以上推奨\n\n"
        f"コスパ重視ならRTX 4060（4万円台〜）が鉄板\n"
        f"価格.com調べ",

        f"まとめ\n\n"
        f"・{name}は{gpu_short}あれば快適\n"
        f"・予算10〜15万で組める\n"
        f"・詳細スペック→ {short_url}\n\n"
        f"#PCゲーム",
    ]
    return tweets


def load_blog_history():
    """ブログ生成履歴を読み込む"""
    blog_history_path = Path(__file__).parent.parent / 'static' / 'blog' / 'generation_history.json'
    if not blog_history_path.exists():
        return []
    with open(blog_history_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_recently_posted_blog_urls(days=14):
    """直近N日以内に投稿済みのブログ記事URLを取得"""
    history = load_history()
    cutoff = datetime.now().timestamp() - (days * 86400)
    posted_urls = set()
    for entry in history:
        if entry.get('name') != '[blog]':
            continue

        posted_at = entry.get('posted_at', '')
        try:
            entry_time = datetime.fromisoformat(posted_at).timestamp()
            if entry_time <= cutoff:
                continue
        except (ValueError, TypeError):
            pass  # パース失敗時は安全側で除外対象に含める

        # blog_urlフィールドから取得
        blog_url = entry.get('blog_url', '')
        if blog_url:
            posted_urls.add(blog_url)
            continue

        # フォールバック: tweet_textからブログURLを抽出（過去の履歴互換）
        tweet_text = entry.get('tweet_text', '')
        for line in tweet_text.split('\n'):
            stripped = line.strip()
            if f'{SITE_URL}/blog/' in stripped:
                posted_urls.add(stripped)
                break

    return posted_urls


def generate_blog_tweet(target_filename=None):
    """ブログ記事紹介ツイートを生成（重複チェック付き）

    Args:
        target_filename: 指定時はその記事を強制選択
    Returns:
        (tweet_text, pattern_type, full_blog_url) or (None, 'blog', None)
    """
    blog_history = load_blog_history()
    if not blog_history:
        return None, 'blog', None

    # ファイル名指定時はその記事を直接選択
    if target_filename:
        matched = [a for a in blog_history if a['filename'] == target_filename]
        if matched:
            article = matched[-1]
            print(f"[INFO] 指定記事を選択: {article['title']} ({target_filename})")
        else:
            print(f"[ERROR] 指定ファイル名が見つかりません: {target_filename}")
            return None, 'blog', None
    else:
        # 直近14日以内に投稿済みのブログURLを取得
        recently_posted = get_recently_posted_blog_urls(days=14)
        if recently_posted:
            print(f"[INFO] 直近14日以内に投稿済みブログURL: {len(recently_posted)}件")

        # 直近10記事から未投稿の記事を抽出
        recent = blog_history[-10:]
        candidates = [
            a for a in recent
            if f"{SITE_URL}/blog/{a['filename']}" not in recently_posted
        ]

        if not candidates:
            print("[INFO] ブログ記事が全て直近14日以内に投稿済み → ゲーム投稿にフォールバック")
            return None, 'blog', None

        article = random.choice(candidates)
    title = article['title']
    filename = article['filename']

    full_url = f"{SITE_URL}/blog/{filename}"
    short_url = shorten_url(full_url)

    patterns = [
        (f"記事書きました\n\n{title}\n\n{short_url}", 'blog'),
        (f"新記事↓\n{title}\n\n価格.comの最新データ使ってます\n{short_url}", 'blog'),
        (f"毎日更新中\n\n{title}\n{short_url}", 'blog'),
        (f"今日のPC記事\n{title}\n\n{short_url}", 'blog'),
        (f"これ需要あると思う\n\n{title}\n{short_url}", 'blog'),
        (f"実データで書いた記事\n{title}\n\n価格.com調べの最新価格入り\n{short_url}", 'blog'),
        (f"ブログ更新\n{title}\n\n{short_url}", 'blog'),
        (f"PC自作勢向け\n{title}\n\n{short_url}", 'blog'),
    ]

    # 週刊レポートには専用パターン
    if 'weekly_report' in article.get('template', ''):
        patterns.extend([
            (f"今週のパーツ相場まとめ\n\n{title}\n\n{short_url}", 'blog'),
            (f"GPU値下がってきた\n詳しくは↓\n\n{short_url}", 'blog'),
            (f"毎週恒例パーツ価格チェック\n{title}\n{short_url}", 'blog'),
        ])

    text, pattern_type = random.choice(patterns)
    print(f"[INFO] ブログ記事選択: {title} ({filename})")
    return text, pattern_type, full_url


def main():
    import argparse
    parser = argparse.ArgumentParser(description='PC Compatibility Checker Twitter Bot')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行（実際に投稿しない）')
    parser.add_argument('--force-blog', action='store_true', help='ブログ記事紹介を強制投稿')
    parser.add_argument('--blog-filename', type=str, default=None, help='投稿するブログ記事のファイル名を指定')
    args = parser.parse_args()

    # 投稿タイプ選択（Phase 2-2: 多様化）
    # ブログ15% / ゲーム35% / 質問・意見30% / データ分析20%
    roll = random.random()
    if args.force_blog:
        roll = 0.0  # ブログモードを強制
        print("[INFO] --force-blog: ブログ記事紹介を強制実行")
    blog_history = load_blog_history()

    # 月曜のみ10%確率でスレッド投稿（Phase 2-3）
    is_monday = datetime.now().weekday() == 0
    if is_monday and random.random() < 0.1:
        print("[モード] スレッド投稿（月曜日特別）")
        games = load_games()
        history = load_history()
        selected_game = select_game(games, history)
        print(f"[選択] {selected_game['name']}")

        tweets = generate_thread_tweets(selected_game)
        success = post_thread(tweets, dry_run=args.dry_run)

        if success and not args.dry_run:
            history.append({
                'name': selected_game['name'],
                'posted_at': datetime.now().isoformat(),
                'tweet_text': tweets[0],
                'type': 'thread',
                'has_image': False,
            })
            save_history(history)
        if not success:
            sys.exit(1)
        return

    if roll < 0.15 and blog_history:
        # ブログ紹介ツイート (15%)
        print("[モード] ブログ記事紹介ツイート")
        tweet_text, pattern_type, full_blog_url = generate_blog_tweet(target_filename=args.blog_filename)
        if tweet_text:
            # ハッシュタグ追加（最大2個）
            current_count = count_hashtags(tweet_text)
            if current_count < 2:
                remaining_tags = 2 - current_count
                possible_tags = ['自作PC', 'PCパーツ', 'ブログ更新', 'GPU', 'ゲーミングPC']
                hashtags_list = random.sample(possible_tags, min(remaining_tags, len(possible_tags)))
                hashtags = ' '.join(f"#{tag}" for tag in hashtags_list)
                tweet_text = tweet_text + f"\n\n{hashtags}"
            
            # 念のためタグ数チェック
            tweet_text = ensure_max_hashtags(tweet_text, max_tags=2)

            success = post_tweet(tweet_text, dry_run=args.dry_run)
            if success and not args.dry_run:
                history = load_history()
                history.append({
                    'name': '[blog]',
                    'posted_at': datetime.now().isoformat(),
                    'tweet_text': tweet_text,
                    'blog_url': full_blog_url,
                    'has_image': False,
                })
                save_history(history)
                print(f"[OK] 投稿履歴を更新しました (blog_url: {full_blog_url})")
            if not success:
                sys.exit(1)
            return
        else:
            print("[INFO] ブログ投稿スキップ → フォールバック")

    if roll < 0.45:
        # 質問・意見ツイート (30%)
        print("[モード] 質問・意見ツイート")
        tweet_text, pattern_type = generate_question_tweet()
        success = post_tweet(tweet_text, dry_run=args.dry_run)
        if success and not args.dry_run:
            history = load_history()
            history.append({
                'name': '[opinion]',
                'posted_at': datetime.now().isoformat(),
                'tweet_text': tweet_text,
                'has_image': False,
            })
            save_history(history)
        if not success:
            sys.exit(1)
        return

    if roll < 0.65:
        # データ分析ツイート (20%) — GPU価格画像付き
        print("[モード] データ分析ツイート")
        tweet_text, pattern_type = generate_data_tweet()
        if tweet_text:
            # GPU価格チャート画像を生成
            data_image = None
            try:
                from generate_gpu_price_chart import generate_gpu_price_chart
                data_image = generate_gpu_price_chart()
                print(f"[OK] GPU価格チャート画像: {data_image}")
            except Exception as e:
                print(f"[WARN] GPU価格チャート生成スキップ: {e}")

            success = post_tweet(tweet_text, dry_run=args.dry_run, image_path=data_image)
            if success and not args.dry_run:
                history = load_history()
                history.append({
                    'name': '[data]',
                    'posted_at': datetime.now().isoformat(),
                    'tweet_text': tweet_text,
                    'has_image': data_image is not None,
                })
                save_history(history)
            if not success:
                sys.exit(1)
            return
        else:
            print("[INFO] データツイート生成失敗 → ゲーム投稿にフォールバック")

    # ゲームスペックツイート (35% + フォールバック)
    print("[モード] ゲームスペックツイート")

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

    # スペックカード画像生成（全投稿に画像を付ける）
    image_path = None
    try:
        from generate_spec_card import generate_spec_card
        rec = selected_game.get('specs', {}).get('recommended', {})
        gpu_img = format_spec(rec.get('gpu', ['不明'])) if rec.get('gpu') else '不明'
        cpu_img = format_spec(rec.get('cpu', ['不明'])) if rec.get('cpu') else '不明'
        ram_img = rec.get('ram_gb', 8)
        storage_img = rec.get('storage_gb')
        meta_score = selected_game.get('metacritic_score')
        image_dir = Path(__file__).parent / 'temp_images'
        image_dir.mkdir(exist_ok=True)
        safe_name = selected_game['name'].replace(' ', '_').replace('/', '_')[:40]
        image_path = str(image_dir / f"spec_{safe_name}.png")
        generate_spec_card(
            game_name=selected_game['name'],
            gpu=gpu_img,
            cpu=cpu_img,
            ram_gb=ram_img if isinstance(ram_img, int) else 8,
            storage_gb=storage_img,
            metacritic_score=meta_score if meta_score and meta_score > 0 else None,
            output_path=image_path,
        )
        print(f"[OK] スペックカード画像生成: {image_path}")
    except Exception as e:
        print(f"[WARN] 画像生成スキップ: {e}")
        image_path = None

    # 投稿
    success = post_tweet(tweet_text, dry_run=args.dry_run, image_path=image_path)

    if success and not args.dry_run:
        # 履歴に追加
        history.append({
            'name': selected_game['name'],
            'posted_at': datetime.now().isoformat(),
            'tweet_text': tweet_text,
            'has_image': image_path is not None,
        })
        save_history(history)
        print("[OK] 投稿履歴を更新しました")

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
