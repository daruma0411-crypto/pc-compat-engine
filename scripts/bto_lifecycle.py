#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTO商品ライフサイクル管理パイプライン

bto_url_verifier.py + bto_price_updater.py の統合版。
週次で実行し、全BTO商品のURL検証・価格更新・廃盤検知を一括処理する。

機能:
  1. URL生存確認（全件）→ url_verified 更新
  2. 価格更新（生存確認済みのみ）
  3. 廃盤検知（404/販売終了キーワード）→ tags に out_of_stock 追加
  4. 差分ログ出力
  5. git commit & push

実行:
  python scripts/bto_lifecycle.py                # フル実行
  python scripts/bto_lifecycle.py --verify-only  # URL検証のみ
  python scripts/bto_lifecycle.py --dry-run      # 書き込みなし

自動化:
  GitHub Actions bto-lifecycle.yml (毎週水曜)
"""

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "workspace", "data")
BTO_JSONL = os.path.join(DATA_DIR, "bto", "products.jsonl")
DIFF_LOG_DIR = os.path.join(DATA_DIR, "diff_logs")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# 在庫切れ/販売終了キーワード
_END_KEYWORDS = [
    "販売終了", "取り扱い終了", "取扱終了", "生産終了",
    "品切れ", "完売", "sold out", "out of stock",
    "現在販売しておりません", "お取り扱いできません",
]

# 誤ページ検出（パソコン工房のproduct_id再利用対策）
_WRONG_PAGE_KEYWORDS = [
    "中古保証", "在庫切れです",
]

# ─────────────────────────────────────────────────────────────────────────────
# HTTP取得
# ─────────────────────────────────────────────────────────────────────────────

def fetch_html(url: str, retries: int = 3) -> tuple[int, str]:
    """URLからHTMLを取得。リトライ付き。"""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ja,en-US;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                return resp.getcode(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if attempt == retries:
                return e.code, ""
            delay = 2 ** attempt
            print(f"  [RETRY {attempt}/{retries}] HTTP {e.code} → {delay}s wait")
            time.sleep(delay)
        except Exception as e:
            if attempt == retries:
                print(f"  [ERROR] {e}")
                return 0, ""
            time.sleep(2 ** attempt)
    return 0, ""


# ─────────────────────────────────────────────────────────────────────────────
# URL検証
# ─────────────────────────────────────────────────────────────────────────────

def verify_url(url: str, model: str, html: str) -> tuple[bool, str]:
    """
    HTMLにモデル名が含まれるか厳密チェック。

    Returns:
        (is_valid, reason)
    """
    if not html:
        return False, "empty_response"

    html_lower = html.lower()

    # 誤ページ検出
    for kw in _WRONG_PAGE_KEYWORDS:
        if kw in html:
            return False, "wrong_product"

    # 販売終了検出
    for kw in _END_KEYWORDS:
        if kw.lower() in html_lower:
            return False, "ended"

    # モデル名の厳密マッチ
    model_key = model.split(" ")[0] if " " in model else model
    if model_key and model_key.lower() in html_lower:
        return True, "model_match"

    return False, "model_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# 価格抽出（bto_price_updater.py から移植）
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_price(raw: str) -> int | None:
    raw = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    raw = raw.replace(",", "").replace("，", "").replace(" ", "").replace("\u3000", "")
    digits = re.sub(r"[^\d]", "", raw)
    if digits and len(digits) >= 4:
        val = int(digits)
        if 10000 <= val <= 3000000:
            return val
    return None


def _extract_price(html: str) -> int | None:
    """汎用価格抽出。複数パターンを試行。"""
    patterns = [
        r'class="[^"]*(?:total_price|price_value|price)[^"]*"[^>]*>\s*[¥￥]?\s*([0-9０-９,，]+)',
        r"販売価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"基本構成価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"通常価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"特別価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"税込[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"[¥￥]\s*([0-9０-９,，]+)",
        r"([0-9０-９,，]+)\s*円\s*[\(（]\s*税込",
        r'"price"\s*:\s*"?(\d[\d,]*)"?',
        r'"lowPrice"\s*:\s*"?(\d[\d,]*)"?',
        r'data-price=["\'](\d+)["\']',
        r'content=["\'](\d[\d,]*)["\']',
    ]
    for pat in patterns:
        for m in re.findall(pat, html):
            price = _normalize_price(m)
            if price:
                return price
    return None


# ─────────────────────────────────────────────────────────────────────────────
# JSONL 読み書き
# ─────────────────────────────────────────────────────────────────────────────

def load_products(path: str) -> list[dict]:
    products = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def save_products(path: str, products: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in products:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# 差分ログ
# ─────────────────────────────────────────────────────────────────────────────

def save_diff_log(changes: list[dict]) -> str | None:
    if not changes:
        return None
    os.makedirs(DIFF_LOG_DIR, exist_ok=True)
    path = os.path.join(DIFF_LOG_DIR, f"bto-{TODAY}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for c in changes:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Git commit & push
# ─────────────────────────────────────────────────────────────────────────────

def git_commit_and_push():
    print("\n=== git commit & push ===")

    def run(cmd):
        result = subprocess.run(
            cmd, cwd=REPO_ROOT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result.returncode

    run(["git", "add", BTO_JSONL])
    run(["git", "add", DIFF_LOG_DIR])

    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO_ROOT,
    )
    if result.returncode == 0:
        print("変更なし。スキップ。")
        return

    run(["git", "commit", "-m", f"auto: BTO lifecycle update {TODAY}"])
    rc = run(["git", "push", "origin", "main"])
    if rc != 0:
        print("[WARN] push 失敗。手動で push してください。")


# ─────────────────────────────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────────────────────────────

def run_lifecycle(verify_only: bool = False, dry_run: bool = False) -> dict:
    """BTOライフサイクル更新のメイン処理。"""
    stats = {
        "verified_ok": 0,
        "verified_fail": 0,
        "price_updated": 0,
        "price_unchanged": 0,
        "ended": 0,
        "error": 0,
    }
    changes = []

    products = load_products(BTO_JSONL)
    total = len(products)
    print(f"BTO商品: {total}件")
    print(f"モード: {'検証のみ' if verify_only else 'フル'} {'(dry-run)' if dry_run else ''}")
    print("=" * 60)

    for i, p in enumerate(products, 1):
        pid = p.get("id", "?")
        maker = p.get("maker", "?")
        model = p.get("model", "?")
        url = p.get("url", "")
        old_price = p.get("price_jpy")
        old_verified = p.get("url_verified")
        tags = p.get("tags", [])

        label = f"[{i}/{total}] {maker} {model}"
        print(f"{label}")

        if not url:
            print(f"  SKIP: URLなし")
            stats["error"] += 1
            continue

        # ─── Step 1: URL検証 ───
        print(f"  URL: {url[:80]}...")
        status_code, html = fetch_html(url)

        if status_code == 0:
            print(f"  ERROR: 取得失敗")
            stats["error"] += 1
            time.sleep(1)
            continue

        if status_code == 403:
            # Bot対策（ark等）→ 前回の検証結果を維持
            print(f"  SKIP: 403 Forbidden (Bot対策)")
            stats["error"] += 1
            time.sleep(1)
            continue

        if status_code == 429:
            # レート制限 → 前回の検証結果を維持
            print(f"  SKIP: 429 Rate Limited")
            stats["error"] += 1
            time.sleep(3)
            continue

        if status_code == 404:
            print(f"  FAIL: 404 Not Found")
            if not dry_run:
                p["url_verified"] = False
                if "out_of_stock" not in tags:
                    tags.append("out_of_stock")
                    p["tags"] = tags
            changes.append({"id": pid, "type": "url_dead", "status": 404})
            stats["verified_fail"] += 1
            stats["ended"] += 1
            time.sleep(0.5)
            continue

        # HTML取得成功 → モデル名チェック
        is_valid, reason = verify_url(url, model, html)

        if not is_valid:
            print(f"  FAIL: {reason}")
            if not dry_run:
                p["url_verified"] = False
                if reason == "ended" and "out_of_stock" not in tags:
                    tags.append("out_of_stock")
                    p["tags"] = tags
            if old_verified is not False:
                changes.append({"id": pid, "type": "url_invalid", "reason": reason})
            stats["verified_fail"] += 1
            time.sleep(0.5)
            continue

        # URL有効
        print(f"  OK: {reason}")
        if not dry_run:
            p["url_verified"] = True
        if old_verified is False:
            changes.append({"id": pid, "type": "url_restored"})
        stats["verified_ok"] += 1

        # ─── Step 2: 価格更新（verify_only でなければ）───
        if verify_only:
            time.sleep(0.5)
            continue

        new_price = _extract_price(html)
        if new_price is None:
            print(f"  価格: 抽出失敗")
            time.sleep(0.5)
            continue

        if old_price == new_price:
            print(f"  価格: {new_price:,}円 (変動なし)")
            stats["price_unchanged"] += 1
        else:
            diff = new_price - (old_price or 0)
            diff_str = f"+{diff:,}" if diff > 0 else f"{diff:,}"
            print(f"  価格: {old_price:,}円 → {new_price:,}円 ({diff_str})")
            if not dry_run:
                p["price_jpy"] = new_price
                p["price_updated_at"] = TODAY
            changes.append({
                "id": pid, "type": "price_change",
                "old": old_price, "new": new_price,
            })
            stats["price_updated"] += 1

        time.sleep(0.5)

    # ─── 保存 ───
    if not dry_run:
        save_products(BTO_JSONL, products)
        print(f"\nproducts.jsonl 保存完了")

        log_path = save_diff_log(changes)
        if log_path:
            print(f"差分ログ: {log_path}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BTO商品ライフサイクル管理")
    parser.add_argument("--verify-only", action="store_true",
                        help="URL検証のみ（価格更新をスキップ）")
    parser.add_argument("--dry-run", action="store_true",
                        help="書き込みなし")
    parser.add_argument("--no-push", action="store_true",
                        help="git push をスキップ")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"BTO ライフサイクル更新 {TODAY}")
    print(f"{'=' * 60}")

    stats = run_lifecycle(
        verify_only=args.verify_only,
        dry_run=args.dry_run,
    )

    # サマリー
    print(f"\n{'=' * 60}")
    print(f"サマリー")
    print(f"{'=' * 60}")
    print(f"  URL有効:   {stats['verified_ok']}件")
    print(f"  URL無効:   {stats['verified_fail']}件")
    print(f"  価格更新:  {stats['price_updated']}件")
    print(f"  価格変動なし: {stats['price_unchanged']}件")
    print(f"  販売終了:  {stats['ended']}件")
    print(f"  エラー:    {stats['error']}件")
    print(f"{'=' * 60}")

    if not args.dry_run and not args.no_push:
        git_commit_and_push()

    print(f"\n=== 完了 {TODAY} ===")


if __name__ == "__main__":
    main()
