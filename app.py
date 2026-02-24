"""
PC互換性チェッカー — Flask Webサーバー
=======================================
GET  /            → static/index.html
POST /api/diagnose → PC部品互換性診断（Claude Haiku）
GET  /api/health  → ヘルスチェック（Render用）
"""
import glob as glob_module
import json
import os
import re
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

app = Flask(__name__, static_folder='static')

# workspace/data/ のルートパス
_PC_WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')

# ================================================================
# 診断ロジック（proxy_server.py から移植）
# ================================================================

_PC_DIAGNOSIS_SYSTEM_PROMPT = """\
あなたはPC自作互換性診断の専門家です。
指定された部品リストの互換性を以下のルールに従って診断し、必ずJSON形式だけで返してください。

## 即NG判定（verdict: "NG"）
- GPU実装長 > ケースGPU最大長
- CPUソケット不一致（MB と CPU のソケット型番が異なる）
- DDR世代不一致（DDR4メモリ + DDR5マザー等）
- マザーボードフォームファクターがケース非対応（例: ATX MB + mATX専用ケース）
- 電源フォームファクター不一致（ATX電源 + SFX専用ケース）

## WARNING判定
- GPU実装長とケース最大長のマージンが 0〜20mm（ケーブル干渉リスク）
- PCIe 5.0 GPU に 8pin 変換アダプタを使用（12VHPWR 対応電源推奨）
- M.2スロット使用によるPCIeレーン帯域共有
- メモリXMP速度がMBの公式最大速度を超過
- 電源使用率が 80〜90%（25%以上のマージン推奨）
- CPU TDP がCPUクーラー定格冷却能力を超過（またはクーラー定格未公開）

## OK判定
- 上記の NG / WARNING に該当しない互換性確認済みの組み合わせ

## UNKNOWN判定
- スペック情報が不足して判断不可の項目

## スペック不足の扱い（重要）
- 診断リストに電源・CPUなど指定されていない部品のスペックは UNKNOWN として扱い、それだけを理由に WARNING/NG にしないこと
- 提供されたスペックで確認できる互換性チェックのみを対象として verdict を決定すること
- 「事前計算済みチェック」が提供された場合、その数値・判定を最優先で使用すること
- GPU長・ケース対応長のマージン判定は事前計算値を使い、AI自身で再計算せずそのまま採用すること

## 出力形式（JSONのみ、説明文・マークダウン不要）
{
  "verdict": "NG" | "WARNING" | "OK" | "UNKNOWN",
  "checks": [
    {"item": "チェック項目名", "status": "NG" | "WARNING" | "OK" | "UNKNOWN", "detail": "具体的な数値や理由"}
  ],
  "summary": "全体の診断結果を1〜2文で説明"
}
"""


def _lookup_pc_specs(parts: list) -> dict:
    """
    workspace/data/*/products.jsonl から型番を検索してスペック辞書を返す。
    余分トークン最少優先マッチングで "NH-D15" が "NH-D15 G2" に誤マッチしない。
    """
    results = {}
    jsonl_paths = glob_module.glob(
        os.path.join(_PC_WORKSPACE_DIR, 'data', '*', 'products.jsonl')
    )
    all_products = []
    for path in jsonl_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_products.append(json.loads(line))
        except Exception:
            pass

    def _normalize(s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower())

    def _tokens(s: str) -> set:
        return set(re.sub(r'[^a-z0-9]', ' ', s.lower()).split())

    for part in parts:
        part_norm = _normalize(part)
        part_tok = _tokens(part)
        best_product = None
        best_extra = float('inf')

        for product in all_products:
            candidates = [
                product.get('name', ''),
                product.get('model_name', ''),
                product.get('sku', ''),
                product.get('model', ''),
                product.get('part_no', ''),
                (product.get('specs') or {}).get('part_no', ''),
                (product.get('specs') or {}).get('model', ''),
            ]
            for c in candidates:
                if not c:
                    continue
                c_norm = _normalize(c)
                c_tok = _tokens(c)
                extra = len(c_tok - part_tok)
                matched = False
                if part_norm in c_norm or c_norm in part_norm:
                    matched = True
                elif len(part_tok) >= 2 and part_tok.issubset(c_tok):
                    matched = True
                if matched and extra < best_extra:
                    best_extra = extra
                    best_product = product
                    break

        if best_product is not None:
            results[part] = best_product

    return results


_CASE_FF_COMPAT: dict = {
    'E-ATX':     {'E-ATX', 'EATX', 'ATX', 'Micro-ATX', 'mATX', 'Mini-ITX'},
    'EATX':      {'E-ATX', 'EATX', 'ATX', 'Micro-ATX', 'mATX', 'Mini-ITX'},
    'ATX':       {'ATX', 'Micro-ATX', 'mATX', 'Mini-ITX'},
    'Micro-ATX': {'Micro-ATX', 'mATX', 'Mini-ITX'},
    'mATX':      {'Micro-ATX', 'mATX', 'Mini-ITX'},
    'Mini-ITX':  {'Mini-ITX'},
}


def _compute_prechecks(parts: list, specs: dict) -> list:
    """
    GPU干渉マージン・CPUソケット・メモリ規格・CPU冷却能力・PSUワット数・
    MBフォームファクターを事前計算して Claude が最優先で使用すべき判定文字列のリストを返す。
    """
    lines = []

    gpu_entries    = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'gpu']
    case_entries   = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'case']
    cpu_entries    = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'cpu']
    mb_entries     = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'motherboard']
    cooler_entries = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'cpu_cooler']
    ram_entries    = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'ram']
    psu_entries    = [(p, specs[p]) for p in parts if p in specs and specs[p].get('category') == 'psu']

    # GPU × ケース 干渉マージン
    for gpu_part, gpu_data in gpu_entries:
        gpu_len_raw = gpu_data.get('length_mm') or (gpu_data.get('specs') or {}).get('length_mm')
        for case_part, case_data in case_entries:
            case_max_raw = (case_data.get('specs') or {}).get('max_gpu_length_mm') \
                           or case_data.get('max_gpu_length_mm')
            if gpu_len_raw is not None and case_max_raw is not None:
                try:
                    gpu_len  = float(str(gpu_len_raw).replace('mm', '').strip())
                    case_max = float(str(case_max_raw).replace('mm', '').strip())
                    margin = case_max - gpu_len
                    if margin <= 0:
                        status = f"NG（GPU非対応: {margin:.0f}mm オーバー）"
                    elif margin <= 20:
                        status = f"WARNING（マージン {margin:.0f}mm、ケーブル干渉リスク）"
                    else:
                        status = f"OK（マージン {margin:.0f}mm）"
                    lines.append(
                        f"- GPU干渉マージン: {gpu_part}({gpu_len:.0f}mm) "
                        f"vs {case_part}(max {case_max:.0f}mm) = {status}"
                    )
                except (ValueError, TypeError):
                    pass

    # CPU ↔ MB ソケット照合
    for cpu_part, cpu_data in cpu_entries:
        cpu_socket = (cpu_data.get('specs') or {}).get('socket') or cpu_data.get('socket', '')
        for mb_part, mb_data in mb_entries:
            mb_socket = (mb_data.get('specs') or {}).get('socket') or mb_data.get('socket', '')
            if cpu_socket and mb_socket:
                if cpu_socket.upper() == mb_socket.upper():
                    lines.append(
                        f"- CPUソケット照合: {cpu_part}({cpu_socket}) "
                        f"vs {mb_part}({mb_socket}) = OK（一致）"
                    )
                else:
                    lines.append(
                        f"- CPUソケット照合: {cpu_part}({cpu_socket}) "
                        f"vs {mb_part}({mb_socket}) = NG（不一致）"
                    )

    # RAM ↔ MB メモリ規格照合
    for ram_part, ram_data in ram_entries:
        ram_type = (ram_data.get('specs') or {}).get('memory_type') or ram_data.get('memory_type', '')
        ram_type_str = ram_type[0] if isinstance(ram_type, list) else str(ram_type)
        for mb_part, mb_data in mb_entries:
            mb_mem   = (mb_data.get('specs') or {}).get('memory_type') or mb_data.get('memory_type', '')
            mb_types = [t.upper() for t in mb_mem] if isinstance(mb_mem, list) \
                       else ([str(mb_mem).upper()] if mb_mem else [])
            if ram_type_str and mb_types:
                if ram_type_str.upper() in mb_types:
                    lines.append(
                        f"- メモリ規格照合: {ram_part}({ram_type_str}) "
                        f"vs {mb_part}({mb_mem}) = OK（対応）"
                    )
                else:
                    lines.append(
                        f"- メモリ規格照合: {ram_part}({ram_type_str}) "
                        f"vs {mb_part}({mb_mem}) = NG（非対応）"
                    )

    # CPU TDP ↔ CPUクーラー 冷却能力照合
    for cpu_part, cpu_data in cpu_entries:
        cpu_tdp = (cpu_data.get('specs') or {}).get('tdp_w') or cpu_data.get('tdp_w')
        if cpu_tdp is None:
            continue
        for cooler_part, cooler_data in cooler_entries:
            cooler_tdp = (cooler_data.get('specs') or {}).get('tdp_rating_w') or cooler_data.get('tdp_rating_w')
            if cooler_tdp is None:
                lines.append(
                    f"- CPU冷却能力照合: {cpu_part}(TDP {cpu_tdp}W) "
                    f"vs {cooler_part}(定格: 未公開) = WARNING（冷却能力未公開のため確認推奨）"
                )
            else:
                try:
                    cpu_w    = float(cpu_tdp)
                    cooler_w = float(cooler_tdp)
                    if cpu_w <= cooler_w:
                        lines.append(
                            f"- CPU冷却能力照合: {cpu_part}(TDP {cpu_w:.0f}W) "
                            f"vs {cooler_part}(定格 {cooler_w:.0f}W) = OK（冷却能力十分）"
                        )
                    else:
                        lines.append(
                            f"- CPU冷却能力照合: {cpu_part}(TDP {cpu_w:.0f}W) "
                            f"vs {cooler_part}(定格 {cooler_w:.0f}W) = NG（冷却能力不足 {cpu_w - cooler_w:.0f}W超過）"
                        )
                except (ValueError, TypeError):
                    pass

    # PSU ワット数チェック
    _SYS_BASE_W = 50  # システム固定消費電力（MB・RAM・ストレージ概算）
    for psu_part, psu_data in psu_entries:
        psu_w_raw = (psu_data.get('specs') or {}).get('wattage_w') or psu_data.get('wattage_w')
        if psu_w_raw is None:
            continue
        try:
            psu_w = float(psu_w_raw)
        except (ValueError, TypeError):
            continue

        gpu_tdp_total = 0.0
        for _, gd in gpu_entries:
            v = (gd.get('specs') or {}).get('tdp_w') or gd.get('tdp_w')
            if v is not None:
                try:
                    gpu_tdp_total += float(v)
                except (ValueError, TypeError):
                    pass

        cpu_tdp_total = 0.0
        for _, cd in cpu_entries:
            v = (cd.get('specs') or {}).get('tdp_w') or cd.get('tdp_w')
            if v is not None:
                try:
                    cpu_tdp_total += float(v)
                except (ValueError, TypeError):
                    pass

        if gpu_tdp_total == 0.0 and cpu_tdp_total == 0.0:
            continue  # 消費電力データ不足 → Claudeに委ねる

        total_w = gpu_tdp_total + cpu_tdp_total + _SYS_BASE_W
        usage_pct = total_w / psu_w * 100

        if usage_pct > 90:
            status = (
                f"NG（電源容量不足: 推定{total_w:.0f}W / {psu_w:.0f}W = {usage_pct:.0f}%、"
                f"容量{total_w - psu_w:.0f}W超過）"
            )
        elif usage_pct > 75:
            status = (
                f"WARNING（使用率{usage_pct:.0f}%、25%以上のマージン推奨: "
                f"推定{total_w:.0f}W / {psu_w:.0f}W）"
            )
        else:
            status = f"OK（使用率{usage_pct:.0f}%、推定{total_w:.0f}W / {psu_w:.0f}W）"

        lines.append(
            f"- PSUワット数チェック: {psu_part}({psu_w:.0f}W) "
            f"vs 推定消費電力{total_w:.0f}W"
            f"(GPU:{gpu_tdp_total:.0f}W + CPU:{cpu_tdp_total:.0f}W + システム{_SYS_BASE_W}W)"
            f" = {status}"
        )

    # MB フォームファクター ↔ ケース互換チェック
    for mb_part, mb_data in mb_entries:
        mb_ff = (mb_data.get('specs') or {}).get('form_factor') or mb_data.get('form_factor', '')
        if not mb_ff:
            continue
        for case_part, case_data in case_entries:
            case_ff = (case_data.get('specs') or {}).get('form_factor') or case_data.get('form_factor', '')
            if not case_ff:
                continue
            allowed = _CASE_FF_COMPAT.get(case_ff.strip(), set())
            if mb_ff.strip() in allowed:
                lines.append(
                    f"- MBフォームファクター互換: {mb_part}({mb_ff}) "
                    f"vs {case_part}(対応: {case_ff}) = OK（対応）"
                )
            else:
                lines.append(
                    f"- MBフォームファクター互換: {mb_part}({mb_ff}) "
                    f"vs {case_part}(対応: {case_ff}) = NG（非対応: {case_ff}ケースに{mb_ff}は非対応）"
                )

    return lines


def _run_pc_diagnosis_with_claude(parts: list, specs: dict) -> dict:
    """
    Claude Haiku でPC部品互換性を診断して結果を返す。
    戻り値: {"verdict": ..., "checks": [...], "summary": ...}
    """
    if not CLAUDE_API_KEY:
        return {
            'verdict': 'UNKNOWN',
            'checks': [],
            'summary': 'ANTHROPIC_API_KEY が設定されていません',
        }

    _SKIP_KEYS = {'source', 'part_no', 'product_id', 'product_url', 'size_raw',
                  'psu_raw', 'connector_raw', 'slot_raw', 'boost_clock',
                  'display_output', 'bus_interface', 'm1_id'}
    specs_lines = []
    for part in parts:
        if part in specs:
            p = specs[part]
            maker = p.get('manufacturer') or p.get('maker') or p.get('source', '')
            specs_lines.append(
                f"**{part}** (maker={maker}, category={p.get('category', '')})"
            )
            nested = p.get('specs', {})
            if nested:
                for k, v in nested.items():
                    specs_lines.append(f"  {k}: {v}")
            else:
                for k, v in p.items():
                    if k not in _SKIP_KEYS and v is not None and v != '':
                        specs_lines.append(f"  {k}: {v}")
        else:
            specs_lines.append(f"**{part}** (スペック未取得 - 型番から推定)")

    precheck_lines = _compute_prechecks(parts, specs)

    user_message = (
        "以下のPC部品の互換性を診断してください。\n\n"
        "## 部品リスト\n"
        + "\n".join(f"- {p}" for p in parts)
        + "\n\n## 取得済みスペック\n"
        + ("\n".join(specs_lines) if specs_lines else "（スペックデータなし）")
        + (
            "\n\n## 事前計算済みチェック（この数値・判定を最優先で使用すること）\n"
            + "\n".join(precheck_lines)
            if precheck_lines else ""
        )
        + "\n\nJSON形式のみで返してください。"
    )

    req_body = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 1024,
        'system': _PC_DIAGNOSIS_SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user_message}],
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=req_body,
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': CLAUDE_API_KEY,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        resp_data = json.loads(resp.read().decode('utf-8'))

    content = resp_data.get('content', [{}])[0].get('text', '{}')

    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            'verdict': 'UNKNOWN',
            'checks': [],
            'summary': f'診断結果のパースに失敗しました: {content[:200]}',
        }


# ================================================================
# アフィリエイトタグ注入ヘルパー
# ================================================================

def _inject_affiliate_tags(html: str) -> str:
    """HTMLのプレースホルダーに環境変数のアフィリエイトIDを注入する。"""
    amazon_tag   = os.environ.get('AMAZON_TAG',    'pccompat-22')
    rakuten_a_id = os.environ.get('RAKUTEN_A_ID',  '')
    rakuten_l_id = os.environ.get('RAKUTEN_L_ID',  '')
    html = html.replace("'__AMAZON_TAG__'",   f"'{amazon_tag}'")
    html = html.replace("'__RAKUTEN_A_ID__'", f"'{rakuten_a_id}'")
    html = html.replace("'__RAKUTEN_L_ID__'", f"'{rakuten_l_id}'")
    return html


# ================================================================
# Flask ルート
# ================================================================

@app.route('/')
@app.route('/compat')
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = _inject_affiliate_tags(html)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/<path:filename>')
def static_pages(filename):
    """ガイド・構成例・ブログ等の静的HTMLページを配信（アフィリエイトタグ注入付き）"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not filename.endswith('.html'):
        return send_from_directory(static_dir, filename)
    html_path = os.path.join(static_dir, filename)
    if not os.path.isfile(html_path):
        return 'Not Found', 404
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = _inject_affiliate_tags(html)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True) or {}
        parts = data.get('parts', [])

        if not parts or not isinstance(parts, list):
            return jsonify(
                {'error': 'parts は文字列リストで指定してください（例: ["RTX 4090", "NZXT H510"]）'}
            ), 400

        if len(parts) > 20:
            return jsonify({'error': 'parts は最大20件まで指定可能です'}), 400

        specs = _lookup_pc_specs(parts)
        not_found = [p for p in parts if p not in specs]
        diagnosis = _run_pc_diagnosis_with_claude(parts, specs)

        return jsonify({
            'verdict':   diagnosis.get('verdict', 'UNKNOWN'),
            'checks':    diagnosis.get('checks', []),
            'summary':   diagnosis.get('summary', ''),
            'not_found': not_found,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================================================================
# チャット型番抽出プロンプト
# ================================================================

_EXTRACT_SYSTEM_PROMPT = """\
あなたはPC自作パーツ型番抽出アシスタントです。
ユーザーのメッセージからPCパーツの型番・製品名を抽出し、必ずJSON形式だけで返してください。

## 抽出対象カテゴリ
GPU, CPU, マザーボード, PCケース, 電源(PSU), メモリ(RAM), CPUクーラー

## 出力形式（JSONのみ）
{
  "parts": ["型番1", "型番2"],
  "missing": ["gpu", "case"],
  "reply": "ユーザーへの返答（日本語・1〜2文）"
}

## ルール
- parts: 会話全体（history含む）から抽出した全型番リスト
- missing: 診断に有用だが未記載のカテゴリ（gpu/cpu/motherboard/case/psu/ram/cooler）
- parts が2件以上あれば reply は「診断します」旨の短文
- parts が1件のみなら reply で不足カテゴリを1つだけ追加質問
- parts が0件なら reply で型番入力を促す（例を1つ示す）
- 型番は正式名称に近い形で抽出すること（例: "RTX 4070" → "RTX 4070"）
"""


def _extract_parts_with_claude(message: str, history: list) -> dict:
    """自然言語メッセージから型番を抽出する。戻り値: {parts, missing, reply}"""
    if not CLAUDE_API_KEY:
        return {'parts': [], 'missing': [], 'reply': '型番を直接入力してください。'}

    messages = []
    for h in history[-6:]:  # 直近6ターンのみ
        if h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': message})

    req_body = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 512,
        'system': _EXTRACT_SYSTEM_PROMPT,
        'messages': messages,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=req_body,
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': CLAUDE_API_KEY,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp_data = json.loads(resp.read().decode('utf-8'))

    content = resp_data.get('content', [{}])[0].get('text', '{}')
    m = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if m:
        content = m.group(1)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {'parts': [], 'missing': [], 'reply': 'もう一度型番を教えてください。'}


@app.route('/api/chat', methods=['POST'])
def chat():
    """自然言語メッセージを受け取り、型番抽出→互換性診断を行う。"""
    try:
        data = request.get_json(force=True) or {}
        message = str(data.get('message', '')).strip()
        history = data.get('history', [])

        if not message:
            return jsonify({'error': 'message が空です'}), 400

        # 型番抽出
        extracted = _extract_parts_with_claude(message, history)
        parts = extracted.get('parts', [])
        reply = extracted.get('reply', '')

        # 型番が不足している場合は clarify を返す
        if len(parts) < 2:
            return jsonify({
                'type': 'clarify',
                'reply': reply,
                'parts': parts,
            })

        # 診断実行
        specs = _lookup_pc_specs(parts)
        not_found = [p for p in parts if p not in specs]
        diagnosis = _run_pc_diagnosis_with_claude(parts, specs)

        return jsonify({
            'type': 'diagnosis',
            'reply': reply or f'{len(parts)}件のパーツを診断しました。',
            'parts': parts,
            'not_found': not_found,
            'diagnosis': {
                'verdict': diagnosis.get('verdict', 'UNKNOWN'),
                'checks':  diagnosis.get('checks', []),
                'summary': diagnosis.get('summary', ''),
            },
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alternatives')
def alternatives():
    """NG/WARNINGパーツの代替品をDBから返す。"""
    try:
        category  = request.args.get('category', '')   # 'gpu' or 'case'
        case_name = request.args.get('case_name', '')
        gpu_name  = request.args.get('gpu_name', '')

        amazon_tag   = os.environ.get('AMAZON_TAG',   'pccompat-22')
        rakuten_a_id = os.environ.get('RAKUTEN_A_ID', '')
        rakuten_l_id = os.environ.get('RAKUTEN_L_ID', '')

        def make_amazon_url(name):
            q = urllib.parse.quote(name)
            return f'https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}'

        def make_rakuten_url(name):
            q = urllib.parse.quote(name)
            if rakuten_a_id and rakuten_l_id:
                return (
                    f'https://hb.afl.rakuten.co.jp/hgc/{rakuten_a_id}/{rakuten_l_id}/?'
                    f'pc=https://search.rakuten.co.jp/search/mall/{q}/&link_type=hybrid_url&ts=1'
                )
            return f'https://search.rakuten.co.jp/search/mall/{q}/'

        # 全商品を読み込む
        jsonl_paths = glob_module.glob(
            os.path.join(_PC_WORKSPACE_DIR, 'data', '*', 'products.jsonl')
        )
        all_products = []
        for path in jsonl_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_products.append(json.loads(line))
            except Exception:
                pass

        result = []

        if category == 'gpu' and case_name:
            # ケース名からケーススペックを取得して max_gpu_length_mm を調べる
            case_specs = _lookup_pc_specs([case_name])
            case_data  = case_specs.get(case_name, {})
            max_len = (case_data.get('specs') or {}).get('max_gpu_length_mm') \
                      or case_data.get('max_gpu_length_mm')
            try:
                max_len = float(str(max_len).replace('mm', '').strip()) if max_len else None
            except (ValueError, TypeError):
                max_len = None

            for p in all_products:
                if p.get('category') != 'gpu':
                    continue
                gpu_len_raw = (p.get('specs') or {}).get('length_mm') or p.get('length_mm')
                try:
                    gpu_len = float(str(gpu_len_raw).replace('mm', '').strip()) if gpu_len_raw else None
                except (ValueError, TypeError):
                    gpu_len = None

                # 長さ制約を満たすGPUのみ（max_len不明な場合は全件）
                if max_len and gpu_len and gpu_len > max_len:
                    continue

                s = p.get('specs', {}) or {}
                result.append({
                    'name':        p.get('name', ''),
                    'maker':       p.get('maker', ''),
                    'specs': {
                        'length_mm':       s.get('length_mm') or p.get('length_mm'),
                        'tdp_w':           s.get('tdp_w') or p.get('tdp_w'),
                        'power_connector': s.get('power_connector') or p.get('power_connector'),
                        'vram':            s.get('vram') or p.get('vram'),
                    },
                    'amazon_url':  make_amazon_url(p.get('name', '')),
                    'rakuten_url': make_rakuten_url(p.get('name', '')),
                })
                if len(result) >= 6:
                    break

        elif category == 'case' and gpu_name:
            # GPU名からGPUスペックを取得して length_mm を調べる
            gpu_specs = _lookup_pc_specs([gpu_name])
            gpu_data  = gpu_specs.get(gpu_name, {})
            gpu_len_raw = (gpu_data.get('specs') or {}).get('length_mm') or gpu_data.get('length_mm')
            try:
                gpu_len = float(str(gpu_len_raw).replace('mm', '').strip()) if gpu_len_raw else None
            except (ValueError, TypeError):
                gpu_len = None

            for p in all_products:
                if p.get('category') != 'case':
                    continue
                s = p.get('specs', {}) or {}
                max_len_raw = s.get('max_gpu_length_mm') or p.get('max_gpu_length_mm')
                try:
                    max_len = float(str(max_len_raw).replace('mm', '').strip()) if max_len_raw else None
                except (ValueError, TypeError):
                    max_len = None

                # GPUが収まるケースのみ（gpu_len不明な場合は全件）
                if gpu_len and max_len and max_len < gpu_len:
                    continue

                result.append({
                    'name':  p.get('name', ''),
                    'maker': p.get('maker', ''),
                    'specs': {
                        'max_gpu_length_mm': s.get('max_gpu_length_mm') or p.get('max_gpu_length_mm'),
                        'form_factors':      s.get('form_factors') or p.get('form_factors'),
                        'dimensions':        s.get('dimensions') or p.get('dimensions'),
                    },
                    'amazon_url':  make_amazon_url(p.get('name', '')),
                    'rakuten_url': make_rakuten_url(p.get('name', '')),
                })
                if len(result) >= 6:
                    break

        return jsonify({'alternatives': result})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
