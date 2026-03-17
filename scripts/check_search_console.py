#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Search Console API でインデックス状況とクエリを確認"""
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDENTIALS_PATH = Path(__file__).parent.parent / 'credentials' / 'google-analytics-service-account.json'
SITE_URL = 'https://pc-jisaku.com'

def main():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_PATH),
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('searchconsole', 'v1', credentials=credentials)
    except Exception as e:
        print(f"❌ Search Console API 接続失敗: {e}")
        print("\n📋 手動確認方法:")
        print("1. https://search.google.com/search-console にアクセス")
        print(f"2. プロパティ: {SITE_URL}")
        print("3. 「サイトマップ」でインデックス状況を確認")
        return

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=28)).strftime('%Y-%m-%d')

    # 検索クエリ TOP20
    print("=" * 60)
    print(f"📊 Google Search Console レポート")
    print(f"期間: {start_date} ～ {end_date}")
    print("=" * 60)

    try:
        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': 20
            }
        ).execute()

        rows = response.get('rows', [])
        if rows:
            print("\n🔍 検索クエリ TOP20:")
            print(f"{'クエリ':<40} {'クリック':>6} {'表示':>8} {'CTR':>6} {'順位':>6}")
            print("-" * 70)
            for row in rows:
                query = row['keys'][0]
                clicks = int(row['clicks'])
                impressions = int(row['impressions'])
                ctr = f"{row['ctr']*100:.1f}%"
                position = f"{row['position']:.1f}"
                print(f"{query:<40} {clicks:>6} {impressions:>8} {ctr:>6} {position:>6}")
        else:
            print("\n⚠️ 検索クエリデータがありません")
    except Exception as e:
        print(f"\n❌ クエリ取得エラー: {e}")

    # ページ別 TOP20
    try:
        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page'],
                'rowLimit': 20
            }
        ).execute()

        rows = response.get('rows', [])
        if rows:
            print("\n📄 ページ別 TOP20:")
            print(f"{'ページ':<60} {'クリック':>6} {'表示':>8}")
            print("-" * 80)
            for row in rows:
                page = row['keys'][0].replace(SITE_URL, '')
                clicks = int(row['clicks'])
                impressions = int(row['impressions'])
                print(f"{page:<60} {clicks:>6} {impressions:>8}")
        else:
            print("\n⚠️ ページデータがありません")
    except Exception as e:
        print(f"\n❌ ページ取得エラー: {e}")


if __name__ == '__main__':
    main()
