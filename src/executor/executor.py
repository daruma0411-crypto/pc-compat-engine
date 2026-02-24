"""
Executor: 並列ツール実行エンジン
================================
Plannerの計画に従って、各ツールを
並列/逐次で実行し、結果を集約する。
"""
import asyncio
import logging
import time
from typing import Optional

from ..tools.base import SearchPlan, SearchStep, SearchResult, StepStatus, ToolType
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class Executor:
    """検索計画の実行エンジン"""

    def __init__(self, registry: ToolRegistry, parallel: bool = True):
        self.registry = registry
        self.parallel = parallel

    async def execute_plan(self, plan: SearchPlan) -> list[SearchResult]:
        """検索計画を実行"""
        results: list[SearchResult] = []
        completed_steps: dict[int, SearchResult] = {}

        if self.parallel:
            results = await self._execute_parallel(plan, completed_steps)
        else:
            results = await self._execute_sequential(plan, completed_steps)

        return results

    async def _execute_parallel(
        self, plan: SearchPlan, completed_steps: dict[int, SearchResult]
    ) -> list[SearchResult]:
        """依存関係を考慮した並列実行"""
        results = []
        remaining = list(plan.steps)
        max_iterations = len(remaining) + 1  # 無限ループ防止

        iteration = 0
        while remaining and iteration < max_iterations:
            iteration += 1

            # 実行可能なステップを抽出（依存が全て完了）
            executable = []
            still_waiting = []

            for step in remaining:
                deps_met = all(
                    dep_id in completed_steps for dep_id in step.depends_on
                )
                if deps_met:
                    executable.append(step)
                else:
                    still_waiting.append(step)

            if not executable:
                logger.warning(f"No executable steps found. Remaining: {[s.step_id for s in remaining]}")
                break

            # 並列実行
            logger.info(f"Executing {len(executable)} steps in parallel: {[s.step_id for s in executable]}")
            tasks = [
                self._execute_step(step, completed_steps) for step in executable
            ]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)

            for step, result in zip(executable, step_results):
                if isinstance(result, Exception):
                    logger.error(f"Step {step.step_id} failed: {result}")
                    step.status = StepStatus.FAILED
                    step.error = str(result)
                else:
                    completed_steps[step.step_id] = result
                    results.append(result)
                    step.status = StepStatus.SUCCESS

            remaining = still_waiting

        return results

    async def _execute_sequential(
        self, plan: SearchPlan, completed_steps: dict[int, SearchResult]
    ) -> list[SearchResult]:
        """逐次実行"""
        results = []
        for step in plan.steps:
            try:
                result = await self._execute_step(step, completed_steps)
                completed_steps[step.step_id] = result
                results.append(result)
                step.status = StepStatus.SUCCESS
            except Exception as e:
                logger.error(f"Step {step.step_id} failed: {e}")
                step.status = StepStatus.FAILED
                step.error = str(e)
        return results

    async def _execute_step(
        self, step: SearchStep, completed_steps: dict[int, SearchResult]
    ) -> SearchResult:
        """1ステップの実行"""
        start_time = time.time()
        step.status = StepStatus.RUNNING

        logger.info(f"  → Step {step.step_id} [{step.tool.value}]: {step.description}")

        # ツール取得
        tool = self.registry.get(step.tool)

        # 依存ステップの結果をパラメータに注入
        params = dict(step.params)
        params["step_id"] = step.step_id

        if step.depends_on:
            dep_results = {
                dep_id: completed_steps[dep_id].data
                for dep_id in step.depends_on
                if dep_id in completed_steps
            }
            params["dependency_results"] = dep_results

        # 実行
        result = await tool.execute(step.query, params)

        elapsed = time.time() - start_time
        logger.info(f"  ✓ Step {step.step_id} completed in {elapsed:.2f}s (confidence: {result.confidence})")

        step.result = result
        return result
