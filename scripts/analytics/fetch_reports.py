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
      "total_sessions": 215,
      "total_pageviews": 422,
      "avg_session_duration": 125.3,
      "bounce_rate": 0.42
    }
    """
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        metrics=[
            Metric(name="activeUsers"),
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
    return {
        "total_users": int(row.metric_values[0].value),
        "total_sessions": int(row.metric_values[1].value),
        "total_pageviews": int(row.metric_values[2].value),
        "avg_session_duration": float(row.metric_values[3].value),
        "bounce_rate": float(row.metric_values[4].value),
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
