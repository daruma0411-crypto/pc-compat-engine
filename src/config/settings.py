"""設定管理"""
from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class LLMConfig:
    """LLM設定"""
    provider: str = "anthropic"  # "anthropic" or "openai"
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.0  # 計画・検証は確定的に

    def __post_init__(self):
        if self.api_key is None:
            if self.provider == "anthropic":
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
            else:
                self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class BigQueryConfig:
    """BigQuery設定"""
    project_id: str = ""
    dataset: str = "pim_catalog"
    credentials_path: Optional[str] = None

    def __post_init__(self):
        self.project_id = self.project_id or os.getenv("GCP_PROJECT_ID", "")
        self.credentials_path = self.credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


@dataclass
class PageIndexConfig:
    """PageIndex設定"""
    api_key: Optional[str] = None
    api_url: str = "https://api.pageindex.ai"
    # ローカルモードの場合
    local_mode: bool = True
    tree_storage_path: str = "./data/trees"

    def __post_init__(self):
        self.api_key = self.api_key or os.getenv("PAGEINDEX_API_KEY")


@dataclass
class VectorDBConfig:
    """Vector DB設定"""
    provider: str = "chroma"  # "chroma", "pinecone", "vertex_ai"
    collection_name: str = "building_materials_faq"
    persist_directory: str = "./data/vectordb"
    embedding_model: str = "text-embedding-3-small"


@dataclass
class EngineConfig:
    """エンジン全体設定"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    bigquery: BigQueryConfig = field(default_factory=BigQueryConfig)
    pageindex: PageIndexConfig = field(default_factory=PageIndexConfig)
    vectordb: VectorDBConfig = field(default_factory=VectorDBConfig)
    max_replan_attempts: int = 2  # 再計画の最大試行回数
    parallel_execution: bool = True  # ツール並列実行
    verbose: bool = True  # デバッグ出力
    use_mock: bool = False  # Trueにするとすべての外部API呼び出しをモックに切り替え
