#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSI マザーボード マニュアルPDF収集スクレイパー

MSI はAkamai CDNによるbot検知が厳しいため、以下の対策を実施:
  - まずトップページにアクセスして Cookie を取得
  - headless=False（デフォルト）で実ブラウザ挙動を模倣
  - 製品ページから /support#manual タブへアクセス

フロー:
  1. workspace/data/msi_mb/products.jsonl を読み込む
  2. source_url + /support#manual でサポートページURL生成
  3. Playwright（Cookie取得済み）でページ取得、PDFリンク抽出
  4. httpx で PDF ダウンロード
  5. PyMuPDF でテキスト抽出
  6. msi_mb/manuals/{model}.txt に保存
  7. products.jsonl の manual_url / manual_path / manual_scraped_at を更新

使い方:
  python msi_mb_manual.py             # 最初の5件（デフォルト）
  python msi_mb_manual.py --limit 22 # 全22件
  python msi_mb_manual.py --all      # 全件
  python msi_mb_manual.py --headless # ヘッドレスモード（bot検知リスクあり）
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

from manual_scraper.base import ManualScraperBase, _UA, extract_text_from_pdf, extract_manual_specs, _ROOT
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone

# ─── PDF リンク抽出 JS ────────────────────────────────────────────────────────

JS_PDF_LINKS = """
() => {
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        const text = a.textContent.trim().toLowerCase();
        const hrefL = href.toLowerCase();
        if (hrefL.includes('.pdf') && (
            hrefL.includes('download.msi.com') ||
            hrefL.includes('msi.com') ||
            text.includes('manual') ||
            text.includes('user guide')
        )) {
            links.push(href);
        }
    });
    return [...new Set(links)];
}
"""

JS_FALLBACK_PDF = """
() => {
    const links = [];
    document.querySelectorAll('a[href*=".pdf"]').forEach(a => {
        if (a.href) links.push(a.href);
    });
    return [...new Set(links)];
}
"""


class MsiMbManualScraper(ManualScraperBase):
    maker = "msi_mb"
    category = "motherboard"
    data_dir = "msi_mb"

    def get_support_page_url(self, product: dict) -> str | None:
        source_url = product.get("source_url", "").rstrip("/")
        if not source_url:
            return None
        # https://www.msi.com/Motherboard/MAG-Z890-TOMAHAWK-WIFI
        # → https://www.msi.com/Motherboard/MAG-Z890-TOMAHAWK-WIFI/support#manual
        return f"{source_url}/support#manual"

    def parse_pdf_links(self, page, support_url: str) -> list[str]:
        try:
            page.goto(support_url, wait_until="domcontentloaded", timeout=40000)
        except Exception as e:
            print(f"  [goto] {e}", file=sys.stderr)
        time.sleep(5)

        # Manual タブをクリック
        try:
            for selector in [
                'a:has-text("MANUAL")',
                'a:has-text("Manual")',
                'li:has-text("MANUAL")',
                '[data-tab="manual"]',
                '#manual',
            ]:
                els = page.query_selector_all(selector)
                if els:
                    els[0].click()
                    time.sleep(3)
                    break
        except Exception:
            pass

        links = page.evaluate(JS_PDF_LINKS)
        if not links:
            links = page.evaluate(JS_FALLBACK_PDF)

        # E（英語）マニュアルを優先
        e_links    = [l for l in links if "_e." in l.lower() or "_e_" in l.lower() or "_en" in l.lower()]
        other      = [l for l in links if l not in e_links]
        return e_links + other

    def run(self) -> None:
        """MSI専用: トップページでCookieを取得してからスクレイプ"""
        import httpx

        products = self.load_products()
        targets = products[: self.limit]
        print(f"\n[MSI MB] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

        updated = 0
        failed = 0

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1280, "height": 900},
                locale="ja-JP",
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = ctx.new_page()

            # まずトップページにアクセスしてCookieを取得（Akamai対策）
            print("  [Akamai対策] トップページにアクセス中...", file=sys.stderr)
            try:
                page.goto("https://www.msi.com/", wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
            except Exception as e:
                print(f"  [Akamai対策] トップページアクセス失敗: {e}", file=sys.stderr)

            for i, prod in enumerate(targets, 1):
                name = prod.get("name", "")[:60]
                print(f"[{i}/{len(targets)}] {name}", file=sys.stderr)

                support_url = self.get_support_page_url(prod)
                if not support_url:
                    print("  SKIP: サポートURL取得不可", file=sys.stderr)
                    failed += 1
                    continue

                print(f"  support_url: {support_url}", file=sys.stderr)

                try:
                    pdf_links = self.parse_pdf_links(page, support_url)
                    print(f"  PDFリンク: {len(pdf_links)} 件", file=sys.stderr)

                    if not pdf_links:
                        print("  SKIP: PDFリンクなし", file=sys.stderr)
                        failed += 1
                        time.sleep(2)
                        continue

                    pdf_url = pdf_links[0]
                    print(f"  ダウンロード中: {pdf_url[:80]}", file=sys.stderr)

                    pdf_bytes = self.download_pdf(pdf_url)
                    if not pdf_bytes:
                        failed += 1
                        time.sleep(2)
                        continue

                    text = extract_text_from_pdf(pdf_bytes)
                    model_key = self._get_model_key(prod)
                    manual_path = self.save_manual_txt(model_key, text)
                    specs = extract_manual_specs(text)

                    prod["manual_url"] = pdf_url
                    prod["manual_path"] = str(manual_path.relative_to(_ROOT))
                    prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
                    prod["manual_specs"] = specs

                    updated += 1
                    print(f"  OK: {len(text)} 文字 | specs={specs}", file=sys.stderr)

                except Exception as e:
                    print(f"  ERROR: {e}", file=sys.stderr)
                    failed += 1

                time.sleep(3)  # MSIはインターバル長めに

            browser.close()

        self.save_products(products)
        print(
            f"\n[MSI MB] 完了: 成功={updated} 失敗={failed} (products.jsonl 保存済み)",
            file=sys.stderr,
        )


def main():
    parser = argparse.ArgumentParser(description="MSI MB マニュアルPDF収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--headless", action="store_true", help="ヘッドレスモード（bot検知リスクあり）")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    # MSIはデフォルトheadless=False（bot検知対策）
    scraper = MsiMbManualScraper(limit=limit, headless=args.headless)
    scraper.run()


if __name__ == "__main__":
    main()
