#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily KPI Reporter for EDDIE-PC
毎朝の KPI 自動レポート → Telegram 配信

データソース:
  - Google Analytics 4 Data API（昨日 + 前週比較）
  - Twitter 投稿履歴（twitter_post_history.json）

実行方法:
  python scripts/daily_kpi_reporter.py          # 本番（Telegram 送信）
  python scripts/daily_kpi_reporter.py --dry-run # テスト（コンソール出力のみ）
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp932 対策
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# fetch_reports.py を import（同じ analytics/ ディレクトリ）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'analytics'))
from fetch_reports import (
    get_daily_overview,
    get_top_pages,
    get_traffic_sources,
    get_device_breakdown,
)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Telegram 設定
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Twitter 投稿履歴
TWITTER_HISTORY_PATH = Path(__file__).parent / 'twitter_post_history.json'


def get_twitter_summary():
    """Twitter 投稿履歴から直近 24h の投稿数と累計を取得"""
    if not TWITTER_HISTORY_PATH.exists():
        return {'posts_today': 0, 'total_posts': 0}

    with open(TWITTER_HISTORY_PATH, 'r', encoding='utf-8') as f:
        history = json.load(f)

    total = len(history)
    yesterday = datetime.now() - timedelta(days=1)
    posts_today = 0

    for entry in history:
        posted_at = entry.get('posted_at', '')
        if posted_at:
            try:
                dt = datetime.fromisoformat(posted_at)
                if dt.date() == yesterday.date():
                    posts_today += 1
            except (ValueError, TypeError):
                pass

    return {'posts_today': posts_today, 'total_posts': total}


def calc_wow_change(current, previous):
    """前週比の変化率を計算（%）"""
    if previous == 0:
        if current > 0:
            return '+∞'
        return '±0'
    change = ((current - previous) / previous) * 100
    if change > 0:
        return f'+{change:.0f}%'
    elif change < 0:
        return f'{change:.0f}%'
    return '±0%'


def generate_report():
    """KPI レポートを生成"""
    # 昨日のデータ
    yesterday_data = get_daily_overview(1)
    # 前週同日のデータ（8日前〜7日前 = 前週の同じ日）
    last_week_data = get_daily_overview_range(8, 7)

    top_pages = get_top_pages(1, 5)
    traffic = get_traffic_sources(1)
    devices = get_device_breakdown(1)
    twitter = get_twitter_summary()

    # None フォールバック
    if yesterday_data is None:
        yesterday_data = {
            'total_users': 0, 'total_sessions': 0,
            'total_pageviews': 0, 'avg_session_duration': 0.0,
            'bounce_rate': 0.0,
        }
    if last_week_data is None:
        last_week_data = {
            'total_users': 0, 'total_sessions': 0,
            'total_pageviews': 0, 'avg_session_duration': 0.0,
            'bounce_rate': 0.0,
        }

    # WoW 変化率
    users_wow = calc_wow_change(yesterday_data['total_users'], last_week_data['total_users'])
    pv_wow = calc_wow_change(yesterday_data['total_pageviews'], last_week_data['total_pageviews'])

    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y年%m月%d日')
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_of_week = day_names[yesterday.weekday()]

    # --- レポート組み立て（モバイル最適化版） ---
    minutes = int(yesterday_data['avg_session_duration'] // 60)
    seconds = int(yesterday_data['avg_session_duration'] % 60)
    
    report = f"""━━━━━━━━━━━━━━━━━
📊 PC互換チェッカー 日次KPI
{date_str}（{day_of_week}）
━━━━━━━━━━━━━━━━━

【サマリー】
👥 {yesterday_data['total_users']:,}人 ({users_wow}) | 📄 {yesterday_data['total_pageviews']:,}PV ({pv_wow})
⏱ {minutes}分{seconds}秒 | 📊 直帰率: {yesterday_data['bounce_rate']*100:.1f}%
"""

    # デバイス（サマリーに統合）
    if devices:
        device_line = " | ".join([f"{d.capitalize()}: {data['users']:,}" for d, data in sorted(devices.items(), key=lambda x: x[1]['users'], reverse=True)])
        report += f"{device_line}\n"

    # 流入元（絵文字で短縮）
    if traffic:
        report += "\n【流入元】\n"
        emoji_map = {
            'direct': '🔗',
            'organic_search': '🔍',
            'referral': '📧',
            'social': '📱',
            'unassigned': '❓'
        }
        for channel, data in sorted(traffic.items(), key=lambda x: x[1]['users'], reverse=True):
            emoji = emoji_map.get(channel, '•')
            channel_name = channel.replace('_', ' ')
            report += f"{emoji} {channel_name}: {data['users']:,}人\n"

    # 人気ページ（0PVを除外、短縮表示）
    if top_pages:
        # 0PVページを除外
        filtered_pages = [p for p in top_pages if p['pageviews'] > 0]
        if filtered_pages:
            report += "\n【人気ページ】\n"
            for i, page in enumerate(filtered_pages[:3], 1):  # Top 3に短縮
                # ページ名を短縮
                page_name = page['page']
                if page_name == '/':
                    page_name = 'トップ'
                elif page_name.startswith('/game/'):
                    game_name = page_name.replace('/game/', '')
                    # 長い名前は省略
                    if len(game_name) > 20:
                        game_name = game_name[:20] + '...'
                    page_name = game_name
                
                report += f"{i}️⃣ {page_name}: {page['pageviews']:,}PV\n"

    # Twitter（短縮版）
    report += f"""
【Twitter】
📝 昨日: {twitter['posts_today']}件 | 📊 累計: {twitter['total_posts']}件

━━━━━━━━━━━━━━━━━
💡 次のアクション:
・12:00/18:00/21:00 自動投稿
・検索流入を増やす施策検討
━━━━━━━━━━━━━━━━━"""

    return report


def get_daily_overview_range(start_days_ago, end_days_ago):
    """
    特定の日付範囲のデータを取得（前週比較用）

    fetch_reports.py の get_daily_overview は "NdaysAgo" 形式を使っているが、
    ここでは特定の1日だけを取得したいので、日付文字列で指定する。
    """
    from google.analytics.data_v1beta.types import (
        DateRange, Metric, RunReportRequest,
    )
    # fetch_reports.py のモジュールレベルで初期化されたクライアントと PROPERTY_ID を再利用
    import analytics.fetch_reports as fr

    start_date = (datetime.now() - timedelta(days=start_days_ago)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=end_days_ago)).strftime('%Y-%m-%d')

    try:
        request = RunReportRequest(
            property=f"properties/{fr.PROPERTY_ID}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
            ],
        )

        response = fr.client.run_report(request)

        if not response.rows:
            return None

        row = response.rows[0]
        return {
            "total_users": int(row.metric_values[0].value),
            "total_sessions": int(row.metric_values[1].value),
            "total_pageviews": int(row.metric_values[2].value),
            "avg_session_duration": float(row.metric_values[3].value),
            "bounce_rate": float(row.metric_values[4].value),
        }
    except Exception as e:
        print(f"[WARN] 前週データ取得失敗（初期段階では正常）: {e}")
        return None


def send_telegram(message, dry_run=False):
    """Telegram にレポートを送信"""
    if dry_run:
        print("[DRY-RUN] Telegram 送信スキップ")
        return True

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERROR] TELEGRAM_BOT_TOKEN または TELEGRAM_CHAT_ID が未設定")
        print("  .env または GitHub Secrets に以下を追加してください:")
        print("  TELEGRAM_BOT_TOKEN=your-bot-token")
        print("  TELEGRAM_CHAT_ID=your-chat-id")
        return False

    import requests

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
    }

    try:
        # Windows ローカル環境で SSL 証明書エラーが出る場合の対策
        verify = not (sys.platform == 'win32')
        response = requests.post(url, data=data, timeout=10, verify=verify)
        response.raise_for_status()
        print("✅ Telegram 通知送信成功")
        return True
    except Exception as e:
        print(f"[ERROR] Telegram 送信失敗: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='EDDIE-PC Daily KPI Reporter')
    parser.add_argument('--dry-run', action='store_true', help='テスト実行（Telegram 送信しない）')
    args = parser.parse_args()

    print("=" * 50)
    print("EDDIE-PC Daily KPI Reporter")
    print("=" * 50)

    # レポート生成
    print("\n[データ取得中...]")
    try:
        report = generate_report()
    except Exception as e:
        print(f"[ERROR] レポート生成失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # コンソール出力
    print("\n" + report)

    # Telegram 送信
    print("\n[Telegram 送信中...]")
    success = send_telegram(report, dry_run=args.dry_run)

    if not success:
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ KPI レポート完了")
    print("=" * 50)


if __name__ == '__main__':
    main()
