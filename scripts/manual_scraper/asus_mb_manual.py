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
  3. Playwright でページ取得、GetPDManual APIレスポンスをキャプチャ
  4. APIレスポンスのJSONからPDFリンクを抽出
  5. httpx で PDF ダウンロード
  6. PyMuPDF でテキスト抽出
  7. asus_mb/manuals/{model}.txt に保存
  8. products.jsonl の manual_url / manual_path / manual_scraped_at を更新

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

# ASUSマニュアルPDFのベースURL
_ASUS_DL_BASE = "https://dlcdnets.asus.com"


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
        """
        ASUSの GetPDManual API レスポンスをネットワークキャプチャで取得してPDFリンクを返す。
        APIは helpdesk_manual/ ページロード時に自動的にコールされる。
        """
        api_data: dict = {}

        def _on_response(response):
            try:
                if "GetPDManual" in response.url:
                    api_data["json"] = response.json()
            except Exception:
                pass

        page.on("response", _on_response)

        try:
            page.goto(support_url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"  [goto] {e}", file=sys.stderr)

        time.sleep(5)

        page.remove_listener("response", _on_response)

        if not api_data.get("json"):
            print("  [WARN] GetPDManual APIレスポンスなし", file=sys.stderr)
            return []

        # APIレスポンスからPDFリンクを抽出
        links = []
        try:
            result = api_data["json"].get("Result", {})
            for group in result.get("Obj", []):
                for file_info in group.get("Files", []):
                    dl_path = (file_info.get("DownloadUrl") or {}).get("Global", "")
                    if dl_path:
                        full_url = _ASUS_DL_BASE + dl_path
                        links.append((file_info.get("Title", ""), full_url))
        except Exception as e:
            print(f"  [parse] {e}", file=sys.stderr)
            return []

        # User's Manual (English) を優先、次にその他英語、日本語
        em_links    = [url for t, url in links if "_EM_" in url or "_EM." in url]
        en_links    = [url for t, url in links if "_E_" in url and url not in em_links]
        jp_links    = [url for t, url in links if "_JP_" in url or "_J_" in url or "japanese" in url.lower()]
        other_links = [url for _, url in links if url not in em_links and url not in en_links and url not in jp_links]

        return em_links + en_links + jp_links + other_links


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
