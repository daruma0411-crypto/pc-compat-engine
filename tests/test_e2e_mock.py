"""
統合テスト: ツイート受信 → 型番抽出 → 診断 → リプライ生成 E2E フロー
===========================================================================
外部 API (X API / LLM) は一切呼び出さず、すべてモックで代替する。

テストケース:
  1. test_extract_parts_from_tweet       — 型番抽出 (RTX 4090 + Z790-E)
  2. test_build_query_from_parts         — 診断クエリ文字列の形式確認
  3. test_e2e_tweet_to_enqueue           — _on_tweet → engine.query → enqueue
  4. test_insufficient_parts_skipped     — 型番1個以下ならスキップ
  5. test_reply_worker_sends_tweet       — reply_worker → tweepy.create_tweet
  6. test_reply_worker_rate_limit        — レート上限でスリープ待機
  7. test_format_reply_ok                — ✅ 判定のリプライ形式
  8. test_format_reply_ng                — ❌ 判定のリプライ形式 + 280字以内
  9. test_format_reply_detail_url        — detail_url_base が設定されたときのURL付与
 10. test_full_pipeline_mock_engine      — PIMRAGEngine(use_mock=True) を通した完全E2E
"""
from __future__ import annotations

import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# プロジェクトルートを sys.path に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.x_monitor_agent import XMonitorAgent, ExtractedParts
from src.agents.x_reply_agent import XReplyAgent, ReplyTask
from src.main import EngineResponse, PIMRAGEngine
from src.config.settings import EngineConfig


# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------

def make_engine_response(
    verdict: str = "OK",
    query: str = "GPU: RTX 4090\nMB: Z790-E GAMING\nで組めるか確認してください。",
) -> EngineResponse:
    """テスト用 EngineResponse を生成する"""
    answers = {
        "OK":       "✅ 組めます\nRTX 4090 と Z790-E GAMING は互換性OK。",
        "WARNING":  "⚠️ 要確認あり\nRTX 4090 はケースの奥行きに注意が必要。",
        "NG":       "❌ 非互換あり\n❌ DDR4メモリは Z790-E に刺さりません。",
        "要実機確認": "組み合わせの詳細なデータが不足しています。",
    }
    return EngineResponse(
        query=query,
        answer=answers.get(verdict, answers["OK"]),
        total_steps=3,
        total_attempts=1,
        elapsed_seconds=0.1,
    )


def make_mock_monitor(engine=None, reply_agent=None) -> XMonitorAgent:
    """XMonitorAgent をモック engine/reply_agent で生成する"""
    if engine is None:
        engine = AsyncMock()
        engine.query = AsyncMock(return_value=make_engine_response())
    if reply_agent is None:
        reply_agent = AsyncMock()
        reply_agent.enqueue = AsyncMock()
    return XMonitorAgent(
        bearer_token="test-bearer",
        engine=engine,
        reply_agent=reply_agent,
    )


def make_reply_agent(detail_url_base: str = "") -> XReplyAgent:
    """XReplyAgent インスタンスを返す（tweepy なし = dry-run）"""
    agent = XReplyAgent(
        api_key="k", api_secret="s",
        access_token="t", access_token_secret="ts",
        detail_url_base=detail_url_base,
    )
    # tweepy.AsyncClient をモッククライアントに差し替え
    mock_client = AsyncMock()
    mock_client.create_tweet = AsyncMock(return_value=MagicMock(data={"id": "999"}))
    agent._client = mock_client
    return agent


# ---------------------------------------------------------------------------
# 1. 型番抽出テスト
# ---------------------------------------------------------------------------

class TestExtractParts:
    """XMonitorAgent._extract_parts() のユニットテスト"""

    def setup_method(self):
        self.monitor = make_mock_monitor()

    def test_nvidia_gpu_and_motherboard(self):
        text = "RTX 4090 と Z790-E GAMING で自作PCを組みたいです"
        parts = self.monitor._extract_parts(text)
        assert any("4090" in g for g in parts.gpu), f"GPU not found: {parts.gpu}"
        assert parts.is_diagnosable(), "2パーツ以上あれば診断可能のはず"

    def test_amd_cpu_and_motherboard(self):
        text = "Ryzen 9 7950X と X670E EXTREME を組み合わせたい"
        parts = self.monitor._extract_parts(text)
        assert any("7950" in c for c in parts.cpu), f"CPU not found: {parts.cpu}"
        assert parts.is_diagnosable()

    def test_single_part_not_diagnosable(self):
        text = "RTX 4090 が欲しい"
        parts = self.monitor._extract_parts(text)
        assert not parts.is_diagnosable(), "1パーツだけでは診断不可のはず"

    def test_no_parts_not_diagnosable(self):
        text = "自作PCって難しそうですよね〜"
        parts = self.monitor._extract_parts(text)
        assert parts.total_count() == 0
        assert not parts.is_diagnosable()

    def test_multiple_categories(self):
        text = "RTX 4090 + i9-14900K + Z790 APEX + Corsair Vengeance DDR5-6000 で組む"
        parts = self.monitor._extract_parts(text)
        assert parts.total_count() >= 2
        assert parts.is_diagnosable()


# ---------------------------------------------------------------------------
# 2. クエリ構築テスト
# ---------------------------------------------------------------------------

class TestBuildQuery:
    """XMonitorAgent._build_query() のユニットテスト"""

    def setup_method(self):
        self.monitor = make_mock_monitor()

    def test_query_contains_gpu_label(self):
        parts = ExtractedParts(gpu=["RTX 4090"], motherboard=["Z790-E GAMING"])
        query = self.monitor._build_query(parts, "https://x.com/i/status/123")
        assert "GPU: RTX 4090" in query
        assert "MB: Z790-E GAMING" in query

    def test_query_ends_with_reference_url(self):
        parts = ExtractedParts(gpu=["RTX 4090"], motherboard=["Z790 APEX"])
        url = "https://x.com/i/status/99999"
        query = self.monitor._build_query(parts, url)
        assert url in query
        assert "で組めるか確認してください。" in query

    def test_empty_category_omitted(self):
        parts = ExtractedParts(gpu=["RTX 4090"], motherboard=["Z790 APEX"])
        query = self.monitor._build_query(parts, "https://x.com/x")
        # cpu は空なので "CPU:" が含まれないはず
        assert "CPU:" not in query

    def test_all_categories_present(self):
        parts = ExtractedParts(
            gpu=["RTX 4090"],
            cpu=["i9-14900K"],
            motherboard=["Z790 APEX"],
            memory=["Vengeance DDR5-6000"],
            psu=["FOCUS GX-1000"],
        )
        query = self.monitor._build_query(parts, "https://x.com/x")
        for label in ["GPU:", "CPU:", "MB:", "RAM:", "PSU:"]:
            assert label in query, f"{label} がクエリに含まれていない"


# ---------------------------------------------------------------------------
# 3. E2E: _on_tweet → engine.query → reply_agent.enqueue
# ---------------------------------------------------------------------------

class TestOnTweetE2E:
    """_on_tweet() の統合フロー確認"""

    def test_diagnosable_tweet_calls_engine_and_enqueue(self):
        """2パーツ以上のツイートでエンジンとキューが呼ばれる"""
        mock_engine = AsyncMock()
        mock_engine.query = AsyncMock(return_value=make_engine_response("OK"))
        mock_reply = AsyncMock()
        mock_reply.enqueue = AsyncMock()

        monitor = make_mock_monitor(engine=mock_engine, reply_agent=mock_reply)

        tweet = {
            "id": "12345",
            "text": "RTX 4090 と Z790-E GAMING って互換性ありますか",
            "author_id": "u001",
            "author_username": "pcbuilder01",
        }
        asyncio.run(monitor._on_tweet(tweet))

        mock_engine.query.assert_called_once()
        query_arg = mock_engine.query.call_args[0][0]
        assert "GPU" in query_arg or "MB" in query_arg

        mock_reply.enqueue.assert_called_once()
        enqueue_args = mock_reply.enqueue.call_args
        assert enqueue_args[0][0] == "12345"           # tweet_id
        assert enqueue_args[0][2] == "pcbuilder01"     # author

    def test_insufficient_parts_skipped(self):
        """型番が1個以下のツイートはエンジンを呼ばない"""
        mock_engine = AsyncMock()
        mock_engine.query = AsyncMock()
        mock_reply = AsyncMock()

        monitor = make_mock_monitor(engine=mock_engine, reply_agent=mock_reply)

        tweet = {
            "id": "99999",
            "text": "RTX 4090 って高いですね〜",
            "author_id": "u002",
        }
        asyncio.run(monitor._on_tweet(tweet))

        mock_engine.query.assert_not_called()
        mock_reply.enqueue.assert_not_called()

    def test_author_fallback_to_author_id(self):
        """author_username がない場合は author_id で代替"""
        mock_engine = AsyncMock()
        mock_engine.query = AsyncMock(return_value=make_engine_response())
        mock_reply = AsyncMock()
        mock_reply.enqueue = AsyncMock()

        monitor = make_mock_monitor(engine=mock_engine, reply_agent=mock_reply)

        tweet = {
            "id": "77777",
            "text": "RTX 4090 と Z790-E GAMING で組みたい",
            "author_id": "uid_fallback",
            # author_username なし
        }
        asyncio.run(monitor._on_tweet(tweet))

        mock_reply.enqueue.assert_called_once()
        author_arg = mock_reply.enqueue.call_args[0][2]
        assert author_arg == "uid_fallback"

    def test_engine_error_does_not_propagate(self):
        """engine.query() が例外を投げてもクラッシュしない"""
        mock_engine = AsyncMock()
        mock_engine.query = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        mock_reply = AsyncMock()

        monitor = make_mock_monitor(engine=mock_engine, reply_agent=mock_reply)

        tweet = {
            "id": "88888",
            "text": "RTX 4090 と Z790-E GAMING 互換性は？",
            "author_id": "u003",
        }
        # 例外が外に出ないことを確認
        asyncio.run(monitor._on_tweet(tweet))
        mock_reply.enqueue.assert_not_called()


# ---------------------------------------------------------------------------
# 4. reply_worker: キューからリプライを送信する
# ---------------------------------------------------------------------------

class TestReplyWorker:
    """XReplyAgent.reply_worker() のテスト"""

    def _run_worker_once(self, agent: XReplyAgent, task: ReplyTask) -> None:
        """
        reply_worker を起動してキューに1タスク投入し、
        処理が完了したら停止する。
        """
        async def _runner():
            # ワーカーをバックグラウンドで起動
            worker = asyncio.create_task(agent.reply_worker())
            # タスク投入
            await agent._queue.put(task)
            # キューが空になるまで待機（最大2秒）
            await asyncio.wait_for(agent._queue.join(), timeout=2.0)
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        asyncio.run(_runner())

    def test_reply_worker_calls_create_tweet(self):
        """reply_worker が tweepy.create_tweet を呼ぶ"""
        agent = make_reply_agent()
        task = ReplyTask(
            tweet_id="555",
            response=make_engine_response("OK"),
            tweet_author="testuser",
            enqueued_at=datetime.utcnow(),
        )
        self._run_worker_once(agent, task)

        agent._client.create_tweet.assert_called_once()
        call_kwargs = agent._client.create_tweet.call_args.kwargs
        assert call_kwargs["in_reply_to_tweet_id"] == "555"
        assert "testuser" in call_kwargs["text"]

    def test_reply_worker_records_history(self):
        """送信成功後に _reply_history に記録される"""
        agent = make_reply_agent()
        assert len(agent._reply_history) == 0

        task = ReplyTask(
            tweet_id="666",
            response=make_engine_response("WARNING"),
            tweet_author="warninguser",
            enqueued_at=datetime.utcnow(),
        )
        self._run_worker_once(agent, task)

        assert len(agent._reply_history) == 1

    def test_reply_worker_rate_limit_blocks(self):
        """max_per_hour を超えたらスリープ待機に入る"""
        agent = make_reply_agent()
        # 履歴を max_per_hour 件埋める（全て「現在時刻」として詰め込む）
        now = datetime.utcnow()
        for _ in range(agent.max_per_hour):
            agent._reply_history.append(now)

        can_send, wait_sec = asyncio.run(agent._check_rate_limit())
        assert can_send is False
        assert wait_sec > 0

    def test_rate_limit_clears_after_one_hour(self):
        """1時間以上前のエントリは削除されレート制限が解除される"""
        agent = make_reply_agent()
        old_time = datetime.utcnow() - timedelta(hours=1, seconds=10)
        for _ in range(agent.max_per_hour):
            agent._reply_history.append(old_time)

        can_send, wait_sec = asyncio.run(agent._check_rate_limit())
        assert can_send is True
        assert wait_sec == 0.0
        # 古いエントリが削除されていること
        assert len(agent._reply_history) == 0


# ---------------------------------------------------------------------------
# 5. _format_reply のフォーマット確認
# ---------------------------------------------------------------------------

class TestFormatReply:
    """XReplyAgent._format_reply() のユニットテスト"""

    def setup_method(self):
        self.agent = make_reply_agent()
        self.agent_with_url = make_reply_agent(detail_url_base="https://pc-compat.example.com")

    def test_ok_reply_within_280_chars(self):
        resp = make_engine_response("OK")
        text = self.agent._format_reply(resp, "user_ok")
        assert len(text) <= 280
        assert "user_ok" in text
        assert "#自作PC互換チェック" in text

    def test_ng_reply_contains_ng_lines(self):
        resp = make_engine_response("NG")
        text = self.agent._format_reply(resp, "user_ng")
        assert len(text) <= 280
        # ❌ 行が本文に含まれるはず
        assert "❌" in text

    def test_warning_reply_verdict_emoji(self):
        resp = make_engine_response("WARNING")
        text = self.agent._format_reply(resp, "user_warn")
        assert len(text) <= 280
        assert "⚠️" in text

    def test_unknown_verdict_fallback(self):
        resp = make_engine_response("要実機確認")
        text = self.agent._format_reply(resp, "user_unknown")
        assert len(text) <= 280
        assert "実機確認" in text

    def test_detail_url_included_when_set(self):
        resp = make_engine_response("OK")
        text = self.agent_with_url._format_reply(resp, "user_url")
        assert len(text) <= 280
        assert "https://pc-compat.example.com" in text

    def test_detail_url_omitted_when_empty(self):
        resp = make_engine_response("OK")
        text = self.agent._format_reply(resp, "user_no_url")
        assert "http" not in text

    def test_footer_always_present(self):
        """フッターは必須"""
        for verdict in ["OK", "WARNING", "NG", "要実機確認"]:
            resp = make_engine_response(verdict)
            text = self.agent._format_reply(resp, "u")
            assert "AIによる自動診断" in text, f"{verdict}: フッターなし"
            assert "#自作PC互換チェック" in text

    def test_very_long_answer_truncated_to_280(self):
        """極端に長い answer でも 280 字を超えない"""
        class LongResp:
            answer = "✅ 問題なし\n" + ("⚠️ " + "x" * 58 + "\n") * 10
            query = "long_test"

        text = self.agent._format_reply(LongResp(), "long_user")
        assert len(text) <= 280


# ---------------------------------------------------------------------------
# 6. 完全E2E: PIMRAGEngine(use_mock=True) を通したパイプライン
# ---------------------------------------------------------------------------

class TestFullPipelineMockEngine:
    """
    PIMRAGEngine を use_mock=True で起動し、
    ツイート受信 → 診断 → リプライ生成 の一連フローを確認する。
    """

    def test_full_e2e_with_mock_engine(self):
        """
        RTX 4090 + Z790-E GAMING のツイートが診断されリプライがエンキューされる。
        """
        async def _run():
            # モックエンジン（use_mock=True で LLM 呼び出しなし）
            config = EngineConfig(use_mock=True)
            engine = PIMRAGEngine(config=config)

            # XReplyAgent: tweepy モック差し替え
            reply_agent = make_reply_agent()
            reply_agent.enqueue = AsyncMock()  # enqueue 自体をモック

            # XMonitorAgent
            monitor = XMonitorAgent(
                bearer_token="test-bearer",
                engine=engine,
                reply_agent=reply_agent,
            )

            tweet = {
                "id": "100001",
                "text": "RTX 4090 と Z790-E GAMING って互換性ありますか？電源は何W必要？",
                "author_id": "u_e2e",
                "author_username": "e2e_tester",
            }
            await monitor._on_tweet(tweet)

            return reply_agent.enqueue

        mock_enqueue = asyncio.run(_run())

        # enqueue が1回呼ばれたこと
        mock_enqueue.assert_called_once()
        call_args = mock_enqueue.call_args[0]
        tweet_id, response, author = call_args

        assert tweet_id == "100001"
        assert author == "e2e_tester"
        assert isinstance(response, EngineResponse)
        assert len(response.answer) > 0, "エンジンからの回答が空"

    def test_full_e2e_reply_text_format(self):
        """
        エンジンの回答からリプライテキストが正しくフォーマットされる。
        """
        async def _run():
            config = EngineConfig(use_mock=True)
            engine = PIMRAGEngine(config=config)

            reply_agent = make_reply_agent()
            captured_responses = []

            original_enqueue = reply_agent.enqueue

            async def capture_enqueue(tweet_id, response, author):
                captured_responses.append((tweet_id, response, author))

            reply_agent.enqueue = capture_enqueue

            monitor = XMonitorAgent(
                bearer_token="test-bearer",
                engine=engine,
                reply_agent=reply_agent,
            )

            tweet = {
                "id": "100002",
                "text": "i9-14900K と Z790-E GAMING って相性どうですか",
                "author_id": "u_format",
                "author_username": "format_checker",
            }
            await monitor._on_tweet(tweet)
            return captured_responses, reply_agent

        captured, agent = asyncio.run(_run())

        assert len(captured) == 1, "enqueue が1回呼ばれていない"
        tweet_id, response, author = captured[0]

        # フォーマットされたリプライを検証
        reply_text = agent._format_reply(response, author)
        assert len(reply_text) <= 280, f"280字超過: {len(reply_text)}"
        assert author in reply_text
        assert "#自作PC互換チェック" in reply_text


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # pytest なしで直接実行する場合
    import os
    os.environ["PYTHONUTF8"] = "1"

    print("=== 統合テスト (mock mode) ===\n")
    tests = [
        ("型番抽出", TestExtractParts),
        ("クエリ構築", TestBuildQuery),
        ("E2Eフロー", TestOnTweetE2E),
        ("リプライワーカー", TestReplyWorker),
        ("フォーマット", TestFormatReply),
        ("完全E2E", TestFullPipelineMockEngine),
    ]

    passed = 0
    failed = 0
    for suite_name, cls in tests:
        instance = cls()
        methods = [m for m in dir(cls) if m.startswith("test_")]
        for method in methods:
            if hasattr(instance, "setup_method"):
                instance.setup_method()
            try:
                getattr(instance, method)()
                print(f"  PASS  [{suite_name}] {method}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  [{suite_name}] {method}: {e}")
                failed += 1

    print(f"\n{'='*50}")
    print(f"結果: {passed} PASS / {failed} FAIL")
    sys.exit(0 if failed == 0 else 1)
