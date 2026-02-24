"""
ツール基底クラスとデータモデル
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import json


class ToolType(str, Enum):
    """ツール種別"""
    BIGQUERY = "bigquery"
    PAGEINDEX = "pageindex"
    VECTOR_DB = "vector_db"


class StepStatus(str, Enum):
    """検索ステップのステータス"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INSUFFICIENT = "insufficient"  # 情報不足


@dataclass
class SearchStep:
    """検索計画の1ステップ"""
    step_id: int
    tool: ToolType
    description: str  # 何を検索するかの説明
    query: str  # 実際の検索クエリ（SQL, キーワード等）
    params: dict = field(default_factory=dict)  # ツール固有のパラメータ
    depends_on: list[int] = field(default_factory=list)  # 依存ステップID
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool": self.tool.value,
            "description": self.description,
            "query": self.query,
            "params": self.params,
            "depends_on": self.depends_on,
        }


@dataclass
class SearchPlan:
    """検索計画全体"""
    original_query: str
    reasoning: str  # LLMの推論過程
    steps: list[SearchStep]
    detected_category: Optional[str] = None  # 建材カテゴリ
    detected_pattern: Optional[str] = None  # クエリパターン
    attempt: int = 1  # 何回目の計画か

    def to_dict(self) -> dict:
        return {
            "original_query": self.original_query,
            "reasoning": self.reasoning,
            "detected_category": self.detected_category,
            "detected_pattern": self.detected_pattern,
            "attempt": self.attempt,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


@dataclass
class SearchResult:
    """1ステップの検索結果"""
    step_id: int
    tool: ToolType
    data: Any  # 検索結果データ
    source: str  # 出典情報
    confidence: float = 1.0  # 信頼度 0-1
    page_refs: list[str] = field(default_factory=list)  # ページ参照

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool": self.tool.value,
            "data": str(self.data) if not isinstance(self.data, (str, dict, list)) else self.data,
            "source": self.source,
            "confidence": self.confidence,
            "page_refs": self.page_refs,
        }


@dataclass
class ValidationResult:
    """検証結果"""
    is_sufficient: bool
    reasoning: str
    missing_info: list[str] = field(default_factory=list)
    suggested_steps: list[dict] = field(default_factory=list)  # 追加検索の提案
    final_answer: Optional[str] = None


class BaseTool(ABC):
    """ツール基底クラス"""

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def execute(self, query: str, params: dict = None) -> SearchResult:
        """検索実行"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """接続確認"""
        pass
