"""
PIM-RAG Engine: メインオーケストレーター
=========================================
Plan → Execute → Validate → (Re-Plan) の
フルループを管理する。
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .config.settings import EngineConfig
from .planner.planner import Planner
from .executor.executor import Executor
from .executor.registry import ToolRegistry
from .validator.validator import Validator
from .tools.base import SearchPlan, SearchResult, ToolType
from .tools.bigquery_tool import BigQueryTool
from .tools.pageindex_tool import PageIndexTool
from .tools.vector_tool import VectorDBTool

logger = logging.getLogger(__name__)


@dataclass
class EngineResponse:
    """エンジンの最終レスポンス"""
    query: str
    answer: str
    plans: list[dict] = field(default_factory=list)  # 全計画履歴
    results: list[dict] = field(default_factory=list)  # 全検索結果
    total_steps: int = 0
    total_attempts: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "metadata": {
                "total_steps": self.total_steps,
                "total_attempts": self.total_attempts,
                "elapsed_seconds": round(self.elapsed_seconds, 2),
            },
            "plans": self.plans,
            "results": self.results,
        }

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class PIMRAGEngine:
    """
    Plan-and-Execute RAGエンジン

    Usage:
        engine = PIMRAGEngine()
        response = await engine.query("ライブナチュラルプレミアムの寸法一覧を教えて")
        print(response.answer)
    """

    def __init__(self, config: EngineConfig = None):
        self.config = config or EngineConfig()

        # コンポーネント初期化
        self.registry = ToolRegistry()
        self.planner = Planner(self.config)
        self.executor = Executor(self.registry, parallel=self.config.parallel_execution)
        self.validator = Validator(self.config)

        # デフォルトツール登録
        self._register_default_tools()

    def _register_default_tools(self):
        """デフォルトのツールを登録"""
        # BigQuery
        bq_tool = BigQueryTool(
            project_id=self.config.bigquery.project_id,
            dataset=self.config.bigquery.dataset,
        )
        self.registry.register(bq_tool)

        # PageIndex
        pi_tool = PageIndexTool(
            api_key=self.config.pageindex.api_key,
            local_mode=self.config.pageindex.local_mode,
            tree_storage_path=self.config.pageindex.tree_storage_path,
        )
        self.registry.register(pi_tool)

        # Vector DB
        vdb_tool = VectorDBTool(
            provider=self.config.vectordb.provider,
            collection_name=self.config.vectordb.collection_name,
            persist_directory=self.config.vectordb.persist_directory,
        )
        self.registry.register(vdb_tool)

    async def query(self, user_query: str) -> EngineResponse:
        """
        メインクエリ実行

        1. Plan: 検索計画を生成
        2. Execute: ツールを並列実行
        3. Validate: 結果を検証
        4. Re-Plan: 情報不足なら再計画（最大N回）
        5. Synthesize: 最終回答を生成
        """
        start_time = time.time()
        all_plans = []
        all_results = []
        total_steps = 0

        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Query: {user_query}")
        logger.info(f"{'='*60}")

        # === Phase 1: Plan ===
        logger.info("\n📋 Phase 1: 検索計画の生成...")
        plan = await self.planner.create_plan(user_query)
        all_plans.append(plan.to_dict())

        for attempt in range(1, self.config.max_replan_attempts + 2):
            # === Phase 2: Execute ===
            logger.info(f"\n⚡ Phase 2: 検索実行 (Attempt {attempt})...")
            results = await self.executor.execute_plan(plan)
            all_results.extend([r.to_dict() for r in results])
            total_steps += len(plan.steps)

            # === Phase 3: Validate ===
            logger.info(f"\n✅ Phase 3: 結果検証...")
            validation = await self.validator.validate(user_query, results)

            if validation.is_sufficient:
                logger.info("  → 情報十分！最終回答を生成します。")

                # 最終回答の生成
                if validation.final_answer:
                    answer = validation.final_answer
                else:
                    answer = await self.validator.synthesize(user_query, results)

                elapsed = time.time() - start_time
                logger.info(f"\n{'='*60}")
                logger.info(f"✨ 完了: {elapsed:.2f}秒, {total_steps}ステップ, {attempt}回試行")
                logger.info(f"{'='*60}")

                return EngineResponse(
                    query=user_query,
                    answer=answer,
                    plans=all_plans,
                    results=all_results,
                    total_steps=total_steps,
                    total_attempts=attempt,
                    elapsed_seconds=elapsed,
                )

            # === Phase 4: Re-Plan ===
            if attempt <= self.config.max_replan_attempts:
                logger.info(f"\n🔄 Phase 4: 情報不足のため再計画 (不足: {validation.missing_info})")
                plan = await self.planner.replan(
                    original_plan=plan,
                    missing_info=validation.missing_info,
                    previous_results=[r.to_dict() for r in results],
                )
                all_plans.append(plan.to_dict())
            else:
                logger.warning("  → 再計画上限に到達。現在の情報で回答を生成します。")

        # 再計画上限到達時: 持っている情報で最善の回答を生成
        all_search_results = []
        for r_dict in all_results:
            all_search_results.append(
                SearchResult(
                    step_id=r_dict.get("step_id", 0),
                    tool=ToolType(r_dict.get("tool", "bigquery")),
                    data=r_dict.get("data"),
                    source=r_dict.get("source", ""),
                    confidence=r_dict.get("confidence", 0.5),
                )
            )

        answer = await self.validator.synthesize(user_query, all_search_results)
        elapsed = time.time() - start_time

        return EngineResponse(
            query=user_query,
            answer=answer,
            plans=all_plans,
            results=all_results,
            total_steps=total_steps,
            total_attempts=self.config.max_replan_attempts + 1,
            elapsed_seconds=elapsed,
        )

    async def health_check(self) -> dict:
        """全ツールのヘルスチェック"""
        return await self.registry.health_check_all()


# === CLI Entry Point ===

async def main():
    """コマンドラインエントリーポイント"""
    import sys

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m src.main <query>")
        print('Example: python -m src.main "ライブナチュラルプレミアムの寸法一覧を教えて"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    engine = PIMRAGEngine()
    response = await engine.query(query)

    print(f"\n{'='*60}")
    print("📝 最終回答:")
    print(f"{'='*60}")
    print(response.answer)
    print(f"\n📊 メタデータ: {response.total_steps}ステップ, "
          f"{response.total_attempts}回試行, {response.elapsed_seconds:.2f}秒")


if __name__ == "__main__":
    asyncio.run(main())
