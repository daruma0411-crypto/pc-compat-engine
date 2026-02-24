"""
XReplyAgent — 診断結果リプライ送信エージェント
================================================
【責務】
EngineResponse を280文字以内のX投稿に変換し、
レート制限を守りながら非同期でリプライを送信する。

【依存】
- tweepy >= 4.14  (AsyncClient.create_tweet)
- asyncio.Queue  (返信キュー)
- EngineResponse (src/main.py)

【データフロー】
XMonitorAgent
  → enqueue(tweet_id, response, author)  # キューに積む
  → reply_worker()                        # キューを監視 (常駐)
    → _check_rate_limit()                 # 1時間上限チェック
    → _format_reply(response, author)     # 280字テキスト生成
    → tweepy.create_tweet()               # X APIでリプライ送信
    → _reply_history に記録

【リプライ形式】
    @{author} {絵文字} {1行サマリー}
    {WARNING/NG 上位2件}
    詳細→ {detail_url}
    ※AIによる自動診断（β版）#自作PC互換チェック

【判定絵文字マッピング】
    OK        → ✅ 組めます
    WARNING   → ⚠️ 要確認あり
    NG        → ❌ 非互換あり
    要実機確認 → 🔍 実機確認推奨
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

MAX_TWEET_CHARS: int = 280
"""X の1ツイート文字数上限"""

DEFAULT_MAX_PER_HOUR: int = 10
"""デフォルトの1時間あたり最大リプライ数 (X API 制限考慮)"""

HASHTAG: str = "#自作PC互換チェック"
"""全リプライに付与するハッシュタグ"""

_URL_CHAR_LEN: int = 22
"""X の t.co 短縮後URL換算文字数"""

_MAX_QUEUE_SIZE: int = 100
"""キューの最大サイズ（超過時は古いタスクを破棄）"""

_VERDICT_EMOJI: dict[str, str] = {
    "OK":       "✅ 組めます",
    "WARNING":  "⚠️ 要確認あり",
    "NG":       "❌ 非互換あり",
    "要実機確認": "🔍 実機確認推奨",
}

_URL_RE = re.compile(r"https?://\S+")


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class ReplyTask:
    """返信キューの1タスク"""
    tweet_id:     str       # リプライ先のツイートID
    response:     object    # EngineResponse インスタンス
    tweet_author: str       # @なしのユーザー名
    enqueued_at:  datetime  # キュー投入時刻（優先度計算用）


# ---------------------------------------------------------------------------
# メインクラス
# ---------------------------------------------------------------------------

class XReplyAgent:
    """
    診断結果リプライ送信エージェント

    Attributes:
        client                  : tweepy.AsyncClient インスタンス
        max_per_hour (int)      : 1時間あたり最大リプライ数
        detail_url_base (str)   : 詳細診断ページのベースURL
                                  空文字の場合はリプライにURL含めない
                                  環境変数 PCCOMPAT_DETAIL_URL_BASE で設定可能
        _queue                  : asyncio.Queue[ReplyTask]
        _reply_history (deque)  : 直近1時間の送信タイムスタンプ
                                  deque(maxlen=max_per_hour) で管理
        _worker_task            : reply_worker() の asyncio.Task
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        detail_url_base: Optional[str] = None,
        max_per_hour: int = DEFAULT_MAX_PER_HOUR,
    ) -> None:
        # detail_url_base: 引数 → 環境変数 → 空文字 の優先順位
        if detail_url_base is None:
            detail_url_base = os.getenv("PCCOMPAT_DETAIL_URL_BASE", "")
        self.detail_url_base = detail_url_base.rstrip("/")
        self.max_per_hour = max_per_hour
        self._queue: asyncio.Queue[ReplyTask] = asyncio.Queue()
        self._reply_history: deque[datetime] = deque(maxlen=max_per_hour)
        self._worker_task: Optional[asyncio.Task] = None
        self._client = None  # tweepy.AsyncClient (start()後に初期化)
        self._credentials = (api_key, api_secret, access_token, access_token_secret)

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        reply_worker() を asyncio.Task として起動する。

        XMonitorAgent.start() から呼び出すことを想定。
        二重起動時は警告ログを出して何もしない。
        """
        if self._worker_task is not None and not self._worker_task.done():
            logger.warning("XReplyAgent は既に起動中です")
            return

        # tweepy.AsyncClient を初期化
        try:
            import tweepy
            api_key, api_secret, access_token, access_token_secret = self._credentials
            self._client = tweepy.AsyncClient(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            logger.info("XReplyAgent: tweepy AsyncClient 初期化完了")
        except ImportError:
            logger.warning("tweepy が未インストール: リプライはログ出力のみ (dry-run モード)")
            self._client = None

        self._worker_task = asyncio.create_task(self.reply_worker())
        logger.info(
            f"XReplyAgent 起動: max_per_hour={self.max_per_hour}, "
            f"detail_url_base={self.detail_url_base!r}"
        )

    async def stop(self) -> None:
        """
        reply_worker タスクをキャンセルして停止する。

        キュー残留タスクは破棄される（ログに記録）。
        """
        if self._worker_task and not self._worker_task.done():
            remaining = self._queue.qsize()
            if remaining > 0:
                logger.warning(f"XReplyAgent 停止: キュー残留 {remaining} 件を破棄")
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("XReplyAgent 停止完了")

    async def enqueue(
        self,
        tweet_id: str,
        response,               # EngineResponse
        tweet_author: str,
    ) -> None:
        """
        返信タスクをキューに追加する。

        Args:
            tweet_id    : リプライ先ツイートID
            response    : PIMRAGEngine.query() の返り値 (EngineResponse)
            tweet_author: @なしのユーザー名

        Note:
            キューの最大サイズは 100。超過時は古いタスクを破棄してログを出す。
        """
        # キュー満杯チェック: asyncio.Queue はデフォルト無制限なので手動で管理
        if self._queue.qsize() >= _MAX_QUEUE_SIZE:
            try:
                dropped = self._queue.get_nowait()
                logger.warning(
                    f"リプライキュー満杯: tweet_id={dropped.tweet_id} "
                    f"(@{dropped.tweet_author}) を破棄"
                )
                self._queue.task_done()
            except asyncio.QueueEmpty:
                pass

        task = ReplyTask(
            tweet_id=tweet_id,
            response=response,
            tweet_author=tweet_author,
            enqueued_at=datetime.utcnow(),
        )
        await self._queue.put(task)
        logger.debug(f"キュー追加: tweet_id={tweet_id}, qsize={self._queue.qsize()}")

    async def reply_worker(self) -> None:
        """
        キューを監視し、レート制限を守りながら順次リプライを送信する。

        無限ループで動作し、キューが空のときは待機する。
        レート上限到達時は残り時間をスリープして待つ。

        処理フロー:
          1. _queue.get() でタスクを取得
          2. _check_rate_limit() が False なら適切な時間スリープ
          3. _format_reply() で280字テキストを生成
          4. tweepy.AsyncClient.create_tweet() でリプライ送信
          5. _reply_history に送信時刻を記録
          6. _queue.task_done() を呼ぶ
        """
        logger.info("reply_worker 開始")
        while True:
            task = await self._queue.get()
            try:
                # レート制限チェック (上限に達していたらスリープ)
                while True:
                    can_send, wait_sec = await self._check_rate_limit()
                    if can_send:
                        break
                    logger.info(
                        f"レート制限: {wait_sec:.0f}秒待機 "
                        f"(直近1時間 {len(self._reply_history)}/{self.max_per_hour} 件)"
                    )
                    await asyncio.sleep(wait_sec + 1.0)

                # リプライ本文を生成
                text = self._format_reply(task.response, task.tweet_author)

                # 送信
                if self._client is not None:
                    await self._client.create_tweet(
                        text=text,
                        in_reply_to_tweet_id=task.tweet_id,
                    )
                    logger.info(
                        f"リプライ送信完了: @{task.tweet_author} "
                        f"(tweet_id={task.tweet_id})"
                    )
                else:
                    # dry-run: ログ出力のみ
                    logger.info(
                        f"[dry-run] リプライ: @{task.tweet_author}\n{text}"
                    )

                self._reply_history.append(datetime.utcnow())

            except asyncio.CancelledError:
                raise  # キャンセルはそのまま伝播
            except Exception as e:
                logger.error(
                    f"リプライ送信エラー (@{task.tweet_author}): {e}"
                )
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    def _format_reply(self, response, tweet_author: str) -> str:
        """
        EngineResponse を280文字以内のリプライテキストに変換する。

        Args:
            response    : EngineResponse インスタンス
            tweet_author: @なしのユーザー名

        Returns:
            str: 280文字以内のリプライテキスト

        構成 (優先度順に削ってMAX_TWEET_CHARS以内に収める):
          1. @{author} {絵文字} {1行サマリー}  ← 必須
          2. {WARNING/NG 上位2件}              ← 文字数が余れば追加
          3. 詳細→ {detail_url}               ← 文字数が余れば追加
          4. ※AIによる自動診断（β版）{HASHTAG} ← 必須

        Note:
            URLは22文字換算 (X の t.co 短縮ルール)。
        """
        answer = getattr(response, "answer", str(response))

        # 1. ヘッダー (必須)
        verdict      = self._extract_verdict(answer)
        verdict_text = _VERDICT_EMOJI.get(verdict, "🔍 実機確認推奨")
        header       = f"@{tweet_author} {verdict_text}"

        # 4. フッター (必須)
        footer = f"※AIによる自動診断（β版）{HASHTAG}"

        # 2. 課題行 (オプション)
        issues      = self._extract_issues(answer)
        issues_text = "\n".join(issues[:2]) if issues else ""

        # 3. 詳細URL (オプション)
        detail_line = ""
        if self.detail_url_base:
            # クエリの最初の16文字からIDを生成 (簡易)
            query_str = getattr(response, "query", "")[:16]
            diag_id   = re.sub(r"[^\w]", "_", query_str).lower()
            detail_line = f"詳細→ {self.detail_url_base}/{diag_id}"

        def _count(text: str) -> int:
            """URLを22字換算した実効文字数を返す"""
            replaced = _URL_RE.sub("x" * _URL_CHAR_LEN, text)
            return len(replaced)

        # 段階的に組み立て: 必須 → issues → detail_url
        required_chars = _count(header) + 1 + _count(footer)  # +1 は改行
        remaining = MAX_TWEET_CHARS - required_chars

        body_parts: list[str] = []

        if issues_text:
            need = _count(issues_text) + 1  # +1 改行
            if need <= remaining:
                body_parts.append(issues_text)
                remaining -= need

        if detail_line:
            need = _count(detail_line) + 1
            if need <= remaining:
                body_parts.append(detail_line)

        parts = [header] + body_parts + [footer]
        reply = "\n".join(parts)

        # 最終保険: 超過していたら issues を除外
        if _count(reply) > MAX_TWEET_CHARS:
            if detail_line:
                reply = "\n".join([header, detail_line, footer])
            else:
                reply = "\n".join([header, footer])

        # それでも超過なら header + footer のみ
        if _count(reply) > MAX_TWEET_CHARS:
            reply = "\n".join([header, footer])

        return reply

    def _extract_verdict(self, answer: str) -> str:
        """
        EngineResponse.answer テキストから総合判定を抽出する。

        Args:
            answer: Synthesizer が生成した最終回答テキスト

        Returns:
            "OK" | "WARNING" | "NG" | "要実機確認"

        検索パターン (優先度順):
          - "❌" または "非互換" または "NG"    → "NG"
          - "⚠️" または "要確認" または "WARNING" → "WARNING"
          - "✅" または "問題なし" または "OK"   → "OK"
          - 上記いずれも一致しない              → "要実機確認"
        """
        if any(kw in answer for kw in ["❌", "非互換", "NG"]):
            return "NG"
        if any(kw in answer for kw in ["⚠️", "要確認", "WARNING"]):
            return "WARNING"
        if any(kw in answer for kw in ["✅", "問題なし", "OK", "互換性OK"]):
            return "OK"
        return "要実機確認"

    def _extract_issues(self, answer: str) -> list[str]:
        """
        answer テキストから ❌ / ⚠️ で始まる行を抽出する。

        Returns:
            list[str]: 60字以内に切り詰めた課題行リスト（優先: ❌ → ⚠️）
        """
        ng_lines: list[str] = []
        warn_lines: list[str] = []

        for line in answer.split("\n"):
            stripped = line.strip()
            if stripped.startswith("❌"):
                ng_lines.append(stripped[:60])
            elif stripped.startswith("⚠️"):
                warn_lines.append(stripped[:60])

        # NG を先に、WARNING を後に
        return ng_lines + warn_lines

    async def _check_rate_limit(self) -> tuple[bool, float]:
        """
        直近1時間の送信数が max_per_hour 未満かチェックする。

        _reply_history から1時間以上前のタイムスタンプを削除した上で
        現在のカウントを確認する。

        Returns:
            (can_send: bool, wait_seconds: float)
            - can_send=True  → 即時送信可能
            - can_send=False → wait_seconds 秒後に再試行

        Example:
            ok, wait = await self._check_rate_limit()
            if not ok:
                await asyncio.sleep(wait)
        """
        now          = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # deque から1時間以上前のエントリを除去
        while self._reply_history and self._reply_history[0] < one_hour_ago:
            self._reply_history.popleft()

        if len(self._reply_history) < self.max_per_hour:
            return True, 0.0

        # 最も古いエントリから1時間後まで待つ
        oldest      = self._reply_history[0]
        wait_until  = oldest + timedelta(hours=1)
        wait_secs   = max(0.0, (wait_until - now).total_seconds())
        return False, wait_secs
