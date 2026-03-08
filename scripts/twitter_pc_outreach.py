#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter PC Outreach Bot
X上でPC関連の悩み・相談をしているユーザーを自動検索し、
実データ（GPU価格・ゲームスペック・性能スコア）を織り込んだリプライを自動送信する。

使い方:
  python scripts/twitter_pc_outreach.py --dry-run  # 検索・生成のみ（投稿しない）
  python scripts/twitter_pc_outreach.py             # 本番実行
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from url_shortener import shorten_url

# ────────────────────────────────────────
# 定数
# ────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
HISTORY_FILE = SCRIPT_DIR / "twitter_outreach_history.json"
SITE_URL = "https://pc-compat-engine-production.up.railway.app"

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_API_URL = "https://api.x.ai/v1/responses"
XAI_MODEL = "grok-4-1-fast"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")

MAX_REPLIES_PER_RUN = 10
REPLY_COOLDOWN_DAYS = 7
LINK_PROBABILITY = 0.2

# ────────────────────────────────────────
# 検索クエリ（21本、毎回ランダム7本選択）
# ────────────────────────────────────────
ALL_QUERIES = [
    # BTO/自作検討
    "BTO 検討 パソコン",
    "自作PC 初めて",
    "PC 構成 相談",
    # スペック相談
    "GPU おすすめ 2025",
    "グラボ 悩む",
    "スペック 足りる ゲーム",
    # 予算相談
    "ゲーミングPC 予算",
    "コスパ GPU おすすめ",
    "自作 安く 組みたい",
    # パフォーマンス
    "ゲーム 重い PC",
    "フレームレート 落ちる",
    "カクつく 設定",
    # 価格動向
    "GPU 値下げ",
    "グラボ 安くなった",
    "RTX 価格 最安",
    # 購入報告
    "グラボ 買った 報告",
    "自作PC 完成 構成",
    "BTO 届いた レビュー",
    # 追加
    "モンハン ワイルズ スペック",
    "RTX 5070 レビュー",
    "ゲーミングPC 初心者 おすすめ",
]

# スパムキーワード
SPAM_KEYWORDS = [
    "airdrop", "giveaway", "副業", "稼ぐ", "プレゼント企画",
    "フォロー&RT", "懸賞", "当選", "LINE登録", "無料配布",
    "投資", "仮想通貨", "FX", "バイナリー", "アフィリエイト",
]

# 除外アカウント（公式ブランド等）
EXCLUDED_ACCOUNTS = [
    "nvidia_jp", "nvidiageforce", "msijapan", "maboroshi_msi",
    "asaboroshi_msi", "daboroshi_msi", "dospara_web", "dospara_parts",
    "mouse_jpn", "tsikimu_jp", "asaboroshi", "amd_jp", "aaboroshi",
    "intelgaming_jp", "galleria_gm", "corsairjp", "aboroshi",
    "akaboroshi", "kaboroshi", "sycom_jp",
]

# ────────────────────────────────────────
# Phase 1: Discovery（xAI x_search）
# ────────────────────────────────────────
DISCOVERY_SYSTEM_PROMPT = """あなたはX（Twitter）でPC自作・BTO・ゲーミングPCに関する投稿を検索するアシスタントです。

## タスク
検索クエリに基づいてX上の投稿を検索し、PC関連で悩んでいる・相談している・報告しているユーザーの投稿を見つけてください。

## グレード判定
- **S級**: 具体的なスペック・予算を挙げて相談している（例：「15万でゲーミングPC組みたい」「RTX 4060とRTX 4070どっちがいい？」）
- **A級**: GPU/CPU/ゲーム名を挙げて検討・購入報告（例：「RTX 4060買った」「モンハンワイルズのスペック確認したい」）
- **B級**: 一般的なPC関連の投稿（例：「ゲーミングPC欲しい」「パソコン重い」）
- **C級**: 内容薄い・関連低い → 除外

## 除外対象
- BOT・スパム・広告アカウント
- 企業公式の宣伝投稿
- airdrop, giveaway, 副業系
- フォロワー5万超の大手インフルエンサー
- 内容のないRT・引用のみ

## 回答フォーマット
必ず以下のJSON配列を ```json...``` コードブロックで返してください。見つからない場合は空配列 [] を返してください。

```json
[
  {
    "post_url": "https://x.com/username/status/1234567890",
    "poster_account": "@username",
    "grade": "S",
    "topic_type": "budget_build | gpu_recommendation | game_spec | performance_issue | price_report | purchase_report | general_pc",
    "post_summary": "投稿内容の要約（日本語）",
    "mentioned_gpu": "RTX 4060",
    "mentioned_cpu": "",
    "mentioned_game": "モンハンワイルズ",
    "mentioned_budget": "15万",
    "tone": "casual | technical | frustrated | excited"
  }
]
```

重要: 最近（直近3日以内）の投稿を優先してください。
"""


def discover_posts(queries: list[str]) -> list[dict]:
    """xAI x_search で PC関連投稿を検索"""
    import requests

    if not XAI_API_KEY:
        print("[FATAL] XAI_API_KEY が未設定です", flush=True)
        sys.exit(1)

    all_posts = []

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] 検索: {query}", flush=True)

        since_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        user_prompt = (
            f"以下のキーワードでX（Twitter）を検索し、PC関連の相談・悩み・報告投稿を見つけてください。\n\n"
            f"検索キーワード: {query}\n"
            f"対象期間: {since_date} 以降の投稿\n\n"
            f"日本語の投稿を優先してください。最大10件まで。"
        )

        payload = {
            "model": XAI_MODEL,
            "temperature": 0.3,
            "instructions": DISCOVERY_SYSTEM_PROMPT,
            "input": user_prompt,
            "tools": [{"type": "x_search"}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}",
        }

        try:
            resp = requests.post(XAI_API_URL, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            output_text = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            output_text += c.get("text", "")

            posts = _parse_json_response(output_text)
            print(f"    → {len(posts)}件発見", flush=True)
            all_posts.extend(posts)

        except Exception as e:
            print(f"    [ERROR] {e}", flush=True)

        # API レート制限対策
        if i < len(queries):
            time.sleep(1)

    return all_posts


def _parse_json_response(text: str) -> list:
    """JSON配列をパース（```json...``` ブロック対応）"""
    m = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    return []


# ────────────────────────────────────────
# Phase 2: Filtering
# ────────────────────────────────────────
def filter_posts(posts: list[dict], history: dict) -> list[dict]:
    """スパム除外・グレード判定・履歴チェック"""
    replied_tweets = {r["target_tweet_id"] for r in history.get("replies", [])}
    recent_users = set()
    cutoff = datetime.now() - timedelta(days=REPLY_COOLDOWN_DAYS)
    for r in history.get("replies", []):
        try:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts > cutoff:
                recent_users.add(r["target_account"].lower())
        except (ValueError, KeyError):
            pass

    filtered = []
    for post in posts:
        grade = post.get("grade", "C").upper()
        account = post.get("poster_account", "").lower().lstrip("@")
        url = post.get("post_url", "")
        summary = post.get("post_summary", "").lower()

        # C級除外
        if grade == "C":
            continue

        # tweet_id 抽出
        tweet_id = _extract_tweet_id(url)
        if not tweet_id:
            continue

        # 重複チェック
        if tweet_id in replied_tweets:
            continue

        # 同一ユーザー7日間禁止
        if account in recent_users:
            continue

        # スパムキーワード
        if any(kw in summary for kw in SPAM_KEYWORDS):
            continue

        # 公式ブランドアカウント除外
        if account in EXCLUDED_ACCOUNTS:
            continue

        post["_tweet_id"] = tweet_id
        post["_account_clean"] = account
        filtered.append(post)

    # Grade S > A > B の優先順でソート
    grade_order = {"S": 0, "A": 1, "B": 2}
    filtered.sort(key=lambda p: grade_order.get(p.get("grade", "B"), 2))

    # 最大件数制限
    return filtered[:MAX_REPLIES_PER_RUN]


def _extract_tweet_id(url: str) -> str:
    """post_url から tweet_id を抽出"""
    m = re.search(r"/status/(\d+)", url)
    return m.group(1) if m else ""


# ────────────────────────────────────────
# Phase 3: Enrichment（blog_data_loader.py 流用）
# ────────────────────────────────────────
def enrich_post(post: dict) -> dict:
    """投稿内容に対応する実データを付与"""
    try:
        from blog_data_loader import (
            load_gpu_prices,
            load_game_specs,
            load_performance_scores,
            load_cpu_prices,
        )
    except ImportError:
        # blog_data_loader.py が同ディレクトリにない場合
        sys.path.insert(0, str(SCRIPT_DIR))
        from blog_data_loader import (
            load_gpu_prices,
            load_game_specs,
            load_performance_scores,
            load_cpu_prices,
        )

    context = {}

    # GPU情報
    mentioned_gpu = post.get("mentioned_gpu", "")
    if mentioned_gpu:
        gpu_prices = load_gpu_prices()
        for chip, data in gpu_prices.items():
            if mentioned_gpu.lower().replace(" ", "") in chip.lower().replace(" ", ""):
                context["gpu_info"] = {
                    "chip": chip,
                    "min_price": data["min_price"],
                    "vram_gb": data.get("vram_gb"),
                    "tdp_w": data.get("tdp_w"),
                    "count": data["count"],
                }
                break

    # ゲーム情報
    mentioned_game = post.get("mentioned_game", "")
    if mentioned_game:
        game_data = load_game_specs(mentioned_game)
        if game_data:
            specs = game_data.get("specs", {})
            rec = specs.get("recommended", {})
            context["game_info"] = {
                "name": game_data["name"],
                "steam_appid": game_data.get("steam_appid") or game_data.get("appid"),
                "rec_gpu": rec.get("gpu", []),
                "rec_cpu": rec.get("cpu", []),
                "rec_ram": rec.get("ram_gb"),
                "metacritic": game_data.get("metacritic_score"),
            }

    # 予算に応じたGPU候補
    mentioned_budget = post.get("mentioned_budget", "")
    if mentioned_budget:
        budget_match = re.search(r"(\d+)", mentioned_budget.replace(",", ""))
        if budget_match:
            budget_yen = int(budget_match.group(1))
            # 「万」が含まれていたら万円単位
            if "万" in mentioned_budget:
                budget_yen *= 10000
            elif budget_yen < 1000:
                budget_yen *= 10000  # 数字だけなら万円と推定

            gpu_budget = int(budget_yen * 0.4)
            gpu_prices = load_gpu_prices()
            candidates = [
                (chip, data)
                for chip, data in gpu_prices.items()
                if data["min_price"] <= gpu_budget
            ]
            candidates.sort(key=lambda x: x[1]["min_price"], reverse=True)
            context["budget_gpu_candidates"] = [
                {"chip": c[0], "price": c[1]["min_price"], "vram": c[1].get("vram_gb")}
                for c in candidates[:3]
            ]

    # 性能スコア（主要GPU）
    perf = load_performance_scores()
    if perf.get("gpu"):
        context["top_gpus"] = [
            {"name": g["name"], "score": g["score"]}
            for g in perf["gpu"][:5]
        ]

    post["_enrichment"] = context
    return post


# ────────────────────────────────────────
# Phase 4: Reply Generation（Claude Sonnet API）
# ────────────────────────────────────────
REPLY_SYSTEM_PROMPT = """あなたはX（Twitter）で自然にPC自作の知識を共有する20代後半〜30代のPCユーザーです。

## 人格設定
- PC自作経験3〜5年。知識は豊富だが押し付けない。
- 友達に話すような自然体。BOT感ゼロが最重要。
- 宣伝・営業トーンは絶対不可。「ぜひチェック」「おすすめです」等の文言は禁止。

## リプライルール
1. **280文字以内**（厳守。超えたら短く削る）
2. 絵文字は最大1〜2個（使わなくてもOK）
3. 相手の投稿内容に具体的に反応する（コピペ感ゼロ）
4. データは自然に織り込む（「今だとRTX 4060が4万円台で買えるよ」のように）
5. ハッシュタグ禁止
6. 「@相手のID」は不要（リプライなので自動付与される）

## トーン使い分け
- casual（カジュアル投稿）→ タメ口（「〜だよ」「〜かも」「〜じゃない？」）
- technical（技術質問）→ 丁寧語寄り（「〜ですね」「〜かなと思います」）
- frustrated（困っている）→ 共感から入る（「わかる」「自分も同じ経験した」）
- excited（購入報告等）→ 祝福・共感（「おめ！」「いいね」「羨ましい」）

## リンクについて
- リンクを含める場合は自然に1つだけ（「参考になるかも→ URL」のように）
- 宣伝っぽいリンク貼りは絶対不可

## NG例
- 「このサイトをチェック！」→ 宣伝感あり ❌
- 「GPU価格はこちら→」→ 営業トーン ❌
- 投稿内容を無視した定型文 → コピペ感 ❌
- 長すぎる情報の羅列 → 読まれない ❌

## OK例
- 「RTX 4060、今4万切ってるの見かけたよ。VRAMも8GBあるし十分かも」→ 自然 ✅
- 「モンハンワイルズならRTX 4060で60fps余裕だった。設定は高で」→ 体験談風 ✅
- 「15万ならRTX 4060 + i5-14400Fあたりが鉄板かな」→ 具体的 ✅
"""


def generate_reply(post: dict, include_link: bool) -> str:
    """Claude Sonnet APIでリプライ文を生成"""
    import requests

    if not ANTHROPIC_API_KEY:
        print("[FATAL] ANTHROPIC_API_KEY が未設定です", flush=True)
        sys.exit(1)

    enrichment = post.get("_enrichment", {})

    # データコンテキスト構築
    data_lines = []
    if enrichment.get("gpu_info"):
        g = enrichment["gpu_info"]
        data_lines.append(
            f"GPU実データ: {g['chip']} 最安{g['min_price']:,}円 / VRAM {g.get('vram_gb', '?')}GB / {g['count']}製品"
        )
    if enrichment.get("game_info"):
        gi = enrichment["game_info"]
        rec_gpu = gi["rec_gpu"][0] if gi["rec_gpu"] else "不明"
        data_lines.append(
            f"ゲームデータ: {gi['name']} 推奨GPU={rec_gpu} / 推奨RAM={gi.get('rec_ram', '?')}GB"
        )
    if enrichment.get("budget_gpu_candidates"):
        cands = enrichment["budget_gpu_candidates"]
        cand_text = " / ".join(f"{c['chip']}({c['price']:,}円)" for c in cands)
        data_lines.append(f"予算内GPU候補: {cand_text}")
    if enrichment.get("top_gpus"):
        top = enrichment["top_gpus"][:3]
        top_text = " / ".join(f"{g['name']}={g['score']}点" for g in top)
        data_lines.append(f"性能スコアTOP3: {top_text}")

    data_context = "\n".join(data_lines) if data_lines else "（実データなし。一般的な知識で回答）"

    # リンク指示（Bitly短縮URL）
    if include_link:
        steam_appid = None
        if enrichment.get("game_info"):
            steam_appid = enrichment["game_info"].get("steam_appid")
        if steam_appid:
            import urllib.parse
            # ゲーム名からスラッグ生成してURLエンコード（日本語対応）
            game_name = enrichment["game_info"].get("name", "")
            if game_name:
                slug = _slugify(game_name)
                encoded_slug = urllib.parse.quote(slug)
                full_url = f"{SITE_URL}/game/{encoded_slug}"
            else:
                full_url = SITE_URL
        else:
            full_url = SITE_URL
        link_url = shorten_url(full_url)
        link_instruction = f"リプライの末尾に自然な形でこのURLを1つ含めてください: {link_url}"
    else:
        link_instruction = "リンクは含めないでください。"

    user_prompt = f"""以下の投稿へのリプライを1つだけ生成してください。

## 元投稿
- アカウント: {post.get('poster_account', '')}
- 内容: {post.get('post_summary', '')}
- トーン: {post.get('tone', 'casual')}
- トピック: {post.get('topic_type', '')}
- 言及GPU: {post.get('mentioned_gpu', '')}
- 言及ゲーム: {post.get('mentioned_game', '')}
- 言及予算: {post.get('mentioned_budget', '')}

## 使える実データ
{data_context}

## リンク
{link_instruction}

リプライ文のみを出力してください。説明や前置きは不要です。280文字以内。"""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 300,
        "temperature": 0.8,
        "system": REPLY_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        reply_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                reply_text += block.get("text", "")
        # 280文字チェック
        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."
        return reply_text.strip()
    except Exception as e:
        print(f"    [ERROR] Claude API: {e}", flush=True)
        return ""


def _slugify(name: str) -> str:
    """ゲーム名からURL用スラッグを生成"""
    slug = name.lower()
    slug = slug.replace(" ", "-").replace(":", "").replace("\u2122", "")
    slug = slug.replace("\u00ae", "").replace("(", "").replace(")", "")
    slug = slug.replace("[", "").replace("]", "").replace("/", "")
    slug = slug.replace("'", "").replace('"', "").replace(",", "")
    slug = slug.replace("・", "").replace("·", "").replace("‐", "-")
    slug = slug.replace("--", "-").replace("--", "-")
    return slug.strip("-")


# ────────────────────────────────────────
# Phase 5: Posting（Tweepy v2）
# ────────────────────────────────────────
def post_reply(tweet_id: str, reply_text: str, dry_run: bool = True, account: str = "", post_url: str = "") -> bool:
    """通常ツイート + 元ツイートURL埋め込みで投稿（Xが自動プレビュー展開）"""
    # @メンション（通知用）+ 元ツイートURL（文脈保持）を付与
    mention = account if account.startswith("@") else f"@{account}" if account else ""
    parts = [mention, reply_text, post_url] if post_url else [mention, reply_text]
    full_text = "\n".join(p for p in parts if p)

    if dry_run:
        print(f"    [DRY RUN] 投稿内容:", flush=True)
        print(f"    {full_text}", flush=True)
        print(f"    文字数: {len(full_text)}", flush=True)
        return True

    missing = [
        k
        for k, v in {
            "TWITTER_API_KEY": TWITTER_API_KEY,
            "TWITTER_API_SECRET": TWITTER_API_SECRET,
            "TWITTER_ACCESS_TOKEN": TWITTER_ACCESS_TOKEN,
            "TWITTER_ACCESS_SECRET": TWITTER_ACCESS_SECRET,
            "TWITTER_BEARER_TOKEN": TWITTER_BEARER_TOKEN,
        }.items()
        if not v
    ]
    if missing:
        print(f"    [ERROR] 環境変数未設定: {', '.join(missing)}", flush=True)
        return False

    try:
        import tweepy

        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET,
        )

        response = client.create_tweet(text=full_text)
        posted_id = response.data["id"]
        print(f"    [SUCCESS] 投稿完了! ID: {posted_id}", flush=True)
        return True

    except Exception as e:
        error_str = str(e)
        if "402" in error_str:
            print(
                "[FATAL] 402 Payment Required: Twitter API クレジット不足", flush=True
            )
            sys.exit(1)
        elif "429" in error_str:
            print("    [WARN] 429 Rate Limit → スキップ", flush=True)
            return False
        else:
            print(f"    [ERROR] 投稿失敗: {type(e).__name__}: {e}", flush=True)
            return False


# ────────────────────────────────────────
# Phase 6: History Tracking
# ────────────────────────────────────────
def load_history() -> dict:
    """履歴を読み込み"""
    if not HISTORY_FILE.exists():
        return {"replies": [], "total_replies": 0, "total_runs": 0}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"replies": [], "total_replies": 0, "total_runs": 0}


def save_history(history: dict) -> None:
    """履歴を保存"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_reply(
    history: dict,
    tweet_id: str,
    account: str,
    reply_text: str,
    grade: str,
    topic_type: str,
    had_link: bool,
) -> None:
    """リプライを履歴に記録"""
    history["replies"].append(
        {
            "target_tweet_id": tweet_id,
            "target_account": account,
            "reply_text": reply_text,
            "grade": grade,
            "topic_type": topic_type,
            "timestamp": datetime.now().isoformat(),
            "had_link": had_link,
        }
    )
    history["total_replies"] = len(history["replies"])


# ────────────────────────────────────────
# メイン
# ────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Twitter PC Outreach Bot")
    parser.add_argument(
        "--dry-run", action="store_true", help="検索・生成のみ（投稿しない）"
    )
    args = parser.parse_args()

    start_time = datetime.now()
    print("=" * 60, flush=True)
    print(
        f"PC Outreach Bot 開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        flush=True,
    )
    if args.dry_run:
        print("[DRY RUN モード]", flush=True)
    print("=" * 60, flush=True)

    # 履歴読み込み
    history = load_history()
    print(
        f"[履歴] 過去リプライ: {history['total_replies']}件 / 実行回数: {history['total_runs']}",
        flush=True,
    )

    # ── Phase 1: Discovery ──
    print("\n--- Phase 1: Discovery ---", flush=True)
    selected_queries = random.sample(ALL_QUERIES, min(7, len(ALL_QUERIES)))
    print(f"選択クエリ: {selected_queries}", flush=True)
    raw_posts = discover_posts(selected_queries)
    print(f"合計発見: {len(raw_posts)}件", flush=True)

    if not raw_posts:
        print("[INFO] 投稿が見つかりませんでした。終了します。", flush=True)
        history["total_runs"] += 1
        save_history(history)
        return

    # ── Phase 2: Filtering ──
    print("\n--- Phase 2: Filtering ---", flush=True)
    targets = filter_posts(raw_posts, history)
    print(f"フィルタ後: {len(targets)}件", flush=True)

    if not targets:
        print("[INFO] フィルタ後の対象がありません。終了します。", flush=True)
        history["total_runs"] += 1
        save_history(history)
        return

    # ── Phase 3-5: Enrichment → Generation → Posting ──
    print("\n--- Phase 3-5: Enrichment → Generation → Posting ---", flush=True)
    replied_count = 0

    for i, post in enumerate(targets, 1):
        tweet_id = post["_tweet_id"]
        account = post.get("poster_account", "")
        grade = post.get("grade", "B")
        topic = post.get("topic_type", "general_pc")

        print(
            f"\n[{i}/{len(targets)}] {account} | {grade}級 | {topic}",
            flush=True,
        )
        print(f"  要約: {post.get('post_summary', '')[:80]}", flush=True)

        # Phase 3: Enrichment
        post = enrich_post(post)
        enrichment = post.get("_enrichment", {})
        if enrichment:
            keys = [k for k in enrichment if enrichment[k]]
            print(f"  データ付与: {', '.join(keys)}", flush=True)

        # Phase 4: Generation
        include_link = random.random() < LINK_PROBABILITY
        reply_text = generate_reply(post, include_link)
        if not reply_text:
            print("  [SKIP] リプライ生成失敗", flush=True)
            continue

        print(f"  生成リプライ ({len(reply_text)}文字):", flush=True)
        print(f"  「{reply_text}」", flush=True)

        # Phase 5: Posting
        post_url = post.get("post_url", "")
        success = post_reply(tweet_id, reply_text, dry_run=args.dry_run, account=account, post_url=post_url)

        if success:
            replied_count += 1
            # Phase 6: Tracking
            had_link = SITE_URL in reply_text or "railway.app" in reply_text
            record_reply(history, tweet_id, account, reply_text, grade, topic, had_link)

        # Anti-Bot: ランダム遅延（60〜300秒）
        if not args.dry_run and i < len(targets):
            delay = random.randint(60, 300)
            print(f"  [待機] {delay}秒...", flush=True)
            time.sleep(delay)

    # 実行回数更新
    history["total_runs"] += 1
    save_history(history)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*60}", flush=True)
    print(
        f"完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({elapsed:.0f}秒)",
        flush=True,
    )
    print(f"リプライ: {replied_count}/{len(targets)}件", flush=True)
    print(f"累計: {history['total_replies']}件 / {history['total_runs']}回", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
