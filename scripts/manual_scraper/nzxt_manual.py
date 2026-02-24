#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NZXT ケース スペックテキスト収集スクレイパー

NZXTのケース製品には product_url が products.jsonl に含まれていないため、
モデル名から公式ページ URL を構築してスペックテキストを取得する。
取得失敗時は既存の specs フィールドを manual_specs として格納する fallback を実装。

フロー:
  1. workspace/data/cases/products.jsonl から maker="nzxt" のレコードを読み込む
  2. モデル名から NZXT 公式製品ページ URL を構築
  3. httpx でページ取得・テキスト抽出（Cloudflare 対策として fallback あり）
  4. manuals/{model}.txt に保存
  5. products.jsonl の manual_path, manual_scraped_at, manual_specs を追加して上書き保存

使い方:
  python nzxt_manual.py             # 最初の5件（デフォルト）
  python nzxt_manual.py --limit 3  # 3件
  python nzxt_manual.py --all      # 全件
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR.parent))

from manual_scraper.base import extract_manual_specs, _UA, _ROOT

import httpx

# ─── 定数 ────────────────────────────────────────────────────────────────────

_JSONL_PATH = _ROOT / "workspace" / "data" / "cases" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "cases" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# ─── ケース用スペックパターン ─────────────────────────────────────────────────

_CASE_SPEC_PATTERNS = {
    "max_gpu_length_mm": [
        r"(?:Maximum\s+)?GPU\s+(?:Clearance|Length)[:\s]+(\d+)\s*mm",
        r"VGA\s+(?:Clearance|Length)[:\s]+(\d+)\s*mm",
        r"Graphics\s+Card\s+Length[:\s]+(?:Up\s+to\s+)?(\d+)\s*mm",
        r"Max\s+GPU\s+Length[:\s]+(\d+)\s*mm",
    ],
    "max_cpu_cooler_height_mm": [
        r"(?:Maximum\s+)?CPU\s+Cooler\s+(?:Clearance|Height)[:\s]+(\d+)\s*mm",
        r"CPU\s+Cooler\s+Height[:\s]+(?:Up\s+to\s+)?(\d+)\s*mm",
        r"Max\s+CPU\s+Cooler[:\s]+(\d+)\s*mm",
    ],
    "max_psu_length_mm": [
        r"(?:Maximum\s+)?PSU\s+(?:Clearance|Length)[:\s]+(\d+)\s*mm",
        r"Power\s+Supply\s+(?:Clearance|Length)[:\s]+(?:Up\s+to\s+)?(\d+)\s*mm",
        r"Max\s+PSU[:\s]+(\d+)\s*mm",
    ],
    "form_factor": [
        r"Motherboard\s+Support[:\s]+([^\n]+)",
        r"Form\s+Factor[:\s]+([^\n]+)",
        r"Supported\s+Motherboard[:\s]+([^\n]+)",
    ],
}


def _extract_case_specs_from_text(text: str) -> dict:
    """ケーススペックテキストから値を抽出する"""
    specs = {}
    for field, patterns in _CASE_SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                if field in ("max_gpu_length_mm", "max_cpu_cooler_height_mm", "max_psu_length_mm"):
                    try:
                        val = int(float(raw))
                        if 50 <= val <= 600:
                            specs[field] = str(val)
                    except ValueError:
                        pass
                elif field == "form_factor":
                    if len(raw) < 80:
                        specs[field] = raw
                break
    return specs


# ─── URL 構築ヘルパー ─────────────────────────────────────────────────────────

def _model_to_slug(model: str) -> str:
    """
    モデル名をURLスラグに変換する。
    例: "NZXT H510" -> "h510"
         "NZXT H9 Flow" -> "h9-flow"
         "NZXT H200i" -> "h200i"
    """
    # "NZXT " プレフィックスを除去
    name = re.sub(r"^NZXT\s+", "", model, flags=re.IGNORECASE).strip()
    # 小文字にしてスペースをハイフンに
    slug = name.lower().replace(" ", "-")
    # 英数字とハイフン以外を除去
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # 連続ハイフンを1つに
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _build_product_urls(model: str) -> list[str]:
    """
    モデル名から NZXT 公式ページの候補 URL リストを構築する。
    """
    slug = _model_to_slug(model)
    return [
        f"https://nzxt.com/product/{slug}",
        f"https://nzxt.com/en-JP/product/{slug}",
    ]


def _model_key(product: dict) -> str:
    """製品の識別キーを返す"""
    model = product.get("model", "")
    if model:
        return re.sub(r"[<>/\\|?*\":]", "_", str(model))[:80]
    return "unknown"


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


# ─── スクレイピング ──────────────────────────────────────────────────────────

def _fetch_page_text(url: str) -> str | None:
    """httpx で URL からページテキストを取得する"""
    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=20, headers=headers, verify=False) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
            print(f"    HTTP {resp.status_code}: {url}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"    接続エラー: {e}", file=sys.stderr)
        return None


def _extract_text_from_html(html: str) -> str:
    """HTML からテキストを抽出する（簡易パーサー）"""
    # scriptタグ・styleタグを除去
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # HTMLタグを除去
    text = re.sub(r"<[^>]+>", "\n", text)
    # HTMLエンティティをデコード
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # 空行を整理
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def _extract_specs_from_json_ld(html: str) -> dict:
    """
    HTML内の JSON-LD (application/ld+json) からスペック情報を抽出する。
    NZXTは Next.js ベースなので __NEXT_DATA__ も試す。
    """
    specs = {}

    # __NEXT_DATA__ から取得を試みる
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            # pageProps.product.specs などを探索
            props = data.get("props", {}).get("pageProps", {})
            product = props.get("product", {})
            if product:
                # スペック情報があれば取得
                spec_list = product.get("specs", [])
                if isinstance(spec_list, list):
                    for spec in spec_list:
                        if isinstance(spec, dict):
                            name = spec.get("name", "")
                            value = spec.get("value", "")
                            if name and value:
                                specs[name] = value
                # description も取得
                desc = product.get("description", "")
                if desc:
                    specs["_description"] = desc
        except (json.JSONDecodeError, KeyError):
            pass

    return specs


def _build_specs_text(product: dict, page_text: str | None, json_specs: dict) -> str:
    """製品情報とスクレイプ結果からスペックテキストを構築する"""
    lines = []
    model = product.get("model", "unknown")
    lines.append(f"=== {model} ===")
    lines.append(f"Maker: NZXT")
    lines.append(f"Category: Case")
    lines.append("")

    # 既存 specs を出力
    existing_specs = product.get("specs", {})
    if existing_specs:
        lines.append("--- Existing Specs ---")
        for k, v in existing_specs.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    # JSON-LD から取得した追加スペック
    if json_specs:
        lines.append("--- Web Specs (JSON-LD / NEXT_DATA) ---")
        for k, v in json_specs.items():
            if not k.startswith("_"):
                lines.append(f"  {k}: {v}")
        desc = json_specs.get("_description", "")
        if desc:
            lines.append(f"\n  Description: {desc}")
        lines.append("")

    # ページテキスト（取得できた場合）
    if page_text and len(page_text) > 100:
        lines.append("--- Page Text ---")
        # テキストを適度な長さに制限
        truncated = page_text[:5000]
        lines.append(truncated)

    return "\n".join(lines)


# ─── メイン処理 ───────────────────────────────────────────────────────────────

def load_products() -> list[dict]:
    products = []
    with open(_JSONL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def save_products(products: list[dict]) -> None:
    with open(_JSONL_PATH, "w", encoding="utf-8") as f:
        for rec in products:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run(limit: int = 5) -> dict:
    """メイン実行。結果サマリーを返す。"""
    from datetime import datetime, timezone

    products = load_products()

    # maker="nzxt" のレコードのみ対象
    nzxt_products = [p for p in products if p.get("maker", "").lower() == "nzxt"]
    targets = nzxt_products[:limit]
    print(f"\n[NZXT] 対象: {len(targets)} / {len(nzxt_products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0
    results = []

    for i, prod in enumerate(targets, 1):
        model = prod.get("model", "unknown")
        model_key = _model_key(prod)
        print(f"[{i}/{len(targets)}] {model}", file=sys.stderr)

        # URL 構築と取得
        urls = _build_product_urls(model)
        page_html = None
        fetched_url = None

        for url in urls:
            print(f"  試行: {url}", file=sys.stderr)
            page_html = _fetch_page_text(url)
            if page_html and len(page_html) > 500:
                fetched_url = url
                print(f"  取得成功: {len(page_html)} bytes", file=sys.stderr)
                break
            time.sleep(0.5)

        # テキスト抽出
        page_text = None
        json_specs = {}

        if page_html:
            page_text = _extract_text_from_html(page_html)
            json_specs = _extract_specs_from_json_ld(page_html)

        # 既存 specs を manual_specs のベースとして利用
        existing_specs = prod.get("specs", {})
        manual_specs = dict(existing_specs)  # 既存スペックをコピー

        # ページテキストから追加スペック抽出（既存値は上書きしない）
        if page_text:
            web_specs = _extract_case_specs_from_text(page_text)
            for k, v in web_specs.items():
                if v and k not in manual_specs:
                    manual_specs[k] = v

        # JSON-LD スペックも統合
        for k, v in json_specs.items():
            if not k.startswith("_") and v:
                manual_specs[f"web_{k}"] = str(v)

        # テキストファイル生成・保存
        spec_text = _build_specs_text(prod, page_text, json_specs)
        safe = _safe_filename(model_key)
        out_path = _MANUAL_DIR / f"{safe}.txt"
        out_path.write_text(spec_text, encoding="utf-8")

        # products.jsonl レコード更新
        prod["manual_path"] = str(out_path.relative_to(_ROOT))
        prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
        prod["manual_specs"] = manual_specs

        if fetched_url:
            prod["product_url"] = fetched_url

        updated += 1
        src = "web+specs" if page_text else "specs_only"
        print(
            f"  OK ({src}): {len(spec_text)} 文字 | manual_specs={manual_specs}",
            file=sys.stderr,
        )
        results.append({
            "model": model,
            "source": src,
            "manual_specs": manual_specs,
        })

        time.sleep(1)

    save_products(products)
    summary = {
        "total": len(targets),
        "updated": updated,
        "failed": failed,
        "results": results,
    }
    print(
        f"\n[NZXT] 完了: 成功={updated} 失敗={failed} | products.jsonl 更新済み",
        file=sys.stderr,
    )
    return summary


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NZXT ケース スペックテキスト収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit)


if __name__ == "__main__":
    main()
