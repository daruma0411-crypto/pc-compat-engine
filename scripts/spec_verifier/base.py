#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec_verifier/base.py
公式サイトからスペック値を取得・検証・修正する共通フレームワーク
"""

from __future__ import annotations

import json
import re
import sys
import time
import pathlib
from typing import Optional

import httpx

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT = True
except ImportError:
    _PLAYWRIGHT = False

_ROOT = pathlib.Path(__file__).parent.parent.parent

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────────────────────────────────────
# ページ取得
# ─────────────────────────────────────────────────────────────────────────────

def fetch_page_httpx(url: str, timeout: int = 20) -> Optional[str]:
    """httpxで静的HTMLを取得する。失敗したらNone。"""
    try:
        headers = {
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "ja,en;q=0.9",
        }
        with httpx.Client(follow_redirects=True, timeout=timeout, verify=False) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
            print(f"  [httpx] status={resp.status_code} len={len(resp.text)}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  [httpx] 失敗: {e}", file=sys.stderr)
        return None


def fetch_page_playwright(url: str, headless: bool = True, wait_ms: int = 2000) -> Optional[str]:
    """Playwrightでページを取得する（JS描画対応）。"""
    if not _PLAYWRIGHT:
        print("  [playwright] インストールされていません", file=sys.stderr)
        return None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1280, "height": 900},
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = ctx.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(wait_ms)
            html = page.content()
            browser.close()
            if len(html) > 500:
                return html
            return None
    except Exception as e:
        print(f"  [playwright] 失敗: {e}", file=sys.stderr)
        return None


def fetch_page(url: str, headless: bool = True) -> Optional[str]:
    """httpx → Playwright の順で取得を試みる。"""
    html = fetch_page_httpx(url)
    if html:
        return html
    print(f"  [fetch] httpx失敗 → Playwright で再試行", file=sys.stderr)
    time.sleep(1)
    return fetch_page_playwright(url, headless=headless)


# ─────────────────────────────────────────────────────────────────────────────
# スペック値抽出
# ─────────────────────────────────────────────────────────────────────────────

def strip_html_tags(html: str) -> str:
    """HTMLタグを除去してテキストを返す。"""
    # scriptとstyleを先に除去
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # タグ除去
    text = re.sub(r'<[^>]+>', ' ', text)
    # 連続空白を正規化
    text = re.sub(r'\s+', ' ', text)
    return text


def extract_spec_value(html: str, patterns: list[str], value_range: tuple[int, int]) -> Optional[int]:
    """
    HTMLテキストからスペック値を正規表現で抽出する。
    複数パターンを試して最初にrange内に収まる整数値を返す。
    """
    text = strip_html_tags(html)
    lo, hi = value_range
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            try:
                val = int(m.group(1))
                if lo <= val <= hi:
                    return val
            except (ValueError, IndexError):
                continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# JSONL 操作
# ─────────────────────────────────────────────────────────────────────────────

def load_jsonl(data_dir: str) -> list[dict]:
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def save_jsonl(data_dir: str, records: list[dict]) -> None:
    path = _ROOT / "workspace" / "data" / data_dir / "products.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# diff 表示
# ─────────────────────────────────────────────────────────────────────────────

def print_diff(product_name: str, field: str, old_val, new_val) -> None:
    if old_val == new_val:
        print(f"  [OK]    {field}: {old_val} （変更なし）")
    else:
        print(f"  [DIFF]  {field}: {old_val}  →  {new_val}  ★要修正")


# ─────────────────────────────────────────────────────────────────────────────
# メイン検証ロジック
# ─────────────────────────────────────────────────────────────────────────────

def verify_product(
    product_id: str,
    cfg: dict,
    dry_run: bool = True,
    headless: bool = True,
) -> dict:
    """
    1製品分の公式スペックを取得・検証し、dry_run=Falseなら更新する。
    返却: {"status": "ok"|"diff"|"skip"|"error", "diffs": {field: (old, new)}}
    """
    data_dir = cfg["data_dir"]
    source_url = cfg["source_url"]
    spec_fields = cfg["spec_fields"]

    print(f"\n{'='*60}")
    print(f"[{product_id}]")
    print(f"  URL: {source_url}")

    # レコード取得
    records = load_jsonl(data_dir)
    target = next((r for r in records if r.get("id") == product_id), None)
    if not target:
        # idが完全一致しない場合、名前から推定
        name_lower = product_id.replace("_", " ").replace("-", " ").lower()
        target = next(
            (r for r in records if not r.get("source_url") and
             all(w in r.get("name", "").lower() for w in name_lower.split() if len(w) > 2)),
            None
        )
    if not target:
        print(f"  [SKIP] レコードが見つかりません")
        return {"status": "skip", "diffs": {}}

    print(f"  製品名: {target.get('name')}")

    # ページ取得
    html = fetch_page(source_url, headless=headless)
    if not html:
        print(f"  [ERROR] ページ取得失敗")
        return {"status": "error", "diffs": {}}

    print(f"  ページ取得: {len(html):,}文字")

    # スペック抽出・比較
    result_diffs = {}
    has_diff = False

    for field, field_cfg in spec_fields.items():
        patterns = field_cfg["patterns"]
        val_range = field_cfg["range"]
        new_val = extract_spec_value(html, patterns, val_range)
        old_val = target.get("specs", {}).get(field)

        if new_val is None:
            print(f"  [SKIP]  {field}: 抽出失敗（パターン不一致）")
            result_diffs[field] = (old_val, None)
            continue

        print_diff(target.get("name", product_id), field, old_val, new_val)

        if old_val != new_val:
            has_diff = True
            result_diffs[field] = (old_val, new_val)

    # source_url 更新（値変更に関わらず常に埋める）
    url_missing = not target.get("source_url")
    if url_missing:
        print(f"  [URL]   source_url を追加: {source_url}")

    # 更新処理
    if not dry_run and (has_diff or url_missing):
        for field, (old_val, new_val) in result_diffs.items():
            if new_val is not None:
                target.setdefault("specs", {})[field] = new_val
        target["source_url"] = source_url
        save_jsonl(data_dir, records)
        print(f"  → products.jsonl を更新しました")
    elif dry_run and (has_diff or url_missing):
        print(f"  → [dry-run] 実際には更新しません")

    status = "diff" if has_diff else "ok"
    return {"status": status, "diffs": result_diffs}
