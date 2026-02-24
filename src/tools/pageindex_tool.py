"""
PageIndex検索ツール
====================
階層型ツリー構造でPDF文書を推論探索する。
Vectorless RAG。
"""
import json
import logging
from pathlib import Path
from typing import Optional

from .base import BaseTool, ToolType, SearchResult

logger = logging.getLogger(__name__)


class PageIndexTool(BaseTool):
    """PageIndex階層型文書検索"""

    def __init__(
        self,
        api_key: str = None,
        api_url: str = "https://api.pageindex.ai",
        local_mode: bool = True,
        tree_storage_path: str = "./data/trees",
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.local_mode = local_mode
        self.tree_storage_path = Path(tree_storage_path)
        self._trees: dict[str, dict] = {}  # document_id -> tree structure

    @property
    def tool_type(self) -> ToolType:
        return ToolType.PAGEINDEX

    @property
    def name(self) -> str:
        return "PageIndex階層型文書検索"

    @property
    def description(self) -> str:
        return "PDF文書のツリー構造を推論で探索。施工マニュアル、仕様書の文脈理解・セクション特定。"

    def load_tree(self, document_id: str, tree_data: dict):
        """ツリー構造をメモリにロード"""
        self._trees[document_id] = tree_data
        logger.info(f"Loaded tree for document: {document_id}")

    def load_tree_from_file(self, document_id: str, filepath: str):
        """ファイルからツリー構造をロード"""
        with open(filepath, "r", encoding="utf-8") as f:
            tree_data = json.load(f)
        self.load_tree(document_id, tree_data)

    async def execute(self, query: str, params: dict = None) -> SearchResult:
        """階層型文書検索実行"""
        params = params or {}
        document_id = params.get("document_id")

        if self.local_mode:
            return await self._local_execute(query, document_id, params)
        else:
            return await self._api_execute(query, document_id, params)

    async def _local_execute(self, query: str, document_id: str, params: dict) -> SearchResult:
        """ローカルモード: メモリ上のツリー構造をLLMで探索"""
        # ツリー構造を取得
        if document_id and document_id in self._trees:
            tree = self._trees[document_id]
        elif self._trees:
            # document_id未指定の場合は全ツリーを対象
            tree = {"documents": self._trees}
        else:
            # モックデータで実行
            return await self._mock_execute(query, params)

        # LLMにツリー構造を渡してノード選択させる
        # （実際のPageIndexのコアロジック）
        selected_nodes = await self._reason_over_tree(query, tree)

        return SearchResult(
            step_id=params.get("step_id", 0),
            tool=ToolType.PAGEINDEX,
            data=selected_nodes,
            source=f"PageIndex: {document_id or 'all_documents'}",
            confidence=0.85,
            page_refs=[n.get("page_range", "") for n in selected_nodes if isinstance(n, dict)],
        )

    async def _api_execute(self, query: str, document_id: str, params: dict) -> SearchResult:
        """API モード: PageIndex Cloud APIを呼び出す"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/v1/search",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "document_id": document_id,
                        "max_results": params.get("max_results", 5),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                result_data = response.json()

            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.PAGEINDEX,
                data=result_data.get("results", []),
                source=f"PageIndex API: {document_id}",
                confidence=result_data.get("confidence", 0.8),
                page_refs=result_data.get("page_refs", []),
            )

        except Exception as e:
            logger.error(f"PageIndex API error: {e}")
            return SearchResult(
                step_id=params.get("step_id", 0),
                tool=ToolType.PAGEINDEX,
                data={"error": str(e)},
                source="PageIndex API",
                confidence=0.0,
            )

    async def _reason_over_tree(self, query: str, tree: dict) -> list[dict]:
        """
        LLMでツリー構造を推論探索する。
        PageIndexのコアアルゴリズムの簡易実装。
        """
        # 本番ではここでLLMを呼び出してノード選択させる
        # prompt = f"""
        # You are given a question and a tree structure of a document.
        # You need to find all nodes that are likely to contain the answer.
        # Question: {query}
        # Document tree structure: {json.dumps(tree, ensure_ascii=False)}
        # Reply in the following JSON format:
        # {{ "thinking": <reasoning>, "node_list": [node_id1, ...] }}
        # """

        # PoC段階ではモックで返す
        return await self._mock_execute(query, {"step_id": 0})

    async def _mock_execute(self, query: str, params: dict) -> SearchResult:
        """モック実行: 朝日ウッドテックカタログのサンプル"""
        mock_tree = {
            "document_id": "asahi_woodtec_2025",
            "title": "朝日ウッドテック 総合カタログ 2025-2026",
            "total_pages": 452,
            "children": [
                {
                    "node_id": "n1",
                    "title": "住宅用 床フロア",
                    "page_range": "1-280",
                    "summary": "住宅用フローリング製品。挽き板、突き板、シートの各グレード。",
                    "children": [
                        {
                            "node_id": "n1.1",
                            "title": "ライブナチュラルプレミアム（挽き板）",
                            "page_range": "10-85",
                            "summary": "最高グレード。天然木挽き板仕上げ。グッドデザイン賞受賞。",
                            "children": [
                                {
                                    "node_id": "n1.1.1",
                                    "title": "STANDARD",
                                    "page_range": "12-55",
                                    "summary": "定番の樹種ラインナップ。ブラックウォルナット、オーク、チェリー等。",
                                },
                                {
                                    "node_id": "n1.1.2",
                                    "title": "SELECT",
                                    "page_range": "56-75",
                                    "summary": "希少樹種のセレクション。",
                                },
                                {
                                    "node_id": "n1.1.3",
                                    "title": "施工仕様・注意事項",
                                    "page_range": "76-85",
                                    "summary": "施工方法、下地条件、床暖房対応、メンテナンス方法。",
                                },
                            ],
                        },
                        {
                            "node_id": "n1.2",
                            "title": "ライブナチュラル（突き板）",
                            "page_range": "86-160",
                            "summary": "スタンダードグレード。突き板仕上げ。",
                        },
                        {
                            "node_id": "n1.3",
                            "title": "エアリス（カラーフロア系）",
                            "page_range": "161-210",
                            "summary": "カラーバリエーション重視のフローリング。",
                        },
                        {
                            "node_id": "n1.4",
                            "title": "アネックス（シート）",
                            "page_range": "211-250",
                            "summary": "シート仕上げのエコノミーライン。",
                        },
                    ],
                },
                {
                    "node_id": "n2",
                    "title": "非住宅用フローリング",
                    "page_range": "281-320",
                    "summary": "公共施設、商業施設、宿泊施設向け。土足対応、高耐久。",
                },
                {
                    "node_id": "n3",
                    "title": "壁・天井材",
                    "page_range": "321-360",
                    "summary": "天然木の壁材、天井材。不燃認定品あり。",
                },
                {
                    "node_id": "n4",
                    "title": "階段・手摺",
                    "page_range": "361-390",
                    "summary": "階段材、手摺。フローリングとのコーディネート。",
                },
                {
                    "node_id": "n5",
                    "title": "適合部材一覧・仕様表",
                    "page_range": "400-440",
                    "summary": "巾木、框、見切り材の適合一覧。床材仕様・価格帯一覧表。",
                    "children": [
                        {
                            "node_id": "n5.1",
                            "title": "巾木・框 適合表",
                            "page_range": "400-415",
                            "summary": "各フローリングシリーズに対応する巾木・框の品番一覧。",
                        },
                        {
                            "node_id": "n5.2",
                            "title": "床材仕様・価格帯一覧表",
                            "page_range": "416-435",
                            "summary": "全製品の寸法、仕様、価格帯を一覧形式で記載。",
                        },
                        {
                            "node_id": "n5.3",
                            "title": "認定・試験データ",
                            "page_range": "436-440",
                            "summary": "不燃認定番号、JIS規格、ホルムアルデヒド等級一覧。",
                        },
                    ],
                },
            ],
        }

        # クエリに基づくノード選択（簡易版）
        query_lower = query.lower()
        selected = []

        if any(kw in query for kw in ["施工", "設置", "工法", "下地"]):
            selected.append({
                "node_id": "n1.1.3",
                "title": "施工仕様・注意事項",
                "page_range": "76-85",
                "content_summary": "ライブナチュラルプレミアムの施工方法、下地条件、"
                                   "床暖房使用時の注意事項、接着剤の指定、メンテナンス方法を記載。"
                                   "直貼り工法はCH接着剤を使用。釘打ち工法は根太間隔303mm以下。",
                "reasoning": "施工に関する質問のため、施工仕様セクションを選択",
            })

        if any(kw in query for kw in ["巾木", "框", "適合", "部材"]):
            selected.append({
                "node_id": "n5.1",
                "title": "巾木・框 適合表",
                "page_range": "400-415",
                "content_summary": "各フローリングシリーズごとに対応する巾木・框の品番を一覧で記載。"
                                   "ライブナチュラルプレミアムは専用巾木SB-xxx、専用框FK-xxxが対応。",
                "reasoning": "適合部材の質問のため、巾木・框適合表セクションを選択",
            })

        if any(kw in query for kw in ["仕様", "寸法", "価格", "一覧", "スペック"]):
            selected.append({
                "node_id": "n5.2",
                "title": "床材仕様・価格帯一覧表",
                "page_range": "416-435",
                "content_summary": "全製品の品番、寸法（幅×厚さ×長さ）、基材、表面仕上げ、"
                                   "対応工法、遮音等級、床暖房対応、価格帯を一覧形式で記載。",
                "reasoning": "仕様一覧の質問のため、床材仕様表セクションを選択",
            })

        if any(kw in query for kw in ["ライブナチュラル", "プレミアム", "挽き板"]):
            selected.append({
                "node_id": "n1.1",
                "title": "ライブナチュラルプレミアム（挽き板）",
                "page_range": "10-85",
                "content_summary": "最高グレードの挽き板フローリング。天然木2mm厚挽き板を使用。"
                                   "STANDARD（定番樹種12種）とSELECT（希少樹種）の2グレード。"
                                   "全製品床暖房対応。遮音等級LL-45。",
                "reasoning": "ライブナチュラルプレミアムについての質問のため",
            })

        if any(kw in query for kw in ["水回り", "耐水", "防水", "キッチン", "洗面"]):
            selected.append({
                "node_id": "n1.1.3",
                "title": "施工仕様・注意事項",
                "page_range": "76-85",
                "content_summary": "⚠️ 水回り使用に関する注意: 天然木フローリングは水濡れに弱い。"
                                   "キッチン・洗面所での使用は防水マットの併用を推奨。"
                                   "水をこぼした場合は速やかに拭き取ること。保証対象外となる場合あり。",
                "reasoning": "水回り使用に関する質問のため、施工注意事項セクションを選択",
            })

        if not selected:
            # デフォルト: ツリー全体の概要を返す
            selected.append({
                "node_id": "root",
                "title": mock_tree["title"],
                "page_range": f"1-{mock_tree['total_pages']}",
                "content_summary": "朝日ウッドテック総合カタログ。住宅用床フロア、非住宅用フローリング、"
                                   "壁天井材、階段手摺、適合部材一覧を収録。452ページ。",
                "tree_structure": mock_tree,
                "reasoning": "特定セクションが特定できないため、文書全体の概要を返す",
            })

        return SearchResult(
            step_id=params.get("step_id", 0),
            tool=ToolType.PAGEINDEX,
            data=selected,
            source="PageIndex (mock): asahi_woodtec_2025",
            confidence=0.85,
            page_refs=[n.get("page_range", "") for n in selected],
        )

    async def health_check(self) -> bool:
        return True
