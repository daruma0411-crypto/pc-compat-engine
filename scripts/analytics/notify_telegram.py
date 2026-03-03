"""
Telegram通知スクリプト
GA4のデイリーサマリーをTelegramに送信する
"""

import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from fetch_reports import get_daily_overview, get_top_pages, get_realtime_users

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_daily_summary():
    """
    毎日のサマリーをTelegramに送信
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        return False

    overview = get_daily_overview(1)  # 昨日のデータ
    realtime = get_realtime_users()
    top_pages = get_top_pages(1, 5)

    if overview is None:
        overview = {
            "total_users": 0,
            "total_sessions": 0,
            "total_pageviews": 0,
            "avg_session_duration": 0.0,
            "bounce_rate": 0.0,
        }

    # 人気ページ一覧
    pages_text = ""
    for i, page in enumerate(top_pages):
        pages_text += f"  {i+1}. {page['page']} ({page['pageviews']}PV)\n"

    message = f"""📊 *PC互換チェッカー - デイリーレポート*
_{datetime.now().strftime('%Y年%m月%d日')}_

🔴 リアルタイム: {realtime['active_users']}人

*昨日の実績:*
👥 ユーザー数: {overview['total_users']:,}
📄 ページビュー: {overview['total_pageviews']:,}
📈 セッション数: {overview['total_sessions']:,}
⏱ 平均滞在時間: {overview['avg_session_duration']:.0f}秒
📊 直帰率: {overview['bounce_rate']*100:.1f}%

*人気ページ:*
{pages_text}"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, data=data)
    if response.ok:
        print("Telegram notification sent!")
        return True
    else:
        print(f"Failed to send: {response.text}")
        return False


if __name__ == "__main__":
    send_daily_summary()
