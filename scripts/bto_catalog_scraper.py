#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTO カタログスクレイパー — 各メーカー一覧ページから新商品を発見・追加

対応メーカー (Phase 2 — 静的HTML取得可能):
  サイコム, ツクモ, SEVEN, FRONTIER, STORM

Phase 3 (JS描画/Bot対策で後日対応):
  パソコン工房 (JS描画), ark (403 Bot対策), ドスパラ, HP, Lenovo, Dell

実行:
  python scripts/bto_catalog_scraper.py                    # フル実行
  python scripts/bto_catalog_scraper.py --maker STORM      # 特定メーカーのみ
  python scripts/bto_catalog_scraper.py --dry-run           # 書き込みなし
  python scripts/bto_catalog_scraper.py --list-makers       # 対応メーカー一覧
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "workspace", "data")
BTO_JSONL = os.path.join(DATA_DIR, "bto", "products.jsonl")
DIFF_LOG_DIR = os.path.join(DATA_DIR, "diff_logs")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ─────────────────────────────────────────────────────────────────────────────
# HTTP取得
# ─────────────────────────────────────────────────────────────────────────────

def fetch_html(url: str, retries: int = 3) -> tuple[int, str]:
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ja,en-US;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                return resp.getcode(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if attempt == retries:
                return e.code, ""
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == retries:
                print(f"  [ERROR] {e}")
                return 0, ""
            time.sleep(2 ** attempt)
    return 0, ""


# ─────────────────────────────────────────────────────────────────────────────
# 価格抽出
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_price(raw: str) -> int | None:
    raw = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    raw = raw.replace(",", "").replace("，", "").replace(" ", "").replace("\u3000", "")
    digits = re.sub(r"[^\d]", "", raw)
    if digits and len(digits) >= 4:
        val = int(digits)
        if 10000 <= val <= 3000000:
            return val
    return None


def _extract_price(html: str) -> int | None:
    patterns = [
        r'class="[^"]*(?:total_price|price_value|price)[^"]*"[^>]*>\s*[¥￥]?\s*([0-9０-９,，]+)',
        r"販売価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"基本構成価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"通常価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"特別価格[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"税込[^0-9０-９]*([0-9０-９,，]+)\s*円",
        r"[¥￥]\s*([0-9０-９,，]+)",
        r"([0-9０-９,，]+)\s*円\s*[\(（]\s*税込",
        r'"price"\s*:\s*"?(\d[\d,]*)"?',
        r'"lowPrice"\s*:\s*"?(\d[\d,]*)"?',
        r'data-price=["\'](\d+)["\']',
    ]
    for pat in patterns:
        for m in re.findall(pat, html):
            price = _normalize_price(m)
            if price:
                return price
    return None


# ─────────────────────────────────────────────────────────────────────────────
# スペック抽出
# ─────────────────────────────────────────────────────────────────────────────

_CPU_PATTERNS = [
    r"Core\s*i[3579]-?\s*\d{4,5}\w*",
    r"Ryzen\s*[3579]\s*\d{3,4}X?3?D?\w*",
]

_GPU_PATTERNS = [
    r"(?:GeForce\s*)?RTX\s*\d{4}\s*(?:Ti\s*)?(?:SUPER)?",
    r"(?:Radeon\s*)?RX\s*\d{4}\s*(?:XT)?",
]


def extract_basic_specs(html: str) -> dict:
    specs = {}
    text = html.replace("\n", " ")

    for pat in _CPU_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            specs["cpu"] = {"name": m.group(0).strip()}
            break

    for pat in _GPU_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            gpu_name = m.group(0).strip()
            specs["gpu"] = {"name": gpu_name}
            vm = re.search(rf"{re.escape(gpu_name)}[^<]{{0,50}}(\d{{1,2}})\s*GB", text, re.IGNORECASE)
            if vm:
                specs["gpu"]["vram_gb"] = int(vm.group(1))
            break

    m = re.search(r"(\d{1,3})\s*GB.*?(?:DDR[45])", text, re.IGNORECASE)
    if m:
        cap = int(m.group(1))
        if 4 <= cap <= 256:
            ddr = "DDR5" if "DDR5" in text.upper() else "DDR4"
            specs["ram"] = {"capacity_gb": cap, "type": ddr}

    m = re.search(r"(\d+)\s*TB\s*(?:NVMe|SSD|M\.2)", text, re.IGNORECASE)
    if m:
        specs["storage"] = [{"type": "NVMe", "capacity_gb": int(m.group(1)) * 1000}]
    else:
        m = re.search(r"(\d+)\s*GB\s*(?:NVMe|SSD|M\.2)", text, re.IGNORECASE)
        if m and int(m.group(1)) >= 128:
            specs["storage"] = [{"type": "NVMe", "capacity_gb": int(m.group(1))}]

    return specs


# ─────────────────────────────────────────────────────────────────────────────
# メーカー別カタログスクレイパー
# ─────────────────────────────────────────────────────────────────────────────

class MakerScraper:
    maker_name: str = ""

    def scrape_list(self) -> list[dict]:
        raise NotImplementedError

    def scrape_detail(self, item: dict) -> dict | None:
        url = item.get("url", "")
        if not url:
            return None
        status, html = fetch_html(url)
        if status != 200 or not html:
            print(f"    SKIP: HTTP {status}")
            return None

        price = _extract_price(html)
        specs = extract_basic_specs(html)
        model = item.get("model", "")
        series = item.get("series", "")

        return {
            "id": self._make_id(model),
            "maker": self.maker_name,
            "series": series,
            "model": model,
            "url": url,
            "price_jpy": price,
            "price_updated_at": TODAY if price else None,
            "affiliate": {"asp": "", "url": "", "commission_rate": 0},
            "specs": specs,
            "warranty_years": 1,
            "tags": ["ゲーミング"],
            "url_verified": True,
        }

    def _make_id(self, model: str) -> str:
        prefix = re.sub(r"[^a-z0-9]", "_", self.maker_name.lower()).strip("_")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", model.lower()).strip("_")
        slug = re.sub(r"_+", "_", slug)
        return f"{prefix}_{slug}"


class SycomScraper(MakerScraper):
    maker_name = "サイコム"

    def scrape_list(self) -> list[dict]:
        items = []
        status, html = fetch_html("https://www.sycom.co.jp/bto/game_pc/")
        if status != 200:
            return items
        for m in re.finditer(r'href=["\'](/custom/model\?no=\d+)["\']', html):
            url = "https://www.sycom.co.jp" + m.group(1)
            if url not in [i["url"] for i in items]:
                items.append({"url": url, "model": "", "series": "G-Master"})
        time.sleep(1)
        return items

    def scrape_detail(self, item: dict) -> dict | None:
        url = item.get("url", "")
        status, html = fetch_html(url)
        if status != 200 or not html:
            return None
        model = ""
        m = re.search(r"(G-Master\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)", html)
        if m:
            model = m.group(1).strip()
        if not model:
            no = re.search(r"no=(\d+)", url)
            model = f"G-Master-{no.group(1)}" if no else "G-Master"

        rec = super().scrape_detail({**item, "model": model})
        if rec:
            rec["model"] = model
            rec["id"] = self._make_id(model)
            rec["affiliate"]["asp"] = "A8.net"
        return rec


class TsukumoScraper(MakerScraper):
    maker_name = "ツクモ"

    def scrape_list(self) -> list[dict]:
        items = []
        for list_url in [
            "https://www.tsukumo.co.jp/bto/pc/game/",
            "https://www.tsukumo.co.jp/bto/pc/game/neo/",
        ]:
            status, html = fetch_html(list_url)
            if status != 200:
                continue
            # プロトコル相対URL: //www.tsukumo.co.jp/bto/pc/game/YYYY/XXX.html
            for m in re.finditer(r'href=["\'](?:https?:)?(//?www\.tsukumo\.co\.jp/bto/pc/game/[^"\']+\.html)["\']', html):
                path = m.group(1)
                if "/spec.html" in path or "/index.html" in path:
                    continue
                url = "https:" + path if path.startswith("//") else path
                model_m = re.search(r"/([^/]+)\.html$", url)
                model = model_m.group(1) if model_m else ""
                if url not in [i["url"] for i in items]:
                    items.append({"url": url, "model": model, "series": "G-GEAR"})
            # 相対パスも拾う
            for m in re.finditer(r'href=["\'](/bto/pc/game/[^"\']+\.html)["\']', html):
                path = m.group(1)
                if "/spec.html" in path or "/index.html" in path:
                    continue
                url = "https://www.tsukumo.co.jp" + path
                model_m = re.search(r"/([^/]+)\.html$", path)
                model = model_m.group(1) if model_m else ""
                if url not in [i["url"] for i in items]:
                    items.append({"url": url, "model": model, "series": "G-GEAR"})
            time.sleep(1)
        return items


class SevenScraper(MakerScraper):
    maker_name = "SEVEN"

    def scrape_list(self) -> list[dict]:
        items = []
        for page in range(1, 4):
            url = "https://pc-seven.co.jp/series/r/gaming-pc-total"
            if page > 1:
                url += f"?page={page}"
            status, html = fetch_html(url)
            if status != 200:
                break
            found = False
            for m in re.finditer(r'href=["\'](/spc/\d+\.html)["\']', html):
                full = "https://pc-seven.co.jp" + m.group(1)
                if full not in [i["url"] for i in items]:
                    items.append({"url": full, "model": "", "series": "ZEFT"})
                    found = True
            if not found and page > 1:
                break
            time.sleep(1)
        return items

    def scrape_detail(self, item: dict) -> dict | None:
        url = item.get("url", "")
        status, html = fetch_html(url)
        if status != 200 or not html:
            return None
        model = ""
        m = re.search(r"(ZEFT\s*[A-Z]\d{2}[A-Z]{0,2})", html)
        if m:
            model = m.group(1).strip()
        if not model:
            sid = re.search(r"/spc/(\d+)\.html", url)
            model = f"ZEFT-{sid.group(1)}" if sid else "ZEFT"
        rec = super().scrape_detail({**item, "model": model})
        if rec:
            rec["model"] = model
            rec["id"] = self._make_id(model)
        return rec


class FrontierScraper(MakerScraper):
    maker_name = "FRONTIER"

    def scrape_list(self) -> list[dict]:
        items = []
        status, html = fetch_html("https://www.frontier-direct.jp/direct/e/ejGame/")
        if status != 200:
            return items
        # /direct/g/gXXXXXX/ or /direct/g/gXXXXXX-t/
        for m in re.finditer(r'href=["\'](/direct/g/g\d+(?:-\w+)?/)["\']', html):
            url = "https://www.frontier-direct.jp" + m.group(1)
            if url not in [i["url"] for i in items]:
                items.append({"url": url, "model": "", "series": "FRONTIER"})
        time.sleep(1)
        return items

    def scrape_detail(self, item: dict) -> dict | None:
        url = item.get("url", "")
        status, html = fetch_html(url)
        if status != 200 or not html:
            return None
        model = ""
        m = re.search(r"(FR[A-Z]{2,6}[A-Z0-9/\-]+)", html)
        if m:
            model = m.group(1).strip().rstrip("/")
        if not model:
            gid = re.search(r"/g/g(\d+)", url)
            model = f"FRONTIER-{gid.group(1)}" if gid else "FRONTIER"
        rec = super().scrape_detail({**item, "model": model})
        if rec:
            rec["model"] = model
            rec["id"] = self._make_id(model)
        return rec


class StormScraper(MakerScraper):
    maker_name = "STORM"

    def scrape_list(self) -> list[dict]:
        items = []
        # カテゴリ: 1=幻界, 2=影界, 335=全商品
        for cat_id in [1, 2]:
            for page in range(1, 5):
                url = f"https://www.stormst.com/products/list?category_id={cat_id}"
                if page > 1:
                    url += f"&pageno={page}"
                status, html = fetch_html(url)
                if status != 200:
                    break
                found = False
                # 絶対URL: https://www.stormst.com/products/detail/XXX
                for m in re.finditer(r'href=["\']?(https://www\.stormst\.com/products/detail/\d+)["\']?', html):
                    prod_url = m.group(1)
                    if prod_url not in [i["url"] for i in items]:
                        items.append({"url": prod_url, "model": "", "series": "STORM"})
                        found = True
                if not found and page > 1:
                    break
                time.sleep(1)
        return items

    def scrape_detail(self, item: dict) -> dict | None:
        url = item.get("url", "")
        status, html = fetch_html(url)
        if status != 200 or not html:
            return None
        model = ""
        # STORM型番: 2-4文字+数字-CPU/GPU略称 (例: PG-PD57Ti, RK2-78X3D57Ti)
        m = re.search(r"((?:PG|RK|GK|SK|PGK|GKG|EG|FZ|FK|FS|KF|PF)[A-Z0-9]*-[A-Z0-9]+(?:Ti)?)", html)
        if m:
            model = m.group(1).strip()
        if not model:
            did = re.search(r"/detail/(\d+)", url)
            model = f"STORM-{did.group(1)}" if did else "STORM"
        rec = super().scrape_detail({**item, "model": model})
        if rec:
            rec["model"] = model
            rec["id"] = self._make_id(model)
        return rec


# ─────────────────────────────────────────────────────────────────────────────
# スクレイパーレジストリ
# ─────────────────────────────────────────────────────────────────────────────

SCRAPERS: dict[str, type[MakerScraper]] = {
    "サイコム": SycomScraper,
    "ツクモ": TsukumoScraper,
    "SEVEN": SevenScraper,
    "FRONTIER": FrontierScraper,
    "STORM": StormScraper,
}


# ─────────────────────────────────────────────────────────────────────────────
# JSONL 読み書き
# ─────────────────────────────────────────────────────────────────────────────

def load_products(path: str) -> list[dict]:
    products = []
    if not os.path.exists(path):
        return products
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def save_products(path: str, products: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in products:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_diff_log(changes: list[dict]) -> str | None:
    if not changes:
        return None
    os.makedirs(DIFF_LOG_DIR, exist_ok=True)
    path = os.path.join(DIFF_LOG_DIR, f"bto-catalog-{TODAY}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for c in changes:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────────────────────────────────────

def run_catalog_scraper(
    makers: list[str] | None = None,
    dry_run: bool = False,
    max_new_per_maker: int = 30,
) -> dict:
    stats = {
        "makers_processed": 0,
        "list_found": 0,
        "new_added": 0,
        "skipped_existing": 0,
        "skipped_no_price": 0,
        "error": 0,
    }
    changes = []

    existing = load_products(BTO_JSONL)
    existing_urls = {p.get("url", "") for p in existing}
    existing_ids = {p.get("id", "") for p in existing}

    target_makers = makers or list(SCRAPERS.keys())
    print(f"対象メーカー: {', '.join(target_makers)}")
    print(f"既存商品数: {len(existing)}")
    print(f"モード: {'dry-run' if dry_run else 'フル'}")
    print("=" * 60)

    new_products = []

    for maker_name in target_makers:
        if maker_name not in SCRAPERS:
            print(f"\n[SKIP] {maker_name}: 未対応メーカー")
            continue

        print(f"\n--- {maker_name} ---")
        scraper = SCRAPERS[maker_name]()

        print(f"  一覧ページ取得中...")
        items = scraper.scrape_list()
        print(f"  発見: {len(items)}件")
        stats["list_found"] += len(items)
        stats["makers_processed"] += 1

        new_items = [i for i in items if i["url"] not in existing_urls]
        stats["skipped_existing"] += len(items) - len(new_items)
        print(f"  新規候補: {len(new_items)}件 (既存スキップ: {len(items) - len(new_items)}件)")

        if not new_items:
            continue

        if len(new_items) > max_new_per_maker:
            print(f"  上限超過 → 先頭{max_new_per_maker}件のみ処理")
            new_items = new_items[:max_new_per_maker]

        added = 0
        for j, item in enumerate(new_items, 1):
            print(f"  [{j}/{len(new_items)}] {item['url'][:70]}...")
            record = scraper.scrape_detail(item)

            if record is None:
                stats["error"] += 1
                time.sleep(0.5)
                continue

            if record.get("price_jpy") is None:
                print(f"    価格取得失敗 → スキップ")
                stats["skipped_no_price"] += 1
                time.sleep(0.5)
                continue

            if record["id"] in existing_ids:
                record["id"] = record["id"] + f"_{added}"

            print(f"    OK: {record['model']} ¥{record['price_jpy']:,}")
            new_products.append(record)
            existing_urls.add(record["url"])
            existing_ids.add(record["id"])
            changes.append({
                "type": "new_product", "maker": maker_name,
                "id": record["id"], "model": record["model"],
                "price": record["price_jpy"],
            })
            stats["new_added"] += 1
            added += 1
            time.sleep(0.5)

    if new_products and not dry_run:
        all_products = existing + new_products
        save_products(BTO_JSONL, all_products)
        print(f"\nproducts.jsonl 保存完了 ({len(existing)} → {len(all_products)}件)")
        log_path = save_diff_log(changes)
        if log_path:
            print(f"差分ログ: {log_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="BTO カタログスクレイパー")
    parser.add_argument("--maker", type=str, default=None,
                        help="特定メーカーのみ実行 (例: STORM)")
    parser.add_argument("--dry-run", action="store_true",
                        help="書き込みなし")
    parser.add_argument("--list-makers", action="store_true",
                        help="対応メーカー一覧を表示")
    parser.add_argument("--max-new", type=int, default=30,
                        help="メーカーあたりの新規追加上限 (default: 30)")
    args = parser.parse_args()

    if args.list_makers:
        print("対応メーカー:")
        for name in SCRAPERS:
            print(f"  - {name}")
        return

    print(f"{'=' * 60}")
    print(f"BTO カタログスクレイプ {TODAY}")
    print(f"{'=' * 60}")

    makers = [args.maker] if args.maker else None
    stats = run_catalog_scraper(
        makers=makers, dry_run=args.dry_run, max_new_per_maker=args.max_new,
    )

    print(f"\n{'=' * 60}")
    print(f"サマリー")
    print(f"{'=' * 60}")
    print(f"  処理メーカー:  {stats['makers_processed']}")
    print(f"  一覧発見:     {stats['list_found']}件")
    print(f"  新規追加:     {stats['new_added']}件")
    print(f"  既存スキップ: {stats['skipped_existing']}件")
    print(f"  価格なしスキップ: {stats['skipped_no_price']}件")
    print(f"  エラー:       {stats['error']}件")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
