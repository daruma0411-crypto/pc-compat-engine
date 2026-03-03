#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTO商品 価格自動更新スクレイパー

各BTOメーカーの商品ページにアクセスし、現在の販売価格を取得して
workspace/data/bto/products.jsonl を更新する。

対応メーカー:
  パソコン工房, サイコム, ツクモ, マウスコンピューター,
  FRONTIER, HP, Lenovo, STORM, SEVEN
  ※ ドスパラはランディングページのみのためスキップ

実行方法:
  python scripts/bto_price_updater.py
  python scripts/bto_price_updater.py --dry-run
"""

import sys
import os
import json
import re
import time
import random
import subprocess
import argparse
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

# ─────────────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────────────

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(REPO_ROOT, "workspace", "data", "bto", "products.jsonl")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# 在庫切れ判定キーワード
OUT_OF_STOCK_KEYWORDS = [
    "品切れ",
    "在庫なし",
    "販売終了",
    "完売",
    "生産終了",
    "取扱終了",
    "sold out",
    "out of stock",
    "現在販売しておりません",
    "お取り扱いできません",
]

# ドスパラはランディングページのため価格取得不可
SKIP_DOMAINS = ["dospara.co.jp"]

# リトライ設定
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # 秒 (指数バックオフの基底)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP取得（リトライ付き）
# ─────────────────────────────────────────────────────────────────────────────

def fetch_html(url: str) -> tuple[int, str]:
    """
    URLからHTMLを取得する。

    Returns:
        (status_code, html_text)
        失敗時は (0, "") を返す。
    """
    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=30,
                verify=False,
                http2=False,
            ) as client:
                resp = client.get(url, headers=headers)
                return resp.status_code, resp.text
        except Exception as e:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            print(f"  [RETRY {attempt}/{MAX_RETRIES}] {e} → {delay:.1f}秒待機")
            if attempt < MAX_RETRIES:
                time.sleep(delay)

    return 0, ""


# ─────────────────────────────────────────────────────────────────────────────
# 共通価格パース
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_price(raw: str) -> int | None:
    """カンマ・全角数字を含む価格文字列を int に変換する。"""
    # 全角→半角
    raw = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    # カンマ・スペース除去
    raw = raw.replace(",", "").replace("，", "").replace(" ", "").replace("\u3000", "")
    digits = re.sub(r"[^\d]", "", raw)
    if digits and len(digits) >= 4:  # 最低4桁（例: 9980）
        val = int(digits)
        # 妥当な価格範囲チェック (1万円〜300万円)
        if 10000 <= val <= 3000000:
            return val
    return None


def _extract_generic_price(html: str) -> int | None:
    """
    汎用の価格抽出。複数パターンを試して最初にヒットした妥当な価格を返す。
    """
    patterns = [
        # ¥XXX,XXX 形式
        r"[¥￥]\s*([0-9０-９,，]+)",
        # 税込 XXX,XXX 円
        r"税込[^0-9０-９]*([0-9０-９,，]+)\s*円",
        # XXX,XXX円（税込）
        r"([0-9０-９,，]+)\s*円\s*[\(（]\s*税込",
        # XXX,XXX円(税込)  alt spacing
        r"([0-9０-９,，]+)\s*円\s*\(税込\)",
        # data-price 属性
        r'data-price=["\'](\d+)["\']',
        # price JSON
        r'"price"\s*:\s*"?(\d[\d,]*)"?',
        # content="XXX" (meta tag)
        r'content=["\'](\d[\d,]*)["\']',
    ]
    for pat in patterns:
        matches = re.findall(pat, html)
        for m in matches:
            price = _normalize_price(m)
            if price:
                return price
    return None


# ─────────────────────────────────────────────────────────────────────────────
# メーカー別価格抽出
# ─────────────────────────────────────────────────────────────────────────────

def extract_price_pc_koubou(html: str) -> int | None:
    """パソコン工房 (pc-koubou.jp) 価格抽出"""
    # パソコン工房は「通常価格」「販売価格」の形式
    # <span class="total_price">XXX,XXX</span>円（税込）
    for pat in [
        r'class="total_price"[^>]*>\s*([0-9,]+)\s*</span>',
        r'class="price_value"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r'id="price"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"通常価格[^0-9]*([0-9,]+)\s*円",
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_sycom(html: str) -> int | None:
    """サイコム (sycom.co.jp) 価格抽出"""
    # サイコムは基本構成価格を表示
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"基本構成価格[^0-9]*([0-9,]+)\s*円",
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"合計金額[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_tsukumo(html: str) -> int | None:
    """ツクモ (tsukumo.co.jp) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"特価[^0-9]*([0-9,]+)\s*円",
        r"税込価格[^0-9]*([0-9,]+)\s*円",
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_mouse(html: str) -> int | None:
    """マウスコンピューター (mouse-jp.co.jp) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"一括価格[^0-9]*([0-9,]+)\s*円",
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
        r'data-price=["\'](\d+)["\']',
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_frontier(html: str) -> int | None:
    """FRONTIER (frontier-direct.jp) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"特別価格[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_hp(html: str) -> int | None:
    """HP (jp.ext.hp.com) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"通常価格[^0-9]*([0-9,]+)\s*円",
        r"キャンペーン価格[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
        r'"price":\s*"?([0-9,]+)"?',
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_lenovo(html: str) -> int | None:
    """Lenovo (lenovo.com/jp) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"特別価格[^0-9]*([0-9,]+)\s*円",
        r"E-クーポン適用後[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
        r'"price":\s*"?([0-9,]+)"?',
        r'"lowPrice":\s*"?([0-9,]+)"?',
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_storm(html: str) -> int | None:
    """STORM (stormst.com) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
        r'id="price"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


def extract_price_seven(html: str) -> int | None:
    """SEVEN (pc-seven.co.jp) 価格抽出"""
    for pat in [
        r'class="[^"]*price[^"]*"[^>]*>\s*[¥￥]?\s*([0-9,]+)',
        r"販売価格[^0-9]*([0-9,]+)\s*円",
        r"税込[^0-9]*([0-9,]+)\s*円",
        r"通常価格[^0-9]*([0-9,]+)\s*円",
    ]:
        m = re.search(pat, html)
        if m:
            price = _normalize_price(m.group(1))
            if price:
                return price
    return _extract_generic_price(html)


# ─────────────────────────────────────────────────────────────────────────────
# メーカー判定 → 抽出関数マッピング
# ─────────────────────────────────────────────────────────────────────────────

def get_price_extractor(url: str):
    """
    URLドメインからメーカーを判定し、対応する価格抽出関数を返す。
    スキップ対象の場合は None を返す。

    Returns:
        (extractor_func, maker_label) or (None, "skip")
    """
    url_lower = url.lower()

    # スキップ判定
    for domain in SKIP_DOMAINS:
        if domain in url_lower:
            return None, "skip_dospara"

    # メーカー判定
    if "pc-koubou.jp" in url_lower:
        return extract_price_pc_koubou, "パソコン工房"
    elif "sycom.co.jp" in url_lower:
        return extract_price_sycom, "サイコム"
    elif "tsukumo.co.jp" in url_lower:
        return extract_price_tsukumo, "ツクモ"
    elif "mouse-jp.co.jp" in url_lower:
        return extract_price_mouse, "マウスコンピューター"
    elif "frontier-direct.jp" in url_lower:
        return extract_price_frontier, "FRONTIER"
    elif "jp.ext.hp.com" in url_lower or "hp.com/jp" in url_lower:
        return extract_price_hp, "HP"
    elif "lenovo.com/jp" in url_lower:
        return extract_price_lenovo, "Lenovo"
    elif "stormst.com" in url_lower:
        return extract_price_storm, "STORM"
    elif "pc-seven.co.jp" in url_lower:
        return extract_price_seven, "SEVEN"
    else:
        # 不明なメーカー → 汎用抽出を試みる
        return _extract_generic_price, "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 在庫切れ判定
# ─────────────────────────────────────────────────────────────────────────────

def check_out_of_stock(html: str) -> bool:
    """HTML内に在庫切れキーワードが含まれるか判定する。"""
    html_lower = html.lower()
    for keyword in OUT_OF_STOCK_KEYWORDS:
        if keyword.lower() in html_lower:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# JSONL 読み書き
# ─────────────────────────────────────────────────────────────────────────────

def load_products(path: str) -> list[dict]:
    """products.jsonl を読み込む。"""
    products = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def save_products(path: str, products: list[dict]) -> None:
    """products.jsonl を上書き保存する。"""
    with open(path, "w", encoding="utf-8") as f:
        for rec in products:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Git commit & push
# ─────────────────────────────────────────────────────────────────────────────

def git_commit_and_push():
    """変更を git commit して push する。"""
    print("\n=== git commit & push ===")

    def run(cmd):
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result.returncode

    # ステージング
    run(["git", "add", DATA_PATH])

    # 変更があるか確認
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_ROOT,
    )
    if result.returncode == 0:
        print("変更なし。コミットをスキップします。")
        return

    commit_msg = f"auto: BTO price update {TODAY}"
    rc = run(["git", "commit", "-m", commit_msg])
    if rc != 0:
        print("[WARN] git commit 失敗")
        return

    rc = run(["git", "push", "origin", "main"])
    if rc != 0:
        print("[WARN] git push 失敗")
    else:
        print("push 完了")


# ─────────────────────────────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────────────────────────────

def update_prices(dry_run: bool = False) -> dict:
    """
    全BTO商品の価格を更新する。

    Returns:
        集計結果 dict: {updated, unchanged, out_of_stock, skipped, error}
    """
    stats = {
        "updated": 0,
        "unchanged": 0,
        "out_of_stock": 0,
        "skipped": 0,
        "error": 0,
    }

    products = load_products(DATA_PATH)
    total = len(products)
    print(f"BTO商品数: {total}件")
    print(f"データファイル: {DATA_PATH}")
    print(f"日付: {TODAY}")
    print(f"Dry-run: {dry_run}")
    print("=" * 60)

    for i, product in enumerate(products, 1):
        pid = product.get("id", "?")
        maker = product.get("maker", "?")
        model = product.get("model", "?")
        url = product.get("url", "")
        old_price = product.get("price_jpy")
        tags = product.get("tags", [])

        label = f"[{i}/{total}] {maker} {model}"

        # URL判定
        if not url:
            print(f"{label} → SKIP: URLなし")
            stats["skipped"] += 1
            continue

        extractor, maker_label = get_price_extractor(url)
        if extractor is None:
            print(f"{label} → SKIP: {maker_label}")
            stats["skipped"] += 1
            continue

        # HTTP取得
        print(f"{label}")
        print(f"  URL: {url}")
        status_code, html = fetch_html(url)

        if status_code == 0:
            print(f"  ERROR: HTTP取得失敗")
            stats["error"] += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        if status_code == 404:
            print(f"  404 Not Found → out_of_stock")
            if "out_of_stock" not in tags:
                if not dry_run:
                    tags.append("out_of_stock")
                    product["tags"] = tags
                print(f"  [DRY-RUN] " if dry_run else "  ", end="")
                print(f"タグ追加: out_of_stock")
            stats["out_of_stock"] += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        if status_code >= 400:
            print(f"  HTTP {status_code} → ERROR")
            stats["error"] += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        # 在庫切れチェック
        if check_out_of_stock(html):
            print(f"  在庫切れキーワード検出 → out_of_stock")
            if "out_of_stock" not in tags:
                if not dry_run:
                    tags.append("out_of_stock")
                    product["tags"] = tags
                prefix = "  [DRY-RUN] " if dry_run else "  "
                print(f"{prefix}タグ追加: out_of_stock")
            stats["out_of_stock"] += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        # 価格抽出
        new_price = extractor(html)

        if new_price is None:
            print(f"  WARN: 価格抽出失敗 (HTML {len(html)} bytes)")
            stats["error"] += 1
            time.sleep(random.uniform(0.5, 1.0))
            continue

        # 価格比較
        if old_price == new_price:
            print(f"  価格変動なし: {new_price:,}円")
            stats["unchanged"] += 1
        else:
            diff = new_price - (old_price or 0)
            diff_str = f"+{diff:,}" if diff > 0 else f"{diff:,}"
            print(f"  価格変動: {old_price:,}円 → {new_price:,}円 ({diff_str}円)")
            if not dry_run:
                product["price_jpy"] = new_price
                product["price_updated_at"] = TODAY
            else:
                print(f"  [DRY-RUN] 書き込みスキップ")
            stats["updated"] += 1

        # レート制限: 0.5〜1.0秒のランダム遅延
        time.sleep(random.uniform(0.5, 1.0))

    # ファイル保存
    if not dry_run and (stats["updated"] > 0 or stats["out_of_stock"] > 0):
        save_products(DATA_PATH, products)
        print(f"\nproducts.jsonl 保存完了")
    elif dry_run:
        print(f"\n[DRY-RUN] products.jsonl への書き込みをスキップしました")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BTO商品 価格自動更新スクレイパー"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変更を実際には書き込まず、何が変わるかのみ表示する",
    )
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"BTO 価格自動更新 {TODAY}")
    print(f"{'=' * 60}")

    stats = update_prices(dry_run=args.dry_run)

    # サマリー出力
    print(f"\n{'=' * 60}")
    print(f"サマリー")
    print(f"{'=' * 60}")
    print(f"  更新:     {stats['updated']}件")
    print(f"  変動なし: {stats['unchanged']}件")
    print(f"  品切れ:   {stats['out_of_stock']}件")
    print(f"  スキップ: {stats['skipped']}件 (ドスパラ等)")
    print(f"  エラー:   {stats['error']}件")
    print(f"{'=' * 60}")

    # Git commit & push (dry-run でなく変更がある場合のみ)
    if not args.dry_run and (stats["updated"] > 0 or stats["out_of_stock"] > 0):
        git_commit_and_push()
    elif args.dry_run:
        print("\n[DRY-RUN] git commit & push をスキップしました")
    else:
        print("\n変更なし。git commit & push をスキップしました")

    print(f"\n=== 全処理完了 {TODAY} ===")


if __name__ == "__main__":
    main()
