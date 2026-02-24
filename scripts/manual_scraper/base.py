#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManualScraperBase - マニュアルPDF収集スクレイパー 共通基底クラス

各メーカーのサブクラスが get_support_page_url() を実装することで
PDF収集・テキスト抽出・products.jsonl補完を共通フローで処理する。
"""

from __future__ import annotations

import io
import json
import pathlib
import re
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

try:
    import fitz  # PyMuPDF
    _PYMUPDF = True
except ImportError:
    _PYMUPDF = False

try:
    import pdfplumber
    _PDFPLUMBER = True
except ImportError:
    _PDFPLUMBER = False

try:
    from playwright.sync_api import sync_playwright, Page
    _PLAYWRIGHT = True
except ImportError:
    _PLAYWRIGHT = False

# プロジェクトルート
_ROOT = pathlib.Path(__file__).parent.parent.parent

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────────────────────────────────────────
# テキスト抽出ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDFバイト列からテキストを抽出する（PyMuPDF → pdfplumber の優先順）"""
    if _PYMUPDF:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            texts = []
            for page in doc:
                texts.append(page.get_text())
            doc.close()
            return "\n".join(texts)
        except Exception as e:
            print(f"  [PyMuPDF] テキスト抽出失敗: {e}", file=sys.stderr)

    if _PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(texts)
        except Exception as e:
            print(f"  [pdfplumber] テキスト抽出失敗: {e}", file=sys.stderr)

    raise RuntimeError("PyMuPDF も pdfplumber も利用できません。pip install pymupdf pdfplumber")


# ─────────────────────────────────────────────────────────────────────────────
# スペック抽出ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def extract_manual_specs(text: str) -> dict:
    """
    マニュアルテキストからスペック値を正規表現で抽出する。
    返却値は products.jsonl の補完候補として使用する。
    """
    specs = {}

    # TDP / 消費電力
    for pat in [
        r"TDP[:\s]+(\d+)\s*W",
        r"(\d+)\s*W\s+TDP",
        r"Maximum\s+Power\s+Consumption[:\s]+(\d+)\s*W",
        r"Typical\s+Power\s+Consumption[:\s]+(\d+)\s*W",
        r"消費電力[:\s]+(\d+)\s*W",
        r"最大消費電力[:\s]+(\d+)\s*W",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 10 <= val <= 600:
                specs["tdp_w"] = val
                break

    # PCIe スロット幅
    for pat in [
        r"(\d+(?:\.\d+)?)\s*[Ss]lot",
        r"PCIe\s+Slot\s+Width[:\s]+(\d+(?:\.\d+)?)",
        r"Occupied\s+Slot[:\s]+(\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 1.0 <= val <= 5.0:
                specs["slot_width"] = val
                break

    # 電源コネクタ
    for pat in [
        r"((?:\d+\s*[xX×]\s*)?(?:6\+2|8|6|16)\s*[-\s]?[Pp]in(?:\s*[xX×]\s*\d+)?)",
        r"Power\s+Connector[:\s]+([^\n]+)",
        r"電源コネクタ[:\s]+([^\n]+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            if len(raw) < 60:
                specs["power_connector"] = raw
                break

    # カード長 (mm)
    for pat in [
        r"Card\s+Length[:\s]+(\d+)\s*mm",
        r"Length[:\s]+(\d+)\s*mm",
        r"(\d{2,3})\s*mm\s+[Cc]ard",
        r"カード長[:\s]+(\d+)\s*mm",
        r"長さ[:\s]+(\d+)\s*mm",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 100 <= val <= 500:
                specs["length_mm"] = val
                break

    # 推奨PSU
    for pat in [
        r"Recommended\s+(?:System\s+)?Power\s+Supply[:\s]+(\d+)\s*W",
        r"Minimum\s+(?:System\s+)?Power\s+Supply[:\s]+(\d+)\s*W",
        r"推奨電源容量[:\s]+(\d+)\s*W",
        r"(\d+)\s*W\s+(?:or\s+above|以上)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 100 <= val <= 2000:
                specs["recommended_psu_w"] = val
                break

    return specs


# ─────────────────────────────────────────────────────────────────────────────
# 基底クラス
# ─────────────────────────────────────────────────────────────────────────────

class ManualScraperBase(ABC):
    """
    各メーカーのマニュアルスクレイパー基底クラス。
    サブクラスは get_support_page_url() を実装すること。
    """

    maker: str = ""          # 例: "asus"
    category: str = ""       # 例: "gpu"
    data_dir: str = ""       # 例: "asus" (workspace/data/ 配下)

    def __init__(self, limit: int = 5, headless: bool = True):
        self.limit = limit
        self.headless = headless
        self.jsonl_path = _ROOT / "workspace" / "data" / self.data_dir / "products.jsonl"
        self.manual_dir = _ROOT / "workspace" / "data" / self.data_dir / "manuals"
        self.manual_dir.mkdir(parents=True, exist_ok=True)

    # ── サブクラスが実装 ──────────────────────────────────────────────────────

    @abstractmethod
    def get_support_page_url(self, product: dict) -> str | None:
        """製品レコードからサポートページURLを返す。取得不可なら None。"""
        ...

    @abstractmethod
    def parse_pdf_links(self, page: "Page", support_url: str) -> list[str]:
        """
        Playwright Page オブジェクトとサポートページURLを受け取り、
        マニュアル PDF の URL リストを返す。
        """
        ...

    # ── 共通ロジック ──────────────────────────────────────────────────────────

    def load_products(self) -> list[dict]:
        """products.jsonl を読み込んで list[dict] を返す"""
        products = []
        with open(self.jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    products.append(json.loads(line))
        return products

    def save_products(self, products: list[dict]) -> None:
        """products.jsonl を上書き保存する"""
        with open(self.jsonl_path, "w", encoding="utf-8") as f:
            for rec in products:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def download_pdf(self, url: str, timeout: int = 30) -> bytes | None:
        """httpx で PDF をダウンロードする"""
        try:
            headers = {"User-Agent": _UA, "Accept": "application/pdf,*/*"}
            with httpx.Client(follow_redirects=True, timeout=timeout, verify=False) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "")
                if "pdf" not in ct and not url.lower().endswith(".pdf"):
                    print(f"  [DL] PDF でない可能性: content-type={ct}", file=sys.stderr)
                return resp.content
        except Exception as e:
            print(f"  [DL] ダウンロード失敗 {url}: {e}", file=sys.stderr)
            return None

    def save_manual_txt(self, model: str, text: str) -> pathlib.Path:
        """テキストを manuals/{model}.txt に保存する"""
        safe_model = re.sub(r'[<>:"/\\|?*]', "_", model)
        out_path = self.manual_dir / f"{safe_model}.txt"
        out_path.write_text(text, encoding="utf-8")
        return out_path

    def _get_model_key(self, product: dict) -> str:
        """製品レコードから識別用モデルキーを返す"""
        for key in ("model", "part_no", "name"):
            val = product.get(key, "")
            if val:
                return str(val)[:80]
        return "unknown"

    def run(self) -> None:
        """メイン実行フロー"""
        if not _PLAYWRIGHT:
            raise RuntimeError("playwright がインストールされていません: pip install playwright && playwright install chromium")

        products = self.load_products()
        targets = products[: self.limit]
        print(f"\n[{self.maker}] 対象: {len(targets)} / {len(products)} 件\n", file=sys.stderr)

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
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = ctx.new_page()

            for i, prod in enumerate(targets, 1):
                model_key = self._get_model_key(prod)
                print(f"[{i}/{len(targets)}] {model_key[:60]}", file=sys.stderr)

                support_url = self.get_support_page_url(prod)
                if not support_url:
                    print("  SKIP: サポートURL取得不可", file=sys.stderr)
                    failed += 1
                    continue

                print(f"  support_url: {support_url}", file=sys.stderr)

                try:
                    pdf_links = self.parse_pdf_links(page, support_url)
                    print(f"  PDF リンク: {len(pdf_links)} 件", file=sys.stderr)

                    if not pdf_links:
                        print("  SKIP: PDFリンクなし", file=sys.stderr)
                        failed += 1
                        time.sleep(1)
                        continue

                    # 最初の1件をダウンロード（マニュアル想定）
                    pdf_url = pdf_links[0]
                    print(f"  ダウンロード中: {pdf_url[:80]}", file=sys.stderr)
                    pdf_bytes = self.download_pdf(pdf_url)

                    if not pdf_bytes:
                        failed += 1
                        time.sleep(1)
                        continue

                    text = extract_text_from_pdf(pdf_bytes)
                    manual_path = self.save_manual_txt(model_key, text)
                    specs = extract_manual_specs(text)

                    # products.jsonl レコードを更新
                    prod["manual_url"] = pdf_url
                    prod["manual_path"] = str(manual_path.relative_to(_ROOT))
                    prod["manual_scraped_at"] = datetime.now(timezone.utc).isoformat()
                    prod["manual_specs"] = specs

                    # null フィールドを manual_specs で補完
                    for field, val in specs.items():
                        if prod.get(field) is None and val is not None:
                            prod[field] = val
                            print(f"  補完: {field} = {val}", file=sys.stderr)

                    updated += 1
                    print(
                        f"  OK: テキスト {len(text)} 文字 | specs={specs}",
                        file=sys.stderr,
                    )

                except Exception as e:
                    print(f"  ERROR: {e}", file=sys.stderr)
                    failed += 1

                time.sleep(2)

            browser.close()

        # products.jsonl 上書き保存
        self.save_products(products)
        print(
            f"\n[{self.maker}] 完了: 成功={updated} 失敗={failed} "
            f"(products.jsonl 保存済み)",
            file=sys.stderr,
        )
