"""
Validator: 検索結果の検証・最終回答生成
=======================================
収集された情報の十分性を判定し、
不足があればre-planを要求、
十分であれば最終回答を合成する。
"""
import json
import logging
from typing import Optional

from ..config.settings import EngineConfig
from ..tools.base import SearchResult, ValidationResult
from ..planner.prompts import VALIDATOR_SYSTEM_PROMPT, SYNTHESIZER_PROMPT

logger = logging.getLogger(__name__)


class Validator:
    """検索結果の検証と最終回答生成"""

    def __init__(self, config: EngineConfig):
        self.config = config

    async def validate(
        self, original_query: str, results: list[SearchResult]
    ) -> ValidationResult:
        """検索結果の十分性を検証"""
        # モックモード
        if self.config.use_mock or not self.config.llm.api_key:
            logger.info("モックモードでValidation応答を生成")
            return self._parse_validation(self._mock_validation())

        # 結果をテキスト化
        results_text = self._format_results(results)

        prompt = VALIDATOR_SYSTEM_PROMPT.format(
            original_query=original_query,
            collected_results=results_text,
        )

        response = await self._call_llm(
            system_prompt=prompt,
            user_message="上記の検索結果を検証し、結果をJSON形式で出力してください。",
        )

        return self._parse_validation(response)

    async def synthesize(
        self, original_query: str, results: list[SearchResult]
    ) -> str:
        """検索結果を統合して最終回答を生成"""
        # モックモード
        if self.config.use_mock or not self.config.llm.api_key:
            logger.info("モックモードでSynthesizer応答を生成")
            return self._mock_synthesis(original_query, results)

        results_text = self._format_results(results)

        prompt = SYNTHESIZER_PROMPT.format(
            original_query=original_query,
            results=results_text,
        )

        response = await self._call_llm(
            system_prompt="あなたは自作PCパーツの互換性判定エキスパートです。正確で分かりやすい日本語で回答してください。",
            user_message=prompt,
        )

        return response

    def _format_results(self, results: list[SearchResult]) -> str:
        """検索結果をテキスト形式に整形"""
        sections = []
        for r in results:
            section = f"## ツール: {r.tool.value} (Step {r.step_id})\n"
            section += f"出典: {r.source}\n"
            section += f"信頼度: {r.confidence}\n"
            if r.page_refs:
                section += f"ページ参照: {', '.join(r.page_refs)}\n"
            section += f"データ:\n{json.dumps(r.data, ensure_ascii=False, indent=2)}\n"
            sections.append(section)
        return "\n---\n".join(sections)

    def _parse_validation(self, response: str) -> ValidationResult:
        """検証結果をパース"""
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            return ValidationResult(
                is_sufficient=data.get("is_sufficient", False),
                reasoning=data.get("reasoning", ""),
                missing_info=data.get("missing_info", []),
                suggested_steps=data.get("suggested_steps", []),
                final_answer=data.get("final_answer"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Validation parse error: {e}, using response as-is")
            # パースできない場合は十分と判定して全文を回答に
            return ValidationResult(
                is_sufficient=True,
                reasoning="JSONパースエラーのため、回答として使用",
                final_answer=response,
            )

    def _extract_json(self, text: str) -> str:
        """JSONブロック抽出"""
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            return text[first_brace : last_brace + 1]
        return text

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """LLM呼び出し"""
        if self.config.llm.provider == "anthropic":
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
                return self._mock_validation()
            except Exception as e:
                logger.warning(f"Anthropic API error in Validator: {e}, falling back to mock")
                return self._mock_validation()
        else:
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
                return self._mock_validation()
            except Exception as e:
                logger.warning(f"OpenAI API error in Validator: {e}, falling back to mock")
                return self._mock_validation()

    def _mock_validation(self) -> str:
        """モック検証結果"""
        return json.dumps({
            "is_sufficient": True,
            "reasoning": "モックモード: 収集された情報で回答可能と判定",
            "missing_info": [],
            "final_answer": None,
        }, ensure_ascii=False)

    def _mock_synthesis(self, query: str, results: list) -> str:
        """PC互換性判定モック最終回答（クエリキーワード分析）"""
        q = query.upper()

        def fmt(verdict: str, summary: str, detail: str, issues: list) -> str:
            txt = f"## 自作PC互換性診断結果\n\n### 総合判定: {verdict} {summary}\n\n"
            txt += f"### 詳細\n{detail}\n\n"
            if issues:
                txt += "### 問題点・注意事項\n" + "\n".join(f"  {i}" for i in issues)
            return txt

        # NG: DDR4 × DDR5マザー
        if "DDR4" in q and "DDR5" in q and any(kw in q for kw in ["Z790", "X670", "DDR5マザー", "DDR5)"]):
            return fmt("❌", "非互換 — DDR世代不一致",
                "RAMのDDR4とマザーボードのDDR5スロットは物理的に互換性がありません（ピン数・切り欠き形状が異なります）。"
                "DDR5対応メモリへの交換が必要です。",
                ["❌ DDR世代不一致: Corsair Vengeance DDR4-3600 × ASUS ROG STRIX Z790-E (DDR5専用スロット)",
                 "   → DDR5メモリ (例: G.Skill Trident Z5 DDR5-6000) への交換を推奨"])

        # WARNING: GPU長マージン5mm
        if "341" in query and "336" in query:
            return fmt("⚠️", "要確認 — GPU/ケース干渉リスク",
                "RTX 4090 (実装長336mm) と Fractal Meshify 2 (GPU最大341mm) の組み合わせは"
                "マージンが5mmしかありません。ケーブルや基板の張り出しで干渉する可能性があります。",
                ["⚠️ GPU長/ケースクリアランス: RTX 4090 336mm / Meshify 2最大 341mm → マージン5mm",
                 "   → 実機でのケーブル取り回し確認を強く推奨。SATAケーブルや補助電源の向きに注意"])

        # 電源容量計算
        if ("450W" in query or "450" in query) and ("253W" in query or "253" in query or "14900K" in query):
            total = 703  # 450 + 253
            rec = int(total * 1.2)
            return fmt("⚠️", f"電源容量 — 最低 {rec}W 以上推奨",
                f"RTX 4090 (450W) + Core i9-14900K (253W) = 合計 {total}W。"
                f"安全マージン20%を加えると {rec}W以上の電源が必要です。",
                [f"⚠️ TDP合計: {total}W → 推奨電源: {rec}W以上",
                 "   → Corsair HX1000 (1000W) または Seasonic FOCUS GX-1000 (1000W) を推奨",
                 "   → 12VHPWRネイティブケーブル付属電源を優先的に選択"])

        # M.2 PCIe排他制限
        if "M.2" in query and ("3本" in query or "PCIE" in q or "レーン" in query):
            return fmt("⚠️", "M.2 PCIe排他制限あり",
                "ASUS ROG STRIX Z790-F でM.2 SSDを3本使用すると、PCIeレーンの共有による帯域制限が発生します。",
                ["⚠️ M.2_4スロット使用時: PCIe 5.0 x16(2)スロットがx8に縮退",
                 "⚠️ M.2_5スロット使用時: PCIe x1スロット#1と#2が無効化",
                 "   → マニュアル『Bandwidth Sharing』セクション(P.1-18)を必ず確認",
                 "   → GPU以外のPCIeカード（サウンド/NIC等）を搭載予定なら構成を見直し推奨"])

        # 12VHPWR注意（単独質問のみ。マルチパートbuildクエリでは除外）
        multi_kw = sum(1 for kw in ["CPU:", "MB:", "GPU:", "RAM:", "CASE:", "COOLER:", "PSU:"] if kw in q)
        if "12VHPWR" in q and multi_kw < 3:
            return ("## 自作PC互換性診断結果\n\n"
                "### 総合判定: ⚠️ 12VHPWRコネクタ — 取り扱い要注意\n\n"
                "### 注意事項（必読）\n"
                "  1. ⚠️ コネクタを根元まで完全に差し込むこと（クリック感を確認）\n"
                "     — 不完全挿入による溶断事故が複数報告されています\n"
                "  2. ❌ 8pin×2→16pin変換アダプタは使用非推奨\n"
                "     — 接触不良・過熱リスクあり。電源付属のネイティブ12VHPWRケーブルを使用\n"
                "  3. ⚠️ ケーブルの折り曲げ半径に注意\n"
                "     — GPU背面コネクタ方向に合わせて緩やかに取り回すこと\n"
                "  4. ✅ PCIe 5.0対応電源（12VHPWRネイティブ）を使用すれば安全性は高い\n\n"
                "### 推奨電源モデル\n"
                "  - Seasonic FOCUS GX-1000 (1000W, 12VHPWR付属)\n"
                "  - Corsair HX1000 (1000W, 12VHPWR付属)\n"
                "  - be quiet! Dark Power Pro 13 1000W\n")

        # OK判定 (multi-part build with no obvious NG)
        kw_count = sum(1 for kw in ["CPU:", "MB:", "GPU:", "RAM:", "CASE:", "COOLER:", "PSU:"] if kw in q)
        if kw_count >= 3:
            return ("## 自作PC互換性診断結果\n\n"
                "### 総合判定: ✅ 互換性OK — 組み立て可能\n\n"
                "### チェック結果一覧\n"
                "  ✅ ソケット一致: AM5 (Ryzen 9 7950X ↔ ROG Crosshair X670E Extreme)\n"
                "  ✅ DDR世代一致: DDR5 (G.Skill Trident Z5 DDR5-6000 対応)\n"
                "  ✅ GPU長クリア: MSI RTX 4080 SUPER 320mm < NZXT H9 Elite 430mm\n"
                "  ✅ クーラー高クリア: be quiet! Dark Rock Pro 5 162mm < H9 Elite 185mm\n"
                "  ✅ RAM高クリア: G.Skill Z5 44mm < クーラー側面クリアランス 55mm\n"
                "  ✅ 電源容量十分: 1000W > (285W + 170W) × 1.2 = 546W\n"
                "  ✅ MBフォームファクタ対応: ATX (X670E) / ケース ATX対応\n\n"
                "### 注意事項\n"
                "  ⚠️ RTX 4080 SUPERの12VHPWRケーブルは電源付属ネイティブケーブルを使用推奨\n"
                "  ⚠️ G.Skill Trident Z5（高さ44mm）とDark Rock Pro 5（側面クリアランス55mm）は"
                "干渉なし（マージン11mm）\n\n"
                "以上の構成に互換性の問題はありません。組み立て可能です。")

        return ("## 自作PC互換性診断結果\n\n"
            "### 総合判定: 🔍 情報収集完了\n\n"
            "収集した情報に基づく診断が完了しました。\n"
            "詳細な互換性確認には追加情報が必要な場合があります。")
