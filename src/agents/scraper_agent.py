"""
PCPartsScraperAgent — メーカー公式サイトスペックスクレイパー
=============================================================
【責務】
GPU/マザーボード/CPUクーラー/ケース/電源メーカーの公式スペックページを
定期クロールし、BigQuery parts テーブルを最新状態に保つ。

【依存】
- playwright.async_api  (ヘッドレスChromium)
- google-cloud-bigquery (BigQueryへのアップサート)
- asyncio, aiohttp      (非同期HTTP)
- src/tools/bigquery_tool.BigQueryTool

【データフロー】
SCRAPE_TARGETS (dict)
  → scrape_manufacturer(manufacturer, category)  # カテゴリ別スクレイプ
    → _fetch_spec_page(url)                       # Playwright でHTML取得
    → _extract_spec_table(html, category)         # スペック表パース
    → _normalize_to_schema(raw, ...)              # 共通スキーマに変換
    → _upsert_bigquery(rows, table)               # BigQuery MERGE
  → run_all()                                     # 全メーカー一括実行
  → run_scheduled(interval_days=7)                # 定期実行ループ

【BigQueryスキーマ (pc_parts.parts テーブル想定)】
    part_id        STRING  PK (例: "rtx4090_asus_rog")
    model_name     STRING
    category       STRING  (gpu / motherboard / cpu_cooler / psu / case)
    manufacturer   STRING
    spec_json      JSON    (カテゴリ固有の詳細スペック)
    scraped_at     TIMESTAMP
    source_url     STRING
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SCRAPE_TARGETS: dict[str, dict[str, list[str]]] = {
    "ASUS": {
        "gpu": [
            "https://www.asus.com/jp/motherboards-components/graphics-cards/all-series/",
        ],
        "motherboard": [
            "https://www.asus.com/jp/motherboards-components/motherboards/all-series/",
        ],
    },
    "MSI": {
        "gpu": [
            "https://jp.msi.com/Graphics-Cards",
        ],
        "motherboard": [
            "https://jp.msi.com/Motherboard",
        ],
    },
    "GIGABYTE": {
        "gpu": [
            "https://www.gigabyte.com/jp/Graphics-Card",
        ],
        "motherboard": [
            "https://www.gigabyte.com/jp/Motherboard",
        ],
    },
    "NZXT": {
        "case": [
            "https://nzxt.com/ja-JP/category/cases",
        ],
        "psu": [
            "https://nzxt.com/ja-JP/category/power-supplies",
        ],
    },
    "Fractal": {
        "case": [
            "https://www.fractal-design.com/products/cases/",
        ],
    },
    "Seasonic": {
        "psu": [
            "https://seasonic.com/product-category/focus/",
        ],
    },
    "Noctua": {
        "cpu_cooler": [
            "https://noctua.at/ja/coolers",
        ],
    },
}
"""スクレイプ対象メーカー・カテゴリ・URLマッピング"""

SCRAPE_INTERVAL_DAYS: int = 7
"""デフォルトの定期実行間隔（日）"""

BIGQUERY_PARTS_TABLE: str = "pc_parts.parts"
"""アップサート先のBigQueryテーブル"""

# IPバン対策: リクエスト間のランダムスリープ (秒)
_REQUEST_DELAY_MIN: float = 1.0
_REQUEST_DELAY_MAX: float = 3.0

# カテゴリ別スペックキー定義
_SPEC_KEYS: dict[str, list[str]] = {
    "gpu":        ["length_mm", "slot_width", "tdp_w", "power_connector", "height_mm", "pcie_version"],
    "motherboard":["socket", "ddr_gen", "form_factor", "m2_slots", "max_memory_speed_mt",
                   "m2_conflict_note", "atx24pin"],
    "cpu_cooler": ["height_mm", "supported_sockets", "max_tdp_w", "side_clearance_mm"],
    "psu":        ["rated_w", "atx_version", "depth_mm", "has_12vhpwr", "modular_type",
                   "efficiency_rating"],
    "case":       ["max_gpu_length_mm", "max_cooler_height_mm", "form_factors",
                   "psu_form_factor", "front_radiator_mm"],
}


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class ScrapeResult:
    """スクレイプ結果の1件"""
    part_id:      str
    model_name:   str
    category:     str
    manufacturer: str
    spec_json:    dict
    source_url:   str
    scraped_at:   datetime = field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        return bool(self.part_id and self.model_name and self.category)


@dataclass
class ScrapeStats:
    """実行統計"""
    total_scraped:         int   = 0
    total_upserted:        int   = 0
    total_errors:          int   = 0
    elapsed_seconds:       float = 0.0
    manufacturer_results:  dict  = field(default_factory=dict)


# ---------------------------------------------------------------------------
# メインクラス
# ---------------------------------------------------------------------------

class PCPartsScraperAgent:
    """
    メーカー公式サイトスペックスクレイパー

    Attributes:
        bq_project_id (str)     : BigQueryプロジェクトID
        headless (bool)         : Chromiumをヘッドレスで起動するか
        concurrency (int)       : 同時スクレイプ数 (デフォルト: 3)
        _playwright             : Playwright インスタンス (start()後に初期化)
        _browser                : Chromium Browser インスタンス
        _semaphore              : concurrency 制御用 asyncio.Semaphore
    """

    def __init__(
        self,
        bq_project_id: str,
        headless: bool = True,
        concurrency: int = 3,
    ) -> None:
        self.bq_project_id = bq_project_id
        self.headless = headless
        self.concurrency = concurrency
        self._playwright = None
        self._browser   = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    async def run_all(self) -> ScrapeStats:
        """
        SCRAPE_TARGETS の全メーカー・全カテゴリをスクレイプして BigQuery に保存する。

        Returns:
            ScrapeStats: 件数・エラー数・経過時間のサマリー
        """
        start_time = time.time()
        stats = ScrapeStats()
        self._semaphore = asyncio.Semaphore(self.concurrency)

        try:
            await self._start_browser()

            # 全 (manufacturer, category) ペアのタスクを生成
            tasks = []
            for manufacturer, categories in SCRAPE_TARGETS.items():
                for category in categories:
                    tasks.append((manufacturer, category))

            results = await asyncio.gather(
                *[self._scrape_with_stats(mfr, cat, stats) for mfr, cat in tasks],
                return_exceptions=True,
            )

            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"スクレイプタスクエラー: {r}")
                    stats.total_errors += 1

        finally:
            await self._close_browser()

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"スクレイプ完了: "
            f"取得={stats.total_scraped} 件, "
            f"保存={stats.total_upserted} 件, "
            f"エラー={stats.total_errors} 件, "
            f"{stats.elapsed_seconds:.1f}秒"
        )
        return stats

    async def run_scheduled(self, interval_days: int = SCRAPE_INTERVAL_DAYS) -> None:
        """
        run_all() を interval_days 間隔で無限ループ実行する。

        Args:
            interval_days: 実行間隔（日単位）

        Note:
            KeyboardInterrupt または asyncio.CancelledError で終了。
        """
        interval_secs = interval_days * 86400
        logger.info(f"定期スクレイプ開始: {interval_days}日間隔")

        try:
            while True:
                stats = await self.run_all()
                logger.info(
                    f"次回スクレイプまで {interval_days} 日待機 "
                    f"(今回: {stats.total_upserted} 件更新)"
                )
                await asyncio.sleep(interval_secs)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("定期スクレイプ停止")

    async def scrape_manufacturer(
        self,
        manufacturer: str,
        category: str,
    ) -> list[ScrapeResult]:
        """
        指定メーカー・カテゴリのスペックページをスクレイプする。

        Args:
            manufacturer: SCRAPE_TARGETS のキー (例: "ASUS")
            category    : カテゴリ名 (例: "gpu", "motherboard")

        Returns:
            list[ScrapeResult]: スクレイプ結果リスト
        """
        if manufacturer not in SCRAPE_TARGETS:
            raise ValueError(f"未登録のメーカー: {manufacturer}")
        if category not in SCRAPE_TARGETS[manufacturer]:
            raise KeyError(f"{manufacturer} に {category} カテゴリが存在しません")

        urls = SCRAPE_TARGETS[manufacturer][category]
        all_results: list[ScrapeResult] = []

        if self._browser is None:
            await self._start_browser()

        for url in urls:
            try:
                html = await self._fetch_spec_page(url)
                if not html:
                    continue

                raw_list = self._extract_spec_table(html, category)
                for raw in raw_list:
                    result = self._normalize_to_schema(raw, manufacturer, category, url)
                    if result and result.is_valid():
                        all_results.append(result)

                # IPバン対策: リクエスト間にランダムスリープ
                delay = random.uniform(_REQUEST_DELAY_MIN, _REQUEST_DELAY_MAX)
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"スクレイプエラー ({manufacturer}/{category} - {url}): {e}")

        logger.info(
            f"{manufacturer}/{category}: {len(all_results)} 件取得"
        )
        return all_results

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    async def _scrape_with_stats(
        self,
        manufacturer: str,
        category: str,
        stats: ScrapeStats,
    ) -> None:
        """scrape_manufacturer + _upsert_bigquery をまとめて実行し stats を更新"""
        async with self._semaphore:
            try:
                results = await self.scrape_manufacturer(manufacturer, category)
                stats.total_scraped += len(results)

                if results:
                    upserted = await self._upsert_bigquery(results)
                    stats.total_upserted += upserted
                    stats.manufacturer_results[f"{manufacturer}/{category}"] = len(results)

            except Exception as e:
                logger.error(f"_scrape_with_stats エラー ({manufacturer}/{category}): {e}")
                stats.total_errors += 1

    async def _fetch_spec_page(self, url: str) -> str:
        """
        PlaywrightでURLを開き、JavaScriptレンダリング後のHTMLを返す。

        Args:
            url: スクレイプ対象URL

        Returns:
            str: ページのHTML文字列 (フルDOM)

        Note:
            - networkidle まで待機 (最大30秒)
            - 失敗時は空文字列を返してログに記録
            - _semaphore による同時アクセス制御あり
        """
        if self._browser is None:
            logger.warning("Browser 未初期化: _fetch_spec_page スキップ")
            return ""

        page = None
        try:
            page = await self._browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            await page.set_extra_http_headers({"Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8"})
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            html = await page.content()
            logger.debug(f"取得完了: {url} ({len(html)} bytes)")
            return html

        except Exception as e:
            logger.warning(f"ページ取得失敗 ({url}): {e}")
            return ""
        finally:
            if page:
                await page.close()

    def _extract_spec_table(self, html: str, category: str) -> list[dict]:
        """
        HTMLからスペック表を解析してカテゴリ別の生データリストを返す。

        Args:
            html    : _fetch_spec_page() の返り値
            category: "gpu" | "motherboard" | "cpu_cooler" | "psu" | "case"

        Returns:
            list[dict]: 生スペックデータ (正規化前)

        Note:
            カテゴリ別に抽出キーが異なる。
            HTMLパース: 標準ライブラリ html.parser ベース (BeautifulSoup 非依存)。
        """
        results: list[dict] = []

        try:
            # 軽量なパースのため正規表現で対応
            # <h1/h2/h3> タグからモデル名を抽出
            name_pattern = re.compile(
                r"<(?:h[123]|title)[^>]*>(.*?)</(?:h[123]|title)>",
                re.IGNORECASE | re.DOTALL,
            )
            # スペック表 (<table>) を抽出
            table_pattern = re.compile(
                r"<table[^>]*>(.*?)</table>",
                re.IGNORECASE | re.DOTALL,
            )
            # <td> / <th> のテキスト抽出
            cell_pattern = re.compile(
                r"<t[dh][^>]*>(.*?)</t[dh]>",
                re.IGNORECASE | re.DOTALL,
            )
            # タグ除去
            tag_re = re.compile(r"<[^>]+>")

            def clean(text: str) -> str:
                return tag_re.sub("", text).strip()

            tables = table_pattern.findall(html)
            if not tables:
                # table がない場合は名前だけ返す (スペック詳細は後続処理に委ねる)
                names = [clean(m) for m in name_pattern.findall(html)]
                for name in names[:20]:  # 最大20件
                    if name and len(name) > 3:
                        results.append({"name": name})
                return results

            for table_html in tables[:10]:  # 最大10テーブル
                cells = [clean(c) for c in cell_pattern.findall(table_html)]
                # 2カラム構造 (key, value) のスペック表を想定
                spec_dict: dict[str, str] = {}
                for i in range(0, len(cells) - 1, 2):
                    key = cells[i].lower()
                    val = cells[i + 1] if i + 1 < len(cells) else ""
                    if key and val:
                        spec_dict[key] = val

                # モデル名を探す
                model_name = (
                    spec_dict.get("製品名") or
                    spec_dict.get("model") or
                    spec_dict.get("product name") or
                    spec_dict.get("モデル") or ""
                )

                if model_name or spec_dict:
                    raw = {"name": model_name, **spec_dict}
                    # カテゴリ別に有用なスペックが含まれているか確認
                    if self._has_relevant_spec(raw, category):
                        results.append(raw)

        except Exception as e:
            logger.warning(f"_extract_spec_table エラー ({category}): {e}")

        return results

    def _has_relevant_spec(self, raw: dict, category: str) -> bool:
        """カテゴリに関連するスペックキーが含まれているか確認"""
        relevant_kws: dict[str, list[str]] = {
            "gpu":        ["length", "長さ", "tdp", "w", "pcie", "slot"],
            "motherboard":["socket", "ddr", "m.2", "atx", "form"],
            "cpu_cooler": ["height", "高さ", "socket", "tdp", "mm"],
            "psu":        ["w", "watt", "atx", "modular", "12v"],
            "case":       ["gpu", "グラフィック", "cooler", "クーラー", "mm", "atx"],
        }
        kws = relevant_kws.get(category, [])
        raw_str = " ".join(str(v).lower() for v in raw.values())
        return any(kw in raw_str for kw in kws)

    def _normalize_to_schema(
        self,
        raw: dict,
        manufacturer: str,
        category: str,
        source_url: str,
    ) -> Optional[ScrapeResult]:
        """
        生スペックデータを共通スキーマ (ScrapeResult) に変換する。

        Args:
            raw         : _extract_spec_table() の1件
            manufacturer: メーカー名
            category    : パーツカテゴリ
            source_url  : スクレイプ元URL

        Returns:
            ScrapeResult: 正規化済みデータ、変換失敗時は None
        """
        try:
            model_name = (
                raw.get("name") or
                raw.get("製品名") or
                raw.get("model") or ""
            ).strip()

            if not model_name:
                return None

            # part_id: "{manufacturer}_{model_name}" をスネークケースに変換
            slug = re.sub(r"[^\w]", "_", f"{manufacturer}_{model_name}").lower()
            slug = re.sub(r"_+", "_", slug).strip("_")
            part_id = slug[:64]  # 最大64文字

            # カテゴリ別 spec_json を構築
            spec_json = self._build_spec_json(raw, category)

            return ScrapeResult(
                part_id=part_id,
                model_name=model_name,
                category=category,
                manufacturer=manufacturer,
                spec_json=spec_json,
                source_url=source_url,
            )

        except Exception as e:
            logger.debug(f"_normalize_to_schema エラー: {e} | raw={raw}")
            return None

    def _build_spec_json(self, raw: dict, category: str) -> dict:
        """生データからカテゴリ別 spec_json を構築する"""

        def find_int(keys: list[str]) -> Optional[int]:
            for k in keys:
                for rk, rv in raw.items():
                    if k in rk.lower():
                        m = re.search(r"\d+", str(rv))
                        if m:
                            return int(m.group())
            return None

        def find_str(keys: list[str]) -> Optional[str]:
            for k in keys:
                for rk, rv in raw.items():
                    if k in rk.lower():
                        return str(rv).strip()
            return None

        def find_bool(keys: list[str], true_words: list[str]) -> bool:
            val = find_str(keys)
            if val is None:
                return False
            return any(w in val.lower() for w in true_words)

        spec: dict = {}

        if category == "gpu":
            spec["length_mm"]       = find_int(["length", "長さ", "card length"])
            spec["slot_width"]      = find_int(["slot", "スロット"])
            spec["tdp_w"]           = find_int(["tdp", "power consumption", "消費電力"])
            spec["power_connector"] = find_str(["connector", "power", "電源コネクタ"])
            spec["height_mm"]       = find_int(["height", "高さ"])
            spec["pcie_version"]    = find_str(["pcie", "pci express", "pci-e"])

        elif category == "motherboard":
            spec["socket"]              = find_str(["socket", "ソケット"])
            spec["ddr_gen"]             = find_str(["memory type", "ddr", "メモリタイプ"])
            spec["form_factor"]         = find_str(["form factor", "フォームファクタ"])
            spec["m2_slots"]            = find_int(["m.2"])
            spec["max_memory_speed_mt"] = find_int(["max memory speed", "最大メモリ速度", "oc"])

        elif category == "cpu_cooler":
            spec["height_mm"]         = find_int(["height", "高さ"])
            spec["supported_sockets"] = find_str(["socket", "compatibility", "対応ソケット"])
            spec["max_tdp_w"]         = find_int(["tdp", "power"])
            spec["side_clearance_mm"] = find_int(["clearance", "クリアランス"])

        elif category == "psu":
            spec["rated_w"]           = find_int(["wattage", "output", "定格"])
            spec["atx_version"]       = find_str(["atx", "standard"])
            spec["depth_mm"]          = find_int(["depth", "奥行き"])
            spec["has_12vhpwr"]       = find_bool(["12vhpwr", "pcie 5"], ["yes", "対応", "○"])
            spec["modular_type"]      = find_str(["modular", "モジュラー"])
            spec["efficiency_rating"] = find_str(["80plus", "efficiency", "80 plus"])

        elif category == "case":
            spec["max_gpu_length_mm"]    = find_int(["gpu length", "グラフィック", "card length"])
            spec["max_cooler_height_mm"] = find_int(["cooler height", "cpu cooler", "クーラー"])
            spec["form_factors"]         = find_str(["form factor", "motherboard", "マザーボード"])
            spec["psu_form_factor"]      = find_str(["psu", "power supply", "電源"])
            spec["front_radiator_mm"]    = find_int(["radiator", "ラジエーター", "front"])

        # None を除去
        return {k: v for k, v in spec.items() if v is not None}

    async def _upsert_bigquery(
        self,
        rows: list[ScrapeResult],
        table: str = BIGQUERY_PARTS_TABLE,
    ) -> int:
        """
        ScrapeResult リストを BigQuery テーブルに MERGE (UPSERT) する。

        Args:
            rows : アップサート対象の ScrapeResult リスト
            table: 対象テーブル名 (デフォルト: BIGQUERY_PARTS_TABLE)

        Returns:
            int: アップサートに成功した件数

        Note:
            bq_project_id が未設定の場合はログ出力して件数0を返す (テスト用)
        """
        if not self.bq_project_id:
            logger.info(
                f"[dry-run] BigQuery UPSERT スキップ: {len(rows)} 件 → {table}"
            )
            for r in rows:
                logger.debug(f"  {r.part_id}: {r.model_name}")
            return 0

        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.bq_project_id)
            dataset, tbl_name = table.split(".", 1)

            bq_rows = [
                {
                    "part_id":      r.part_id,
                    "model_name":   r.model_name,
                    "category":     r.category,
                    "manufacturer": r.manufacturer,
                    "spec_json":    json.dumps(r.spec_json, ensure_ascii=False),
                    "scraped_at":   r.scraped_at.isoformat(),
                    "source_url":   r.source_url,
                }
                for r in rows
            ]

            # streaming insert (簡易版: 本番環境では MERGE を推奨)
            errors = client.insert_rows_json(
                f"{self.bq_project_id}.{dataset}.{tbl_name}",
                bq_rows,
            )
            if errors:
                logger.error(f"BigQuery insert エラー: {errors}")
                return len(rows) - len(errors)

            logger.info(f"BigQuery UPSERT 完了: {len(rows)} 件 → {table}")
            return len(rows)

        except ImportError:
            logger.warning("google-cloud-bigquery 未インストール: UPSERT スキップ")
            return 0
        except Exception as e:
            logger.error(f"BigQuery UPSERT エラー: {e}")
            return 0

    # ------------------------------------------------------------------
    # Browser ライフサイクル
    # ------------------------------------------------------------------

    async def _start_browser(self) -> None:
        """Playwright Chromium Browser を起動する"""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            logger.info("Playwright Browser 起動完了")
        except ImportError:
            logger.error("playwright 未インストール: pip install playwright && playwright install chromium")
            self._browser = None
        except Exception as e:
            logger.error(f"Browser 起動エラー: {e}")
            self._browser = None

    async def _close_browser(self) -> None:
        """Playwright Browser を終了する"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.debug("Playwright Browser 終了")
