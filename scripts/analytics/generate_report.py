"""
HTMLレポート生成スクリプト
"""

import os
import sys
import json
from datetime import datetime

# fetch_reports.py と同じディレクトリから import
sys.path.insert(0, os.path.dirname(__file__))
from fetch_reports import (
    get_daily_overview,
    get_top_pages,
    get_traffic_sources,
    get_device_breakdown,
    get_realtime_users,
)


def generate_html_report(days=7):
    """
    HTMLレポート生成

    保存先: reports/analytics_YYYYMMDD.html
    """
    overview = get_daily_overview(days)
    top_pages = get_top_pages(days, 10)
    traffic = get_traffic_sources(days)
    devices = get_device_breakdown(days)
    realtime = get_realtime_users()

    # overview が None の場合のフォールバック
    if overview is None:
        overview = {
            "total_users": 0,
            "total_sessions": 0,
            "total_pageviews": 0,
            "avg_session_duration": 0.0,
            "bounce_rate": 0.0,
        }

    # テーブル行生成
    top_pages_rows = ""
    for i, page in enumerate(top_pages):
        top_pages_rows += f"""
    <tr>
      <td>{i+1}</td>
      <td>{page['page']}</td>
      <td>{page['pageviews']:,}</td>
      <td>{page['users']:,}</td>
    </tr>"""

    traffic_rows = ""
    for channel_name, data in traffic.items():
        traffic_rows += f"""
    <tr>
      <td>{channel_name}</td>
      <td>{data['users']:,}</td>
      <td>{data['sessions']:,}</td>
    </tr>"""

    device_rows = ""
    for device, data in devices.items():
        device_rows += f"""
    <tr>
      <td>{device.capitalize()}</td>
      <td>{data['users']:,}</td>
      <td>{data['sessions']:,}</td>
    </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Analytics Report - {datetime.now().strftime('%Y-%m-%d')}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }}
    h1 {{
      color: #1a73e8;
      border-bottom: 3px solid #1a73e8;
      padding-bottom: 10px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin: 20px 0;
    }}
    .metric-card {{
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .metric-value {{
      font-size: 2em;
      font-weight: bold;
      color: #1a73e8;
    }}
    .metric-label {{
      color: #666;
      margin-top: 5px;
    }}
    table {{
      width: 100%;
      background: white;
      border-collapse: collapse;
      margin: 20px 0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    th, td {{
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #e0e0e0;
    }}
    th {{
      background: #1a73e8;
      color: white;
    }}
    .realtime {{
      background: #34a853;
      color: white;
      padding: 10px 20px;
      border-radius: 20px;
      display: inline-block;
      margin: 20px 0;
    }}
  </style>
</head>
<body>
  <h1>PC互換チェッカー - Analytics Report</h1>
  <p>期間: 過去{days}日間 | 生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>

  <div class="realtime">
    リアルタイム: {realtime['active_users']}人
  </div>

  <h2>サマリー</h2>
  <div class="metrics">
    <div class="metric-card">
      <div class="metric-value">{overview['total_users']:,}</div>
      <div class="metric-label">ユーザー数</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{overview['total_sessions']:,}</div>
      <div class="metric-label">セッション数</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{overview['total_pageviews']:,}</div>
      <div class="metric-label">ページビュー</div>
    </div>
    <div class="metric-card">
      <div class="metric-value">{overview['avg_session_duration']:.1f}秒</div>
      <div class="metric-label">平均セッション時間</div>
    </div>
  </div>

  <h2>人気ページ TOP 10</h2>
  <table>
    <tr>
      <th>#</th>
      <th>ページ</th>
      <th>ページビュー</th>
      <th>ユーザー数</th>
    </tr>{top_pages_rows}
  </table>

  <h2>流入元</h2>
  <table>
    <tr>
      <th>チャネル</th>
      <th>ユーザー数</th>
      <th>セッション数</th>
    </tr>{traffic_rows}
  </table>

  <h2>デバイス</h2>
  <table>
    <tr>
      <th>デバイス</th>
      <th>ユーザー数</th>
      <th>セッション数</th>
    </tr>{device_rows}
  </table>

</body>
</html>"""

    # 保存
    reports_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    filename = os.path.join(reports_dir, f"analytics_{datetime.now().strftime('%Y%m%d')}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report saved: {filename}")
    return filename


if __name__ == "__main__":
    generate_html_report(7)
