"""
ManualCollectorAgent — PDFマニュアル取得・PageIndex登録エージェント
=================================================================
【責務】
マザーボード・ケースなどのPDFマニュアルを公式サイトから取得し、
PageIndex ツリー構造に変換して pc_parts.page_index テーブルに登録する。
M.2排他制限・電源コネクタ仕様などの「詳細スペック」情報を診断エンジンに
提供することが主目的。

【依存】
- aiohttp                   (非同期PDF ダウンロード)
- pdfplumber                (PDF テキスト・表抽出)
- google-cloud-bigquery     (BigQuery への登録)
- src/tools/bigquery_tool.BigQueryTool
- src/tools/pageindex_tool.PageIndexTool

【データフロー】
BigQuery (parts テーブル)
  → _find_uncollected()          # マニュアル未取得のパーツ一覧
  → _find_manual_url(part_id)    # 公式サイトからPDF URLを探索
  → _download_pdf(url, part_id)  # PDFをローカルに保存
  → _extract_tree(pdf_path, part_id)  # pdfplumber でPageIndexツリー生成
  → _update_status(part_id, "done", tree_path)  # BigQuery 更新
  → PageIndexTool.register(tree) # PageIndex に登録 (診断エンジンから参照可能)

【優先度ロジック】
    マニュアルが有用なパーツカテゴリ（優先度順）:
    1. motherboard  ← M.2排他・PCIeレーン・電源フェーズ情報が重要
    2. case         ← GPU最大長・クーラー最大高の詳細値
    3. psu          ← 12VHPWRコネクタ数・ケーブル注意事項
    4. cpu_cooler   ← 対応ソケット・バックプレート干渉
    5. gpu          ← (通常スペック表で十分なためバッチ最後)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

MANUAL_DOWNLOAD_DIR: str = "data/manuals"
"""PDFダウンロード先ディレクトリ (プロジェクトルート相対)"""

PRIORITY_CATEGORIES: list[str] = [
    "motherboard",
    "case",
    "psu",
    "cpu_cooler",
    "gpu",
]
"""マニュアル収集の優先度順カテゴリリスト"""

BIGQUERY_PARTS_TABLE: str = "pc_parts.parts"
"""パーツ情報テーブル"""

BIGQUERY_PAGEINDEX_TABLE: str = "pc_parts.page_index"
"""PageIndexノード登録先テーブル"""

MANUAL_SECTION_KEYWORDS: dict[str, list[str]] = {
    "motherboard": [
        "M.2", "PCIe", "bandwidth", "slot", "memory", "DDR",
        "power connector", "ATX", "電源", "帯域", "排他", "Limitation",
        "Warning", "Caution", "Note",
    ],
    "case": [
        "GPU clearance", "graphic card", "maximum length",
        "CPU cooler height", "radiator", "fan", "取り付け",
        "Limitation", "Warning",
    ],
    "psu": [
        "12VHPWR", "cable", "connector", "ATX 3.0",
        "注意", "caution", "warning", "溶ける", "bend",
    ],
    "cpu_cooler": [
        "socket", "compatibility", "backplate",
        "height", "TDP", "対応ソケット", "clearance",
    ],
    "gpu": [
        "power requirement", "slot width", "length",
        "connector", "minimum PSU", "12VHPWR",
    ],
}
"""カテゴリ別の重要セクション検出キーワード"""

# 既知のマニュアルURLパターン
_KNOWN_MANUAL_URL_PATTERNS: dict[str, str] = {
    "ASUS":    "https://dlcdnets.asus.com/pub/ASUS/mb/{model}/{model}_e_manual.pdf",
    "MSI":     "https://download.msi.com/archive/msp_exe/{model}/User_Guide.pdf",
    "Fractal": "https://www.fractal-design.com/app/uploads/manuals/{model}_manual.pdf",
}

# ダウンロードタイムアウト (秒)
_DOWNLOAD_TIMEOUT: int = 60

# PDF 1チャンクのページ数 (TOC未検出時のフォールバック)
_FALLBACK_CHUNK_PAGES: int = 10


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class ManualTask:
    """マニュアル取得タスクの1件"""
    part_id:       str
    model_name:    str
    category:      str
    manufacturer:  str
    manual_url:    Optional[str] = None
    status:        str = "pending"   # pending|downloading|parsing|done|failed
    error_message: Optional[str] = None
    tree_path:     Optional[str] = None


@dataclass
class PageIndexNode:
    """PageIndexの1ノード"""
    node_id:         str
    title:           str
    page_range:      str
    content_summary: str
    keywords:        list[str] = field(default_factory=list)
    children:        list["PageIndexNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_id":         self.node_id,
            "title":           self.title,
            "page_range":      self.page_range,
            "content_summary": self.content_summary,
            "keywords":        self.keywords,
            "children":        [c.to_dict() for c in self.children],
        }


@dataclass
class CollectionStats:
    """実行統計"""
    total_found:      int   = 0
    total_downloaded: int   = 0
    total_parsed:     int   = 0
    total_registered: int   = 0
    total_failed:     int   = 0
    elapsed_seconds:  float = 0.0


# ---------------------------------------------------------------------------
# メインクラス
# ---------------------------------------------------------------------------

class ManualCollectorAgent:
    """
    PDFマニュアル取得・PageIndex登録エージェント

    Attributes:
        bq_project_id (str)         : BigQueryプロジェクトID
        download_dir (Path)         : PDF保存先ディレクトリ
        concurrency (int)           : 同時ダウンロード数
        _session                    : aiohttp.ClientSession (run()後に初期化)
        _semaphore                  : concurrency 制御用 asyncio.Semaphore
    """

    def __init__(
        self,
        bq_project_id: str,
        download_dir: str = MANUAL_DOWNLOAD_DIR,
        concurrency: int = 2,
    ) -> None:
        self.bq_project_id = bq_project_id
        self.download_dir  = Path(download_dir)
        self.concurrency   = concurrency
        self._session      = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    async def run(self, limit: int = 20) -> CollectionStats:
        """
        マニュアル未取得のパーツを最大 limit 件処理する。

        処理フロー:
          1. download_dir を作成 (存在しない場合)
          2. aiohttp.ClientSession を初期化
          3. _find_uncollected(limit) でタスクリストを取得
          4. 各タスクを _process_task() で処理 (concurrency 制限付き)
          5. CollectionStats を返して Session をクローズ

        Args:
            limit: 1回の実行で処理する最大パーツ件数

        Returns:
            CollectionStats: 処理件数・成功/失敗のサマリー
        """
        start_time = time.time()
        stats      = CollectionStats()
        self._semaphore = asyncio.Semaphore(self.concurrency)

        # ダウンロードディレクトリを作成
        self.download_dir.mkdir(parents=True, exist_ok=True)

        try:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                }
            )
        except ImportError:
            logger.warning("aiohttp 未インストール: PDF ダウンロードは dry-run モード")
            self._session = None

        try:
            tasks = await self._find_uncollected(limit)
            stats.total_found = len(tasks)
            logger.info(f"マニュアル未取得: {len(tasks)} 件")

            results = await asyncio.gather(
                *[self._process_task_with_semaphore(task, stats) for task in tasks],
                return_exceptions=True,
            )

            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"タスクエラー: {r}")
                    stats.total_failed += 1

        finally:
            if self._session:
                await self._session.close()

        stats.elapsed_seconds = time.time() - start_time
        logger.info(
            f"マニュアル収集完了: "
            f"取得={stats.total_downloaded}, "
            f"解析={stats.total_parsed}, "
            f"登録={stats.total_registered}, "
            f"失敗={stats.total_failed}, "
            f"{stats.elapsed_seconds:.1f}秒"
        )
        return stats

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    async def _process_task_with_semaphore(
        self, task: ManualTask, stats: CollectionStats
    ) -> None:
        """セマフォ制御付きで _process_task を実行して stats を更新"""
        async with self._semaphore:
            success = await self._process_task(task)
            if success:
                stats.total_registered += 1
            else:
                stats.total_failed += 1

    async def _find_uncollected(self, limit: int) -> list[ManualTask]:
        """
        BigQuery の parts テーブルからマニュアル未取得のパーツを取得する。

        Args:
            limit: 取得する最大件数

        Returns:
            list[ManualTask]: 優先度順のタスクリスト

        Note:
            bq_project_id が未設定の場合はモックデータを返す
        """
        if not self.bq_project_id:
            logger.info("bq_project_id 未設定: モックタスクを使用")
            return self._mock_tasks(limit)

        try:
            from google.cloud import bigquery

            client    = bigquery.Client(project=self.bq_project_id)
            priority_sql = " ".join(
                f"WHEN category = '{cat}' THEN {i}"
                for i, cat in enumerate(self._get_priority_order())
            )

            sql = f"""
                SELECT part_id, model_name, category, manufacturer
                FROM `{self.bq_project_id}.pc_parts.parts`
                WHERE manual_status IS NULL OR manual_status = 'pending'
                ORDER BY
                    CASE {priority_sql} ELSE 99 END,
                    scraped_at ASC
                LIMIT {limit}
            """

            rows = client.query(sql).result()
            tasks = [
                ManualTask(
                    part_id=row["part_id"],
                    model_name=row["model_name"],
                    category=row["category"],
                    manufacturer=row["manufacturer"],
                )
                for row in rows
            ]
            return tasks

        except ImportError:
            logger.warning("google-cloud-bigquery 未インストール: モックタスクを使用")
            return self._mock_tasks(limit)
        except Exception as e:
            logger.error(f"BigQuery クエリエラー: {e}")
            return self._mock_tasks(limit)

    def _mock_tasks(self, limit: int) -> list[ManualTask]:
        """テスト用のモックタスクリストを返す"""
        mock = [
            ManualTask(
                part_id="z790e", model_name="ASUS ROG STRIX Z790-E",
                category="motherboard", manufacturer="ASUS",
            ),
            ManualTask(
                part_id="meshify2", model_name="Fractal Design Meshify 2",
                category="case", manufacturer="Fractal",
            ),
            ManualTask(
                part_id="focus_gx_1000", model_name="Seasonic FOCUS GX-1000",
                category="psu", manufacturer="Seasonic",
            ),
        ]
        return mock[:limit]

    async def _find_manual_url(self, task: ManualTask) -> Optional[str]:
        """
        パーツの公式PDFマニュアルURLを検索する。

        Args:
            task: ManualTask インスタンス

        Returns:
            str | None: PDF URL。見つからない場合は None

        検索戦略 (順番に試行):
          1. 既知URLパターン辞書から直接取得
          2. メーカー公式サポートページをスクレイプしてPDFリンクを検索
          3. 上記失敗時は None を返してログに記録
        """
        manufacturer = task.manufacturer
        model_name   = task.model_name

        # 既知パターンから試行
        if manufacturer in _KNOWN_MANUAL_URL_PATTERNS:
            pattern   = _KNOWN_MANUAL_URL_PATTERNS[manufacturer]
            model_slug = re.sub(r"[^\w-]", "-", model_name).strip("-")
            candidate  = pattern.format(model=model_slug)

            if await self._url_exists(candidate):
                logger.info(f"既知パターンでURL発見: {candidate}")
                return candidate

        # メーカー別の検索ページURLを生成
        search_url = self._build_support_search_url(manufacturer, model_name)
        if search_url:
            found_url = await self._scrape_manual_link(search_url)
            if found_url:
                return found_url

        logger.warning(
            f"マニュアルURL未発見: {manufacturer} / {model_name}"
        )
        return None

    async def _url_exists(self, url: str) -> bool:
        """URLが存在するか HEAD リクエストで確認"""
        if self._session is None:
            return False
        try:
            async with self._session.head(url, timeout=10) as resp:
                return resp.status in (200, 302, 301)
        except Exception:
            return False

    def _build_support_search_url(
        self, manufacturer: str, model_name: str
    ) -> Optional[str]:
        """メーカー別サポートページの検索URL を生成する"""
        search_map: dict[str, str] = {
            "ASUS":    f"https://www.asus.com/jp/support/download-center/?m={model_name}",
            "MSI":     f"https://jp.msi.com/support/downloads?keyword={model_name}",
            "GIGABYTE":f"https://www.gigabyte.com/jp/support/search?k={model_name}",
            "Fractal": f"https://www.fractal-design.com/support/product-downloads/?search={model_name}",
        }
        return search_map.get(manufacturer)

    async def _scrape_manual_link(self, search_url: str) -> Optional[str]:
        """サポートページをスクレイプしてPDFリンクを探す"""
        if self._session is None:
            return None

        try:
            async with self._session.get(
                search_url, timeout=20
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text(errors="replace")

            # ".pdf" リンクを探す (マニュアル関連キーワード優先)
            pdf_links = re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, re.IGNORECASE)
            manual_kws = ["manual", "user_guide", "user-guide", "specification"]
            for link in pdf_links:
                if any(kw in link.lower() for kw in manual_kws):
                    # 相対URLを絶対URLに変換
                    if link.startswith("http"):
                        return link
                    base = re.match(r"https?://[^/]+", search_url)
                    if base:
                        return base.group() + "/" + link.lstrip("/")

        except Exception as e:
            logger.debug(f"サポートページスクレイプ失敗 ({search_url}): {e}")

        return None

    async def _download_pdf(self, url: str, part_id: str) -> Optional[str]:
        """
        PDFをダウンロードしてローカルに保存する。

        Args:
            url    : PDFのURL
            part_id: ファイル名に使用するパーツID

        Returns:
            str | None: 保存したファイルパス。失敗時は None

        Note:
            - 既存ファイルがある場合はスキップ（上書きしない）
            - タイムアウト: 60秒
            - Content-Type が application/pdf 以外の場合は警告
        """
        dest_path = self.download_dir / f"{part_id}.pdf"

        # 既存ファイルがあればスキップ
        if dest_path.exists():
            logger.info(f"PDF 既存スキップ: {dest_path}")
            return str(dest_path)

        if self._session is None:
            logger.info(f"[dry-run] PDF ダウンロードスキップ: {url}")
            return None

        try:
            async with self._session.get(
                url, timeout=_DOWNLOAD_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"PDF ダウンロード失敗 (HTTP {resp.status}): {url}")
                    return None

                content_type = resp.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower():
                    logger.warning(
                        f"Content-Type が PDF 以外: {content_type} ({url})"
                    )

                data = await resp.read()

            dest_path.write_bytes(data)
            logger.info(
                f"PDF ダウンロード完了: {dest_path} "
                f"({len(data) // 1024} KB)"
            )
            return str(dest_path)

        except asyncio.TimeoutError:
            logger.error(f"PDF ダウンロードタイムアウト: {url}")
            return None
        except Exception as e:
            logger.error(f"PDF ダウンロードエラー ({url}): {e}")
            return None

    def _extract_tree(
        self,
        pdf_path: str,
        part_id: str,
        category: str,
    ) -> Optional[PageIndexNode]:
        """
        PDFからPageIndexツリーを生成する。

        Args:
            pdf_path : ダウンロード済みPDFのパス
            part_id  : ルートノードIDに使用
            category : セクション検出キーワード選択に使用

        Returns:
            PageIndexNode | None: ルートノード (子ノード含む)。失敗時は None

        処理フロー:
          1. pdfplumber でPDFを開く
          2. 目次ページ (TOC) を検出して章タイトル・ページ番号を抽出
          3. MANUAL_SECTION_KEYWORDS[category] に一致するセクションを特定
          4. 各セクションのテキストを抽出して content_summary (200字以内) を生成
          5. PageIndexNode ツリーを構築して返す
        """
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber 未インストール: pip install pdfplumber")
            return None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF 解析開始: {pdf_path} ({total_pages} ページ)")

                # --- 目次を検出 ---
                toc = self._detect_toc(pdf)

                # --- ルートノード作成 ---
                # モデル名を1ページ目のテキストから抽出
                first_text = pdf.pages[0].extract_text() or ""
                root_title = self._extract_model_name_from_text(first_text) or part_id

                root = PageIndexNode(
                    node_id=f"{part_id}_root",
                    title=f"{root_title} マニュアル",
                    page_range=f"1-{total_pages}",
                    content_summary=first_text[:200].replace("\n", " "),
                    keywords=MANUAL_SECTION_KEYWORDS.get(category, [])[:5],
                )

                # --- セクション別ノードを生成 ---
                section_kws = MANUAL_SECTION_KEYWORDS.get(category, [])

                if toc:
                    # TOC ベースでセクションを作成
                    root.children = self._build_toc_nodes(
                        pdf, toc, part_id, section_kws, total_pages
                    )
                else:
                    # フォールバック: 10ページごとにチャンク分割
                    root.children = self._build_chunk_nodes(
                        pdf, part_id, section_kws, total_pages
                    )

                logger.info(
                    f"PageIndexツリー生成完了: "
                    f"{len(root.children)} セクション"
                )
                return root

        except Exception as e:
            logger.error(f"PDF 解析エラー ({pdf_path}): {e}")
            return None

    def _detect_toc(self, pdf) -> list[dict]:
        """
        PDFの目次ページを検出して (title, page_num) リストを返す。

        Returns:
            list[dict]: [{"title": str, "page": int}, ...]
            目次未検出時は空リスト
        """
        toc_entries: list[dict] = []

        # 最初の5ページで目次を探す
        for page_idx in range(min(5, len(pdf.pages))):
            text = pdf.pages[page_idx].extract_text() or ""

            # 目次のサインを探す: "Chapter N", "目次", "Contents" など
            if not re.search(
                r"(?:目次|Contents|Table of Contents|Chapter\s+\d+)",
                text, re.IGNORECASE
            ):
                continue

            # 行ごとにパース: "セクション名 ............. 12" の形式
            for line in text.split("\n"):
                line = line.strip()
                # 末尾の数字 = ページ番号
                m = re.search(r"^(.+?)[\s\.]{3,}(\d+)\s*$", line)
                if m:
                    title = m.group(1).strip()
                    page  = int(m.group(2))
                    if title and 1 <= page <= len(pdf.pages):
                        toc_entries.append({"title": title, "page": page})

            if toc_entries:
                logger.debug(f"目次検出: {len(toc_entries)} エントリ (page {page_idx + 1})")
                return toc_entries

        return []

    def _build_toc_nodes(
        self,
        pdf,
        toc: list[dict],
        part_id: str,
        section_kws: list[str],
        total_pages: int,
    ) -> list[PageIndexNode]:
        """目次をもとに PageIndexNode のリストを生成する"""
        nodes: list[PageIndexNode] = []

        for i, entry in enumerate(toc):
            title    = entry["title"]
            start_pg = entry["page"]
            end_pg   = toc[i + 1]["page"] - 1 if i + 1 < len(toc) else total_pages

            # セクションキーワードとの関連度チェック
            title_lower = title.lower()
            matched_kws = [
                kw for kw in section_kws
                if kw.lower() in title_lower
            ]

            # セクションのテキストを抽出 (最大3ページ)
            section_text = self._extract_section_text(pdf, start_pg, min(end_pg, start_pg + 2))
            summary      = section_text[:200].replace("\n", " ")

            # キーワードが一致したか全セクションを追加
            # (重要セクションは優先的に登録)
            title_slug = re.sub(r"[^\w]", "_", title).lower()[:30]
            node_id = f"{part_id}_{title_slug}"

            nodes.append(PageIndexNode(
                node_id=node_id,
                title=title,
                page_range=f"{start_pg}-{end_pg}",
                content_summary=summary,
                keywords=matched_kws or [title[:20]],
            ))

        return nodes

    def _build_chunk_nodes(
        self,
        pdf,
        part_id: str,
        section_kws: list[str],
        total_pages: int,
    ) -> list[PageIndexNode]:
        """目次未検出時: 10ページごとにチャンク分割して PageIndexNode を生成"""
        nodes: list[PageIndexNode] = []

        for start in range(1, total_pages + 1, _FALLBACK_CHUNK_PAGES):
            end  = min(start + _FALLBACK_CHUNK_PAGES - 1, total_pages)
            text = self._extract_section_text(pdf, start, end)

            # キーワードマッチ確認
            text_lower   = text.lower()
            matched_kws = [kw for kw in section_kws if kw.lower() in text_lower]
            if not matched_kws:
                continue  # キーワードが含まれないチャンクはスキップ

            # タイトル: テキストの1行目か "Pageのx-y" フォールバック
            first_line = text.split("\n")[0].strip()[:40] if text else ""
            title      = first_line or f"Page {start}-{end}"

            nodes.append(PageIndexNode(
                node_id=f"{part_id}_chunk_{start}_{end}",
                title=title,
                page_range=f"{start}-{end}",
                content_summary=text[:200].replace("\n", " "),
                keywords=matched_kws,
            ))

        return nodes

    def _extract_section_text(self, pdf, start_page: int, end_page: int) -> str:
        """指定ページ範囲のテキストを抽出して返す"""
        texts: list[str] = []
        for pg_num in range(start_page, min(end_page + 1, len(pdf.pages) + 1)):
            try:
                page_text = pdf.pages[pg_num - 1].extract_text() or ""
                texts.append(page_text)
            except Exception:
                pass
        return "\n".join(texts)

    def _extract_model_name_from_text(self, text: str) -> Optional[str]:
        """PDFテキストからモデル名らしい行を抽出する"""
        # 大文字英数字が多い短い行がモデル名候補
        for line in text.split("\n"):
            line = line.strip()
            if 5 < len(line) < 60 and re.search(r"[A-Z0-9]{3,}", line):
                return line
        return None

    async def _update_status(
        self,
        part_id: str,
        status: str,
        tree_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        BigQuery の parts テーブルの manual_status を更新する。

        Args:
            part_id      : 更新対象のパーツID
            status       : "pending" | "downloading" | "parsing" | "done" | "failed"
            tree_path    : 生成したツリーJSONのパス (status="done" 時)
            error_message: エラー詳細 (status="failed" 時)
        """
        logger.debug(
            f"ステータス更新: {part_id} → {status}"
            + (f" (tree={tree_path})" if tree_path else "")
            + (f" (error={error_message})" if error_message else "")
        )

        if not self.bq_project_id:
            return  # dry-run

        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.bq_project_id)

            set_clauses = [f"manual_status = '{status}'"]
            if tree_path:
                set_clauses.append(f"manual_tree_path = '{tree_path}'")
            if error_message:
                safe_err = error_message.replace("'", "\\'")[:256]
                set_clauses.append(f"manual_error = '{safe_err}'")

            sql = f"""
                UPDATE `{self.bq_project_id}.pc_parts.parts`
                SET {', '.join(set_clauses)}
                WHERE part_id = '{part_id}'
            """
            client.query(sql).result()

        except ImportError:
            pass  # 未インストール時はサイレント
        except Exception as e:
            logger.warning(f"ステータス更新エラー ({part_id}): {e}")

    def _get_priority_order(self) -> list[str]:
        """
        PRIORITY_CATEGORIES をそのまま返す。

        Returns:
            list[str]: カテゴリの優先度順リスト

        Note:
            将来的に BigQuery の stats をもとに動的に優先度を計算するために
            独立メソッドとして定義。
        """
        return PRIORITY_CATEGORIES

    async def _process_task(self, task: ManualTask) -> bool:
        """
        1件の ManualTask を end-to-end で処理する。

        処理フロー:
          1. _find_manual_url(task) → URL取得
          2. _update_status("downloading")
          3. _download_pdf(url, part_id) → ローカルパス取得
          4. _update_status("parsing")
          5. _extract_tree(pdf_path, part_id, category) → PageIndexNode
          6. tree を JSON 保存
          7. _update_status("done", tree_path)
          8. PageIndexTool.register(tree.to_dict())

        Returns:
            bool: 成功した場合 True
        """
        part_id = task.part_id
        logger.info(f"マニュアル収集開始: {task.model_name} ({task.category})")

        # 1. URL 取得
        url = await self._find_manual_url(task)
        if not url:
            await self._update_status(
                part_id, "failed",
                error_message="マニュアルURL未発見"
            )
            return False

        # 2. ダウンロード
        await self._update_status(part_id, "downloading")
        pdf_path = await self._download_pdf(url, part_id)
        if not pdf_path:
            await self._update_status(
                part_id, "failed",
                error_message=f"PDF ダウンロード失敗: {url}"
            )
            return False

        # 3. 解析
        await self._update_status(part_id, "parsing")
        tree = self._extract_tree(pdf_path, part_id, task.category)
        if not tree:
            await self._update_status(
                part_id, "failed",
                error_message="PDF 解析失敗"
            )
            return False

        # 4. ツリーを JSON 保存
        tree_path = str(self.download_dir / f"{part_id}_tree.json")
        try:
            with open(tree_path, "w", encoding="utf-8") as f:
                json.dump(tree.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ツリーJSON保存エラー ({part_id}): {e}")
            tree_path = None

        # 5. BigQuery ステータス更新
        await self._update_status(part_id, "done", tree_path=tree_path)

        # 6. PageIndex に登録 (診断エンジンから参照可能)
        try:
            from ..tools.pageindex_tool import PageIndexTool
            pi_tool = PageIndexTool(local_mode=True)
            pi_tool.register(tree.to_dict())
            logger.info(f"PageIndex 登録完了: {part_id}")
        except Exception as e:
            logger.warning(f"PageIndex 登録エラー ({part_id}): {e}")
            # PageIndex 登録失敗でも全体は success 扱い

        logger.info(
            f"マニュアル収集完了: {task.model_name} "
            f"({len(tree.children)} セクション)"
        )
        return True
