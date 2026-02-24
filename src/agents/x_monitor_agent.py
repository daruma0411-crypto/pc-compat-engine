"""
XMonitorAgent — X APIストリーム監視エージェント
================================================
【責務】
X API v2 のフィルタードストリームを監視し、自作PC組み立て関連の
投稿から型番を抽出して診断エンジン (PIMRAGEngine) に投入する。

【依存】
- tweepy >= 4.14  (X API v2 AsyncStreamingClient)
- PIMRAGEngine    (src/main.py)
- XReplyAgent     (src/agents/x_reply_agent.py)
- PART_NUMBER_PATTERNS (src/config/domain_rules.py)

【データフロー】
X FilteredStream
  → _on_tweet(tweet)        # ストリームコールバック
  → _extract_parts(text)    # 型番抽出 (PART_NUMBER_PATTERNS)
  → _build_query(parts)     # 診断クエリ文字列を構築
  → engine.query(query)     # 診断エンジンに投入
  → reply_agent.enqueue()   # リプライキューに積む
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from ..config.domain_rules import PART_NUMBER_PATTERNS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

MONITOR_KEYWORDS: list[str] = [
    # 物理干渉
    "自作PC 干渉", "グラボ 入らない", "GPU 長さ",
    "クーラー 干渉", "メモリ 干渉",
    # 互換性
    "マザボ 互換", "ソケット 合わない", "DDR5 マザー", "AM5 AM4",
    # 電源
    "電源 足りる", "電源 ワット", "12VHPWR", "溶けた",
    # 組み立て失敗
    "起動しない 自作", "認識されない", "BIOSに入れない",
]
"""X APIフィルタードストリームに登録するキーワードルール"""

MIN_PARTS_FOR_DIAGNOSIS: int = 2
"""型番が何個以上あれば診断エンジンに投入するか"""

# PART_NUMBER_PATTERNS のキー → ExtractedParts フィールド名のマッピング
_PATTERN_TO_FIELD: dict[str, str] = {
    "nvidia_gpu":  "gpu",
    "amd_gpu":     "gpu",
    "intel_cpu":   "cpu",
    "amd_cpu":     "cpu",
    "motherboard": "motherboard",
    "psu":         "psu",
    "cpu_cooler":  "cpu_cooler",
    "case":        "case",
    "memory":      "memory",
}


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class ExtractedParts:
    """ツイートテキストから抽出したパーツ型番"""
    gpu:         list[str] = field(default_factory=list)
    motherboard: list[str] = field(default_factory=list)
    cpu:         list[str] = field(default_factory=list)
    cpu_cooler:  list[str] = field(default_factory=list)
    psu:         list[str] = field(default_factory=list)
    memory:      list[str] = field(default_factory=list)
    case:        list[str] = field(default_factory=list)

    def total_count(self) -> int:
        return sum(len(v) for v in vars(self).values() if isinstance(v, list))

    def is_diagnosable(self) -> bool:
        return self.total_count() >= MIN_PARTS_FOR_DIAGNOSIS


# ---------------------------------------------------------------------------
# tweepy AsyncStreamingClient サブクラス
# ---------------------------------------------------------------------------

class _PCCompatStreamingClient:
    """
    tweepy.AsyncStreamingClient のラッパー。
    tweepy が未インストールの場合はスタブとして動作する。
    """

    def __init__(self, bearer_token: str, on_tweet_callback):
        self._bearer_token = bearer_token
        self._on_tweet_callback = on_tweet_callback
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        import tweepy  # 遅延インポート (ImportError は呼び出し元でハンドル)

        class _InnerClient(tweepy.AsyncStreamingClient):
            def __init__(inner_self, bearer_token, callback):
                super().__init__(bearer_token, wait_on_rate_limit=True)
                inner_self._callback = callback

            async def on_tweet(inner_self, tweet):
                data = {
                    "id":        str(tweet.id),
                    "text":      tweet.text or "",
                    "author_id": str(tweet.author_id or ""),
                }
                await inner_self._callback(data)

            async def on_errors(inner_self, errors):
                for err in errors:
                    logger.error(f"Stream error: {err}")

            async def on_closed(inner_self, resp):
                logger.warning("Stream closed by server")

            async def on_disconnect(inner_self):
                logger.info("Stream disconnected")

        self._client = _InnerClient(self._bearer_token, self._on_tweet_callback)

    async def get_rules(self):
        self._ensure_client()
        return await self._client.get_rules()

    async def delete_rules(self, ids):
        self._ensure_client()
        return await self._client.delete_rules(ids)

    async def add_rules(self, rules):
        self._ensure_client()
        return await self._client.add_rules(rules)

    async def filter(self, **kwargs):
        self._ensure_client()
        return await self._client.filter(**kwargs)

    def disconnect(self):
        if self._client:
            self._client.disconnect()


# ---------------------------------------------------------------------------
# メインクラス
# ---------------------------------------------------------------------------

class XMonitorAgent:
    """
    X APIフィルタードストリーム監視エージェント

    Attributes:
        bearer_token (str)      : X API Bearer Token
        engine                  : PIMRAGEngine インスタンス
        reply_agent             : XReplyAgent インスタンス
        _stream_rules (list)    : 現在登録中のフィルタールール
        _running (bool)         : ストリーム稼働フラグ
        _processed_count (int)  : 処理済みツイート数（監視用）
    """

    def __init__(
        self,
        bearer_token: str,
        engine,                     # PIMRAGEngine
        reply_agent,                # XReplyAgent
    ) -> None:
        self.bearer_token = bearer_token
        self.engine = engine
        self.reply_agent = reply_agent
        self._stream_rules: list[dict] = []
        self._running: bool = False
        self._processed_count: int = 0
        self._streaming_client: Optional[_PCCompatStreamingClient] = None

    # ------------------------------------------------------------------
    # 公開インターフェース
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        ストリーム監視を開始する。

        処理フロー:
          1. _setup_stream_rules() でキーワードルールを X API に登録
          2. tweepy.AsyncStreamingClient でストリームを開始
          3. 受信ツイートごとに _on_tweet() を呼び出す
          4. Ctrl+C (KeyboardInterrupt) または stop() で終了
        """
        if self._running:
            logger.warning("XMonitorAgent は既に起動中です")
            return

        try:
            import tweepy  # noqa: F401  インストール確認のみ
        except ImportError:
            logger.error("tweepy がインストールされていません: pip install 'tweepy>=4.14'")
            return

        # リプライエージェントを先に起動
        await self.reply_agent.start()

        self._streaming_client = _PCCompatStreamingClient(
            self.bearer_token,
            on_tweet_callback=self._on_tweet,
        )

        await self._setup_stream_rules()

        self._running = True
        logger.info(
            f"XMonitorAgent 起動: ルール {len(self._stream_rules)} 件, "
            f"キーワード {len(MONITOR_KEYWORDS)} 件"
        )

        try:
            await self._streaming_client.filter(
                tweet_fields=["author_id", "text", "created_at"],
                expansions=["author_id"],
                user_fields=["username"],
            )
        except KeyboardInterrupt:
            await self.stop()
        except Exception as e:
            logger.error(f"ストリームエラー: {e}")
            self._running = False

    async def stop(self) -> None:
        """
        ストリームを安全に停止する。

        - _running フラグを False に設定
        - tweepy クライアントの disconnect() を呼び出す
        - 未処理キューがあれば reply_agent に flush を依頼
        """
        self._running = False
        if self._streaming_client:
            self._streaming_client.disconnect()
        logger.info(
            f"XMonitorAgent 停止: 処理済み {self._processed_count} 件"
        )
        await self.reply_agent.stop()

    # ------------------------------------------------------------------
    # 内部メソッド
    # ------------------------------------------------------------------

    async def _on_tweet(self, tweet: dict) -> None:
        """
        ツイート受信コールバック。

        Args:
            tweet: {id, text, author_id} の辞書

        処理フロー:
          1. _extract_parts(text) で型番を抽出
          2. parts.is_diagnosable() が False なら早期リターン
          3. _build_query(parts, tweet_url) で診断クエリを構築
          4. engine.query(query) で診断を実行
          5. reply_agent.enqueue(tweet_id, response, author) に渡す
        """
        text = tweet.get("text", "")
        parts = self._extract_parts(text)

        if not parts.is_diagnosable():
            logger.debug(
                f"型番不足 ({parts.total_count()}件) → スキップ: {text[:50]!r}"
            )
            return

        tweet_id   = tweet.get("id", "")
        author_id  = tweet.get("author_id", "")
        # expansions で username が取れれば使う。なければ author_id で代替
        author     = tweet.get("author_username") or author_id or "unknown"
        tweet_url  = f"https://x.com/i/status/{tweet_id}"

        query = self._build_query(parts, tweet_url)
        logger.info(f"診断開始 (@{author}): {query[:80]}")

        try:
            response = await self.engine.query(query)
            await self.reply_agent.enqueue(tweet_id, response, author)
            self._processed_count += 1
        except Exception as e:
            logger.error(f"診断エラー (@{author}): {e}")

    def _extract_parts(self, text: str) -> ExtractedParts:
        """
        テキストから型番を正規表現で抽出する。

        PART_NUMBER_PATTERNS (src/config/domain_rules.py) の全パターンを
        カテゴリ別に試行し、マッチした型番を ExtractedParts に格納する。

        Args:
            text: ツイートテキスト（半角・全角混在可）

        Returns:
            ExtractedParts: カテゴリ別の型番リスト

        Example:
            >>> agent._extract_parts("RTX 4090とZ790 APEXが欲しい")
            ExtractedParts(gpu=["RTX 4090"], motherboard=["Z790 APEX"])
        """
        parts = ExtractedParts()

        for pattern_key, pattern_data in PART_NUMBER_PATTERNS.items():
            field_name = _PATTERN_TO_FIELD.get(pattern_key)
            if field_name is None:
                continue

            target_list: list[str] = getattr(parts, field_name)

            for pattern in pattern_data.get("patterns", []):
                try:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                except re.error as exc:
                    logger.debug(f"正規表現エラー ({pattern}): {exc}")
                    continue

                for match in matches:
                    # findall がグループを持つ場合はタプルになる
                    if isinstance(match, tuple):
                        match_str = " ".join(m.strip() for m in match if m).strip()
                    else:
                        match_str = match.strip()

                    if match_str and match_str not in target_list:
                        target_list.append(match_str)

        return parts

    def _build_query(self, parts: ExtractedParts, tweet_url: str) -> str:
        """
        抽出型番リストを診断エンジン用クエリ文字列に整形する。

        Args:
            parts: _extract_parts() の返り値
            tweet_url: 元ツイートURL (https://x.com/user/status/ID)

        Returns:
            str: 診断エンジンに渡すクエリ文字列

        Example:
            >>> agent._build_query(parts, "https://x.com/...")
            "GPU: RTX 4090, MB: ROG Z790 APEX で組めるか確認してください。\n(参照: https://x.com/...)"
        """
        label_map: list[tuple[str, str]] = [
            ("cpu",         "CPU"),
            ("motherboard", "MB"),
            ("gpu",         "GPU"),
            ("memory",      "RAM"),
            ("cpu_cooler",  "COOLER"),
            ("case",        "CASE"),
            ("psu",         "PSU"),
        ]
        lines = []
        for field_name, label in label_map:
            values: list[str] = getattr(parts, field_name)
            if values:
                lines.append(f"{label}: {', '.join(values)}")

        query = "\n".join(lines)
        query += f"\nで組めるか確認してください。\n(参照: {tweet_url})"
        return query

    async def _setup_stream_rules(self) -> None:
        """
        既存ルールを削除して MONITOR_KEYWORDS を X API に登録する。

        - GET /2/tweets/search/stream/rules で既存ルール一覧取得
        - DELETE /2/tweets/search/stream/rules で全削除
        - POST /2/tweets/search/stream/rules で MONITOR_KEYWORDS を登録
        - 登録成功後 _stream_rules を更新

        Note:
            X API の1リクエスト上限（25ルール）に注意。
            MONITOR_KEYWORDS が25件を超える場合は OR 結合してまとめる。
        """
        try:
            import tweepy
        except ImportError:
            logger.warning("tweepy 未インストール: ストリームルールをスキップ")
            return

        # 既存ルールを削除
        try:
            existing = await self._streaming_client.get_rules()
            if existing.data:
                ids = [r.id for r in existing.data]
                await self._streaming_client.delete_rules(ids)
                logger.info(f"既存ストリームルール {len(ids)} 件削除")
        except Exception as e:
            logger.warning(f"既存ルール取得/削除エラー: {e}")

        # キーワードを OR 結合して 512 文字・25 ルール以内に収める
        LANG_SUFFIX = " lang:ja -is:retweet"
        RULE_MAX_LEN = 512
        suffix_len = len(LANG_SUFFIX) + 2  # 括弧2文字分

        rules_to_add: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for kw in MONITOR_KEYWORDS:
            kw_q = f'"{kw}"' if " " in kw else kw
            separator_len = 4 if current_chunk else 0  # " OR "
            if current_len + separator_len + len(kw_q) + suffix_len > RULE_MAX_LEN and current_chunk:
                chunk = "(" + " OR ".join(current_chunk) + ")" + LANG_SUFFIX
                rules_to_add.append(chunk)
                current_chunk = [kw_q]
                current_len = len(kw_q)
            else:
                current_chunk.append(kw_q)
                current_len += separator_len + len(kw_q)

        if current_chunk:
            chunk = "(" + " OR ".join(current_chunk) + ")" + LANG_SUFFIX
            rules_to_add.append(chunk)

        rules_to_add = rules_to_add[:25]  # X API 上限

        stream_rules = [
            tweepy.StreamRule(value=r, tag=f"pc_compat_{i}")
            for i, r in enumerate(rules_to_add)
        ]

        try:
            result = await self._streaming_client.add_rules(stream_rules)
            if result.errors:
                logger.error(f"ルール登録エラー: {result.errors}")
            else:
                self._stream_rules = [
                    {"value": r.value, "tag": r.tag}
                    for r in (result.data or [])
                ]
                logger.info(f"ストリームルール登録完了: {len(self._stream_rules)} 件")
        except Exception as e:
            logger.error(f"ストリームルール登録失敗: {e}")
