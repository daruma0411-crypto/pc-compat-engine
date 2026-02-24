"""
X Monitor Scraper
=================
Playwright を使って X（旧Twitter）で「グラボ 入らない」を検索し、
型番を抽出して pc-compat-engine 診断APIに送信する。
結果は logs/x_monitor_YYYY-MM-DD.jsonl に保存。
15分ごとの定期実行を想定。

【初回セットアップ】
  python scripts/x_setup_session.py
  → ブラウザが開くので、手動でXにログイン → Enter → セッション保存

使い方（セットアップ済み後）:
    python scripts/x_monitor_scraper.py

環境変数（.env または shell）:
    COMPAT_API_URL : 診断API URL（省略時: https://pc-compat-engine.onrender.com/api/diagnose）
    X_SEARCH_QUERY : 検索ワード（カンマ区切りで複数指定可、省略時はデフォルトリストを使用）
    MAX_TWEETS     : 取得最大件数（省略時: 20）

依存パッケージのインストール:
    pip install playwright python-dotenv requests
    playwright install chromium
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# ----------------------------------------------------------------
# 設定
# ----------------------------------------------------------------
load_dotenv()

COMPAT_API_URL = os.getenv(
    "COMPAT_API_URL",
    "https://pc-compat-engine.onrender.com/api/diagnose",
)
_DEFAULT_QUERIES: list[str] = [
    "RTX ケース 干渉",
    "4090 入らない",
    "5080 入らない",
    "マザボ 対応 確認",
    "DDR5 互換",
    "自作PC 互換性",
]
_env_query = os.getenv("X_SEARCH_QUERY", "")
SEARCH_QUERIES: list[str] = (
    [q.strip() for q in _env_query.split(",") if q.strip()]
    if _env_query else _DEFAULT_QUERIES
)
MAX_TWEETS = int(os.getenv("MAX_TWEETS", "20"))

_SCRIPT_DIR  = Path(__file__).parent
_PROJECT_DIR = _SCRIPT_DIR.parent
_LOG_DIR     = _PROJECT_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_TODAY         = datetime.now().strftime("%Y-%m-%d")
_LOG_FILE      = _LOG_DIR / f"x_monitor_{_TODAY}.jsonl"
_SEEN_IDS_FILE = _LOG_DIR / "seen_ids.txt"
_SESSION_FILE  = _LOG_DIR / "x_session.json"

# ----------------------------------------------------------------
# ロガー
# ----------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# 型番抽出パターン（domain_rules.py / PART_NUMBER_PATTERNS から展開）
# ----------------------------------------------------------------
_PART_PATTERNS: list[str] = [
    # NVIDIA GPU
    r"RTX\s*\d{4}(?:\s*Ti|\s*Super|\s*SUPER)?",
    r"GTX\s*\d{4}(?:\s*Ti)?",
    # AMD GPU
    r"RX\s*\d{4}(?:\s*XT|\s*XTX|\s*GRE)?",
    # Intel CPU
    r"Core\s+(?:Ultra\s+)?\d{1,2}-\d{4,5}[A-Z]{0,2}",
    r"i[3579]-\d{4,5}[A-Z]{0,2}",
    # AMD CPU
    r"Ryzen\s+[357]\s+\d{4}[A-Z]{0,2}",
    r"Ryzen\s+9\s+\d{4}[A-Z]{0,2}",
    # Noctua クーラー
    r"NH-[A-Z]\d+[A-Z]?(?:\s+SE-AM\d)?",
    # PCケース
    r"H[5-9]\d{2}(?:\s+(?:Elite|Flow|ATX))?",
    r"Define\s+[R]?\d+(?:\s+(?:Nano|Mini|XL))?",
    r"Meshify\s+[C2]?(?:\s+Compact)?",
    r"\b[45]000D(?:\s+AIRFLOW)?(?:\s+RGB)?",
    r"O11\s+(?:Dynamic|Air|Evo|XL)?",
    # 電源
    r"(?:RM|HX|AX|SF|MX|TX)\d{3,4}[xi]?",
    # メモリ
    r"\bDDR[45]-\d{4,5}\b",
    r"\b\d{2}GB\s+DDR[45]\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PART_PATTERNS]


def extract_parts(text: str) -> list[str]:
    """ツイートテキストからPC部品の型番を抽出し重複なしで返す。"""
    found: list[str] = []
    for pattern in _COMPILED:
        for m in pattern.finditer(text):
            val = m.group().strip()
            if val and val not in found:
                found.append(val)
    return found


# ----------------------------------------------------------------
# 処理済みID管理
# ----------------------------------------------------------------

def load_seen_ids() -> set[str]:
    if not _SEEN_IDS_FILE.exists():
        return set()
    return set(_SEEN_IDS_FILE.read_text(encoding="utf-8").splitlines())


def append_seen_id(tweet_id: str) -> None:
    with _SEEN_IDS_FILE.open("a", encoding="utf-8") as f:
        f.write(tweet_id + "\n")


# ----------------------------------------------------------------
# ログ書き込み
# ----------------------------------------------------------------

def write_log(record: dict) -> None:
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------
# 診断API呼び出し
# ----------------------------------------------------------------

def call_diagnose(parts: list[str]) -> dict:
    """POST /api/diagnose を呼び出して診断結果を返す。"""
    try:
        resp = requests.post(
            COMPAT_API_URL,
            json={"parts": parts},
            timeout=90,
            verify=False,  # 企業プロキシのSSLインスペクション対策
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"verdict": "ERROR", "summary": str(exc), "checks": []}


# ----------------------------------------------------------------
# Playwright: ログイン
# ----------------------------------------------------------------

def _login(page) -> bool:
    """
    X のログインフローを実行する。成功: True / 失敗: False

    フロー:
      1. ユーザー名/メール入力 → Next ボタンクリック
      2. （任意）不審アクティビティ確認: @username を要求される場合あり
      3. パスワード入力 → Log in ボタンクリック
    """
    logger.info("Xにログイン中...")
    try:
        page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
    except Exception as exc:
        logger.error(f"ログインページへのアクセス失敗: {exc}")
        return False

    # Step1: ユーザー名/メール入力
    try:
        username_loc = page.locator("input[autocomplete='username']")
        username_loc.wait_for(timeout=15000)
        username_loc.click()
        page.wait_for_timeout(500)
        # press_sequentially で1文字ずつ入力（Xのキーストロークイベント検知対策）
        username_loc.press_sequentially(X_USERNAME, delay=80)
        page.wait_for_timeout(800)
        # "次へ" / "Next" ボタンをクリック（日英どちらのUIでも対応）
        next_btn = page.locator("div[role='button']").filter(
            has_text=re.compile(r"^(Next|次へ)$")
        ).first
        if next_btn.count():
            next_btn.click()
        else:
            page.keyboard.press("Enter")
    except PlaywrightTimeoutError:
        logger.error("ユーザー名入力フィールドが見つかりません")
        return False

    page.wait_for_timeout(3000)
    page.screenshot(path=str(_LOG_DIR / "login_step2.png"))
    logger.info(f"Step2 URL: {page.url}")

    # Step2: 不審アクティビティ確認（"Enter your phone number or username"）
    verify_input = page.query_selector("input[data-testid='ocfEnterTextTextInput']")
    if verify_input:
        logger.info("不審アクティビティ確認ステップを検出 → @username を入力")
        handle = X_USERNAME.split("@")[0]
        verify_input.press_sequentially(handle, delay=80)
        next_btn2 = page.locator("div[role='button']").filter(
            has_text=re.compile(r"^(Next|次へ)$")
        ).first
        if next_btn2.count():
            next_btn2.click()
        else:
            page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

    # Step3: パスワード入力
    try:
        pw_loc = page.locator("input[name='password']")
        pw_loc.wait_for(timeout=12000)
        pw_loc.click()
        page.wait_for_timeout(300)
        pw_loc.press_sequentially(X_PASSWORD, delay=80)
        page.wait_for_timeout(500)
        # ログインボタン（data-testid or テキスト「ログイン」/「Log in」）
        login_btn = page.locator("[data-testid='LoginForm_Login_Button']")
        if not login_btn.count():
            login_btn = page.locator("div[role='button']").filter(
                has_text=re.compile(r"^(Log in|ログイン)$")
            ).first
        if login_btn.count():
            login_btn.click()
        else:
            page.keyboard.press("Enter")
    except PlaywrightTimeoutError:
        logger.error("パスワード入力フィールドが見つかりません")
        page.screenshot(path=str(_LOG_DIR / "login_error.png"))
        logger.error(f"エラー時スクリーンショット: {_LOG_DIR / 'login_error.png'}")
        return False

    # ホーム画面へのリダイレクトを待つ
    try:
        page.wait_for_url(re.compile(r"x\.com/(home|for-you)"), timeout=20000)
        logger.info("ログイン成功")
        return True
    except PlaywrightTimeoutError:
        current = page.url
        logger.warning(f"ログイン後リダイレクト待機タイムアウト: {current}")
        page.screenshot(path=str(_LOG_DIR / "login_error.png"))
        return "x.com" in current and "login" not in current


def _is_logged_in(page) -> bool:
    """セッションファイルを使って X にアクセスし、ログイン済みか確認する。"""
    try:
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)
        return "login" not in page.url
    except Exception:
        return False


# ----------------------------------------------------------------
# Playwright: 検索 & ツイート収集
# ----------------------------------------------------------------

def search_tweets(page, query: str, max_count: int) -> list[dict]:
    """
    X で query を検索し、最新ツイートを最大 max_count 件収集する。
    返り値: [{"id": ..., "text": ..., "url": ...}, ...]
    """
    encoded = requests.utils.quote(query)
    search_url = f"https://x.com/search?q={encoded}&src=typed_query&f=live"
    logger.info(f"検索: {search_url}")

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
    except Exception as exc:
        logger.error(f"検索ページへのアクセス失敗: {exc}")
        return []

    page.wait_for_timeout(3000)

    tweets: list[dict] = []
    seen_in_page: set[str] = set()
    scroll_attempts = 0
    max_scrolls = 10

    while len(tweets) < max_count and scroll_attempts < max_scrolls:
        articles = page.query_selector_all("article[data-testid='tweet']")

        for article in articles:
            # ツイートID を /status/ID のリンクから取得
            tweet_id = None
            tweet_url = None
            for link in article.query_selector_all("a[href*='/status/']"):
                href = link.get_attribute("href") or ""
                m = re.search(r"/status/(\d+)", href)
                if m:
                    tweet_id = m.group(1)
                    tweet_url = f"https://x.com/i/status/{tweet_id}"
                    break

            if not tweet_id or tweet_id in seen_in_page:
                continue
            seen_in_page.add(tweet_id)

            # テキスト取得
            text_el = article.query_selector("[data-testid='tweetText']")
            tweet_text = text_el.inner_text() if text_el else ""

            tweets.append({"id": tweet_id, "text": tweet_text, "url": tweet_url})

            if len(tweets) >= max_count:
                break

        if len(tweets) >= max_count:
            break

        # スクロールして追加読み込み
        page.evaluate("window.scrollBy(0, 1500)")
        page.wait_for_timeout(2000)
        scroll_attempts += 1

    logger.info(f"ツイート収集: {len(tweets)} 件")
    return tweets


# ----------------------------------------------------------------
# メイン処理
# ----------------------------------------------------------------

def main() -> None:
    # セッションファイルの存在確認（初回セットアップ誘導）
    if not _SESSION_FILE.exists():
        logger.error(
            "セッションファイルが見つかりません。\n"
            "  まず以下のコマンドで初回セットアップを実行してください:\n"
            "    python scripts/x_setup_session.py"
        )
        sys.exit(1)

    seen_ids = load_seen_ids()
    logger.info(
        f"開始 | クエリ数={len(SEARCH_QUERIES)} 上限={MAX_TWEETS}件/クエリ "
        f"処理済みID={len(seen_ids)}件"
    )
    for _q in SEARCH_QUERIES:
        logger.info(f"  クエリ: {_q!r}")

    # ---- Playwright セッション ----
    tweets: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        _CONTEXT_OPTS = dict(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )

        _stealth = Stealth()

        def _new_stealth_page(ctx):
            p = ctx.new_page()
            _stealth.apply_stealth_sync(p)
            return p

        # 保存済みセッションをロード
        logger.info(f"保存済みセッションをロード: {_SESSION_FILE}")
        context = browser.new_context(
            storage_state=str(_SESSION_FILE), **_CONTEXT_OPTS
        )
        page = _new_stealth_page(context)

        # ログイン状態を確認
        if not _is_logged_in(page):
            logger.error(
                "セッションが期限切れです。再セットアップが必要です:\n"
                "    python scripts/x_setup_session.py"
            )
            browser.close()
            sys.exit(1)

        _seen_in_run: set[str] = set()
        _all_tweets: list[dict] = []
        for _query in SEARCH_QUERIES:
            for _t in search_tweets(page, _query, MAX_TWEETS):
                if _t["id"] not in _seen_in_run:
                    _all_tweets.append(_t)
                    _seen_in_run.add(_t["id"])
        tweets = _all_tweets
        browser.close()

    # ---- ツイート処理 ----
    diagnosed_count = 0
    skipped_count = 0

    for tweet in tweets:
        tweet_id   = tweet["id"]
        tweet_text = tweet["text"]
        tweet_url  = tweet["url"]
        now_str    = datetime.now().isoformat(timespec="seconds")

        # 処理済みならスキップ
        if tweet_id in seen_ids:
            skipped_count += 1
            continue

        # 型番抽出
        parts = extract_parts(tweet_text)

        if not parts:
            logger.debug(f"型番なし → スキップ: {tweet_text[:60]!r}")
            write_log({
                "timestamp": now_str,
                "tweet_id":  tweet_id,
                "tweet_url": tweet_url,
                "skipped":   True,
                "reason":    "no_parts_found",
                "tweet_text": tweet_text[:200],
            })
            append_seen_id(tweet_id)
            seen_ids.add(tweet_id)
            skipped_count += 1
            continue

        logger.info(f"診断: {parts} | {tweet_url}")

        # 診断API呼び出し
        result  = call_diagnose(parts)
        verdict = result.get("verdict", "UNKNOWN")
        summary = result.get("summary", "")
        checks  = result.get("checks", [])

        logger.info(f"  → [{verdict}] {summary[:100]}")

        # ログ書き込み
        write_log({
            "timestamp":  now_str,
            "tweet_id":   tweet_id,
            "tweet_url":  tweet_url,
            "tweet_text": tweet_text[:500],
            "parts":      parts,
            "verdict":    verdict,
            "summary":    summary,
            "checks":     checks,
        })

        append_seen_id(tweet_id)
        seen_ids.add(tweet_id)
        diagnosed_count += 1
        time.sleep(1)  # API レート制限対策

    logger.info(
        f"完了: 診断={diagnosed_count}件 スキップ={skipped_count}件 | "
        f"ログ: {_LOG_FILE}"
    )


if __name__ == "__main__":
    main()
