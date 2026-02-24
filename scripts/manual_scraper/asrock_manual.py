#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASRock マザーボード マニュアルPDF収集スクレイパー

ASRock マザーボード製品のマニュアル PDF をダウンロードし、
テキスト抽出・スペック補完を行う。

フロー:
  1. workspace/data/asrock_mb/products.jsonl を読み込む
  2. product_url から #Download ページ URL を生成
  3. Playwright でページ取得、PDF リンクを検索
  4. httpx で PDF をダウンロード
  5. fitz (PyMuPDF) でテキスト抽出
  6. manuals/{model}.txt に保存
  7. products.jsonl のスペック補完・上書き

使い方:
  python asrock_manual.py             # 最初の5件（デフォルト）
  python asrock_manual.py --limit 3  # 3件
  python asrock_manual.py --all      # 全件
  python asrock_manual.py --no-headless  # ブラウザ表示（デバッグ用）
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

from manual_scraper.base import extract_text_from_pdf, extract_manual_specs, _UA, _ROOT

try:
    import httpx
except ImportError:
    print("pip install httpx", file=sys.stderr)
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

# ─── 定数 ────────────────────────────────────────────────────────────────────

_JSONL_PATH = _ROOT / "workspace" / "data" / "asrock_mb" / "products.jsonl"
_MANUAL_DIR = _ROOT / "workspace" / "data" / "asrock_mb" / "manuals"
_MANUAL_DIR.mkdir(parents=True, exist_ok=True)

# ─── ヘルパー ─────────────────────────────────────────────────────────────────

def _download_url(product_url: str) -> str:
    """product_url からダウンロードページ URL を返す（index.asp → index.asp#Download）"""
    base = product_url.rstrip("/")
    if "#" in base:
        base = base.split("#")[0]
    return base + "#Download"


def _spec_url(product_url: str) -> str:
    """product_url からスペックページ URL を返す（Specification.asp）"""
    base = product_url.rstrip("/")
    return base.replace("index.asp", "Specification.asp")


def _model_key(product: dict) -> str:
    """製品の識別キーを返す（specs.model > name の優先順）"""
    # specs 内の model を優先
    specs = product.get("specs", {})
    if isinstance(specs, dict):
        model = specs.get("model", "")
        if model:
            return re.sub(r"[<>/\\|?*\":]", "_", str(model))[:80]
    for key in ("model", "name"):
        val = product.get(key, "")
        if val:
            return re.sub(r"[<>/\\|?*\":]", "_", str(val))[:80]
    return "unknown"


def _get_product_url(product: dict) -> str:
    """製品レコードから URL を返す（source_url > product_url の優先順）"""
    return product.get("source_url", "") or product.get("product_url", "")


def _safe_filename(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", s)


# ─── PDF リンク検索 JS ───────────────────────────────────────────────────────

JS_PDF_LINKS = """
() => {
    return [...document.querySelectorAll('a[href]')]
        .map(a => ({href: a.href, text: a.textContent.trim()}))
        .filter(l => l.href.toLowerCase().includes('.pdf') ||
                     l.href.toLowerCase().includes('manual') ||
                     l.text.toLowerCase().includes('manual'));
}
"""

# ASRock スペックページ用 JS テキスト抽出
JS_SPEC_TEXT = """
() => {
    const lines = [];
    document.querySelectorAll('.spec-item, .spec-content, tr, .row').forEach(el => {
        const text = el.textContent.replace(/\\s+/g, ' ').trim();
        if (text && text.length > 3) lines.push(text);
    });
    if (lines.length === 0) return document.body.innerText;
    return lines.join('\\n');
}
"""

# ─── ASRock MB スペック補完パターン ────────────────────────────────────────────

_MB_SPEC_PATTERNS = {
    "pcie_x16_slots": [
        r"(\d+)\s*x\s*PCI(?:e|E|[-\s]Express)\s*x16",
        r"PCI(?:e|E|[-\s]Express)\s*x16\s*(?:slot|スロット)[^\d]*(\d+)",
        r"Expansion\s*Slot.*?(\d+)\s*x\s*PCI.*?x16",
    ],
    "sata_ports": [
        r"(\d+)\s*x\s*SATA",
        r"SATA\s*(?:III|3|6\.?0).*?(\d+)\s*(?:port|connector|ポート|個)",
        r"SATA.*?x\s*(\d+)",
    ],
    "max_memory_gb": [
        r"(?:Max|Maximum|最大)\s*(?:capacity|Capacity|容量)[:\s]*(\d+)\s*GB",
        r"(?:up\s*to|最大)\s*(\d+)\s*GB",
        r"DDR\d[^\n]*?(?:Max|最大)[:\s]*(\d+)\s*GB",
    ],
    "memory_slots": [
        r"(\d+)\s*x\s*DDR\d\s*DIMM",
        r"DDR\d\s*DIMM\s*(?:slot|スロット)[^\d]*(\d+)",
    ],
    "m2_slots": [
        r"(\d+)\s*x\s*M\.?2",
        r"M\.?2\s*(?:slot|スロット|Socket|Connector)[^\d]*(\d+)",
    ],
}


def _extract_mb_specs_from_text(text: str) -> dict:
    """マザーボード用: マニュアル/スペックテキストからスペック値を抽出する"""
    specs = {}
    for field, patterns in _MB_SPEC_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if field == "pcie_x16_slots" and 1 <= val <= 8:
                        specs[field] = val
                    elif field == "sata_ports" and 1 <= val <= 16:
                        specs[field] = val
                    elif field == "max_memory_gb" and 16 <= val <= 1024:
                        specs[field] = val
                    elif field == "memory_slots" and 1 <= val <= 8:
                        specs[field] = val
                    elif field == "m2_slots" and 1 <= val <= 10:
                        specs[field] = val
                except ValueError:
                    pass
                break
    return specs


# ─── PDF ダウンロード ────────────────────────────────────────────────────────

def download_pdf(url: str, timeout: int = 60) -> bytes | None:
    """httpx で PDF をダウンロードする（SSL検証無効化: ASRock の証明書問題対応）"""
    try:
        headers = {
            "User-Agent": _UA,
            "Accept": "application/pdf,*/*",
            "Referer": "https://www.asrock.com/",
        }
        with httpx.Client(follow_redirects=True, timeout=timeout, verify=False) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
            print(f"  [DL] 小さすぎるレスポンス: {len(resp.content)} bytes, ct={ct}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  [DL] ダウンロード失敗 {url}: {e}", file=sys.stderr)
        return None


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


def find_pdf_links(page, product_url: str) -> list[str]:
    """ダウンロードページにアクセスして PDF リンクを収集する"""
    dl_url = _download_url(product_url)
    print(f"  download_url: {dl_url}", file=sys.stderr)

    try:
        page.goto(dl_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [goto error] {e}", file=sys.stderr)
    time.sleep(3)

    # ASRock のダウンロードページはタブ切り替え式のことがある
    # "Manual" タブや "Download" セクションをクリックしてみる
    try:
        # Manual カテゴリを展開するボタンがあればクリック
        manual_btns = page.query_selector_all('a:has-text("Manual"), button:has-text("Manual")')
        for btn in manual_btns[:2]:
            try:
                btn.click()
                time.sleep(1)
            except Exception:
                pass
    except Exception:
        pass

    # ダウンロードページ内のPDFリンクを探す
    links = page.evaluate(JS_PDF_LINKS)

    # 全リンクを収集: ftp:// → https://download.asrock.com に変換
    manual_pdfs = []  # User Manual PDF（最優先）
    other_pdfs = []   # その他の PDF

    if links:
        for link in links:
            href = link.get("href", "")
            text = link.get("text", "")
            if not href:
                continue

            # ftp://asrockchina.com.cn/... → https://download.asrock.com/... に変換
            if href.lower().startswith("ftp://asrockchina.com.cn/"):
                href = "https://download.asrock.com/" + href[len("ftp://asrockchina.com.cn/"):]

            # ftp:// のままなら除外
            if href.lower().startswith("ftp://"):
                continue
            if ".pdf" not in href.lower():
                continue

            href_lower = href.lower()
            text_lower = text.lower()

            # Declaration/RoHS/FCC は除外（認証書類で不要）
            if "/declaration/" in href_lower:
                continue

            # User Manual を最優先（RAID, QIG は除外）
            is_user_manual = (
                ("manual" in href_lower
                 and "raid" not in href_lower
                 and "qig" not in href_lower
                 and "declaration" not in href_lower)
                or "user guide" in text_lower
                or "user manual" in text_lower
            )
            if is_user_manual:
                manual_pdfs.append(href)
            else:
                other_pdfs.append(href)

    pdf_urls = manual_pdfs + other_pdfs

    # 重複排除
    seen = set()
    unique = []
    for u in pdf_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique


def scrape_spec_text(page, product_url: str) -> str:
    """スペックページにアクセスしてテキストを取得する（PDFフォールバック用）"""
    spec_url = _spec_url(product_url)
    print(f"  spec_url (fallback): {spec_url}", file=sys.stderr)

    try:
        page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [goto error] {e}", file=sys.stderr)
    time.sleep(2)

    text = page.evaluate(JS_SPEC_TEXT)

    # フォールバック: JS で取れなければ body テキスト全体
    if not text or len(text) < 100:
        text = page.evaluate("() => document.body.innerText")

    return text or ""


def run(limit: int = 5, headless: bool = True) -> None:
    from datetime import datetime, timezone

    products = load_products()
    targets = products[:limit]
    print(f"\n[ASRock MB] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

    updated = 0
    failed = 0

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

        for i, prod in enumerate(targets, 1):
            model = _model_key(prod)
            name = prod.get("name", "")[:60]
            print(f"[{i}/{len(targets)}] {name}", file=sys.stderr)

            purl = _get_product_url(prod)
            if not purl:
                print("  SKIP: product_url なし", file=sys.stderr)
                failed += 1
                continue

            try:
                # Step 1: ダウンロードページから PDF リンクを探す
                pdf_links = find_pdf_links(page, purl)
                print(f"  PDF リンク: {len(pdf_links)} 件", file=sys.stderr)

                text = ""
                pdf_url = None

                if pdf_links:
                    # Step 2: PDF をダウンロード・テキスト抽出
                    for link in pdf_links[:3]:  # 最大3リンクまで試行
                        print(f"  ダウンロード中: {link[:100]}", file=sys.stderr)
                        pdf_bytes = download_pdf(link)
                        if pdf_bytes:
                            try:
                                text = extract_text_from_pdf(pdf_bytes)
                                if text and len(text) > 100:
                                    pdf_url = link
                                    print(f"  PDF テキスト抽出成功: {len(text)} 文字", file=sys.stderr)
                                    break
                                else:
                                    print(f"  PDF テキストが少なすぎ: {len(text)} 文字", file=sys.stderr)
                            except Exception as e:
                                print(f"  [PDF解析失敗] {e}", file=sys.stderr)

                # Step 3: PDF が取れなかった場合、スペックページのテキストでフォールバック
                if not text or len(text) < 100:
                    print("  PDF 取得不可 → スペックページテキストでフォールバック", file=sys.stderr)
                    text = scrape_spec_text(page, purl)

                if not text or len(text) < 50:
                    print("  WARN: テキスト取得なし", file=sys.stderr)
                    failed += 1
                    continue

                # テキスト保存
                safe = _safe_filename(model)
                out_path = _MANUAL_DIR / f"{safe}.txt"
                out_path.write_text(text, encoding="utf-8")

                # スペック抽出（MB固有パターン + base共通の両方）
                specs_mb = _extract_mb_specs_from_text(text)
                specs_base = extract_manual_specs(text)
                specs = {**specs_base, **specs_mb}

                # products.jsonl 更新
                if pdf_url:
                    prod["manual_url"] = pdf_url
                prod["manual_path"] = str(out_path.relative_to(_ROOT))
                prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
                prod["manual_specs"] = specs

                # null フィールドを specs 内で補完
                null_filled = []
                prod_specs = prod.get("specs", {})
                if isinstance(prod_specs, dict):
                    for field, val in specs.items():
                        if prod_specs.get(field) is None and val is not None:
                            prod_specs[field] = val
                            null_filled.append(f"{field}={val}")
                    prod["specs"] = prod_specs

                updated += 1
                src = "PDF" if pdf_url else "spec_page"
                print(
                    f"  OK ({src}): {len(text)} 文字 | specs={specs}"
                    + (f" | 補完={null_filled}" if null_filled else ""),
                    file=sys.stderr,
                )

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                failed += 1

            time.sleep(2)

        browser.close()

    save_products(products)
    print(
        f"\n[ASRock MB] 完了: 成功={updated} 失敗={failed} | products.jsonl 更新済み",
        file=sys.stderr,
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ASRock MB マニュアルPDF収集スクレイパー")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    limit = 999999 if args.all else args.limit
    run(limit=limit, headless=not args.no_headless)


if __name__ == "__main__":
    main()
