"""
朝日ウッドテック PoC デモ
==========================
Plan-and-Execute RAGエンジンの動作デモ。
モックデータを使用して、建材カタログの
質問応答フローを実演する。
"""
import asyncio
import json
import logging
import sys
import os

# パスを通す
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import EngineConfig, LLMConfig
from src.main import PIMRAGEngine


# サンプルクエリ集
DEMO_QUERIES = [
    {
        "query": "ライブナチュラルプレミアムの寸法一覧を教えて",
        "description": "スペック検索（BigQuery主体）",
        "expected_tools": ["bigquery"],
    },
    {
        "query": "ライブナチュラルプレミアム ブラックウォルナットを水回りに使えるか？",
        "description": "使用可否判定（BigQuery + PageIndex + VectorDB）",
        "expected_tools": ["bigquery", "pageindex", "vector_db"],
    },
    {
        "query": "ブラックウォルナットの床材に合う巾木の品番を教えて",
        "description": "適合部材検索（BigQuery リレーション + PageIndex 適合表）",
        "expected_tools": ["bigquery", "pageindex"],
    },
    {
        "query": "このカタログのシリーズ構成とER図を分析して",
        "description": "PIM化分析（PageIndex構造分析）",
        "expected_tools": ["pageindex"],
    },
    {
        "query": "ライブナチュラルプレミアムの施工時の注意点は？",
        "description": "施工ガイド（PageIndex マニュアル探索）",
        "expected_tools": ["pageindex"],
    },
]


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🏗️  PIM-RAG Engine: Plan-and-Execute Demo                 ║
║   建材カタログ × AI検索基盤                                  ║
║                                                              ║
║   対象: 朝日ウッドテック 総合カタログ 2025-2026              ║
║   ツール: BigQuery + PageIndex + Vector DB                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def print_section(title: str, content: str = ""):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")
    if content:
        print(content)


async def run_single_query(engine: PIMRAGEngine, query_info: dict):
    """1つのクエリを実行して結果を表示"""
    print_section(
        f"🔍 {query_info['description']}",
        f"   質問: {query_info['query']}\n"
        f"   期待ツール: {', '.join(query_info['expected_tools'])}"
    )

    response = await engine.query(query_info["query"])

    # 計画の表示
    if response.plans:
        plan = response.plans[0]
        print(f"\n  📋 検索計画:")
        print(f"     推論: {plan.get('reasoning', 'N/A')[:100]}...")
        print(f"     カテゴリ: {plan.get('detected_category', 'N/A')}")
        print(f"     パターン: {plan.get('detected_pattern', 'N/A')}")
        for step in plan.get("steps", []):
            print(f"     Step {step['step_id']}: [{step['tool']}] {step['description']}")

    # 結果の表示
    print(f"\n  ⚡ 検索結果:")
    for r in response.results:
        tool = r.get("tool", "unknown")
        source = r.get("source", "N/A")
        confidence = r.get("confidence", 0)
        data = r.get("data", {})
        data_preview = json.dumps(data, ensure_ascii=False)[:200]
        print(f"     [{tool}] (信頼度: {confidence}) {source}")
        print(f"       → {data_preview}...")

    # 最終回答
    print(f"\n  📝 最終回答:")
    print(f"  {'-'*50}")
    for line in response.answer.split("\n"):
        print(f"  {line}")
    print(f"  {'-'*50}")
    print(f"  📊 {response.total_steps}ステップ, {response.total_attempts}回試行, {response.elapsed_seconds:.2f}秒")

    return response


async def run_demo():
    """デモ実行"""
    print_banner()

    # エンジン初期化（モックモード）
    config = EngineConfig(
        llm=LLMConfig(provider="anthropic"),  # API keyがなければモックにフォールバック
        verbose=False,  # デモ中は詳細ログを抑制
    )
    engine = PIMRAGEngine(config)

    # ヘルスチェック
    health = await engine.health_check()
    print(f"🏥 ツールヘルスチェック: {json.dumps(health)}")

    # 全クエリを実行
    results = []
    for i, query_info in enumerate(DEMO_QUERIES, 1):
        print(f"\n{'═'*60}")
        print(f"  Demo {i}/{len(DEMO_QUERIES)}")
        print(f"{'═'*60}")

        response = await run_single_query(engine, query_info)
        results.append(response)

    # サマリー
    print_section("📊 デモサマリー")
    for i, (qi, resp) in enumerate(zip(DEMO_QUERIES, results), 1):
        print(f"  {i}. {qi['description']}: {resp.total_steps}ステップ, {resp.elapsed_seconds:.2f}秒")

    total_time = sum(r.elapsed_seconds for r in results)
    total_steps = sum(r.total_steps for r in results)
    print(f"\n  合計: {total_steps}ステップ, {total_time:.2f}秒")

    print(f"\n{'═'*60}")
    print("  ✅ デモ完了！")
    print(f"{'═'*60}\n")


async def run_interactive():
    """対話モード"""
    print_banner()
    print("  💬 対話モード - 質問を入力してください（'quit'で終了）\n")

    config = EngineConfig(
        llm=LLMConfig(provider="anthropic"),
        verbose=True,
    )
    engine = PIMRAGEngine(config)

    while True:
        try:
            query = input("\n🔍 質問: ").strip()
            if query.lower() in ("quit", "exit", "q"):
                print("👋 終了します")
                break
            if not query:
                continue

            response = await engine.query(query)
            print(f"\n📝 回答:\n{response.answer}")
            print(f"\n📊 {response.total_steps}ステップ, {response.elapsed_seconds:.2f}秒")

        except KeyboardInterrupt:
            print("\n👋 終了します")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if "--interactive" in sys.argv or "-i" in sys.argv:
        asyncio.run(run_interactive())
    else:
        asyncio.run(run_demo())
