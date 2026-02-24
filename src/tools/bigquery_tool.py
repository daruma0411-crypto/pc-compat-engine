"""
BigQuery検索ツール
==================
構造化データ（品番・寸法・スペック）の
SQL検索を実行する。
"""
import json
import logging
from typing import Optional

from .base import BaseTool, ToolType, SearchResult

logger = logging.getLogger(__name__)


class BigQueryTool(BaseTool):
    """BigQuery構造化データ検索"""

    def __init__(self, project_id: str = "", dataset: str = "pim_catalog", credentials_path: str = None):
        self.project_id = project_id
        self.dataset = dataset
        self.credentials_path = credentials_path
        self._client = None

    @property
    def tool_type(self) -> ToolType:
        return ToolType.BIGQUERY

    @property
    def name(self) -> str:
        return "BigQuery構造化データ検索"

    @property
    def description(self) -> str:
        return "品番の完全一致・ワイルドカード検索、数値比較、スペック一覧取得。PIMデータのSQL検索。"

    def _get_client(self):
        """BigQueryクライアント取得（遅延初期化）"""
        if self._client is None:
            if not self.project_id:
                logger.info("project_id未設定のためBigQueryモックモードを使用")
                self._client = "mock"
                return self._client
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=self.project_id)
            except ImportError:
                logger.warning("google-cloud-bigquery not installed, using mock mode")
                self._client = "mock"
        return self._client

    async def execute(self, query: str, params: dict = None) -> SearchResult:
        """SQL検索実行"""
        params = params or {}
        client = self._get_client()

        if client == "mock":
            return await self._mock_execute(query, params)

        try:
            # SQLインジェクション対策: パラメータ化クエリ
            job_config = None
            if params.get("query_params"):
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter(k, "STRING", v)
                        for k, v in params["query_params"].items()
                    ]
                )

            query_job = client.query(query, job_config=job_config)
            results = query_job.result()

            rows = []
            for row in results:
                rows.append(dict(row))

            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.BIGQUERY,
                data=rows,
                source=f"BigQuery: {self.dataset}",
                confidence=1.0,  # SQLは確定的
            )

        except Exception as e:
            logger.error(f"BigQuery execution error: {e}")
            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.BIGQUERY,
                data={"error": str(e)},
                source=f"BigQuery: {self.dataset}",
                confidence=0.0,
            )

    async def _mock_execute(self, query: str, params: dict) -> SearchResult:
        """モック実行（PC互換性判定PoC用）"""
        q = query.lower()

        # PCパーツマスタデータ
        PC_PARTS = {
            "gpu": [
                {"part_id": "rtx4090", "model_name": "NVIDIA RTX 4090", "category": "gpu",
                 "manufacturer": "NVIDIA", "length_mm": 336, "slot_width": 3, "height_mm": 61,
                 "tdp_w": 450, "power_connector": "16pin_12VHPWR", "pcie_gen": 4,
                 "note_12vhpwr": "完全挿入必須。変換アダプタ非推奨。溶断事例あり。"},
                {"part_id": "rtx4080s", "model_name": "MSI GeForce RTX 4080 SUPER", "category": "gpu",
                 "manufacturer": "MSI", "length_mm": 320, "slot_width": 3, "height_mm": 59,
                 "tdp_w": 285, "power_connector": "16pin_12VHPWR", "pcie_gen": 4},
            ],
            "motherboard": [
                {"part_id": "z790e", "model_name": "ASUS ROG STRIX Z790-E", "category": "motherboard",
                 "manufacturer": "ASUS", "socket": "LGA1700", "ddr_gen": "DDR5",
                 "form_factor": "ATX", "m2_slots": 4,
                 "m2_conflict_note": "M.2_4使用時: PCIe x16(2)がx8縮退"},
                {"part_id": "z790f", "model_name": "ASUS ROG STRIX Z790-F", "category": "motherboard",
                 "manufacturer": "ASUS", "socket": "LGA1700", "ddr_gen": "DDR5",
                 "form_factor": "ATX", "m2_slots": 5,
                 "m2_conflict_note": "M.2_4: PCIe x16(2)→x8 / M.2_5: PCIe x1 #1/#2無効化"},
                {"part_id": "x670e", "model_name": "ASUS ROG Crosshair X670E Extreme", "category": "motherboard",
                 "manufacturer": "ASUS", "socket": "AM5", "ddr_gen": "DDR5",
                 "form_factor": "ATX", "m2_slots": 5,
                 "m2_conflict_note": "M.2_5使用時: PCIe x4スロット無効"},
            ],
            "cpu": [
                {"part_id": "i9_14900k", "model_name": "Intel Core i9-14900K", "category": "cpu",
                 "manufacturer": "Intel", "socket": "LGA1700", "tdp_w": 253,
                 "max_mem_gen": "DDR5", "mem_speed_max": 5600},
                {"part_id": "r9_7950x", "model_name": "AMD Ryzen 9 7950X", "category": "cpu",
                 "manufacturer": "AMD", "socket": "AM5", "tdp_w": 170,
                 "max_mem_gen": "DDR5", "mem_speed_max": 5200},
            ],
            "memory": [
                {"part_id": "cv_ddr4", "model_name": "Corsair Vengeance DDR4-3600 32GB", "category": "memory",
                 "manufacturer": "Corsair", "ddr_gen": "DDR4", "speed": 3600,
                 "capacity_gb": 32, "height_mm": 34},
                {"part_id": "gs_ddr5", "model_name": "G.Skill Trident Z5 DDR5-6000 32GB", "category": "memory",
                 "manufacturer": "G.Skill", "ddr_gen": "DDR5", "speed": 6000,
                 "capacity_gb": 32, "height_mm": 44},
            ],
            "case": [
                {"part_id": "fd_define7", "model_name": "Fractal Design Define 7", "category": "case",
                 "manufacturer": "Fractal Design", "max_gpu_length_mm": 467,
                 "max_cooler_height_mm": 185, "supported_form_factors": "E-ATX/ATX/mATX/ITX"},
                {"part_id": "fd_meshify2", "model_name": "Fractal Meshify 2", "category": "case",
                 "manufacturer": "Fractal Design", "max_gpu_length_mm": 341,
                 "max_cooler_height_mm": 185, "supported_form_factors": "E-ATX/ATX/mATX/ITX"},
                {"part_id": "nzxt_h9", "model_name": "NZXT H9 Elite", "category": "case",
                 "manufacturer": "NZXT", "max_gpu_length_mm": 430,
                 "max_cooler_height_mm": 185, "supported_form_factors": "ATX/mATX/ITX"},
            ],
            "cpu_cooler": [
                {"part_id": "nh_d15", "model_name": "Noctua NH-D15", "category": "cpu_cooler",
                 "manufacturer": "Noctua", "height_mm": 165, "max_supported_tdp_w": 250,
                 "clearance_side_mm": 62, "socket_support": "LGA1700/AM5/AM4"},
                {"part_id": "bq_drp5", "model_name": "be quiet! Dark Rock Pro 5", "category": "cpu_cooler",
                 "manufacturer": "be quiet!", "height_mm": 162, "max_supported_tdp_w": 250,
                 "clearance_side_mm": 55, "socket_support": "LGA1700/AM5/AM4"},
            ],
            "psu": [
                {"part_id": "cs_rm850x", "model_name": "Corsair RM850x", "category": "psu",
                 "manufacturer": "Corsair", "wattage": 850, "form_factor": "ATX",
                 "connector_12vhpwr": 0, "connector_8pin_pcie": 4},
                {"part_id": "ss_gx1000", "model_name": "Seasonic FOCUS GX-1000", "category": "psu",
                 "manufacturer": "Seasonic", "wattage": 1000, "form_factor": "ATX",
                 "connector_12vhpwr": 1, "connector_8pin_pcie": 4},
            ],
        }

        # カテゴリ別フィルタ
        selected: list = []
        if any(kw in q for kw in ["gpu", "4090", "4080", "rtx", "グラフィック"]):
            selected.extend(PC_PARTS["gpu"])
        if any(kw in q for kw in ["motherboard", "マザー", "z790", "x670", "mb"]):
            selected.extend(PC_PARTS["motherboard"])
        if any(kw in q for kw in ["cpu", "i9", "i7", "ryzen", "14900", "7950"]):
            selected.extend(PC_PARTS["cpu"])
        if any(kw in q for kw in ["memory", "メモリ", "ram", "ddr"]):
            selected.extend(PC_PARTS["memory"])
        if any(kw in q for kw in ["case", "ケース", "define", "meshify", "h9"]):
            selected.extend(PC_PARTS["case"])
        if any(kw in q for kw in ["cooler", "クーラー", "noctua", "nh-d15", "dark rock"]):
            selected.extend(PC_PARTS["cpu_cooler"])
        if any(kw in q for kw in ["psu", "電源", "power", "rm850", "gx-1000", "seasonic", "corsair rm"]):
            selected.extend(PC_PARTS["psu"])

        # 何も選択されなければ全カテゴリ返却
        if not selected:
            for parts in PC_PARTS.values():
                selected.extend(parts)

        return SearchResult(
            step_id=params.get("step_id", 0),
            tool=ToolType.BIGQUERY,
            data=selected,
            source="BigQuery (mock): pc_compat_catalog",
            confidence=1.0,
        )

    async def health_check(self) -> bool:
        client = self._get_client()
        if client == "mock":
            return True
        try:
            client.query("SELECT 1").result()
            return True
        except Exception:
            return False
