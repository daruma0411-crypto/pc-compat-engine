#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper_asus.py - ASUS GPU / マザーボード スクレイパー

ASUS 公式サイト（www.asus.com/jp / rog.asus.com）の製品一覧ページから
GPU・MB の製品 URL を収集し、各スペックページのテキストから specs を抽出して
products.jsonl に保存する。

使い方:
  python scripts/scraper_asus.py            # GPU + MB 両方（上限 30 件ずつ）
  python scripts/scraper_asus.py --gpu      # GPU のみ
  python scripts/scraper_asus.py --mb       # MB のみ
  python scripts/scraper_asus.py --limit 5  # 各カテゴリ上限 5 件（デバッグ用）
  python scripts/scraper_asus.py --all      # ページネーション全件
  python scripts/scraper_asus.py --no-headless  # ブラウザ表示（デバッグ用）
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, Page, Browser
except ImportError:
    print("pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

# ─── パス定数 ─────────────────────────────────────────────────────────────────

_ROOT = pathlib.Path(__file__).parent.parent
_GPU_JSONL = _ROOT / "workspace" / "data" / "asus" / "products.jsonl"
_MB_JSONL  = _ROOT / "workspace" / "data" / "asus_mb" / "products.jsonl"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

_TS = datetime.now(timezone.utc).isoformat()

# ─── ID スラグ生成 ─────────────────────────────────────────────────────────────

_HEX_HASH_RE = re.compile(r"^[0-9a-f]{12}$")


def _slugify(name: str) -> str:
    """製品名を SCHEMA.md 準拠のスラグに変換する"""
    s = name.lower()
    s = re.sub(r"[™®©]", "", s)
    s = re.sub(r"[ /\\]", "-", s)
    s = re.sub(r"[^a-z0-9\-_]", "", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def _make_id(name: str) -> str:
    return f"asus_{_slugify(name)}"


def _is_hex_id(id_str: str) -> bool:
    """旧フォーマットの hex hash ID かどうかを判定する"""
    return bool(_HEX_HASH_RE.match(str(id_str)))


# ─── GPU スペック抽出 ──────────────────────────────────────────────────────────

# GPU スペック抽出用パターン
_GPU_PATTERNS = {
    "gpu_chip": [
        r"GPU[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"Chip[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"((?:NVIDIA|AMD)\s+(?:GeForce|Radeon)\s+[^\n,]{4,40})",
    ],
    "vram": [
        r"(?:Video\s+Memory|VRAM|メモリ容量)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"(\d+\s*GB\s+(?:GDDR\d+X?|HBM\d*))",
    ],
    "bus_interface": [
        r"(?:Bus\s+(?:Interface|Standard)|インターフェース)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"(PCI\s*Express\s*[\d.]+\s*x\d*)",
    ],
    "boost_clock": [
        r"(?:Boost\s+Clock|ブーストクロック)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"OC\s+mode[:\s]+([^\n]+?)(?:\s*\n|$)",
    ],
    "display_output": [
        r"(?:Display\s+Output|Resolution\s+Support|映像出力)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"(?:HDMI|DisplayPort)[^\n]{5,60}",
    ],
    "size_raw": [
        r"(?:Card\s+Dimension[s]?|Product\s+Dimension[s]?|サイズ)[:\s]+([^\n]+?(?:\d+\s*[xX×]\s*\d+\s*[xX×]\s*\d+)[^\n]*)",
        r"(\d{2,3}\s*[xX×]\s*\d+\s*[xX×]\s*\d+\s*mm)",
    ],
    "psu_raw": [
        r"(?:Recommended\s+(?:System\s+)?PSU|推奨PSU|System\s+Power\s+Supply)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"(\d{3,4}\s*W(?:\+)?)\s*(?:or above|以上|Recommended)",
    ],
    "power_connector": [
        r"(?:Power\s+Connector[s]?|電源コネクタ)[:\s]+([^\n]+?)(?:\s*\n|$)",
        r"((?:\d+\s*[xX×]\s*)?(?:16|8|6)\s*-?\s*[Pp]in(?:\s*[xX×]\s*\d+)?)",
    ],
}

_GPU_NUM_PATTERNS = {
    "length_mm": [
        r"(\d{2,3})\s*[xX×]\s*\d+\s*[xX×]\s*\d+\s*mm",
        r"Card\s+Length[:\s]+(\d+)\s*mm",
        r"Length[:\s]+(\d+)\s*mm",
    ],
    "tdp_w": [
        r"(?:TDP|推奨PSU容量|Maximum\s+GPU\s+Power)[:\s]+(\d+)\s*W",
        r"(\d+)\s*W\s+TDP",
        r"Power\s+Consumption[:\s]+(\d+)\s*W",
    ],
    "slot_width": [
        r"([\d.]+)\s*[Ss]lot",
        r"Slot[s]?[:\s]+([\d.]+)",
        r"スロット[:\s]+([\d.]+)",
    ],
}


def _extract_gpu_specs(text: str) -> dict:
    """スペックテキストから GPU specs dict を生成する"""
    specs: dict = {}

    for field, patterns in _GPU_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                raw = (m.group(1) if m.lastindex else m.group(0)).strip()
                raw = re.sub(r"\s+", " ", raw)
                if raw and len(raw) < 120:
                    specs[field] = raw
                    break

    for field, patterns in _GPU_NUM_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if field == "length_mm" and 100 <= val <= 500:
                        specs[field] = int(val)
                        break
                    elif field == "tdp_w" and 50 <= val <= 800:
                        specs[field] = int(val)
                        break
                    elif field == "slot_width" and 1.0 <= val <= 5.0:
                        specs[field] = val
                        break
                except (ValueError, IndexError):
                    pass

    return specs


# ─── MB スペック抽出 ───────────────────────────────────────────────────────────

_MB_PATTERNS = {
    "socket": [
        r"(?:CPU\s+Socket|Socket\s+Type|ソケット)[:\s]+([^\n,]{2,20})",
        r"(LGA\d{4}|AM[45]|FM[12])",
    ],
    "chipset": [
        r"(?:Chipset|チップセット)[:\s]+([^\n,]{2,30})",
        r"((?:Z|B|H|X|A)\d{3,4}(?:E)?)\b",
    ],
    "form_factor": [
        r"(?:Form\s+Factor|フォームファクター)[:\s]+([^\n,]{2,20})",
        r"(ATX|EATX|Micro-?ATX|Mini-?ITX|E-?ATX)",
    ],
    "memory_type": [
        r"(?:Memory\s+Type|メモリ種別)[:\s]+([^\n,]{3,20})",
        r"(DDR[45](?:-\d+)?)",
    ],
    "power_connector": [
        r"(?:CPU\s+Power\s+Connector|電源コネクタ)[:\s]+([^\n]+?)(?:\n|$)",
        r"(\d+\s*[xX×]\s*\d+\s*[Pp]in)",
    ],
}

_MB_NUM_PATTERNS = {
    "m2_slots": [
        r"(?:M\.2\s+Slot[s]?)[:\s]+(\d+)",
        r"(\d+)\s*[xX×]\s*M\.2",
    ],
    "max_memory_gb": [
        r"(?:Max\.?\s+Memory|最大メモリ容量)[:\s]+(\d+)\s*GB",
        r"(\d+)\s*GB\s+(?:Max|Maximum)",
    ],
    "memory_slots": [
        r"(?:Memory\s+Slot[s]?|メモリスロット)[:\s]+(\d+)",
        r"(\d+)\s*[xX×]\s*DIMM",
        r"(\d+)\s*slots?",
    ],
    "sata_ports": [
        r"(\d+)\s*[xX×]\s*SATA",
        r"SATA[^:]*:\s*(\d+)",
    ],
}


def _extract_mb_specs(text: str) -> dict:
    """スペックテキストから MB specs dict を生成する"""
    specs: dict = {}

    for field, patterns in _MB_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                raw = (m.group(1) if m.lastindex else m.group(0)).strip()
                raw = re.sub(r"\s+", " ", raw)
                if raw and len(raw) < 60:
                    specs[field] = raw
                    break

    for field, patterns in _MB_NUM_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if field == "m2_slots" and 0 <= val <= 10:
                        specs[field] = val
                        break
                    elif field == "max_memory_gb" and 16 <= val <= 512:
                        specs[field] = val
                        break
                    elif field == "memory_slots" and 1 <= val <= 8:
                        specs[field] = val
                        break
                    elif field == "sata_ports" and 0 <= val <= 12:
                        specs[field] = val
                        break
                except (ValueError, IndexError):
                    pass

    return specs


# ─── JavaScript 抽出スクリプト ─────────────────────────────────────────────────

# www.asus.com の techspec ページ用
JS_WWW_SPEC = """
() => {
    const lines = [];
    // TechSpec テーブル行
    document.querySelectorAll(
        '[class*="TechSpec__rowTable"] [class*="TechSpec__specTitle"], ' +
        '[class*="TechSpec__rowTable"] [class*="TechSpec__specContent"], ' +
        '[class*="rowTableTitle"], [class*="rowTableItem"]'
    ).forEach(el => {
        const t = el.textContent.replace(/\\s+/g, ' ').trim();
        if (t) lines.push(t);
    });
    // フォールバック: 汎用テーブル
    if (lines.length < 5) {
        document.querySelectorAll('table tr, dl dt, dl dd').forEach(el => {
            const t = el.textContent.replace(/\\s+/g, ' ').trim();
            if (t && t.length < 200) lines.push(t);
        });
    }
    return lines.length >= 3 ? lines.join('\\n') : document.body.innerText;
}
"""

# rog.asus.com の spec ページ用
JS_ROG_SPEC = """
() => {
    const lines = [];
    document.querySelectorAll('.spec-list li, .spec-row, table tr, dl').forEach(el => {
        const t = el.textContent.replace(/\\s+/g, ' ').trim();
        if (t && t.length < 300) lines.push(t);
    });
    return lines.length >= 3 ? lines.join('\\n') : document.body.innerText;
}
"""

# 製品一覧ページから製品リンクを取得
JS_GPU_LINKS_WWW = """
() => {
    // カテゴリページ・ナビページを除外するための既知セグメント
    const EXCLUDE = ['all-series', 'overview', 'spec', 'techspec', 'gallery',
                     'compatibility', 'award', 'faq', 'support', 'download',
                     'where-to-buy', 'review', 'features', 'design', 'videos'];
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (!href.startsWith('https://www.asus.com')) return;
        if (!href.includes('/graphics-cards/')) return;
        if (href.includes('#')) return;
        try {
            const url = new URL(href);
            const segs = url.pathname.replace(/\\/$/, '').split('/').filter(Boolean);
            const last = segs[segs.length - 1] || '';
            // 除外ページ
            if (EXCLUDE.some(e => last === e)) return;
            // 製品URLの末尾セグメントには型番の数字が含まれる (RTX5080, B850, X870E など)
            if (!/\\d/.test(last)) return;
            links.push(href.split('?')[0].replace(/\\/$/, ''));
        } catch(e) {}
    });
    return [...new Set(links)];
}
"""

JS_GPU_LINKS_ROG = """
() => {
    const EXCLUDE = ['all-series', 'overview', 'spec', 'techspec', 'gallery',
                     'compatibility', 'award', 'faq', 'support', 'download',
                     'where-to-buy', 'review', 'features', 'design', 'videos'];
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (!href.startsWith('https://rog.asus.com')) return;
        if (!href.includes('/graphics-cards/')) return;
        if (href.includes('#')) return;
        try {
            const url = new URL(href);
            const segs = url.pathname.replace(/\\/$/, '').split('/').filter(Boolean);
            const last = segs[segs.length - 1] || '';
            if (EXCLUDE.some(e => last === e)) return;
            // ROGの製品URLも型番に数字が含まれる
            if (!/\\d/.test(last)) return;
            links.push(href.split('?')[0].replace(/\\/$/, ''));
        } catch(e) {}
    });
    return [...new Set(links)];
}
"""

JS_MB_LINKS_WWW = """
() => {
    const EXCLUDE = ['all-series', 'overview', 'spec', 'techspec', 'gallery',
                     'compatibility', 'award', 'faq', 'support', 'download',
                     'where-to-buy', 'review', 'features', 'design', 'videos'];
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (!href.startsWith('https://www.asus.com')) return;
        if (!href.includes('/motherboards/')) return;
        if (href.includes('#')) return;
        try {
            const url = new URL(href);
            const segs = url.pathname.replace(/\\/$/, '').split('/').filter(Boolean);
            const last = segs[segs.length - 1] || '';
            if (EXCLUDE.some(e => last === e)) return;
            if (!/\\d/.test(last)) return;
            links.push(href.split('?')[0].replace(/\\/$/, ''));
        } catch(e) {}
    });
    return [...new Set(links)];
}
"""

JS_MB_LINKS_ROG = """
() => {
    const EXCLUDE = ['all-series', 'overview', 'spec', 'techspec', 'gallery',
                     'compatibility', 'award', 'faq', 'support', 'download',
                     'where-to-buy', 'review', 'features', 'design', 'videos'];
    const links = [];
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.href || '';
        if (!href.startsWith('https://rog.asus.com')) return;
        if (!href.includes('/motherboards/')) return;
        if (href.includes('#')) return;
        try {
            const url = new URL(href);
            const segs = url.pathname.replace(/\\/$/, '').split('/').filter(Boolean);
            const last = segs[segs.length - 1] || '';
            if (EXCLUDE.some(e => last === e)) return;
            if (!/\\d/.test(last)) return;
            links.push(href.split('?')[0].replace(/\\/$/, ''));
        } catch(e) {}
    });
    return [...new Set(links)];
}
"""

# ─── JSONL 読み書き ─────────────────────────────────────────────────────────────

def _load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _save_jsonl(path: pathlib.Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _normalize_ids(records: list[dict]) -> list[dict]:
    """hex hash ID を正規スラグ形式に修正する"""
    fixed = 0
    for rec in records:
        if _is_hex_id(rec.get("id", "")):
            new_id = _make_id(rec.get("name", "unknown"))
            print(f"  ID修正: {rec['id']} → {new_id}", file=sys.stderr)
            rec["id"] = new_id
            fixed += 1
    if fixed:
        print(f"  ID正規化: {fixed} 件", file=sys.stderr)
    return records


# ─── メインスクレイパークラス ──────────────────────────────────────────────────

class AsusScraper:

    # GPU 一覧ページ
    GPU_LIST_PAGES = [
        ("https://www.asus.com/jp/motherboards-components/graphics-cards/all-series/", "www"),
        ("https://rog.asus.com/jp/graphics-cards/graphics-cards/all-series/", "rog"),
    ]

    # MB 一覧ページ
    MB_LIST_PAGES = [
        ("https://rog.asus.com/jp/motherboards/all-series/", "rog"),
        ("https://www.asus.com/jp/motherboards-components/motherboards/all-series/", "www"),
    ]

    def __init__(self, limit: int = 30, headless: bool = True):
        self.limit = limit
        self.headless = headless
        self._browser: Browser | None = None
        self._pw = None

    # ── ブラウザ管理 ────────────────────────────────────────────────────────────

    def _start_browser(self):
        self._pw = sync_playwright().__enter__()
        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

    def _new_page(self) -> Page:
        ctx = self._browser.new_context(
            user_agent=_UA,
            viewport={"width": 1280, "height": 900},
            locale="ja-JP",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        return ctx.new_page()

    def _stop_browser(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    # ── 一覧ページから製品 URL を収集 ─────────────────────────────────────────────

    def _collect_links(self, page: Page, list_url: str, js_extract: str,
                       click_more_max: int = 5) -> list[str]:
        """一覧ページを開き、「もっと見る」をクリックして製品 URL を収集する"""
        print(f"  [一覧] {list_url}", file=sys.stderr)
        try:
            page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  [WARN] ページ遷移エラー: {e}", file=sys.stderr)
            return []
        time.sleep(3)

        # 「もっと見る」ボタンをクリックして全件ロード
        for _ in range(click_more_max):
            clicked = False
            for btn_text in ["もっと見る", "MORE", "Load More", "Show More", "さらに表示"]:
                try:
                    btn = page.get_by_text(btn_text, exact=False)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        time.sleep(2)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                break

        links: list[str] = page.evaluate(js_extract)
        print(f"  [一覧] {len(links)} 件の製品 URL を取得", file=sys.stderr)
        return links

    def scrape_gpu_urls(self, page: Page) -> list[str]:
        """GPU 一覧ページから製品 URL リストを収集する"""
        all_links: list[str] = []
        seen: set[str] = set()
        for list_url, site_type in self.GPU_LIST_PAGES:
            js = JS_GPU_LINKS_WWW if site_type == "www" else JS_GPU_LINKS_ROG
            links = self._collect_links(page, list_url, js)
            for lnk in links:
                if lnk not in seen:
                    seen.add(lnk)
                    all_links.append(lnk)
        return all_links

    def scrape_mb_urls(self, page: Page) -> list[str]:
        """MB 一覧ページから製品 URL リストを収集する"""
        all_links: list[str] = []
        seen: set[str] = set()
        for list_url, site_type in self.MB_LIST_PAGES:
            js = JS_MB_LINKS_ROG if site_type == "rog" else JS_MB_LINKS_WWW
            links = self._collect_links(page, list_url, js)
            for lnk in links:
                if lnk not in seen:
                    seen.add(lnk)
                    all_links.append(lnk)
        return all_links

    # ── スペックページからテキストを取得 ──────────────────────────────────────────

    def _get_spec_url(self, product_url: str) -> str:
        """製品 URL → スペックページ URL"""
        base = product_url.rstrip("/")
        if "rog.asus.com" in base:
            return base + "/spec/"
        return base + "/techspec/"

    def _fetch_spec_text(self, page: Page, product_url: str) -> str:
        """スペックページにアクセスしてテキストを返す"""
        spec_url = self._get_spec_url(product_url)
        try:
            page.goto(spec_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"    [WARN] {e}", file=sys.stderr)
        time.sleep(2)

        if "rog.asus.com" in product_url:
            text = page.evaluate(JS_ROG_SPEC)
        else:
            text = page.evaluate(JS_WWW_SPEC)

        if not text or len(text) < 100:
            text = page.evaluate("() => document.body.innerText") or ""

        return text

    # ── 製品名を取得 ─────────────────────────────────────────────────────────────

    def _fetch_product_name(self, page: Page, product_url: str) -> str:
        """製品ページから製品名を取得する"""
        try:
            # h1 タグを優先
            name = page.evaluate("""
            () => {
                const h1 = document.querySelector('h1');
                if (h1) return h1.textContent.trim();
                const title = document.title;
                return title ? title.split('|')[0].trim() : '';
            }
            """)
            if name and len(name) > 3:
                return name
        except Exception:
            pass
        # URL の末尾から推測
        seg = product_url.rstrip("/").split("/")[-1]
        return seg.replace("-", " ").upper()

    # ── GPU 全件処理 ──────────────────────────────────────────────────────────────

    def run_gpu(self) -> int:
        """GPU をスクレイプして products.jsonl を更新する。更新件数を返す。"""
        print("\n[GPU] スクレイプ開始\n", file=sys.stderr)
        existing = _load_jsonl(_GPU_JSONL)
        existing = _normalize_ids(existing)
        by_url: dict[str, dict] = {r["source_url"]: r for r in existing if r.get("source_url")}

        page = self._new_page()

        # Phase 1: 製品 URL 収集
        product_urls = self.scrape_gpu_urls(page)
        if not product_urls:
            print("[GPU] 製品 URL を取得できませんでした", file=sys.stderr)
            return 0

        target_urls = product_urls[: self.limit]
        print(f"\n[GPU] 対象: {len(target_urls)} / {len(product_urls)} 件\n", file=sys.stderr)

        # Phase 2: 各スペックページをスクレイプ
        updated = 0
        added = 0

        for i, purl in enumerate(target_urls, 1):
            print(f"[{i}/{len(target_urls)}] {purl[:80]}", file=sys.stderr)
            try:
                text = self._fetch_spec_text(page, purl)
                if not text or len(text) < 50:
                    print("  SKIP: テキスト取得不可", file=sys.stderr)
                    time.sleep(1)
                    continue

                specs = _extract_gpu_specs(text)
                name = self._fetch_product_name(page, purl)

                if purl in by_url:
                    # 既存レコード更新
                    rec = by_url[purl]
                    rec["specs"].update({k: v for k, v in specs.items() if v is not None})
                    rec["name"] = name or rec["name"]
                    updated += 1
                    print(f"  UPDATE: {name[:50]} | specs={list(specs.keys())}", file=sys.stderr)
                else:
                    # 新規レコード
                    rec = {
                        "id": _make_id(name),
                        "name": name,
                        "maker": "asus",
                        "category": "gpu",
                        "source_url": purl,
                        "manual_url": None,
                        "manual_path": None,
                        "manual_scraped_at": None,
                        "created_at": _TS,
                        "specs": specs,
                    }
                    by_url[purl] = rec
                    added += 1
                    print(f"  ADD: {name[:50]} | specs={list(specs.keys())}", file=sys.stderr)

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)

            time.sleep(1.5)

        # 既存レコード（対象外のもの）も含めて保存
        all_records = list(by_url.values())
        _save_jsonl(_GPU_JSONL, all_records)
        total = updated + added
        print(
            f"\n[GPU] 完了: 更新={updated} 追加={added} 合計={len(all_records)} 件 | products.jsonl 保存済み",
            file=sys.stderr,
        )
        return total

    # ── MB 全件処理 ───────────────────────────────────────────────────────────────

    def run_mb(self) -> int:
        """MB をスクレイプして products.jsonl を更新する。更新件数を返す。"""
        print("\n[MB] スクレイプ開始\n", file=sys.stderr)
        existing = _load_jsonl(_MB_JSONL)
        existing = _normalize_ids(existing)
        by_url: dict[str, dict] = {r["source_url"]: r for r in existing if r.get("source_url")}

        page = self._new_page()

        # Phase 1: 製品 URL 収集
        product_urls = self.scrape_mb_urls(page)
        if not product_urls:
            print("[MB] 製品 URL を取得できませんでした", file=sys.stderr)
            return 0

        target_urls = product_urls[: self.limit]
        print(f"\n[MB] 対象: {len(target_urls)} / {len(product_urls)} 件\n", file=sys.stderr)

        # Phase 2: 各スペックページをスクレイプ
        updated = 0
        added = 0

        for i, purl in enumerate(target_urls, 1):
            print(f"[{i}/{len(target_urls)}] {purl[:80]}", file=sys.stderr)
            try:
                text = self._fetch_spec_text(page, purl)
                if not text or len(text) < 50:
                    print("  SKIP: テキスト取得不可", file=sys.stderr)
                    time.sleep(1)
                    continue

                specs = _extract_mb_specs(text)
                name = self._fetch_product_name(page, purl)

                if purl in by_url:
                    rec = by_url[purl]
                    rec["specs"].update({k: v for k, v in specs.items() if v is not None})
                    rec["name"] = name or rec["name"]
                    updated += 1
                    print(f"  UPDATE: {name[:50]} | specs={list(specs.keys())}", file=sys.stderr)
                else:
                    rec = {
                        "id": _make_id(name),
                        "name": name,
                        "maker": "asus",
                        "category": "motherboard",
                        "source_url": purl,
                        "manual_url": None,
                        "manual_path": None,
                        "manual_scraped_at": None,
                        "created_at": _TS,
                        "specs": specs,
                    }
                    by_url[purl] = rec
                    added += 1
                    print(f"  ADD: {name[:50]} | specs={list(specs.keys())}", file=sys.stderr)

            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)

            time.sleep(1.5)

        all_records = list(by_url.values())
        _save_jsonl(_MB_JSONL, all_records)
        total = updated + added
        print(
            f"\n[MB] 完了: 更新={updated} 追加={added} 合計={len(all_records)} 件 | products.jsonl 保存済み",
            file=sys.stderr,
        )
        return total

    # ── 統合実行 ──────────────────────────────────────────────────────────────────

    def run(self, gpu: bool = True, mb: bool = True) -> None:
        self._start_browser()
        try:
            if gpu:
                self.run_gpu()
            if mb:
                self.run_mb()
        finally:
            self._stop_browser()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ASUS GPU / MB スペックスクレイパー"
    )
    parser.add_argument("--gpu", action="store_true", help="GPU のみ実行")
    parser.add_argument("--mb", action="store_true", help="MB のみ実行")
    parser.add_argument("--limit", type=int, default=30, help="各カテゴリ上限件数 (default: 30)")
    parser.add_argument("--all", dest="all_", action="store_true", help="ページネーション全件")
    parser.add_argument("--no-headless", action="store_true", help="ブラウザ表示（デバッグ用）")
    args = parser.parse_args()

    run_gpu = args.gpu or (not args.gpu and not args.mb)
    run_mb  = args.mb  or (not args.gpu and not args.mb)
    limit   = 999_999 if args.all_ else args.limit

    scraper = AsusScraper(limit=limit, headless=not args.no_headless)
    scraper.run(gpu=run_gpu, mb=run_mb)


if __name__ == "__main__":
    main()
