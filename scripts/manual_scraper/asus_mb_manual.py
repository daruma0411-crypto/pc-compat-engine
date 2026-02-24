#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASUS マザーボード マニュアルPDF収集スクレイパー

対象URL例:
  ROGライン:   https://rog.asus.com/motherboards/rog-strix/rog-strix-z790-f-gaming-wifi/
  → サポートURL: https://rog.asus.com/motherboards/rog-strix/rog-strix-z790-f-gaming-wifi/helpdesk_manual/
  PRIMEライン: https://www.asus.com/motherboards-components/motherboards/.../
  → サポートURL: {source_url}helpdesk_manual/

フロー:
  1. workspace/data/asus_mb/products.jsonl を読み込む
  2. source_url + helpdesk_manual/ でサポートページURL生成
  3. Playwright でページ取得、PDFリンク抽出
  4. httpx で PDF ダウンロード
  5. PyMuPDF でテキスト抽出
  6. asus_mb/manuals/{model}.txt に保存
  7. products.jsonl の manual_url / manual_path / manual_scraped_at を更新

使い方:
  python asus_mb_manual.py             # 最初の5件（デフォルト）
  python asus_mb_manual.py --limit 14 # 全14件
  python asus_mb_manual.py --all      # 全件
  python asus_mb_manual.py --no-headless  # ブラウザ表示（デバッグ用）
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
        const hrefL = href.toLowerCase();
        // ASUSマニュアルPDFはdlcdnets.asus.com / dlcdnet.asus.com にホスト
        if (hrefL.includes('.pdf') && (
            hrefL.includes('dlcdnets.asus.com') ||
            hrefL.includes('dlcdnet.asus.com') ||
            hrefL.includes('asus.com') ||
            text.includes('manual') ||
            text.includes('ユーザーズ') ||
            text.includes('user guide')
        )) {
            links.push(href);
        }
    });
    return [...new Set(links)];
}
"""

JS_FALLBACK_LINKS = """
() => {
    // フォールバック: ページ内の全PDFリンク
    const links = [];
    document.querySelectorAll('a[href*=".pdf"]').forEach(a => {
        if (a.href) links.push(a.href);
    });
    return [...new Set(links)];
}
"""


class AsusMbManualScraper(ManualScraperBase):
    maker = "asus_mb"
    category = "motherboard"
    data_dir = "asus_mb"

    def get_support_page_url(self, product: dict) -> str | None:
        source_url = product.get("source_url", "").rstrip("/")
        if not source_url:
            return None
        # https://rog.asus.com/motherboards/rog-strix/.../
        # → https://rog.asus.com/motherboards/rog-strix/.../helpdesk_manual/
        return f"{source_url}/helpdesk_manual/"

    def parse_pdf_links(self, page, support_url: str) -> list[str]:
        try:
            page.goto(support_url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print(f"  [goto] {e}", file=sys.stderr)
        time.sleep(4)

        # 言語選択ドロップダウンが出た場合はスキップ（Escapeで閉じる）
        try:
            page.keyboard.press("Escape")
            time.sleep(1)
        except Exception:
            pass

        # "User Manual" / "Manual" フィルタタブをクリックする試み
        try:
            for selector in [
                'a:has-text("User Manual")',
                'span:has-text("User Manual")',
                'a:has-text("マニュアル")',
                '[data-type="manual"]',
            ]:
                els = page.query_selector_all(selector)
                if els:
                    els[0].click()
                    time.sleep(2)
                    break
        except Exception:
            pass

        links = page.evaluate(JS_PDF_LINKS)
        if not links:
            links = page.evaluate(JS_FALLBACK_LINKS)

        # EM（英語マニュアル）を優先、次に日本語(JP)、その他
        em_links = [l for l in links if "_em_" in l.lower() or "_e_manual" in l.lower()]
        jp_links = [l for l in links if "_jp_" in l.lower() or "japanese" in l.lower()]
        other    = [l for l in links if l not in em_links and l not in jp_links]

        return em_links + jp_links + other


def main():
    parser = argparse.ArgumentParser(description="ASUS MB マニュアルPDF収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    scraper = AsusMbManualScraper(limit=limit, headless=not args.no_headless)
    scraper.run()


if __name__ == "__main__":
    main()
