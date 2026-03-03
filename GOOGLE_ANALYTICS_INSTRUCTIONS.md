# Google Analytics 自動レポート取得 実装指示書

## 📌 目的

Google Analytics 4 (GA4) のデータを自動取得し、サイト分析を自動化する。

### 取得したいデータ
- **ユーザー数**（日別・週別・月別）
- **ページビュー数**
- **人気ページ**（どのゲームページが見られているか）
- **流入元**（検索エンジン、SNS、直接アクセス）
- **デバイス**（PC、モバイル、タブレット）
- **地域**（国・都市）
- **検索キーワード**（Search Console連携時）
- **リアルタイムユーザー数**

### 活用方法
- 毎日自動でレポート生成 → Telegram通知
- ダッシュボード表示（HTML形式）
- CSV/JSONエクスポート

---

## 🎯 実装タスク

### フェーズ1: Google Analytics API セットアップ

#### タスク1.1: サービスアカウント作成

**手順（手動・初回のみ）:**

1. **Google Cloud Console にアクセス**
   ```
   https://console.cloud.google.com/
   ```

2. **プロジェクト作成**
   - 「新しいプロジェクト」→ 名前: `pc-compat-analytics`

3. **Analytics Data API を有効化**
   - 「APIとサービス」→「ライブラリ」
   - 検索: `Google Analytics Data API`
   - 「有効にする」

4. **サービスアカウント作成**
   - 「APIとサービス」→「認証情報」
   - 「認証情報を作成」→「サービスアカウント」
   - 名前: `analytics-reader`
   - ロール: `閲覧者`
   - 「完了」

5. **キーファイルダウンロード**
   - 作成したサービスアカウントをクリック
   - 「キー」タブ → 「鍵を追加」→「新しい鍵を作成」
   - 形式: JSON
   - ダウンロード → `service-account-key.json` に保存

6. **Google Analytics にサービスアカウントを追加**
   - Google Analytics（https://analytics.google.com/）にアクセス
   - 「管理」→「プロパティ アクセス管理」
   - サービスアカウントのメールアドレスを追加
   - 権限: `閲覧者`

---

#### タスク1.2: 認証情報の配置

**ファイル構成:**
```
pc-compat-engine/
├── credentials/
│   └── google-analytics-service-account.json  # ← ここに配置
├── .gitignore  # ← credentials/ を追加
```

**.gitignore に追加:**
```
# Google Analytics credentials
credentials/
*.json
!package.json
!workspace/data/**/*.json
```

**環境変数設定:**
```bash
# .env ファイルに追加
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-analytics-service-account.json
GA4_PROPERTY_ID=482563486  # あなたのプロパティID
```

---

### フェーズ2: データ取得スクリプト実装

#### タスク2.1: 基本レポート取得

**ファイル:** `scripts/analytics/fetch_reports.py`

```python
"""
Google Analytics 4 データ取得スクリプト

必要ライブラリ:
pip install google-analytics-data google-auth
"""

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account
import os
import json
from datetime import datetime, timedelta

# 認証
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
PROPERTY_ID = os.getenv('GA4_PROPERTY_ID')

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

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
        order_bys=[{"metric": {"metric_name": "screenPageViews"}, "desc": True}],
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
    # テスト実行
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
```

---

#### タスク2.2: レポート生成（HTML形式）

**ファイル:** `scripts/analytics/generate_report.py`

```python
"""
HTMLレポート生成スクリプト
"""

from fetch_reports import (
    get_daily_overview,
    get_top_pages,
    get_traffic_sources,
    get_device_breakdown,
    get_realtime_users,
)
from datetime import datetime
import json

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
    
    html = f"""
<!DOCTYPE html>
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
  <h1>📊 PC互換チェッカー - Analytics Report</h1>
  <p>期間: 過去{days}日間 | 生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
  
  <div class="realtime">
    🔴 リアルタイム: {realtime['active_users']}人
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
    </tr>
    {"".join([f'''
    <tr>
      <td>{i+1}</td>
      <td>{page['page']}</td>
      <td>{page['pageviews']:,}</td>
      <td>{page['users']:,}</td>
    </tr>
    ''' for i, page in enumerate(top_pages)])}
  </table>
  
  <h2>流入元</h2>
  <table>
    <tr>
      <th>チャネル</th>
      <th>ユーザー数</th>
      <th>セッション数</th>
    </tr>
    {"".join([f'''
    <tr>
      <td>{channel_name}</td>
      <td>{data['users']:,}</td>
      <td>{data['sessions']:,}</td>
    </tr>
    ''' for channel_name, data in traffic.items()])}
  </table>
  
  <h2>デバイス</h2>
  <table>
    <tr>
      <th>デバイス</th>
      <th>ユーザー数</th>
      <th>セッション数</th>
    </tr>
    {"".join([f'''
    <tr>
      <td>{device.capitalize()}</td>
      <td>{data['users']:,}</td>
      <td>{data['sessions']:,}</td>
    </tr>
    ''' for device, data in devices.items()])}
  </table>
  
</body>
</html>
"""
    
    # 保存
    import os
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/analytics_{datetime.now().strftime('%Y%m%d')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Report saved: {filename}")
    return filename


if __name__ == "__main__":
    generate_html_report(7)
```

---

### フェーズ3: 自動化・通知

#### タスク3.1: 定期実行スクリプト

**ファイル:** `scripts/analytics/daily_report.sh`

```bash
#!/bin/bash
# 毎日AM 9:00に実行（cron設定）

cd /path/to/pc-compat-engine

# Pythonスクリプト実行
python scripts/analytics/generate_report.py

# Telegram通知（オプション）
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  REPORT_FILE=$(ls -t reports/analytics_*.html | head -1)
  
  # サマリーテキスト取得
  SUMMARY=$(python scripts/analytics/fetch_reports.py | grep -A 5 "Daily Overview")
  
  # Telegram送信
  curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TELEGRAM_CHAT_ID" \
    -d "text=📊 本日のアナリティクスレポート%0A%0A$SUMMARY%0A%0A詳細: $REPORT_FILE"
fi
```

**crontab 設定:**
```cron
# 毎日AM 9:00にレポート生成
0 9 * * * /path/to/pc-compat-engine/scripts/analytics/daily_report.sh
```

---

#### タスク3.2: Telegram 通知スクリプト

**ファイル:** `scripts/analytics/notify_telegram.py`

```python
"""
Telegram通知スクリプト
"""

import os
import requests
from fetch_reports import get_daily_overview, get_realtime_users

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_daily_summary():
    """
    毎日のサマリーをTelegramに送信
    """
    overview = get_daily_overview(1)  # 昨日のデータ
    realtime = get_realtime_users()
    
    message = f"""
📊 **PC互換チェッカー - 本日のレポート**

🔴 リアルタイム: {realtime['active_users']}人

**昨日の実績:**
👥 ユーザー数: {overview['total_users']:,}
📄 ページビュー: {overview['total_pageviews']:,}
📈 セッション数: {overview['total_sessions']:,}
⏱️ 平均滞在時間: {overview['avg_session_duration']:.1f}秒
📊 直帰率: {overview['bounce_rate']*100:.1f}%

詳細レポート: reports/analytics_{datetime.now().strftime('%Y%m%d')}.html
"""
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, data=data)
    if response.ok:
        print("Telegram notification sent!")
    else:
        print(f"Failed to send: {response.text}")


if __name__ == "__main__":
    from datetime import datetime
    send_daily_summary()
```

---

### フェーズ4: ダッシュボード表示

#### タスク4.1: Webダッシュボード（オプション）

**ファイル:** `static/dashboard.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>Analytics Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
</head>
<body>
  <h1>📊 リアルタイムダッシュボード</h1>
  
  <div id="realtime">読み込み中...</div>
  
  <canvas id="traffic-chart" width="400" height="200"></canvas>
  
  <script>
    // /api/analytics エンドポイントから取得
    async function loadAnalytics() {
      const response = await fetch('/api/analytics?days=7');
      const data = await response.json();
      
      document.getElementById('realtime').innerHTML = 
        `🔴 リアルタイム: ${data.realtime.active_users}人`;
      
      // Chart.js でグラフ描画
      const ctx = document.getElementById('traffic-chart');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: Object.keys(data.traffic),
          datasets: [{
            label: 'ユーザー数',
            data: Object.values(data.traffic).map(v => v.users)
          }]
        }
      });
    }
    
    loadAnalytics();
    setInterval(loadAnalytics, 60000);  // 1分ごとに更新
  </script>
</body>
</html>
```

**Flask エンドポイント追加:**
```python
# app.py に追加

@app.route('/api/analytics')
def api_analytics():
    """
    Analytics データAPI
    """
    from scripts.analytics.fetch_reports import (
        get_daily_overview,
        get_traffic_sources,
        get_realtime_users
    )
    
    days = request.args.get('days', 7, type=int)
    
    return jsonify({
        'overview': get_daily_overview(days),
        'traffic': get_traffic_sources(days),
        'realtime': get_realtime_users()
    })
```

---

## 📦 依存ライブラリ

**インストール:**
```bash
pip install google-analytics-data google-auth requests
```

**requirements.txt に追加:**
```
google-analytics-data==0.18.0
google-auth==2.23.0
```

---

## ✅ 完了条件

### フェーズ1完了:
- [ ] サービスアカウント作成
- [ ] `credentials/google-analytics-service-account.json` 配置
- [ ] Google Analytics にサービスアカウント追加

### フェーズ2完了:
- [ ] `fetch_reports.py` でデータ取得成功
- [ ] `generate_report.py` でHTML生成成功
- [ ] `reports/` フォルダにHTMLファイル保存

### フェーズ3完了:
- [ ] cron設定（毎日AM 9:00実行）
- [ ] Telegram通知動作確認

### フェーズ4完了（オプション）:
- [ ] `/api/analytics` エンドポイント実装
- [ ] ダッシュボードページ表示

---

## 🚀 実装開始コマンド

Claude Code で実装する場合:

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# フェーズ2のみ実装（フェーズ1は手動設定が必要）
claude "GOOGLE_ANALYTICS_INSTRUCTIONS.md のフェーズ2を実装してください。
Google Analytics Data APIを使ってレポート取得スクリプトを作成してください。"

# フェーズ3実装
claude "フェーズ3を実装してください。定期実行とTelegram通知を追加してください。"
```

---

## 📝 注意事項

### セキュリティ
- **credentials/ フォルダは絶対にGitにコミットしない**
- `.gitignore` に `credentials/` を追加済みか確認
- サービスアカウントキーは厳重管理

### レート制限
- Google Analytics Data API: 1日あたり50,000リクエスト
- 頻繁にリアルタイムデータを取得しすぎない（1分に1回程度）

### プロパティID確認
```
Google Analytics → 管理 → プロパティ設定 → プロパティID
例: 482563486
```

---

以上です。実装頑張ってください！ 📊
