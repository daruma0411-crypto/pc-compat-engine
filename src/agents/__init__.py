"""
src/agents/ — PC互換性判定エージェント群
=========================================
PC互換性判定エンジンを中心に、SNS監視・返信・データ収集を
自律的に行う4つのエージェントを提供する。

エージェント構成図:
    X Stream
        ↓
    XMonitorAgent          ← X APIフィルタードストリーム監視
        ↓ DiagnosisTask
    PIMRAGEngine           ← 診断エンジン本体 (src/main.py)
        ↓ EngineResponse
    XReplyAgent            ← 280字リプライ送信 (レート制限付き)

    [独立バッチ]
    PCPartsScraperAgent    ← メーカー公式サイトからスペック収集
    ManualCollectorAgent   ← PDFマニュアル取得 → PageIndex登録
"""

from .x_monitor_agent import XMonitorAgent
from .x_reply_agent import XReplyAgent
from .scraper_agent import PCPartsScraperAgent
from .manual_collector_agent import ManualCollectorAgent

__all__ = [
    "XMonitorAgent",
    "XReplyAgent",
    "PCPartsScraperAgent",
    "ManualCollectorAgent",
]
