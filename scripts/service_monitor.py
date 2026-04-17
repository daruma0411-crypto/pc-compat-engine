#!/usr/bin/env python3
"""
AKGNET サービス監視スクリプト
GitHub Actions から定期実行し、全サービスのヘルスチェックを行う。
異常検知時は GitHub Issue を自動作成して通知する。
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
import ssl
import time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)

# === 監視対象サービス ===
SERVICES = [
    {
        "name": "pc-compat-engine",
        "url": "https://pc-compat-engine-production.up.railway.app/",
        "host": "Railway",
    },
    {
        "name": "AIサービス",
        "url": "http://34.85.123.74/",
        "host": "GCP VM",
    },
    {
        "name": "トミー精工PIM",
        "url": "https://bio.tomys.co.jp/products/autoclaves/",
        "host": "Railway",
    },
    {
        "name": "PB企画プランナー",
        "url": "https://web-production-1c92b.up.railway.app/",
        "host": "Railway",
    },
    {
        "name": "boatrace-predictor",
        "url": "https://web-production-c977.up.railway.app/",
        "host": "Railway",
    },
]

TIMEOUT = 15  # seconds


def check_http(service):
    """HTTP ヘルスチェック"""
    url = service["url"]
    name = service["name"]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    start = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "AKGNET-Monitor/1.0")
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        elapsed = time.time() - start
        code = resp.getcode()

        if code == 200 and elapsed <= 10:
            return {"name": name, "status": "OK", "code": code, "time": round(elapsed, 2), "note": ""}
        elif code == 200:
            return {"name": name, "status": "SLOW", "code": code, "time": round(elapsed, 2), "note": f"応答{elapsed:.1f}s"}
        else:
            return {"name": name, "status": "DOWN", "code": code, "time": round(elapsed, 2), "note": f"HTTP {code}"}
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        return {"name": name, "status": "DOWN", "code": e.code, "time": round(elapsed, 2), "note": str(e.reason)}
    except Exception as e:
        elapsed = time.time() - start
        return {"name": name, "status": "DOWN", "code": 0, "time": round(elapsed, 2), "note": str(e)[:80]}


def check_twitter_bot():
    """GitHub Actions の Twitter Bot 最新実行結果"""
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--repo", "daruma0411-crypto/pc-compat-engine",
             "--workflow=twitter-bot.yml", "--limit=1", "--json", "conclusion,startedAt"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return {"name": "Twitter Bot", "status": "UNKNOWN", "code": "-", "time": "-", "note": "gh CLI error"}

        data = json.loads(result.stdout)
        if not data:
            return {"name": "Twitter Bot", "status": "UNKNOWN", "code": "-", "time": "-", "note": "実行履歴なし"}

        run = data[0]
        conclusion = run.get("conclusion", "unknown")
        started = run.get("startedAt", "")[:10]

        if conclusion == "success":
            return {"name": "Twitter Bot", "status": "OK", "code": "-", "time": "-", "note": f"最終成功: {started}"}
        else:
            return {"name": "Twitter Bot", "status": "FAIL", "code": "-", "time": "-", "note": f"{conclusion} ({started})"}
    except Exception as e:
        return {"name": "Twitter Bot", "status": "UNKNOWN", "code": "-", "time": "-", "note": str(e)[:80]}


def create_github_issue(failures, all_results):
    """異常時に GitHub Issue を作成"""
    title = f"[ALERT] サービス異常検知 {NOW.strftime('%Y-%m-%d %H:%M')}"

    body_lines = ["## 異常検知サービス\n"]
    for f in failures:
        body_lines.append(f"- **{f['name']}** — {f['status']} (code: {f['code']}, {f['time']}s) {f['note']}")

    body_lines.append("\n## 全サービス状況\n")
    body_lines.append("| サービス | 状態 | 応答時間 | 備考 |")
    body_lines.append("|---|---|---|---|")
    for r in all_results:
        body_lines.append(f"| {r['name']} | {r['status']} | {r['time']}s | {r['note']} |")

    body_lines.append(f"\n---\n自動生成: `service_monitor.py` {NOW.strftime('%Y-%m-%d %H:%M JST')}")

    body = "\n".join(body_lines)

    try:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--repo", "daruma0411-crypto/pc-compat-engine",
             "--title", title,
             "--body", body,
             "--label", "alert,monitoring"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"Issue created: {result.stdout.strip()}")
        else:
            # label が無い場合はラベルなしで再試行
            result2 = subprocess.run(
                ["gh", "issue", "create",
                 "--repo", "daruma0411-crypto/pc-compat-engine",
                 "--title", title,
                 "--body", body],
                capture_output=True, text=True, timeout=30
            )
            if result2.returncode == 0:
                print(f"Issue created (no labels): {result2.stdout.strip()}")
            else:
                print(f"Issue creation failed: {result2.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"Issue creation error: {e}", file=sys.stderr)


def main():
    print(f"=== AKGNET Service Monitor === {NOW.strftime('%Y-%m-%d %H:%M JST')}")
    print()

    # 1. HTTP checks
    results = []
    for svc in SERVICES:
        r = check_http(svc)
        results.append(r)
        icon = "[OK]" if r["status"] == "OK" else "[NG]" if r["status"] == "DOWN" else "[!!]"
        print(f"  {icon} {r['name']:20s} {r['status']:5s} {r['time']}s  {r['note']}")

    # 2. Twitter Bot check
    tw = check_twitter_bot()
    results.append(tw)
    icon = "[OK]" if tw["status"] == "OK" else "[NG]"
    print(f"  {icon} {tw['name']:20s} {tw['status']:5s} {tw['time']}  {tw['note']}")

    print()

    # 3. Detect failures
    failures = [r for r in results if r["status"] in ("DOWN", "FAIL")]
    ok_count = sum(1 for r in results if r["status"] == "OK")
    total = len(results)

    if failures:
        print(f"ALERT: {len(failures)} failures / {total} services")
        for f in failures:
            print(f"  -> {f['name']}: {f['status']} - {f['note']}")

        # Create GitHub Issue on CI
        if os.environ.get("GITHUB_ACTIONS"):
            create_github_issue(failures, results)

        sys.exit(1)  # workflow failure -> GitHub email notification
    else:
        print(f"ALL OK: {ok_count}/{total} services healthy")
        sys.exit(0)


if __name__ == "__main__":
    main()
