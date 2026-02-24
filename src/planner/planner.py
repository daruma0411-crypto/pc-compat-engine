"""
Planner: 検索計画生成エンジン
==============================
ユーザーの質問をLLMで分析し、
最適なツール選択と検索手順を計画する。
"""
import json
import logging
from typing import Optional

from ..config.settings import EngineConfig
from ..config.domain_rules import get_domain_prompt
from ..tools.base import SearchPlan, SearchStep, ToolType, StepStatus
from .prompts import PLANNER_SYSTEM_PROMPT, REPLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Planner:
    """検索計画生成器"""

    def __init__(self, config: EngineConfig):
        self.config = config
        self.domain_prompt = get_domain_prompt()

    async def create_plan(self, query: str) -> SearchPlan:
        """ユーザー質問から検索計画を生成"""
        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            domain_rules=self.domain_prompt
        )

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=f"以下の質問に対する検索計画を立案してください:\n\n{query}",
        )

        plan = self._parse_plan_response(response, query)

        if self.config.verbose:
            logger.info(f"検索計画生成完了: {len(plan.steps)}ステップ")
            logger.info(f"推論: {plan.reasoning}")
            for step in plan.steps:
                logger.info(f"  Step {step.step_id}: [{step.tool.value}] {step.description}")

        return plan

    async def replan(
        self,
        original_plan: SearchPlan,
        missing_info: list[str],
        previous_results: list[dict],
    ) -> SearchPlan:
        """情報不足時の再計画"""
        system_prompt = REPLANNER_SYSTEM_PROMPT.format(
            previous_plan=original_plan.to_json(),
            missing_info=json.dumps(missing_info, ensure_ascii=False),
        )

        response = await self._call_llm(
            system_prompt=system_prompt,
            user_message=(
                f"元の質問: {original_plan.original_query}\n\n"
                f"前回の検索結果サマリー:\n{json.dumps(previous_results, ensure_ascii=False, indent=2)}\n\n"
                f"不足情報を補完する追加検索計画を立案してください。"
            ),
        )

        plan = self._parse_plan_response(response, original_plan.original_query)
        plan.attempt = original_plan.attempt + 1
        return plan

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """LLM呼び出し（プロバイダー抽象化）"""
        if self.config.llm.provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_message)
        else:
            return await self._call_openai(system_prompt, user_message)

    async def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Anthropic Claude API呼び出し"""
        # モックモード or APIキー未設定 → モック使用
        if self.config.use_mock or not self.config.llm.api_key:
            logger.info("モックモードでPlanner応答を生成")
            return self._mock_response(user_message)
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.config.llm.api_key)
            response = await client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except ImportError:
            logger.warning("anthropic package not installed, falling back to mock")
            return self._mock_response(user_message)
        except Exception as e:
            logger.warning(f"Anthropic API error: {e}, falling back to mock")
            return self._mock_response(user_message)

    async def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """OpenAI API呼び出し"""
        # モックモード or APIキー未設定 → モック使用
        if self.config.use_mock or not self.config.llm.api_key:
            logger.info("モックモードでPlanner応答を生成")
            return self._mock_response(user_message)
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.config.llm.api_key)
            response = await client.chat.completions.create(
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content
        except ImportError:
            logger.warning("openai package not installed, falling back to mock")
            return self._mock_response(user_message)
        except Exception as e:
            logger.warning(f"OpenAI API error: {e}, falling back to mock")
            return self._mock_response(user_message)

    def _parse_plan_response(self, response: str, query: str) -> SearchPlan:
        """LLMレスポンスをSearchPlanにパース"""
        # JSONブロックを抽出
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nResponse: {response}")
            # フォールバック: 基本的なBigQuery検索のみ
            return SearchPlan(
                original_query=query,
                reasoning="JSONパースエラーのため、デフォルト計画を使用",
                steps=[
                    SearchStep(
                        step_id=1,
                        tool=ToolType.BIGQUERY,
                        description="製品情報の検索",
                        query=f"SELECT * FROM products WHERE name LIKE '%{query}%' LIMIT 10",
                    )
                ],
            )

        steps = []
        for s in data.get("steps", []):
            tool_type = ToolType(s["tool"])
            steps.append(
                SearchStep(
                    step_id=s["step_id"],
                    tool=tool_type,
                    description=s["description"],
                    query=s["query"],
                    params=s.get("params", {}),
                    depends_on=s.get("depends_on", []),
                )
            )

        return SearchPlan(
            original_query=query,
            reasoning=data.get("reasoning", ""),
            steps=steps,
            detected_category=data.get("detected_category"),
            detected_pattern=data.get("detected_pattern"),
        )

    def _extract_json(self, text: str) -> str:
        """テキストからJSONブロックを抽出"""
        # ```json ... ``` ブロックを探す
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        # ```  ... ``` ブロックを探す
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
        # そのままJSONとして解釈を試みる
        # { から最後の } までを抽出
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            return text[first_brace : last_brace + 1]
        return text

    def _mock_response(self, query: str) -> str:
        """PC互換性判定用モックレスポンス（パターン自動検出）"""
        q = query.upper()

        # パターン検出（優先順位高→低: multi > clearance > m2 > power > 12vhpwr > other）
        multi_part_kws = ["CPU:", "MB:", "GPU:", "RAM:", "CASE:", "COOLER:", "PSU:"]
        has_multi    = sum(1 for kw in multi_part_kws if kw in q) >= 3
        has_clearance = "クリアランス" in query or ("GPU" in q and "341" in query)
        has_m2       = "M.2" in query and ("PCIE" in q or "レーン" in query or "3本" in query or "帯域" in query)
        has_power    = ("TDP" in q or "ワット" in query or "電源容量" in query) and not has_multi
        # 12VHPWRは単独質問のみ（multi-partクエリで偶然含まれるケースを除外）
        has_12vhpwr  = "12VHPWR" in q and not has_multi and not has_power

        if has_multi:
            pattern = "build_compatibility"
            categories = ["cpu", "motherboard", "memory", "gpu", "case", "cpu_cooler", "psu"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "CPUとマザーボードのソケット・DDR世代取得",
                    "query": "SELECT model_name, category, socket, ddr_gen, form_factor FROM parts WHERE category IN ('cpu','motherboard')",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 2, "tool": "bigquery",
                    "description": "GPU長・スロット幅・補助電源取得",
                    "query": "SELECT model_name, length_mm, slot_width, tdp_w, power_connector FROM parts WHERE category='gpu'",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 3, "tool": "bigquery",
                    "description": "ケースのGPU最大長・クーラー最大高取得",
                    "query": "SELECT model_name, max_gpu_length_mm, max_cooler_height_mm, supported_form_factors FROM parts WHERE category='case'",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 4, "tool": "bigquery",
                    "description": "CPUクーラー高さ・電源容量取得",
                    "query": "SELECT model_name, category, height_mm, wattage, tdp_w FROM parts WHERE category IN ('cpu_cooler','psu','memory')",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 5, "tool": "pageindex",
                    "description": "マザーボードPDFでM.2排他制限確認",
                    "query": "M.2 PCIe bandwidth sharing 排他",
                    "params": {"section_hint": "Bandwidth Sharing"}, "depends_on": [1],
                },
            ]
        elif has_clearance:
            pattern = "physical_interference"
            categories = ["gpu", "case"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "GPU長さとケース最大GPU長取得",
                    "query": "SELECT model_name, length_mm, max_gpu_length_mm FROM parts WHERE category IN ('gpu','case')",
                    "params": {}, "depends_on": [],
                },
            ]
        elif has_m2:
            pattern = "m2_pcie_conflict"
            categories = ["motherboard"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "Z790-FのM.2スロット排他仕様取得",
                    "query": "SELECT model_name, m2_slots, m2_conflict_note FROM parts WHERE model_name LIKE '%Z790-F%'",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 2, "tool": "pageindex",
                    "description": "M.2接続によるPCIeレーン無効化を確認",
                    "query": "M.2 PCIe bandwidth sharing 排他 帯域",
                    "params": {"part_id": "z790f", "section_hint": "Bandwidth Sharing"}, "depends_on": [],
                },
            ]
        elif has_power:
            pattern = "power_budget"
            categories = ["gpu", "cpu"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "GPU TDP取得",
                    "query": "SELECT model_name, tdp_w FROM parts WHERE category='gpu' AND model_name LIKE '%4090%'",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 2, "tool": "bigquery",
                    "description": "CPU TDP取得",
                    "query": "SELECT model_name, tdp_w FROM parts WHERE category='cpu' AND model_name LIKE '%14900K%'",
                    "params": {}, "depends_on": [],
                },
            ]
        elif has_12vhpwr:
            pattern = "next_gen_warnings"
            categories = ["gpu"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "RTX 4090のGPU仕様取得（12VHPWR詳細）",
                    "query": "SELECT model_name, power_connector, tdp_w FROM parts WHERE model_name LIKE '%4090%'",
                    "params": {}, "depends_on": [],
                },
                {
                    "step_id": 2, "tool": "pageindex",
                    "description": "12VHPWRケーブル注意事項をPDFから検索",
                    "query": "12VHPWR 溶断 取り付け角度 注意",
                    "params": {"part_id": "rtx4090", "section_hint": "Warning"}, "depends_on": [],
                },
            ]
        else:
            pattern = "spec_lookup"
            categories = ["other"]
            steps = [
                {
                    "step_id": 1, "tool": "bigquery",
                    "description": "スペック検索",
                    "query": "SELECT * FROM parts LIMIT 10",
                    "params": {}, "depends_on": [],
                },
            ]

        return json.dumps(
            {
                "reasoning": f"[モック] クエリキーワードからパターン '{pattern}' を検出",
                "detected_category": categories[0] if len(categories) == 1 else "multi",
                "detected_categories": categories,
                "detected_pattern": pattern,
                "steps": steps,
            },
            ensure_ascii=False,
        )
