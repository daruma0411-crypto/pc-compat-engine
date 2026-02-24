"""
Vector DB検索ツール
====================
FAQ、過去問い合わせ、チャット履歴の
意味的類似度検索。
"""
import json
import logging
from typing import Optional

from .base import BaseTool, ToolType, SearchResult

logger = logging.getLogger(__name__)


class VectorDBTool(BaseTool):
    """ベクトル類似度検索"""

    def __init__(
        self,
        provider: str = "chroma",
        collection_name: str = "building_materials_faq",
        persist_directory: str = "./data/vectordb",
    ):
        self.provider = provider
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._collection = None

    @property
    def tool_type(self) -> ToolType:
        return ToolType.VECTOR_DB

    @property
    def name(self) -> str:
        return "Vector DB意味検索"

    @property
    def description(self) -> str:
        return "FAQ、過去問い合わせ、メモの意味的類似度検索。曖昧なキーワードに強い。"

    def _get_collection(self):
        """Chromaコレクション取得（遅延初期化）"""
        if self._collection is None:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=self.persist_directory)
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                )
            except ImportError:
                logger.warning("chromadb not installed, using mock mode")
                self._collection = "mock"
        return self._collection

    async def execute(self, query: str, params: dict = None) -> SearchResult:
        """ベクトル検索実行"""
        params = params or {}
        collection = self._get_collection()

        if collection == "mock":
            return await self._mock_execute(query, params)

        try:
            results = collection.query(
                query_texts=[query],
                n_results=params.get("n_results", 5),
            )

            formatted = []
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })

            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.VECTOR_DB,
                data=formatted,
                source=f"VectorDB: {self.collection_name}",
                confidence=0.7,
            )

        except Exception as e:
            logger.error(f"Vector DB error: {e}")
            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.VECTOR_DB,
                data={"error": str(e)},
                source=f"VectorDB: {self.collection_name}",
                confidence=0.0,
            )

    async def add_documents(self, documents: list[dict]):
        """ドキュメント追加"""
        collection = self._get_collection()
        if collection == "mock":
            logger.info(f"Mock: Would add {len(documents)} documents")
            return

        collection.add(
            documents=[d["content"] for d in documents],
            metadatas=[d.get("metadata", {}) for d in documents],
            ids=[d["id"] for d in documents],
        )

    async def _mock_execute(self, query: str, params: dict) -> SearchResult:
        """モック実行: 建材FAQサンプル"""
        mock_faq = [
            {
                "content": "Q: フローリングの床鳴りが気になります。原因は？\n"
                           "A: 床鳴りの主な原因は①下地の不陸②接着剤の劣化③湿度変化による木材の伸縮です。"
                           "施工後1年以内であれば施工業者にご相談ください。",
                "metadata": {"category": "troubleshooting", "manufacturer": "一般"},
                "distance": 0.3,
            },
            {
                "content": "Q: 天然木フローリングを水回りに使用できますか？\n"
                           "A: 推奨しません。天然木は水分により膨張・変色のリスクがあります。"
                           "やむを得ず使用する場合は防水マットを必ず敷いてください。"
                           "なお、水濡れによる損傷は保証対象外です。",
                "metadata": {"category": "usability", "manufacturer": "一般"},
                "distance": 0.25,
            },
            {
                "content": "Q: 床暖房対応のフローリングで注意することは？\n"
                           "A: 床面温度は27℃以下に設定してください。"
                           "急激な温度変化は隙間や反りの原因になります。"
                           "必ず「床暖房対応」と明記された製品をご使用ください。",
                "metadata": {"category": "installation", "manufacturer": "一般"},
                "distance": 0.35,
            },
        ]

        # クエリに基づく簡易フィルタ
        query_lower = query.lower()
        if "水回り" in query or "耐水" in query:
            selected = [f for f in mock_faq if "水" in f["content"]]
        elif "床鳴り" in query:
            selected = [f for f in mock_faq if "床鳴り" in f["content"]]
        elif "床暖" in query:
            selected = [f for f in mock_faq if "床暖" in f["content"]]
        else:
            selected = mock_faq[:2]

        return SearchResult(
            step_id=params.get("step_id", 0),
            tool=ToolType.VECTOR_DB,
            data=selected,
            source="VectorDB (mock): building_materials_faq",
            confidence=0.7,
        )

    async def health_check(self) -> bool:
        collection = self._get_collection()
        return collection is not None
