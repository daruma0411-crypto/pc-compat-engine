#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIGABYTE マザーボード マニュアルPDF収集スクレイパー

フロー:
  1. workspace/data/gigabyte_mb/products.jsonl を読み込む
  2. source_url + /support#support-manual でサポートページURL生成
  3. Playwright でページ取得、PDFリンク抽出
  4. httpx で PDF ダウンロード
  5. PyMuPDF でテキスト抽出
  6. gigabyte_mb/manuals/{model}.txt に保存
  7. products.jsonl の manual_url / manual_path / manual_scraped_at を更新

使い方:
  python gigabyte_mb_manual.py             # 最初の5件（デフォルト）
  python gigabyte_mb_manual.py --limit 10 # 10件
  python gigabyte_mb_manual.py --all      # 全件
  python gigabyte_mb_manual.py --no-headless  # ブラウザ表示（デバッグ用）
"""

from __future__ import annotations

import argparse
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pathlib
_SCRIPT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR.parent))

from manual_scraper.base import ManualScraperBase, _UA

# ─── PDF リンク抽出 JS ────────────────────────────────────────────────────────

JS_PDF_LINKS = """
() => {
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        const text = a.textContent.trim().toLowerCase();
        if (href.toLowerCase().includes('.pdf') &&
            (href.toLowerCase().includes('manual') ||
             href.toLowerCase().includes('um_') ||
             text.includes('manual') ||
             text.includes('user guide') ||
             text.includes('ユーザーズ'))) {
            links.push(href);
        }
    });
    return [...new Set(links)];
}
"""

JS_ALL_PDF_LINKS = """
() => {
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (href.toLowerCase().includes('.pdf') &&
            href.includes('download.gigabyte.com')) {
            links.push(href);
        }
    });
    return [...new Set(links)];
}
"""


class GigabyteMbManualScraper(ManualScraperBase):
    maker = "gigabyte_mb"
    category = "motherboard"
    data_dir = "gigabyte_mb"

    def get_support_page_url(self, product: dict) -> str | None:
        source_url = product.get("source_url", "").rstrip("/")
        if not source_url:
            return None
        # https://www.gigabyte.com/Motherboard/Z890-AORUS-MASTER
        # → https://www.gigabyte.com/Motherboard/Z890-AORUS-MASTER/support#support-manual
        return f"{source_url}/support#support-manual"

    def parse_pdf_links(self, page, support_url: str) -> list[str]:
        try:
            page.goto(support_url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print(f"  [goto] {e}", file=sys.stderr)
        time.sleep(4)

        # "Manual" タブをクリック（タブ切り替え式の場合）
        try:
            for selector in [
                'a:has-text("Manual")',
                'li:has-text("Manual")',
                '[data-tab="manual"]',
                '#support-manual',
            ]:
                els = page.query_selector_all(selector)
                if els:
                    els[0].click()
                    time.sleep(2)
                    break
        except Exception:
            pass

        # マニュアルPDFリンク（優先）
        links = page.evaluate(JS_PDF_LINKS)
        if not links:
            # download.gigabyte.com の全PDFリンク（フォールバック）
            links = page.evaluate(JS_ALL_PDF_LINKS)

        # QIG（クイックインストールガイド）より User Manual を優先
        manual_links = [l for l in links if "manual" in l.lower() and "qig" not in l.lower()]
        qig_links    = [l for l in links if "qig" in l.lower()]
        other_links  = [l for l in links if l not in manual_links and l not in qig_links]

        return manual_links + qig_links + other_links


def main():
    parser = argparse.ArgumentParser(description="GIGABYTE MB マニュアルPDF収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    scraper = GigabyteMbManualScraper(limit=limit, headless=not args.no_headless)
    scraper.run()


if __name__ == "__main__":
    main()
