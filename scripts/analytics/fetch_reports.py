"""
Google Analytics 4 データ取得スクリプト

必要ライブラリ:
pip install google-analytics-data google-auth python-dotenv
"""

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# 認証
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
PROPERTY_ID = os.getenv('GA4_PROPERTY_ID')

_scopes = ['https://www.googleapis.com/auth/analytics.readonly']

if CREDENTIALS_JSON:
    # Railway等: 環境変数にJSON文字列を直接設定
    info = json.loads(CREDENTIALS_JSON)
    credentials = service_account.Credentials.from_service_account_info(info, scopes=_scopes)
elif CREDENTIALS_PATH:
    # ローカル: ファイルパスから読み込み
    if not os.path.isabs(CREDENTIALS_PATH):
        CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', CREDENTIALS_PATH)
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=_scopes)
else:
    raise RuntimeError("GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS must be set")

client = BetaAnalyticsDataClient(credentials=credentials)


def get_daily_overview(days=7):
    """
    過去N日間のサマリーレポート取得

    返り値:
    {
      "total_users": 142,
      "new_users": 98,
      "returning_users": 44,
      "total_sessions": 215,
      "total_pageviews": 422,
      "avg_session_duration": 125.3,
      "bounce_rate": 0.42,
      "sessions_per_user": 1.51
    }
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="newUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
        ],
    )

    response = client.run_report(request)

    if not response.rows:
        return None

    row = response.rows[0]
    total_users = int(row.metric_values[0].value)
    new_users = int(row.metric_values[1].value)
    total_sessions = int(row.metric_values[2].value)
    
    return {
        "total_users": total_users,
        "new_users": new_users,
        "returning_users": total_users - new_users,
        "total_sessions": total_sessions,
        "total_pageviews": int(row.metric_values[3].value),
        "avg_session_duration": float(row.metric_values[4].value),
        "bounce_rate": float(row.metric_values[5].value),
        "sessions_per_user": round(total_sessions / total_users, 2) if total_users > 0 else 0.0,
    }


def get_top_pages(days=7, limit=10):
    """
    人気ページランキング

    返り値:
    [
      {"page": "/game/elden-ring", "pageviews": 85, "users": 42},
      {"page": "/", "pageviews": 120, "users": 78},
      ...
    ]
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=limit,
    )

    response = client.run_report(request)

    results = []
    for row in response.rows:
        results.append({
            "page": row.dimension_values[0].value,
            "pageviews": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
        })

    return results


def get_traffic_sources(days=7):
    """
    流入元レポート

    返り値:
    {
      "organic_search": {"users": 85, "sessions": 120},
      "direct": {"users": 42, "sessions": 58},
      "referral": {"users": 15, "sessions": 20},
      "social": {"users": 5, "sessions": 7}
    }
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
        ],
    )

    response = client.run_report(request)

    channel_map = {
        "Organic Search": "organic_search",
        "Direct": "direct",
        "Referral": "referral",
        "Organic Social": "social",
        "Paid Search": "paid_search",
    }

    results = {}
    for row in response.rows:
        channel = row.dimension_values[0].value
        key = channel_map.get(channel, channel.lower().replace(" ", "_"))
        results[key] = {
            "users": int(row.metric_values[0].value),
            "sessions": int(row.metric_values[1].value),
        }

    return results


def get_device_breakdown(days=7):
    """
    デバイス別レポート

    返り値:
    {
      "desktop": {"users": 95, "sessions": 140},
      "mobile": {"users": 42, "sessions": 68},
      "tablet": {"users": 5, "sessions": 7}
    }
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
        ],
    )

    response = client.run_report(request)

    results = {}
    for row in response.rows:
        device = row.dimension_values[0].value.lower()
        results[device] = {
            "users": int(row.metric_values[0].value),
            "sessions": int(row.metric_values[1].value),
        }

    return results


def get_event_counts(event_names, start_date="7daysAgo", end_date="yesterday"):
    """
    指定したイベントの回数と、それを起こしたユーザー数

    返り値（期間中に1回も起きなかったイベントは 0 で返す）:
    {
      "chat_send": {"count": 12, "users": 7},
      "purchase_click": {"count": 3, "users": 2},
      ...
    }
    """
    from google.analytics.data_v1beta.types import Filter, FilterExpression

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="eventName")],
        metrics=[
            Metric(name="eventCount"),
            Metric(name="totalUsers"),
        ],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                in_list_filter=Filter.InListFilter(values=list(event_names)),
            )
        ),
    )

    response = client.run_report(request)

    results = {name: {"count": 0, "users": 0} for name in event_names}
    for row in response.rows:
        results[row.dimension_values[0].value] = {
            "count": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
        }

    return results


def get_returning_users(start_date, end_date):
    """
    リピーター数（GA4 の newVsReturning で数える）

    activeUsers - newUsers で出すと、GA4 の数え方の違いでマイナスになることがあるため、
    こちらを使う。
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="newVsReturning")],
        metrics=[Metric(name="activeUsers")],
    )

    response = client.run_report(request)

    for row in response.rows:
        if row.dimension_values[0].value == "returning":
            return int(row.metric_values[0].value)
    return 0


def get_realtime_users():
    """
    リアルタイムユーザー数取得

    返り値:
    {
      "active_users": 3
    }
    """
    from google.analytics.data_v1beta.types import RunRealtimeReportRequest

    request = RunRealtimeReportRequest(
        property=f"properties/{PROPERTY_ID}",
        metrics=[Metric(name="activeUsers")],
    )

    response = client.run_realtime_report(request)

    if not response.rows:
        return {"active_users": 0}

    return {
        "active_users": int(response.rows[0].metric_values[0].value)
    }


if __name__ == "__main__":
    print("=== Daily Overview (Past 7 days) ===")
    overview = get_daily_overview(7)
    print(json.dumps(overview, indent=2, ensure_ascii=False))

    print("\n=== Top Pages ===")
    top_pages = get_top_pages(7, 10)
    print(json.dumps(top_pages, indent=2, ensure_ascii=False))

    print("\n=== Traffic Sources ===")
    traffic = get_traffic_sources(7)
    print(json.dumps(traffic, indent=2, ensure_ascii=False))

    print("\n=== Device Breakdown ===")
    devices = get_device_breakdown(7)
    print(json.dumps(devices, indent=2, ensure_ascii=False))

    print("\n=== Realtime Users ===")
    realtime = get_realtime_users()
    print(json.dumps(realtime, indent=2, ensure_ascii=False))
