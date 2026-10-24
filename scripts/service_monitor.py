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
        # deep=1 で AI 相談に使う Anthropic API キーが有効かまで確かめる
        "url": "https://pc-compat-engine-production.up.railway.app/api/health?deep=1",
        "host": "Railway",
        "expect_json": {"api_key_valid": True},
    },
    {
        "name": "AIサービス",
        "url": "https://34.85.123.74/",
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
REPO = "daruma0411-crypto/pc-compat-engine"


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

        if code == 200 and service.get("expect_json"):
            try:
                body = json.loads(resp.read().decode("utf-8"))
            except ValueError:
                body = {}
            wrong = [k for k, v in service["expect_json"].items() if body.get(k) != v]
            if wrong:
                note = ", ".join(f"{k}={body.get(k)}" for k in wrong)
                return {"name": name, "status": "DOWN", "code": code, "time": round(elapsed, 2), "note": note}

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


# === 監視する自動化ジョブ ===
# fail_after: 直近この回数すべてが失敗したときだけ異常とみなす（1回の失敗で騒がない）
WORKFLOWS = [
    {"name": "Twitter Bot", "file": "twitter-bot.yml", "fail_after": 3},
    {"name": "Blog Generator", "file": "blog-generator.yml", "fail_after": 1},
]


def check_workflow(wf):
    """GitHub Actions のジョブが直近で続けて失敗していないかを見る"""
    name, n = wf["name"], wf["fail_after"]
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--repo", REPO,
             f"--workflow={wf['file']}", "--status=completed", f"--limit={n}",
             "--json", "conclusion,startedAt"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return {"name": name, "status": "UNKNOWN", "code": "-", "time": "-", "note": "gh CLI error"}

        runs = json.loads(result.stdout)
        if not runs:
            return {"name": name, "status": "UNKNOWN", "code": "-", "time": "-", "note": "実行履歴なし"}

        started = runs[0].get("startedAt", "")[:10]
        failed = [r for r in runs if r.get("conclusion") != "success"]
        if len(runs) >= n and len(failed) == len(runs):
            return {"name": name, "status": "FAIL", "code": "-", "time": "-",
                    "note": f"直近{n}回連続で失敗 ({started})"}
        note = f"最終実行: {started}" + (f"（直近{len(runs)}回中{len(failed)}回失敗）" if failed else "")
        return {"name": name, "status": "OK", "code": "-", "time": "-", "note": note}
    except Exception as e:
        return {"name": name, "status": "UNKNOWN", "code": "-", "time": "-", "note": str(e)[:80]}


def find_open_alert_issue():
    """まだ閉じていない [ALERT] Issue の番号を返す（なければ None）"""
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", REPO, "--state", "open",
         "--search", "[ALERT] in:title", "--json", "number", "--limit", "1"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None
    issues = json.loads(result.stdout or "[]")
    return issues[0]["number"] if issues else None


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
        # 開いたままの Alert Issue があれば、新しく作らずにそこへ追記する
        existing = find_open_alert_issue()
        if existing:
            result = subprocess.run(
                ["gh", "issue", "comment", str(existing), "--repo", REPO,
                 "--body", f"### {title}\n\n{body}"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"Issue #{existing} に追記しました")
                return
            print(f"Issue comment failed: {result.stderr}", file=sys.stderr)

        result = subprocess.run(
            ["gh", "issue", "create",
             "--repo", REPO,
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
                 "--repo", REPO,
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

    # 2. Automation jobs
    for wf in WORKFLOWS:
        r = check_workflow(wf)
        results.append(r)
        icon = "[OK]" if r["status"] == "OK" else "[NG]" if r["status"] == "FAIL" else "[!!]"
        print(f"  {icon} {r['name']:20s} {r['status']:5s} {r['time']}  {r['note']}")

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
