"""
自作PC互換性判定エンジン — モックデモ
========================================
pc_domain_rules + pc_prompts に差し替え後の
Plan-and-Execute ループをモックデータで実演。

実行:
    python -m examples.pc_demo          # 全クエリデモ
    python -m examples.pc_demo -i       # 対話モード
    python -m examples.pc_demo --query "RTX 4090とケースの互換性は？"
"""
import asyncio
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows cp932 対策
if sys.stdout.encoding.lower() in ("cp932", "shift_jis", "shift-jis"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.config.settings import EngineConfig, LLMConfig
from src.main import PIMRAGEngine


# ============================================================
# PC互換性判定 サンプルクエリ
# ============================================================
DEMO_QUERIES = [
    # --- build_compatibility (全構成チェック) ---
    {
        "id": "full_build_ng",
        "description": "全構成チェック: DDR4メモリ × DDR5マザー → 即NG確認",
        "query": (
            "以下の構成で自作PCを組めるか確認してください:\n"
            "CPU: Intel Core i9-14900K (LGA1700)\n"
            "MB: ASUS ROG STRIX Z790-E (LGA1700, DDR5)\n"
            "RAM: Corsair Vengeance DDR4-3600 32GB\n"
            "GPU: NVIDIA RTX 4090 (336mm, 3スロット)\n"
            "Case: Fractal Design Define 7 (GPU最大467mm)\n"
            "Cooler: Noctua NH-D15 (全高165mm)\n"
            "PSU: Corsair RM850x (850W, ATX)"
        ),
        "expected_verdict": "NG",
        "expected_pattern": "build_compatibility",
        "expected_ng": ["DDR世代不一致: DDR4メモリ × DDR5スロット"],
    },
    {
        "id": "full_build_ok",
        "description": "全構成チェック: 正常構成 → OK確認",
        "query": (
            "以下の構成で問題ないか教えてください:\n"
            "CPU: AMD Ryzen 9 7950X (AM5, TDP 170W)\n"
            "MB: ASUS ROG Crosshair X670E Extreme (AM5, DDR5)\n"
            "RAM: G.Skill Trident Z5 DDR5-6000 32GB (高さ44mm)\n"
            "GPU: MSI GeForce RTX 4080 SUPER (320mm, 3スロット, TDP 285W)\n"
            "Case: NZXT H9 Elite (GPU最大430mm, クーラー最大185mm)\n"
            "Cooler: be quiet! Dark Rock Pro 5 (全高162mm, 側面クリアランス55mm)\n"
            "PSU: Seasonic FOCUS GX-1000 (1000W, ATX, 12VHPWR対応)"
        ),
        "expected_verdict": "OK",
        "expected_pattern": "build_compatibility",
        "expected_ok": ["ソケット一致(AM5)", "DDR5一致", "GPU長クリア", "電源容量十分"],
    },
    # --- physical_interference (物理干渉) ---
    {
        "id": "gpu_case_margin_warn",
        "description": "物理干渉: GPU長とケースのマージン確認",
        "query": (
            "RTX 4090（実装長336mm）をFractal Meshify 2（GPU最大341mm）に"
            "搭載する場合のクリアランスを教えてください。"
        ),
        "expected_verdict": "WARNING",
        "expected_pattern": "physical_interference",
    },
    # --- m2_pcie_conflict (M.2排他制限) ---
    {
        "id": "m2_bandwidth_conflict",
        "description": "M.2排他制限: Z790マザーでM.2を3本使う場合の影響",
        "query": (
            "ASUS ROG STRIX Z790-F でM.2 SSDを3本搭載したいです。"
            "PCIeレーンへの影響を教えてください。"
        ),
        "expected_pattern": "m2_pcie_conflict",
    },
    # --- power_budget (電源容量) ---
    {
        "id": "power_calculation",
        "description": "電源容量計算: RTX 4090 + i9-14900K の必要ワット数",
        "query": (
            "RTX 4090（TDP 450W）とCore i9-14900K（TDP 253W）の組み合わせに"
            "必要な電源容量を教えてください。"
        ),
        "expected_pattern": "power_budget",
    },
    # --- next_gen_warnings (新規格注意) ---
    {
        "id": "12vhpwr_warning",
        "description": "新規格警告: 12VHPWRケーブルの使用上の注意",
        "query": "RTX 4090の12VHPWRコネクタを使う際の注意事項を教えてください。",
        "expected_pattern": "next_gen_warnings",
    },
]


# ============================================================
# 出力ヘルパー
# ============================================================

def banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║   🖥️  PC互換性判定エンジン — Plan-and-Execute Demo       ║
║   pc_domain_rules + pc_prompts (PC特化版)                ║
║   ツール: BigQuery(mock) + PageIndex(mock) + VectorDB    ║
╚══════════════════════════════════════════════════════════╝
""")


def section(title: str, sub: str = ""):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    if sub:
        print(f"  {sub}")
    print(f"{'─'*60}")


def show_plan(response):
    if not response.plans:
        return
    plan = response.plans[0]
    print(f"\n  📋 検索計画:")
    print(f"     パターン : {plan.get('detected_query_pattern', plan.get('detected_pattern', 'N/A'))}")
    print(f"     カテゴリ : {plan.get('detected_categories', plan.get('detected_category', 'N/A'))}")
    reasoning = plan.get('reasoning', 'N/A')
    print(f"     推論     : {reasoning[:120]}{'...' if len(reasoning) > 120 else ''}")
    for step in plan.get("steps", []):
        deps = f" (依存: {step['depends_on']})" if step.get('depends_on') else " (並列)"
        print(f"     Step {step['step_id']}: [{step['tool']}]{deps} {step['description']}")


def show_results(response):
    print(f"\n  ⚡ 検索結果 ({len(response.results)}件):")
    for r in response.results:
        tool = r.get("tool", "?")
        conf = r.get("confidence", 0)
        src  = r.get("source", "N/A")
        data = json.dumps(r.get("data", {}), ensure_ascii=False)
        preview = data[:150] + ("..." if len(data) > 150 else "")
        print(f"     [{tool}] conf={conf:.1f} | {src}")
        print(f"       {preview}")


def show_answer(response, query_info: dict):
    print(f"\n  📝 最終判定:")
    print(f"  {'─'*50}")
    for line in response.answer.split("\n"):
        print(f"  {line}")
    print(f"  {'─'*50}")

    # 期待値との照合（デモ用）
    expected_verdict = query_info.get("expected_verdict")
    if expected_verdict:
        answer_upper = response.answer.upper()
        verdict_map = {"OK": "✅", "WARNING": "⚠️", "NG": "❌"}
        found = any(
            kw in answer_upper
            for kw in {
                "OK": ["OK", "問題なし", "組め", "✅"],
                "WARNING": ["WARNING", "要確認", "注意", "⚠"],
                "NG": ["NG", "非互換", "組めない", "❌"],
            }.get(expected_verdict, [])
        )
        mark = "✅" if found else "⚠️"
        print(f"\n  {mark} 期待判定 '{expected_verdict}' → {'検出' if found else '未検出'}")

    print(f"\n  📊 {response.total_steps}ステップ | "
          f"{response.total_attempts}回試行 | "
          f"{response.elapsed_seconds:.2f}秒")


# ============================================================
# デモ実行
# ============================================================

async def run_demo(queries=None, verbose=False):
    banner()

    config = EngineConfig(
        llm=LLMConfig(provider="anthropic"),
        verbose=verbose,
        use_mock=True,  # モックデモ: Trueで外部API不要。実API使用時はFalseに変更
    )
    engine = PIMRAGEngine(config)

    # ヘルスチェック
    health = await engine.health_check()
    print(f"🏥 ツールヘルスチェック: {json.dumps(health)}")

    targets = queries or DEMO_QUERIES
    results_summary = []

    for i, q in enumerate(targets, 1):
        print(f"\n{'═'*60}")
        print(f"  Demo {i}/{len(targets)}: {q['description']}")
        print(f"{'═'*60}")
        print(f"  質問:\n  {q['query'][:200]}")

        resp = await engine.query(q["query"])

        show_plan(resp)
        show_results(resp)
        show_answer(resp, q)
        results_summary.append((q, resp))

    # ─── サマリー ───
    section("📊 デモサマリー")
    total_t = sum(r.elapsed_seconds for _, r in results_summary)
    total_s = sum(r.total_steps for _, r in results_summary)
    for i, (q, r) in enumerate(results_summary, 1):
        print(f"  {i}. {q['description'][:50]:<50} "
              f"{r.total_steps}step / {r.elapsed_seconds:.2f}s")
    print(f"\n  合計: {total_s}ステップ, {total_t:.2f}秒")
    print(f"\n{'═'*60}")
    print("  ✅ デモ完了!")
    print(f"{'═'*60}\n")


async def run_interactive():
    banner()
    print("  💬 対話モード — 質問を入力（'quit'で終了）\n")

    config = EngineConfig(llm=LLMConfig(provider="anthropic"), verbose=True, use_mock=True)
    engine = PIMRAGEngine(config)

    while True:
        try:
            query = input("\n🔍 構成または質問: ").strip()
            if query.lower() in ("quit", "exit", "q"):
                print("👋 終了します")
                break
            if not query:
                continue

            resp = await engine.query(query)
            show_plan(resp)
            show_results(resp)
            print(f"\n📝 判定結果:\n{resp.answer}")
            print(f"\n📊 {resp.total_steps}ステップ / {resp.elapsed_seconds:.2f}秒")

        except KeyboardInterrupt:
            print("\n👋 終了します")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback; traceback.print_exc()


# ============================================================
# エントリーポイント
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if "--interactive" in sys.argv or "-i" in sys.argv:
        asyncio.run(run_interactive())
    elif "--query" in sys.argv:
        idx = sys.argv.index("--query")
        q_text = sys.argv[idx + 1]
        custom = [{"id": "cli", "description": "CLI指定クエリ", "query": q_text}]
        asyncio.run(run_demo(queries=custom, verbose=True))
    else:
        asyncio.run(run_demo())
