"""
X セッション初期設定ツール
==========================
ブラウザを **表示モード** で起動し、ユーザーが手動で X にログインします。
ログイン成功後、セッション情報を logs/x_session.json に保存します。
以後、x_monitor_scraper.py は保存済みセッションを使ってヘッドレスで動作します。

使い方:
    python scripts/x_setup_session.py

必要パッケージ:
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

_SCRIPT_DIR  = Path(__file__).parent
_PROJECT_DIR = _SCRIPT_DIR.parent
_LOG_DIR     = _PROJECT_DIR / "logs"
_SESSION_FILE = _LOG_DIR / "x_session.json"


def main() -> None:
    _LOG_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("X セッション初期設定ツール")
    print("=" * 60)
    print()
    print("ブラウザが起動します。X (Twitter) にログインしてください。")
    print()
    print("手順:")
    print("  1. 開いたブラウザで daruma0411@gmail.com / パスワードを入力")
    print("  2. 2要素認証・電話番号確認が出た場合もその場で対応")
    print("  3. ホーム画面（タイムライン）が表示されたら、")
    print("     このターミナルに戻って Enter を押してください")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,          # ← 表示モード（重要）
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            no_viewport=False,
        )
        page = context.new_page()

        print("ブラウザを起動中...")
        try:
            page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            print(f"  警告: ページ読み込みエラー ({exc})")

        print()
        print(">>> ブラウザで X にログインしてから、ここで Enter を押してください <<<")
        try:
            input()
        except KeyboardInterrupt:
            print("\nキャンセルされました。")
            browser.close()
            sys.exit(0)

        # 現在のURLを確認
        current_url = page.url
        print(f"現在のURL: {current_url}")

        if "login" in current_url.lower() and "x.com/home" not in current_url:
            print()
            print("⚠️  まだログインページにいるようです。")
            print("   ログインを完了してから再度 Enter を押してください。")
            try:
                input()
            except KeyboardInterrupt:
                print("\nキャンセルされました。")
                browser.close()
                sys.exit(0)
            current_url = page.url

        # セッション保存
        context.storage_state(path=str(_SESSION_FILE))
        browser.close()

    print()
    print(f"✅ セッション保存完了: {_SESSION_FILE}")
    print()
    print("これで x_monitor_scraper.py がログイン不要で動作します。")
    print("以下のコマンドで監視を開始してください:")
    print()
    print("    python scripts/x_monitor_scraper.py")
    print()


if __name__ == "__main__":
    main()
