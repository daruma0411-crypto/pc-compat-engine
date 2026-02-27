"""
/api/chat エンドポイントのAPI呼び出し部分 抜粋
ソース: app.py（2026-02-28時点）

このファイルは参照・設計検討用。実際の動作コードは app.py を参照。
"""

# ================================================================
# モデル・パラメータ設定
# ================================================================

API_CONFIG = {
    'model':      'claude-haiku-4-5-20251001',
    'max_tokens': 2000,
    'endpoint':   'https://api.anthropic.com/v1/messages',
}

# コンテキストウィンドウ上限: 200,000トークン
# 推定使用量: 5,000〜8,500トークン（3〜4%）


# ================================================================
# system フィールドの組み立て（/api/chat より）
# ================================================================

def build_system_prompt(session, is_hearing, all_products, budget_yen, detected_resolution):
    """
    Claudeに渡すsystemプロンプトを組み立てる。

    ヒアリング段階（is_hearing=True）:
        confirmed_parts_text + _SHOP_CLERK_SYSTEM_PROMPT
        → RAG製品リストなし（トークン節約）

    提案段階（is_hearing=False）:
        current_build_text + confirmed_parts_text + _SHOP_CLERK_SYSTEM_PROMPT + products_summary
        → 全情報を渡す
    """

    # ① 確定済みパーツ（常に付加）
    confirmed_parts_text = format_confirmed_parts(session['confirmed_parts'])

    if is_hearing:
        # ヒアリング段階: シンプル構成
        system_prompt = confirmed_parts_text + "\n" + _SHOP_CLERK_SYSTEM_PROMPT
        # 推定: ~4,300トークン

    else:
        # 提案段階: 全情報付加

        # ② RAG: 予算×解像度でフィルタした製品リスト
        filtered_products = retrieve_parts(
            budget=budget_yen,
            game_name=None,
            resolution=detected_resolution,  # 'FHD' / 'WQHD' / '4K'
            quality='high',
            all_products=all_products
        )
        products_summary = _format_products_for_claude(filtered_products)
        # 推定: ~300〜600トークン

        # ③ current_build（スペック付き現在構成・修正6で追加）
        current_build_text = format_current_build_for_claude(
            session['current_build'],
            session.get('recheck_flags', [])
        )
        # 推定: ~100〜150トークン

        system_prompt = (
            current_build_text + "\n"           # 現在構成（コード確定）
            + confirmed_parts_text + "\n"        # パーツ名リスト
            + _SHOP_CLERK_SYSTEM_PROMPT          # 店長プロンプト（4,225トークン）
            + "\n\n利用可能な製品:\n"
            + products_summary                   # RAG結果
        )
        # 推定: ~4,900〜5,100トークン

    return system_prompt


# ================================================================
# messages フィールドの組み立て（/api/chat より）
# ================================================================

def build_messages(session, current_message):
    """
    Claudeに渡すmessagesリストを組み立てる。

    構造:
        [
            {'role': 'user',      'content': '20万でモンハンやりたい'},
            {'role': 'assistant', 'content': '{"message": "...", "recommended_parts": [...]}'},
            {'role': 'user',      'content': 'RTX 5070でお願いします'},
            ...（直近10メッセージ）
            {'role': 'user',      'content': current_message},  ← 今回の入力
        ]

    注意:
        - 保持上限: 直近10メッセージ（5往復）
        - assistant の content は Claude が返した JSON 文字列そのまま
        - 古いメッセージは自動削除（session['history'] = session['history'][-10:]）
    """
    messages = []
    for h in session['history'][-10:]:
        if h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': current_message})
    return messages


# ================================================================
# Claude API呼び出し本体（call_claude_chat）
# ================================================================

import json
import urllib.request

def call_claude_chat(system, messages, claude_api_key):
    """
    Claude API を呼び出してレスポンステキストを返す。

    リクエスト構造:
        POST https://api.anthropic.com/v1/messages
        Headers:
            Content-Type: application/json
            X-API-Key: {ANTHROPIC_API_KEY}
            anthropic-version: 2023-06-01
        Body:
            {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2000,
                "system": "{system_prompt}",   ← 上記 build_system_prompt() の結果
                "messages": [                   ← 上記 build_messages() の結果
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."},
                    ...
                ]
            }

    レスポンス:
        Claude が返す JSON 文字列（```json ブロック包み）
        → parse_claude_json_response() でパース
        → {'message': '...', 'recommended_parts': [...]} の形式
    """
    req_body = json.dumps({
        'model':      'claude-haiku-4-5-20251001',
        'max_tokens': 2000,
        'system':     system,
        'messages':   messages,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=req_body,
        headers={
            'Content-Type':      'application/json',
            'X-API-Key':         claude_api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        resp_data = json.loads(resp.read().decode('utf-8'))

    content = resp_data.get('content', [{}])[0].get('text', '{}')
    return content  # Claude の生テキスト（JSON文字列）


# ================================================================
# Claude レスポンスのパース（parse_claude_json_response）
# ================================================================

import re

def parse_claude_json_response(text):
    """
    Claude が返した JSON 文字列をパースする。

    Claude は必ず以下の形式で返す（_SHOP_CLERK_SYSTEM_PROMPT で指示）:
        ```json
        {
          "message": "ユーザーへのメッセージ",
          "recommended_parts": [
            {"category": "GPU", "name": "...", "reason": "...", "price_range": "¥XX,XXX"}
          ]
        }
        ```

    失敗時のフォールバック:
        {'message': '少し詳しく教えてください。', 'recommended_parts': []}
    """
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            'message': '少し詳しく教えてください。',
            'recommended_parts': []
        }


# ================================================================
# recommended_parts 受け取り後の処理（/api/chat の後半）
# ================================================================

def process_recommended_parts(response_data, session, all_products, amazon_tag, rakuten_a_id, rakuten_l_id):
    """
    Claudeが返した recommended_parts を処理する。

    処理内容:
        1. confirmed_parts に追加（カテゴリ→製品名のマッピング）
        2. AmazonアフィリエイトURLを付与（未設定の場合）
        3. current_build を更新（DBからスペック取得）
        4. 依存関係チェック（ソケット変更→MB/RAMリセット等）
        5. reset_parts / recheck_parts をレスポンスに付加

    戻り値:
        response_data に以下を追加して返す:
            - reset_parts:   UIからリセットすべきカテゴリリスト
            - recheck_parts: 再確認が必要なカテゴリリスト
            - current_build: 現在構成のサマリー（フロントエンド更新用）
    """
    import urllib.parse

    def _make_amzn(name):
        q = urllib.parse.quote(name)
        return f'https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}'

    def _make_raku(name):
        q = urllib.parse.quote(name)
        if rakuten_a_id and rakuten_l_id:
            return (f'https://hb.afl.rakuten.co.jp/hgc/{rakuten_a_id}/{rakuten_l_id}/?'
                    f'pc=https://search.rakuten.co.jp/search/mall/{q}/&link_type=hybrid_url&ts=1')
        return f'https://search.rakuten.co.jp/search/mall/{q}/'

    all_reset_parts   = []
    all_recheck_parts = []

    if response_data.get('recommended_parts'):
        for part in response_data['recommended_parts']:
            category      = part.get('category', '').upper()
            part_name     = part.get('name', '')
            user_specified = part.get('user_specified', False)

            if category and part_name:
                # confirmed_parts 更新
                session['confirmed_parts'][category] = part_name

                # アフィリエイトURL付与
                if not part.get('amazon_url'):
                    part['amazon_url']  = _make_amzn(part_name)
                if not part.get('rakuten_url'):
                    part['rakuten_url'] = _make_raku(part_name)

                # current_build 更新 + 依存関係チェック
                dep_result = update_current_build(
                    session, category.lower(), part_name, all_products, user_specified
                )
                all_reset_parts.extend(dep_result['reset_parts'])
                all_recheck_parts.extend(dep_result['recheck_parts'])

    # レスポンスに付加
    if all_reset_parts:
        response_data['reset_parts']   = list(set(all_reset_parts))
    if all_recheck_parts:
        response_data['recheck_parts'] = list(set(all_recheck_parts))

    # current_build サマリーをフロントエンドへ送信
    response_data['current_build'] = {
        cat: ({'name': p['name'], 'user_specified': p.get('user_specified', False)} if p else None)
        for cat, p in session['current_build'].items()
    }

    # recheck_flags をクリア（今回の応答で通知済み）
    session['recheck_flags'] = []

    return response_data


# ================================================================
# ステージ判定ロジック（hearing → recommending 移行条件）
# ================================================================

HEARING_TO_RECOMMENDING_CONDITIONS = {
    # 会話全文から以下のキーワードが揃ったら提案段階へ移行
    'has_budget': ['万', '円'],
    'has_resolution': ['1080', '1440', '2160', '4k', 'wqhd', 'fhd', '①', '②', '③'],
    'has_quality': ['最高', '高画質', '標準', 'フレーム', 'fps', 'おまかせ', '①', '②', '③'],
}

# 注意:
#   - 一度 'recommending' に入ったら 'hearing' に戻らない
#   - stage は session に永続化される
#   - 予算は session['budget_yen'] に保存（セッション継続中は再抽出不要）
