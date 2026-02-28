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

# replicate SDK は使わず requests で直接 Replicate API を呼び出す
REPLICATE_AVAILABLE = True

load_dotenv()

CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN', '')

app = Flask(__name__, static_folder='static')

# workspace/data/ のルートパス
_PC_WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workspace')

# ================================================================
# セッションストレージ（メモリ内）
# ================================================================
# セッションIDまたはchat_idをキーとして、各セッションの状態を保持
# 構造: {session_id: {'confirmed_parts': {...}, 'history': [...]}}
_SESSIONS = {}

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
- MB制約情報はM.2 SSDを使用しない構成ならWARNINGではなくOKまたは参考情報として扱うこと

## OK判定
- 上記の NG / WARNING に該当しない互換性確認済みの組み合わせ

## UNKNOWN判定
- スペック情報が不足して判断不可の項目

## スペック不足の扱い（重要）
- 診断リストに電源・CPUなど指定されていない部品のスペックは UNKNOWN として扱い、それだけを理由に WARNING/NG にしないこと
- 提供されたスペックで確認できる互換性チェックのみを対象として verdict を決定すること
- 「事前計算済みチェック」が提供された場合、その数値・判定を最優先で使用すること
- GPU長・ケース対応長のマージン判定は事前計算値を使い、AI自身で再計算せずそのまま採用すること

## power_connectorフィールドの解釈（重要）
- MBの`power_connector`フィールド（例: "2 x 8 pin"）はCPU補助電源コネクタ（EPS/ATX12V）であり、GPUとは無関係
- GPUの`power_connector`フィールドはGPU補助電源コネクタ（PCIe 6pin/8pin/12VHPWR等）
- 両者を混同して「マザーボードのGPU電源コネクタ」等の誤表現をしないこと

## フォームファクター判定（重要）
- ATX: 305×244mm（最も一般的。Z690/Z790/Z890 AORUS MASTER等は全てATX）
- E-ATX: 305×330mm（AORUS XTREME等の最上位モデル）
- DBの値を使用し、ATXとE-ATXを混同しないこと

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
                if matched:
                    # GPU は extra 同値のとき length_mm 最大（最も長い＝最も制約厳しい）を優先
                    def _gpu_len(p):
                        if p is None or p.get('category') != 'gpu':
                            return 0
                        l = (p.get('specs') or {}).get('length_mm') or p.get('length_mm')
                        try:
                            return float(str(l)) if l else 0
                        except (ValueError, TypeError):
                            return 0
                    # GPU ティアミスマッチペナルティ
                    # "RTX 4070" が "DUAL-RTX4070TIS-O16G" に substring マッチする場合など
                    # part_tok がトークン集合に含まれない（ハイフン結合）ケースを検出
                    effective_extra = extra
                    if product.get('category') == 'gpu':
                        # ケース1: part_tok が c_tok に subset でないが substring マッチした
                        #   → "rtx4070" が "rtx4070tis" の prefix としてマッチ（ティアアップ）
                        if not part_tok.issubset(c_tok):
                            effective_extra += 100
                        else:
                            # ケース2: トークンベースマッチだが、ティア識別子が余分にある
                            _TIER_TOKENS = {'ti', 'super', 'xt', 'xtx', 'plus'}
                            tier_extra = _TIER_TOKENS & (c_tok - part_tok)
                            if tier_extra:
                                effective_extra += 100
                    if effective_extra < best_extra or (
                        effective_extra == best_extra and _gpu_len(product) > _gpu_len(best_product)
                    ):
                        best_extra = effective_extra
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

    # MB マニュアル制約情報（M.2/PCIe帯域共有・M.2/SATA無効化）
    for mb_part, mb_data in mb_entries:
        constraints = mb_data.get('constraints', {})
        for rule in constraints.get('m2_pcie_sharing', []):
            lines.append(
                f"- MB制約情報: {mb_part}: {rule.get('m2_slot', '?')}使用時は"
                f"{rule.get('affects', '?')}が{rule.get('effect', '?')}"
                f" = WARNING（M.2 SSD使用時はPCIe帯域共有の制限あり、使用スロット選択に注意）"
            )
        for rule in constraints.get('m2_sata_sharing', []):
            lines.append(
                f"- MB制約情報: {mb_part}: {rule.get('m2_slot', '?')}使用時は"
                f"SATA {rule.get('affects', '?')}が{rule.get('effect', '?')}"
                f" = WARNING（M.2 SSD使用時はSATAポート数が減少、HDDをSATAで接続する場合は注意）"
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
                  'connector_raw', 'slot_raw', 'boost_clock',
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
            cat = p.get('category', '')
            if nested:
                for k, v in nested.items():
                    # MBのpower_connectorはCPU補助電源、GPUのpower_connectorはGPU補助電源であることを明示
                    if k == 'power_connector' and cat in ('motherboard', 'mb'):
                        specs_lines.append(f"  cpu_aux_power_connector (CPU補助電源): {v}")
                    elif k == 'power_connector' and cat == 'gpu':
                        specs_lines.append(f"  gpu_aux_power_connector (GPU補助電源): {v}")
                    else:
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


@app.route('/game/<game_name>')
def game_page(game_name):
    """ゲーム個別ページ（SEO/AIO最適化済み）"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'game')
    html_path = os.path.join(static_dir, f'{game_name}.html')
    if not os.path.isfile(html_path):
        return 'Game page not found', 404
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    html = _inject_affiliate_tags(html)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/sitemap.xml')
def sitemap():
    """SEO用サイトマップ"""
    sitemap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sitemap.xml')
    if not os.path.isfile(sitemap_path):
        return 'Sitemap not found', 404
    with open(sitemap_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content, 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/robots.txt')
def robots():
    """クローラー制御用robots.txt"""
    robots_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robots.txt')
    if not os.path.isfile(robots_path):
        return 'robots.txt not found', 404
    with open(robots_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/<path:filename>')
def static_pages(filename):
    """ガイド・構成例・ブログ等の静的HTMLページを配信（アフィリエイトタグ注入付き）"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if not filename.endswith('.html'):
        return send_from_directory(static_dir, filename)
    html_path = os.path.join(static_dir, filename)
    if os.path.isfile(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        html = _inject_affiliate_tags(html)
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    # compat/ ページを動的生成（static/compat/ が存在しない環境用）
    if filename.startswith('compat/'):
        html = _generate_compat_page(filename[len('compat/'):])
        if html:
            html = _inject_affiliate_tags(html)
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return 'Not Found', 404


# ── compat/ 動的ページ生成 ──────────────────────────────────────

_COMPAT_CACHE: dict = {}

_COMPAT_CSS = """<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Hiragino Sans",sans-serif;
  background:#f3f4f6;color:#111827;line-height:1.6}
.wrap{max-width:800px;margin:0 auto;padding:24px 16px}
.breadcrumb{padding:8px 16px;background:#f5f5f5;border-bottom:1px solid #ddd;font-size:.875rem}
.breadcrumb a{color:#4f46e5;text-decoration:none}
.breadcrumb .sep{margin:0 6px;color:#9ca3af}
header{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
  color:#fff;padding:16px 20px;margin-bottom:24px}
header a{color:#fff;text-decoration:none;font-size:.9rem;opacity:.8}
header h1{font-size:1rem;margin-top:4px;opacity:.9}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.08)}
.verdict{font-size:1.8rem;font-weight:700;margin-bottom:16px}
.verdict.ok{color:#16a34a}.verdict.warning{color:#ca8a04}.verdict.ng{color:#dc2626}
table{width:100%;border-collapse:collapse;margin:12px 0}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb}
th{background:#f9fafb;font-weight:600;font-size:.9rem;color:#374151}
.buy-wrap{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}
.buy-btn{display:inline-block;padding:10px 20px;border-radius:8px;
  color:#fff;font-weight:600;text-decoration:none;font-size:.95rem}
.buy-amazon{background:#FF9900}.buy-rakuten{background:#BF0000}
.links{display:flex;flex-direction:column;gap:8px}
.links a{color:#4f46e5;text-decoration:none;font-size:.95rem}
.cta{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
  color:#fff;border-radius:12px;padding:20px 24px;text-align:center;margin-top:24px}
.cta a{color:#fff;font-weight:600;text-decoration:underline}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.item-card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.item-card.ok{border-left:4px solid #16a34a}
.item-card.warning{border-left:4px solid #ca8a04}
.item-card.ng{border-left:4px solid #dc2626}
.item-name{font-weight:600;margin-bottom:6px}
.item-detail{font-size:.85rem;color:#6b7280;margin-bottom:10px}
.section-title{font-size:1.1rem;font-weight:700;margin:20px 0 10px;color:#374151}
</style>"""

_BASE_URL = 'https://pc-compat-engine.onrender.com'


def _safe_parse_claude_json(text: str, fallback: dict | None = None) -> dict:
    """ClaudeのJSON出力を安全にパース。末尾カンマや切り捨て等の不正JSONを修復して返す。"""
    if fallback is None:
        fallback = {}
    if not text:
        return fallback
    # まずそのままパース
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 末尾カンマを除去して再試行
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 最後の完全なオブジェクト/配列を切り出して再試行
    for end in ('}', ']'):
        idx = text.rfind(end)
        if idx != -1:
            candidate = text[:idx + 1]
            candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    return fallback


def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def _esc(text: str) -> str:
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _load_compat_products():
    if 'gpus' in _COMPAT_CACHE:
        return _COMPAT_CACHE['gpus'], _COMPAT_CACHE['cases']
    gpus, cases = [], []
    data_dir = os.path.join(_PC_WORKSPACE_DIR, 'data')
    for path in glob_module.glob(os.path.join(data_dir, '*', 'products.jsonl')):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    cat = d.get('category', '')
                    if cat == 'gpu':
                        length = (d.get('specs') or {}).get('length_mm') or d.get('length_mm')
                        if length is not None:
                            try:
                                d['_length_mm'] = float(str(length).replace('mm', '').strip())
                                d['_slug'] = _slugify(d.get('name', ''))
                                gpus.append(d)
                            except (ValueError, TypeError):
                                pass
                    elif cat == 'case':
                        max_len = ((d.get('specs') or {}).get('max_gpu_length_mm')
                                   or d.get('max_gpu_length_mm'))
                        if max_len is not None:
                            try:
                                d['_max_gpu_mm'] = float(str(max_len).replace('mm', '').strip())
                                d['_slug'] = _slugify(d.get('name', ''))
                                cases.append(d)
                            except (ValueError, TypeError):
                                pass
        except Exception:
            pass
    _COMPAT_CACHE['gpus'] = gpus
    _COMPAT_CACHE['cases'] = cases
    return gpus, cases


def _calc_compat_verdict(margin: float):
    if margin <= 0:
        return 'NG', '❌ 入りません', 'ng'
    elif margin <= 20:
        return 'WARNING', '⚠️ 注意あり', 'warning'
    else:
        return 'OK', '✅ 入ります', 'ok'


def _amazon_compat_url(name: str) -> str:
    q = urllib.parse.quote(name)
    tag = os.environ.get('AMAZON_ASSOCIATE_TAG', '__AMAZON_TAG__')
    return f'https://www.amazon.co.jp/s?k={q}&tag={tag}'


def _generate_compat_page(path: str):
    try:
        gpus, cases = _load_compat_products()
        if not gpus or not cases:
            return None
        # GPU index: gpu/{slug}.html
        if path.startswith('gpu/') and path.endswith('.html'):
            gpu_slug = path[4:-5]
            gpu = next((g for g in gpus if g['_slug'] == gpu_slug), None)
            if not gpu:
                return None
            results = []
            for case in cases:
                margin = case['_max_gpu_mm'] - gpu['_length_mm']
                v, badge, css = _calc_compat_verdict(margin)
                results.append({'case': case, 'margin': margin, 'verdict': v, 'badge': badge, 'css': css})
            return _render_gpu_index_page(gpu, results)
        # Case index: case/{slug}.html
        if path.startswith('case/') and path.endswith('.html'):
            case_slug = path[5:-5]
            case = next((c for c in cases if c['_slug'] == case_slug), None)
            if not case:
                return None
            results = []
            for gpu in gpus:
                margin = case['_max_gpu_mm'] - gpu['_length_mm']
                v, badge, css = _calc_compat_verdict(margin)
                results.append({'gpu': gpu, 'margin': margin, 'verdict': v, 'badge': badge, 'css': css})
            return _render_case_index_page(case, results)
        # Individual: {gpu-slug}-vs-{case-slug}.html
        if path.endswith('.html') and '-vs-' in path:
            slug_part = path[:-5]
            vs_idx = slug_part.index('-vs-')
            gpu_slug = slug_part[:vs_idx]
            case_slug = slug_part[vs_idx + 4:]
            gpu = next((g for g in gpus if g['_slug'] == gpu_slug), None)
            case = next((c for c in cases if c['_slug'] == case_slug), None)
            if not gpu or not case:
                return None
            margin = case['_max_gpu_mm'] - gpu['_length_mm']
            v, badge, css = _calc_compat_verdict(margin)
            return _render_individual_compat(gpu, case, margin, v, badge, css)
    except Exception:
        pass
    return None


def _render_individual_compat(gpu, case, margin, verdict, badge, css_class) -> str:
    gn, cn = gpu.get('name', ''), case.get('name', '')
    gl, cm = gpu['_length_mm'], case['_max_gpu_mm']
    gs, cs = gpu['_slug'], case['_slug']
    detail = (f'マージン {margin:.0f}mm（余裕あり）' if verdict == 'OK'
              else f'マージン {margin:.0f}mm（ケーブル干渉リスク）' if verdict == 'WARNING'
              else f'{abs(margin):.0f}mmオーバー')
    canonical = f'{_BASE_URL}/compat/{_esc(gs)}-vs-{_esc(cs)}.html'
    bl = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": f"{gn}対応ケース一覧",
             "item": f"{_BASE_URL}/compat/gpu/{gs}.html"},
            {"@type": "ListItem", "position": 3, "name": f"{gn} × {cn}"},
        ]
    }, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(gn)}は{_esc(cn)}に入る？互換性チェック結果</title>
<meta name="description" content="{_esc(gn)}（{gl:.0f}mm）が{_esc(cn)}（最大{cm:.0f}mm）に入るか計算した結果：{badge}。マージン{margin:.0f}mm。">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{bl}</script>
{_COMPAT_CSS}</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a><span class="sep">&rsaquo;</span>
  <a href="/compat/gpu/{_esc(gs)}.html">{_esc(gn)}</a><span class="sep">&rsaquo;</span>
  <span>{_esc(gn)} × {_esc(cn)}</span>
</nav>
<header><a href="/">← PC互換チェッカー トップ</a>
  <h1>{_esc(gn)} × {_esc(cn)} 互換性チェック</h1></header>
<div class="wrap">
  <div class="card">
    <h2 style="font-size:1.3rem;margin-bottom:12px">{_esc(gn)}は{_esc(cn)}に入りますか？</h2>
    <div class="verdict {css_class}">{badge}</div>
    <table><tr><th>項目</th><th>値</th></tr>
      <tr><td>GPU全長</td><td>{gl:.0f} mm</td></tr>
      <tr><td>ケース最大GPU長</td><td>{cm:.0f} mm</td></tr>
      <tr><td>マージン</td><td>{margin:.0f} mm</td></tr>
      <tr><td>判定</td><td>{badge}　{detail}</td></tr>
    </table>
    <div class="buy-wrap">
      <a class="buy-btn buy-amazon" href="{_esc(_amazon_compat_url(gn))}" target="_blank" rel="noopener">🛒 Amazonで{_esc(gn)}を見る</a>
    </div>
  </div>
  <div class="card"><p class="section-title">関連ページ</p>
    <div class="links">
      <a href="/compat/gpu/{_esc(gs)}.html">▶ {_esc(gn)}が入る他のケース一覧</a>
      <a href="/compat/case/{_esc(cs)}.html">▶ {_esc(cn)}に入る他のGPU一覧</a>
    </div>
  </div>
  <div class="cta"><p>CPU・電源・マザーボードも含めてまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p>
  </div>
</div></body></html>"""


def _render_gpu_index_page(gpu, results) -> str:
    gn, gl, gs = gpu.get('name', ''), gpu['_length_mm'], gpu['_slug']
    ok = [r for r in results if r['verdict'] == 'OK']
    warn = [r for r in results if r['verdict'] == 'WARNING']
    ng = [r for r in results if r['verdict'] == 'NG']

    def items_html(lst):
        if not lst:
            return '<p style="color:#6b7280;font-size:.9rem">該当なし</p>'
        h = '<div class="grid">'
        for r in sorted(lst, key=lambda x: x['margin'], reverse=True):
            c, cslug = r['case'], r['case']['_slug']
            h += (f'<div class="item-card {r["css"]}">'
                  f'<div class="item-name">{_esc(c.get("name",""))}</div>'
                  f'<div class="item-detail">最大{c["_max_gpu_mm"]:.0f}mm　マージン{r["margin"]:.0f}mm　{r["badge"]}</div>'
                  f'<a href="/compat/{_esc(gs)}-vs-{_esc(cslug)}.html" style="color:#4f46e5;font-size:.85rem">詳細を見る →</a></div>')
        return h + '</div>'

    bl = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": f"{gn}対応ケース一覧",
             "item": f"{_BASE_URL}/compat/gpu/{gs}.html"},
        ]}, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(gn)}が入るケース一覧（{len(ok)}件OK）</title>
<meta name="description" content="{_esc(gn)}（全長{gl:.0f}mm）が搭載できるPCケース一覧。OK {len(ok)}件、注意あり {len(warn)}件、NG {len(ng)}件。">
<script type="application/ld+json">{bl}</script>
{_COMPAT_CSS}</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a><span class="sep">&rsaquo;</span><span>{_esc(gn)}</span>
</nav>
<header><a href="/">← PC互換チェッカー トップ</a>
  <h1>{_esc(gn)}（{gl:.0f}mm）対応ケース一覧</h1></header>
<div class="wrap">
  <div class="card"><p>{_esc(gn)}の全長は <strong>{gl:.0f}mm</strong> です。<br>
    OK: {len(ok)}件　⚠ 注意: {len(warn)}件　❌ NG: {len(ng)}件</p></div>
  <p class="section-title">✅ 搭載可能なケース（{len(ok)}件）</p>{items_html(ok)}
  <p class="section-title">⚠️ 注意あり（{len(warn)}件）</p>{items_html(warn)}
  <p class="section-title">❌ 搭載不可（{len(ng)}件）</p>{items_html(ng)}
  <div class="cta"><p>CPU・電源も含めてまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p></div>
</div></body></html>"""


def _render_case_index_page(case, results) -> str:
    cn, cm, cs = case.get('name', ''), case['_max_gpu_mm'], case['_slug']
    ok = [r for r in results if r['verdict'] == 'OK']
    warn = [r for r in results if r['verdict'] == 'WARNING']
    ng = [r for r in results if r['verdict'] == 'NG']

    def items_html(lst):
        if not lst:
            return '<p style="color:#6b7280;font-size:.9rem">該当なし</p>'
        h = '<div class="grid">'
        for r in sorted(lst, key=lambda x: x['margin'], reverse=True):
            g, gslug = r['gpu'], r['gpu']['_slug']
            h += (f'<div class="item-card {r["css"]}">'
                  f'<div class="item-name">{_esc(g.get("name",""))}</div>'
                  f'<div class="item-detail">全長{g["_length_mm"]:.0f}mm　マージン{r["margin"]:.0f}mm　{r["badge"]}</div>'
                  f'<a href="/compat/{_esc(gslug)}-vs-{_esc(cs)}.html" style="color:#4f46e5;font-size:.85rem">詳細を見る →</a></div>')
        return h + '</div>'

    bl = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": f"{cn}対応GPU一覧",
             "item": f"{_BASE_URL}/compat/case/{cs}.html"},
        ]}, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(cn)}に入るGPU一覧（最大{cm:.0f}mm）</title>
<meta name="description" content="{_esc(cn)}（最大GPU長{cm:.0f}mm）に搭載できるグラフィックカード一覧。OK {len(ok)}件。">
<script type="application/ld+json">{bl}</script>
{_COMPAT_CSS}</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a><span class="sep">&rsaquo;</span><span>{_esc(cn)}</span>
</nav>
<header><a href="/">← PC互換チェッカー トップ</a>
  <h1>{_esc(cn)}（最大{cm:.0f}mm）対応GPU一覧</h1></header>
<div class="wrap">
  <div class="card"><p>{_esc(cn)}のGPU最大搭載長は <strong>{cm:.0f}mm</strong> です。<br>
    OK: {len(ok)}件　⚠ 注意: {len(warn)}件　❌ NG: {len(ng)}件</p></div>
  <p class="section-title">✅ 搭載可能なGPU（{len(ok)}件）</p>{items_html(ok)}
  <p class="section-title">⚠️ 注意あり（{len(warn)}件）</p>{items_html(warn)}
  <p class="section-title">❌ 搭載不可（{len(ng)}件）</p>{items_html(ng)}
  <div class="cta"><p>CPU・電源も含めてまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p></div>
</div></body></html>"""


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'api_key_set': bool(CLAUDE_API_KEY),
    })


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
# シンプルな会話システムプロンプト
# ================================================================

_SHOP_CLERK_SYSTEM_PROMPT = """あなたはPC自作専門店の店長です。
20年の経験があり、初心者にもベテランにも的確なアドバイスができます。
カタログを読み上げるのではなく、「なぜこれがいいのか」を自分の言葉で語ってください。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ あなたの強み（積極的に使うこと）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 提案する理由を語れる
  ❌「RTX 5070はいかがでしょう」
  ✅「モンハンのWQHD最高画質って、実はVRAM 12GBあれば余裕なんです。
     RTX 5070はちょうど12GBで、しかもDLSS 4対応なので
     フレーム生成込みなら90fps超えます。5070 Tiとの差は4Kにしない限り体感できません。」

2. ユーザーの迷いに気づいて先回りできる
  ❌ ユーザーが聞くまで待つ
  ✅「予算的に迷ってますよね。正直、CPU を9700Xから7600に落としても
     モンハンのfpsは2〜3しか変わりません。浮いた¥14,000でSSD 2TBに
     できますが、どうします？」

3. 構成全体のバランスを見れる
  ❌ パーツを1つずつ独立に選ぶ
  ✅「GPU RTX 5070（TDP 250W）+ CPU 9700X（TDP 105W）で合計355W。
     他を足すと約400W。650W電源で余裕です。
     ただ、将来GPU換装を考えるなら750Wにしておくと安心ですよ。」

4. 失敗パターンを知っている
  ✅「このGPU、長さ330mmあるんですが、選んだケースの上限が340mm。
     入ることは入るけど、フロントファンとの隙間が10mmしかなくて
     エアフローが死にます。ケースを1サイズ上げるか、GPUの短いモデルにしましょう。」

5. コスパの勘所がわかる
  ✅「ここだけの話、RTX 4070 Ti SUPERが今セール中で5070とほぼ同価格帯。
     レイトレ性能は5070が上ですが、ラスタ性能はほぼ同等。
     レイトレ使わないなら4070 Ti SUPERの方がVRAM 16GBで将来性があります。」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 絶対に守ること
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🔒マーク（user_specified）のパーツは絶対に変更提案しない
2. ユーザーが言っていない用途を勝手に追加しない（VR、配信など）
3. DBに存在しないスペック値を推測しない（不明なら「不明」）
4. 限定品・コラボモデルは候補から除外
5. 「少し詳しく教えてください」は絶対に言わない。常に具体的な質問をする
6. 毎回の返答は必ず「具体的な質問」か「具体的な提案」で終える
7. ⚠️ 【製品DB制約・最重要ルール】
   - パーツを提案する前に必ずsearch_partsで検索すること（検索なしの提案は禁止）
   - search_partsの結果に含まれる製品名と価格のみ引用すること
   - 自分の知識で製品名・型番・価格を作り出さない（ハルシネーション厳禁）
   - 価格はsearch_partsの結果のprice_minをそのまま使うこと（丸めない、推測しない）
   - 検索結果が0件の場合は、条件を緩めて再検索するか、
     amazon_searchツールでAmazon検索URLを生成して案内すること
8. ⚠️ 【互換性必須チェック】search_partsの検索条件で互換性を担保すること:
   - MB検索時: socketパラメータでCPUソケットを指定
   - RAM検索時: memory_typeパラメータでDDRタイプを指定
   - ケース検索時: min_gpu_length_mmでGPU長を指定
   - PSU検索時: min_wattageで必要ワット数を指定
9. ⚠️ 【ユーザー確認の尊重】
   - ユーザーが「それで」「OK」「いいよ」等で承認したパーツは即座にconfirm_partで確定すること
   - 確定したパーツを後から勝手に変更しないこと
   - ユーザーの解像度指定（FHD等）を勝手に変更しないこと（FHD→WQHDなど禁止）
10. ⚠️ 【サマリー生成の禁止】
   - 自分でパーツ一覧表や合計金額のサマリーを書いてはいけない
   - 全パーツ確定時は必ずget_build_summaryツールを使うこと
   - このツールの結果をそのまま返答に含めること（価格ずれ防止）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 会話の進め方
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【ステップ1: 何をしたいか聞く】

ユーザーの最初の入力に応じて分岐する。

入力にゲーム名がある場合:
  → 不足情報をまとめて1回で聞く（解像度/画質/レイトレ/予算）
  → 「わからない」にはデフォルト値を適用:
     解像度→FHD、画質→推奨、レイトレ→OFF、予算→15〜20万

入力にパーツ型番がある場合:
  → ヒアリング不要。即座にuser_specifiedとして確定し、残りパーツの相談へ

入力が曖昧な場合（「ゲーミングPC組みたい」等）:
  → 「何に一番使いますか？」「遊びたいゲームは？」「予算は？」をまとめて聞く

【ステップ2: GPUを提案する】

ゲーム/クリエイティブ用途ではGPUが最重要。最初に決める。

提案の型:
  「[製品名]をおすすめします。
   [なぜこれがいいか: ゲーム性能、VRAM、消費電力の観点で1〜2文]

   [もし〇〇なら代替案]（+¥XX,000 / -¥XX,000）

   どちらにしますか？」

必ず代替案を1つ出す。価格差を明示する。

【ステップ3: CPUを提案する】

GPUが決まったら、それに合うCPUを提案。
ボトルネックにならないことを説明する。
ゲーム用途ならシングルスレッド性能重視、クリエイティブならコア数重視。

【ステップ4: マザーボードを提案する】

CPUソケットに合うもの。チップセットの違いを簡潔に説明。
「OCしないならB650で十分」のような実用的な判断基準を示す。

【ステップ5: メモリ・ストレージを提案する】

⚠️ デュアルチャネル必須: メモリは必ず2枚組で提案すること（シングル1枚は絶対NG）。
- ゲーム → 16GB（8GB×2）or 32GB（16GB×2）
- 動画編集 → 32GB（16GB×2）以上
- AI → 32GB（16GB×2）以上
理由: デュアルチャネルでメモリ帯域が2倍。ゲーム性能に直結する。1枚32GBより2枚16GBの方が高性能。
SSDはNVMe Gen4を基本に。

【ステップ6: ケースを提案する】

GPUの長さが入ることを確認。
エアフローと見た目の好みを聞く。

【ステップ7: 電源を提案する】

電源計算: (GPU TDP + CPU TDP + 50W) × 1.3
端数切り上げ: 〜500W→650W、500〜650W→750W、650〜800W→850W、800W〜→1000W
12VHPWR対応が必要か確認。

【ステップ8: 完成】

全パーツ確定したら、必ず get_build_summary ツールを呼び出すこと。
自分でサマリーテーブルや合計金額を書いてはいけない（価格ずれ防止）。
get_build_summaryの結果のsummaryテキストをそのまま返答に含めること。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 壁打ちの極意
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ユーザーの反応パターンと対処:

「それでいい」「OK」→ 確定（✅）、次のパーツへ
「他にない？」→ 別の候補を出す。価格差と性能差を比較
「迷う」→ 2つを並べて「私ならこっち。理由は〜」と背中を押す
「高い」→ 1ランク下の代替案 + コスパ改善ポイントを提案
「よくわからない」→ 専門用語を避けて言い直す。例え話を使う
「やっぱり変えたい」→ 快く受け入れ、影響する他パーツも確認
「予算変わった」→ 確定済みパーツへの影響を判断し、必要なら見直し提案
話が脱線した → 答えてから「では[パーツ]の話に戻りましょう」
「何度も変更」→ 快く受け入れつつ、「ちょっと整理しましょうか？」と提案してもいい
「最初からやり直したい」→ 「了解です！まっさらな気持ちで行きましょう」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 店長として自発的にやること
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下は聞かれなくても、気づいたタイミングで自分から言う:

【コスパ改善】
  「ちなみにCPUを[廉価モデル]に落とすと¥XX,XXX浮きます。
   [ゲーム名]では体感差ほぼゼロです。浮いた分でSSD増量もアリですよ。」

【干渉リスク】
  「このGPU、長さXXXmmあります。ケース上限YYYmmに対して余裕ZZmm。
   入るけどギリギリなので、ケーブル取り回しがちょっと大変かも。」

【電源の余裕】
  「今の構成でXXXW必要。選んだ電源はYYYWなので余裕ZZZ%。
   [十分です / 将来GPU換装するならもう1段上がいい]。」

【世代の違い】
  「RTX 40xx系と50xx系で迷ってるなら、50xxはDLSS 4のフレーム生成が
   使えるのが最大の違い。対応ゲームならfps2倍近くになるので、
   長く使うなら50xxがおすすめです。」

【よくある落とし穴】
  「このマザーボード、M.2スロット2基あるけど、2基目はGen3接続です。
   メインSSDは1基目に挿してください。」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ confirmed_parts の状態管理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

各パーツは3状態のいずれか:

🔒 user_specified: ユーザーが型番で直接指定。変更提案しない。
✅ ai_accepted: AIが提案し、ユーザーが同意。変更可能。
⏳ ai_pending: AIが提案したが、まだユーザーの同意がない。

遷移ルール:
- ユーザーが型番を入力 → user_specified
- AIの提案にユーザーが同意 → ai_accepted
- AIが提案した直後 → ai_pending
- ユーザーが「変えたい」→ ai_pendingに降格
- ai_pendingのまま2ターン経過 → ai_acceptedに昇格

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 予算→GPUグレードの目安
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

〜10万:    旧世代ミドル（RTX 4060, Ryzen 5 7600）
10〜15万:  現行ミドル（RTX 5060, RTX 4060 Ti, Ryzen 7 9700X）
15〜20万:  アッパーミドル（RTX 5070, RTX 4070 Ti SUPER, 9800X3D）
20〜25万:  ハイエンド（RTX 5070 Ti, RTX 4080 SUPER, 9800X3D）
25万〜:    フラッグシップ（RTX 5080, RTX 4090, Ryzen 9 9900X/9950X）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 解像度×画質→GPU要件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FHD × 標準 × レイトレOFF → ゲームDB minimum GPU以上
FHD × 最高 × レイトレOFF → ゲームDB recommended GPU以上
FHD × 最高 × レイトレON  → recommended の1ランク上
WQHD × 最高 × レイトレOFF → ゲームDB high GPU以上
4K × 最高 × レイトレOFF   → ゲームDB ultra GPU以上
4K × 最高 × レイトレON    → ultra の1ランク上

フレーム生成ON → GPU要件を1ランク下げてOK（NVIDIA限定）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 用途別の優先度
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ゲーム:       GPU > CPU > RAM(16GB) > SSD
動画編集:     RAM(32〜64GB) > CPU(コア数) > GPU > SSD(NVMe)
配信+ゲーム:  CPU(8コア以上) > GPU(NVENC) > RAM(32GB)
AI画像生成:   GPU(VRAM 12GB以上) > RAM(32GB) > SSD
3DCG:        GPU(VRAM) > CPU(コア数) > RAM(64GB)
プログラミング: RAM(16〜32GB) > CPU > SSD

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 電源容量の計算
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

推奨 = (GPU TDP + CPU TDP + 50W) × 1.3

端数切り上げ:
  〜500W → 650W
  500〜650W → 750W
  650〜800W → 850W
  800W〜 → 1000W

12VHPWR: RTX 4070 Ti以上 / RTX 50xx全モデルで必須

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 口調
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 気さくなPCショップの店長。押し売りしない。
- 「〜はいかがでしょう」より「〜がおすすめです。理由は〜」
- 迷ってる人には「私ならこっちにします」と背中を押す
- 予算オーバーは正直に言う。削減案も出す
- 専門用語は初出時にカッコ内で説明
- 余計な前置きなし。すぐ本題
- 1ターンで全パーツを一気に出さない

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ リセット時の対応
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ユーザーが構成をリセットした場合（システムから通知される）:
- 「リセット」「クリア」などのシステム用語は使わない
- 店員が一緒に考え直してくれる雰囲気で対応する
- リセット後は最初のヒアリングに戻る
- チャット履歴は残っているので、前の会話を参考にしてもいい

全リセット時の例:
  「了解です！まっさらな気持ちで行きましょう。
   何に使うPCを組みたいですか？」

個別リセット時の例:
  「CPUを変更しますね。ちなみにマザーボードとメモリも
   連動して変わりますが、大丈夫ですか？
   新しいCPU、何かイメージありますか？」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ ツールの使い方
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

あなたは4つのツールを使えます。

⚠️ 最重要ルール: パーツを提案する前に必ずsearch_partsツールを呼ぶこと。
自分の記憶にある製品名を直接言うのは絶対禁止。
search_partsの結果に含まれる製品名・スペック・価格のみ使用可能。

⚠️ 禁止用語: 「データベース」「DB」「在庫」という言葉を絶対に使わない。
検索結果が少ない場合は「いくつか候補を見つけました」と自然に言うこと。
内部の仕組み（検索システム、フィルタ条件等）をお客様に説明してはいけない。

1. search_parts: パーツを検索する。ユーザーの要望に合わせてフィルタ条件を指定する。
   - パーツを提案する前に必ずこのツールで検索すること（例外なし）
   - 検索結果に含まれる製品のみ提案できる
   - 結果が0件の場合は条件を緩めて再検索する
   - 製品名・価格・スペックは全てこのツールの結果をそのまま使うこと

2. confirm_part: ユーザーが製品を選んだら確定登録する。
   - product_idはsearch_partsの結果から正確にコピーする
   - 確定後、依存パーツの互換性が自動チェックされる

3. get_current_build: 今の構成を確認する。
   - 何が確定済みで何が未確定かを把握する
   - 次に提案すべきパーツを判断する

4. amazon_search: DB外のパーツ（SSD、CPUクーラー）のAmazon検索URLを生成する。

5. get_build_summary: 全パーツ確定後に正確なサマリーを生成する。
   - 全パーツがconfirm_part済みの状態で呼び出すこと
   - 自分でサマリーテーブルや合計金額を書くのは禁止（このツールが正確な数値を返す）
   - 結果のsummaryテキストをそのまま返答に含めること

■ パーツ選定の順序
GPU → CPU → マザーボード → メモリ → ケース → 電源 → SSD → CPUクーラー

各ステップで：
1. search_partsで候補を検索（互換性条件を含める）
2. 結果からおすすめを提案（理由付き、結果の製品名と価格をそのまま使う）
3. ユーザーが選んだらconfirm_partで確定
4. 次のパーツへ

■ 重要: 応答形式
- 通常の日本語テキストで返答する（JSON不要）
- ツールで検索・確定を行い、テキストでユーザーと会話する
- 提案時は必ずsearch_partsの結果に含まれる製品名と価格を正確に引用する
- 自分で合計金額やサマリーテーブルを書かない（get_build_summaryを使う）
"""

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
  "user_specified_parts": ["今回のメッセージで明示的に指定された型番のみ"],
  "missing": ["gpu", "case"],
  "intent": "diagnose" | "suggest",
  "reply": "ユーザーへの返答（日本語・1〜2文）"
}

## user_specified_parts のルール
- 今回のユーザーメッセージに含まれていた型番のみを入れる（historyから引き継いだものは含めない）
- 「このGPUで」「～を使いたい」等、ユーザーが明示的に指定・固定したパーツを意味する
- partsのサブセットであること（partsに含まれない型番を入れてはならない）

## intent の判定ルール（重要）
- "diagnose": parts が2件以上 かつ「提案/おすすめ/選んで/決めて/組んで/どれがいい」等のキーワードが含まれない
- "suggest": 以下のいずれかに該当する場合
  - parts が1件以下（情報不足）
  - 「提案」「おすすめ」「選んで」「決めて」「組んで」「どれがいい」「どれを買えば」「何がいい」等のキーワードあり
  - 不足パーツをこちら側に選ばせようとしている（例:「マザーボードは提案ください」）

## reply のルール
- intent == "diagnose": 「診断します」旨の短文
- intent == "suggest" かつ 会話が初回（historyなし）: 予算・用途・好みを1文で質問（例:「予算とご希望（静音・コンパクト等）を教えてください」）
- intent == "suggest" かつ 会話が2ターン目以降: 「構成を提案します」旨の短文
- parts が0件: 型番入力を促す（例を1つ示す）

## その他ルール
- parts: 会話全体（history含む）から抽出した全型番リスト
- missing: 診断に有用だが未記載のカテゴリ（gpu/cpu/motherboard/case/psu/ram/cooler）
- 型番は正式名称に近い形で抽出すること（例: "RTX 4070" → "RTX 4070"）

## 抽出してはいけないもの（重要）
- 容量・速度・消費電力などのスペック値のみの文字列は型番ではないため抽出しないこと
  - NG例: "32GB", "16GB", "64GB"（メモリ容量 → 型番ではない）
  - NG例: "DDR5", "DDR4"（メモリ規格 → 型番ではない）
  - NG例: "3200MHz", "6000MHz"（動作クロック → 型番ではない）
  - NG例: "850W", "750W", "650W"（電源容量のみ → 型番ではない）
  - NG例: "125W", "65W"（TDP値 → 型番ではない）
- 型番には必ずメーカー名・製品シリーズ名・製品番号が含まれる
  - OK例: "RTX 4070", "Core i7-13700K", "ROG STRIX Z790-F", "Lancool 216", "NH-D15"
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


def _load_all_products() -> list:
    """全カテゴリの products.jsonl を読み込んで返す。"""
    jsonl_paths = glob_module.glob(
        os.path.join(_PC_WORKSPACE_DIR, 'data', '*', 'products.jsonl')
    )
    products = []
    for path in jsonl_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        products.append(json.loads(line))
        except Exception:
            pass
    return products


def _suggest_build_with_claude(parts: list, message: str, history: list = None, user_specified_parts: list = None) -> dict:
    """
    確定済みパーツ（GPU/ケース等）とユーザーメッセージ（予算・用途）から
    残りのパーツを含む全構成を提案する。
    戻り値は /api/recommend と同じ type="recommendation" 形式。
    """
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

    all_products = _load_all_products()

    # historyからユーザーの予算を抽出（ゲームモードからの引き継ぎ等）
    _BUDGET_PAT = re.compile(r'予算\s*(\d+)\s*万')
    budget_from_history = ''
    for h in (history or []):
        if h.get('role') == 'user':
            m = _BUDGET_PAT.search(h.get('content', ''))
            if m:
                budget_from_history = f'{m.group(1)}万円'
    # 今回のmessageにも予算があれば上書き
    m = _BUDGET_PAT.search(message)
    if m:
        budget_from_history = f'{m.group(1)}万円'

    # コラボ・限定品モデルをDB候補から除外するキーワード
    _COLLAB_KEYWORDS = [
        'HATSUNE MIKU', '初音ミク', 'GUNDAM', 'ガンダム', 'EVANGELION', 'エヴァ',
        'EVANGELION', 'LIMITED EDITION', 'Evangelion', 'CAPCOM', 'ANNIVERSARY',
    ]
    def _is_collab(name: str) -> bool:
        n = name.upper()
        return any(kw.upper() in n for kw in _COLLAB_KEYWORDS)

    # 確定パーツのスペックをDBから取得
    confirmed_specs = _lookup_pc_specs(parts) if parts else {}

    # 確定パーツのカテゴリを判定
    _CAT_MAP = {
        'gpu': 'GPU', 'case': 'ケース', 'cpu': 'CPU',
        'motherboard': 'マザーボード', 'mb': 'マザーボード',
        'psu': '電源', 'power_supply': '電源',
        'cooler': 'CPUクーラー', 'cpu_cooler': 'CPUクーラー',
        'ram': 'RAM', 'memory': 'RAM',
    }
    confirmed_gpu  = next((s for s in confirmed_specs.values() if s.get('category') == 'gpu'), None)
    confirmed_case = next((s for s in confirmed_specs.values() if s.get('category') == 'case'), None)
    confirmed_mb   = next((s for s in confirmed_specs.values() if s.get('category') in ('motherboard', 'mb')), None)
    confirmed_cpu  = next((s for s in confirmed_specs.values() if s.get('category') == 'cpu'), None)

    # GPU/ケース互換チェック情報
    compat_info = ''
    if confirmed_gpu and confirmed_case:
        gpu_len = (confirmed_gpu.get('specs') or {}).get('length_mm') or confirmed_gpu.get('length_mm')
        case_max = (confirmed_case.get('specs') or {}).get('max_gpu_length_mm') or confirmed_case.get('max_gpu_length_mm')
        try:
            gl = float(str(gpu_len)) if gpu_len else None
            cm = float(str(case_max)) if case_max else None
            if gl and cm:
                margin = cm - gl
                if margin >= 0:
                    compat_info = f'GPU({confirmed_gpu["name"]}: {gl:.0f}mm) は {confirmed_case["name"]}(max {cm:.0f}mm) に収まります（マージン {margin:.0f}mm OK）。'
                else:
                    compat_info = f'※注意: GPU({confirmed_gpu["name"]}: {gl:.0f}mm) は {confirmed_case["name"]}(max {cm:.0f}mm) に入りません（{abs(margin):.0f}mmオーバー）。'
        except (ValueError, TypeError):
            pass

    # 確定済みカテゴリを特定して、不足カテゴリのみClaudeに提案させる
    confirmed_categories = set()
    prefixed_build = []  # 確定パーツをbuildリストの先頭に追加
    for part_name, spec in confirmed_specs.items():
        cat_key = spec.get('category', '')
        cat_label = _CAT_MAP.get(cat_key, cat_key.upper())
        confirmed_categories.add(cat_key)
        s = spec.get('specs') or {}
        extras = []
        if s.get('length_mm'): extras.append(f'{s["length_mm"]}mm')
        if s.get('tdp_w'):     extras.append(f'TDP {s["tdp_w"]}W')
        reason = '（ユーザー指定済み）' + (' / '.join(extras) and f' ― {" / ".join(extras)}' or '')
        prefixed_build.append({
            'category':    cat_label,
            'name':        spec.get('name', part_name),
            'reason':      reason,
            'price_range': '',
            'confirmed':   True,
        })

    # 不足カテゴリを特定してDB候補を渡す
    need_gpu  = 'gpu'  not in confirmed_categories
    need_case = 'case' not in confirmed_categories
    need_cpu  = 'cpu'  not in confirmed_categories
    need_psu  = 'psu'  not in confirmed_categories and 'power_supply' not in confirmed_categories

    def fmt_p(p):
        s = p.get('specs') or {}
        extras = []
        if s.get('length_mm'):  extras.append(f'{s["length_mm"]}mm')
        if s.get('tdp_w'):      extras.append(f'TDP {s["tdp_w"]}W')
        if s.get('wattage_w'):  extras.append(f'{s["wattage_w"]}W')
        if s.get('socket'):     extras.append(s['socket'])
        extra_str = ' / '.join(extras)
        return f'- {p["name"]}' + (f' ({extra_str})' if extra_str else '')

    # 確定パーツ情報をCPU/MB選定の参考として渡す
    confirmed_info = ''
    if confirmed_gpu:
        s = confirmed_gpu.get('specs') or {}
        confirmed_info += f'確定GPU: {confirmed_gpu["name"]} (TDP {s.get("tdp_w","?")}W, {s.get("length_mm","?")}mm)\n'
    if confirmed_case:
        s = confirmed_case.get('specs') or {}
        confirmed_info += f'確定ケース: {confirmed_case["name"]} (max GPU {s.get("max_gpu_length_mm","?")}mm)\n'
    if confirmed_mb:
        s = confirmed_mb.get('specs') or {}
        mb_socket   = s.get('socket', '')
        mb_chipset  = s.get('chipset', '')
        mb_mem_type = s.get('memory_type', '')
        mb_sata     = s.get('sata_ports', '')
        mb_m2       = s.get('m2_slots', '')
        mb_ff       = s.get('form_factor', '')
        confirmed_info += (
            f'確定MB: {confirmed_mb["name"]} ('
            f'ソケット: {mb_socket}, チップセット: {mb_chipset}, '
            f'メモリ規格: {mb_mem_type}, フォームファクター: {mb_ff}'
            + (f', SATAポート: {mb_sata}本' if mb_sata else '')
            + (f', M.2スロット: {mb_m2}本' if mb_m2 else '')
            + ')\n'
        )
    else:
        mb_socket = ''
    if confirmed_cpu:
        confirmed_info += f'確定CPU: {confirmed_cpu["name"]}\n'
    # ユーザーが明示指定したパーツは変更禁止
    if user_specified_parts:
        confirmed_info += (
            f'\n【変更禁止パーツ（ユーザー直接指定）】: {", ".join(user_specified_parts)}\n'
            f'→ 互換性問題があっても変更提案せず、そのまま確定として構成に含めること\n'
        )

    # 必要なカテゴリのみDB候補リストを構築
    db_sections = ''
    if need_gpu:
        gpu_cands = [p for p in all_products if p.get('category') == 'gpu' and not _is_collab(p.get('name', ''))][:5]
        db_sections += '## GPU候補\n' + '\n'.join(fmt_p(p) for p in gpu_cands) + '\n\n'
    if need_case:
        case_cands = [p for p in all_products if p.get('category') == 'case'][:4]
        db_sections += '## ケース候補\n' + '\n'.join(fmt_p(p) for p in case_cands) + '\n\n'
    if need_cpu:
        cpu_cands = [p for p in all_products if p.get('category') == 'cpu']
        # MBのソケットが判明している場合、Intel/AMDで候補を絞り込む
        if mb_socket.startswith('LGA'):
            intel_cands = [p for p in cpu_cands if any(k in p.get('name', '') for k in ['Core', 'Xeon', 'Pentium', 'Celeron'])]
            if intel_cands:
                cpu_cands = intel_cands
        elif mb_socket.startswith('AM') or mb_socket.startswith('TR'):
            amd_cands = [p for p in cpu_cands if any(k in p.get('name', '') for k in ['Ryzen', 'Athlon', 'Threadripper', 'EPYC'])]
            if amd_cands:
                cpu_cands = amd_cands
        cpu_cands = cpu_cands[:4]
        db_sections += '## CPU候補\n' + '\n'.join(fmt_p(p) for p in cpu_cands) + '\n\n'
    # 確定GPU/CPUのTDPから推奨PSU容量を算出
    _gpu_tdp = 0
    _cpu_tdp = 0
    if confirmed_gpu:
        _gpu_tdp = (confirmed_gpu.get('specs') or {}).get('tdp_w') or 0
    if confirmed_cpu:
        _cpu_tdp = (confirmed_cpu.get('specs') or {}).get('tdp_w') or 0
    _total_draw = _gpu_tdp + _cpu_tdp + 100  # system overhead 100W
    _psu_target = max(_total_draw + 200, 550)  # 200Wヘッドルーム、最低550W
    _PSU_STEPS = [450, 550, 650, 750, 850, 1000, 1200, 1600]
    _recommended_psu_w = _PSU_STEPS[-1]  # フォールバック: 最大
    for step in _PSU_STEPS:
        if step >= _psu_target:
            _recommended_psu_w = step
            break
    if _gpu_tdp == 0 and _cpu_tdp == 0:
        _recommended_psu_w = 650  # TDP不明時はミドル帯デフォルト

    if need_psu:
        # 推奨容量付近のPSUのみ候補に渡す（過剰な大容量を除外）
        _psu_lo = _recommended_psu_w - 100
        _psu_hi = _recommended_psu_w + 200
        psu_cands = [p for p in all_products
                     if p.get('category') in ('psu', 'power_supply')
                     and _psu_lo <= ((p.get('specs') or {}).get('wattage_w') or 0) <= _psu_hi][:4]
        if not psu_cands:
            psu_cands = [p for p in all_products if p.get('category') in ('psu', 'power_supply')][:4]
        db_sections += '## 電源候補\n' + '\n'.join(fmt_p(p) for p in psu_cands) + '\n\n'

    # 提案が必要なカテゴリのJSON指示を構築
    needed_items = []
    if need_cpu:    needed_items.append('{"category":"CPU","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')
    if need_case:   needed_items.append('{"category":"ケース","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')
    if need_gpu:    needed_items.append('{"category":"GPU","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')
    needed_items.append('{"category":"マザーボード","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')
    if need_psu:    needed_items.append('{"category":"電源","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')
    needed_items.append('{"category":"RAM","name":"DDR5 32GB など","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}')

    build_prompt = (
        'PC自作の不足パーツを提案してください。\n\n'
        f'## ユーザー要求\n{message}\n\n'
        + (f'## 確定情報\n{confirmed_info}\n' if confirmed_info else '')
        + (f'## GPU/ケース互換チェック結果\n{compat_info}\n\n' if compat_info else '')
        + db_sections
        + '## 指示\n'
        + '- 上記DB候補から互換性・予算を考慮して不足パーツのみ選定すること\n'
        + (f'- 【必須】確定MBのソケットは「{mb_socket}」。LGA系ならIntel CPU、AM系ならAMD CPUのみ提案すること。絶対に別ソケットのCPUを選ばないこと\n' if mb_socket else '- CPU/MBのソケット一致を必ず確認すること\n')
        + f'- 【電源容量】推奨{_recommended_psu_w}W。計算式: (GPU TDP + CPU TDP + 100W) × 1.5。候補リストから{_recommended_psu_w}Wを選ぶこと。必要以上に大容量（例: 合計500W未満の構成に850W）を選ばないこと\n'
        + '- ユーザーが言及していない用途（VR/動画編集/ゲーミング等）を勝手に追加しないこと\n'
        + (f'- 【必須・厳守】予算は{budget_from_history}。確定パーツ込みの合計がこの範囲に収まるよう残りのパーツを選定すること。絶対に超えないこと\n' if budget_from_history else '- 予算の記載があれば合計がその範囲に収まるよう選定すること\n')
        + '- ユーザーメッセージにHDD台数（例: HDD 3台・3.5インチ2本）が含まれる場合、HDDカテゴリを構成リストに必ず追加し、確定MBのSATAポート数・ケースの3.5インチベイ数も考慮すること\n'
        + '- ユーザーメッセージにNVMe/SSD台数が含まれる場合、NVMe SSDカテゴリを構成リストに必ず追加し、確定MBのM.2スロット数を考慮すること\n\n'
        + '以下のJSON形式だけで返してください（説明不要）:\n'
        '{"reply":"2〜3文の提案コメント（日本語・フレンドリー）",'
        '"recommended_build":[' + ','.join(needed_items) + '],'
        '"total_estimate":"¥XX万〜¥XX万",'
        '"tip":"互換性・注意点の1文アドバイス"}'
    )

    build_body = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': build_prompt}]
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=build_body,
        headers={
            'x-api-key': CLAUDE_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        build_result = json.loads(resp.read())
    build_text = build_result['content'][0]['text'].strip()
    json_match = re.search(r'\{.*\}', build_text, re.DOTALL)
    build_data = _safe_parse_claude_json(json_match.group()) if json_match else {}

    # 確定パーツを先頭に固定し、Claude提案の不足パーツを追加
    suggested_build = build_data.get('recommended_build', [])
    for item in suggested_build:
        item['amazon_url']  = make_amazon_url(item.get('name', ''))
        item['rakuten_url'] = make_rakuten_url(item.get('name', ''))
    for item in prefixed_build:
        item['amazon_url']  = make_amazon_url(item.get('name', ''))
        item['rakuten_url'] = make_rakuten_url(item.get('name', ''))

    # 重複カテゴリは確定パーツ優先
    confirmed_cat_labels = {i['category'] for i in prefixed_build}
    deduped_suggested = [i for i in suggested_build if i.get('category') not in confirmed_cat_labels]
    recommended_build = prefixed_build + deduped_suggested

    # カテゴリを英語キーに正規化（フロントのCATEGORY_ORDERと合わせる）
    _CAT_NORMALIZE = {
        'ケース': 'CASE', 'case': 'CASE', 'Case': 'CASE', 'CASE': 'CASE',
        'マザーボード': 'MB', 'motherboard': 'MB', 'Motherboard': 'MB', 'mb': 'MB', 'MB': 'MB',
        '電源': 'PSU', 'power_supply': 'PSU', 'psu': 'PSU', 'Psu': 'PSU', 'PSU': 'PSU',
        'cpu': 'CPU', 'Cpu': 'CPU', 'CPU': 'CPU',
        'gpu': 'GPU', 'Gpu': 'GPU', 'GPU': 'GPU',
        'ram': 'RAM', 'Ram': 'RAM', 'RAM': 'RAM', 'メモリ': 'RAM',
        'cooler': 'COOLER', 'Cooler': 'COOLER', 'COOLER': 'COOLER', 'クーラー': 'COOLER',
    }
    for item in recommended_build:
        cat = item.get('category', '')
        item['category'] = _CAT_NORMALIZE.get(cat, cat.upper() if cat else '')

    # kakaku実価格を各itemに付加
    _CAT_TO_KAKAKU = {
        'GPU': 'gpu', 'CPU': 'cpu', 'RAM': 'ram',
        'MB': 'mb', 'PSU': 'psu', 'CASE': 'case', 'COOLER': 'cooler',
    }
    for item in recommended_build:
        if not item.get('price_low'):
            cat_key = _CAT_TO_KAKAKU.get(item.get('category', ''), '')
            if cat_key:
                price = _lookup_kakaku_price(item.get('name', ''), cat_key, all_products)
                if price:
                    item['price_min'] = price
                    item['price_low'] = price  # フロントのrenderSummaryCardが参照

    total_estimate = _calc_total_estimate(recommended_build, build_data.get('total_estimate', ''))
    radar_scores   = _compute_radar_scores(recommended_build, all_products, total_estimate)

    # 予算を数値化（try-exceptで安全に処理）
    budget_numeric = None
    if budget_from_history:
        try:
            budget_numeric = int(budget_from_history.replace('万円', '')) * 10000
        except (ValueError, AttributeError):
            pass  # 予算パース失敗時はNoneのまま

    return {
        'type':              'recommendation',
        'game':              {'name': '推奨構成', 'appid': None, 'screenshot': None},
        'reply':             build_data.get('reply', '構成を提案します。'),
        'recommended_build': recommended_build,
        'total_estimate':    total_estimate or build_data.get('total_estimate', ''),
        'budget_yen':        budget_numeric,
        'tip':               build_data.get('tip', ''),
        'radar_scores':      radar_scores,
        'game_req_scores':   None,
        'compat_info':       compat_info,
    }


def _load_all_pc_products():
    """全カテゴリの products.jsonl を読み込んで製品リストを返す（2022年以降のみ）"""
    from datetime import datetime
    
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
    
    # 最新世代の製品のみに絞る（製品名から判定）
    import re
    def is_recent_product(product):
        name = product.get('name', '').upper()
        category = product.get('category', '')
        
        # GPU: RTX 40xx/50xx, RX 7000/9000シリーズのみ
        if category == 'gpu':
            if re.search(r'RTX\s*(?:40[0-9]{2}|50[0-9]{2})', name):  # RTX 4000/5000
                return True
            if re.search(r'RX\s*(?:7[0-9]{3}|9[0-9]{3})', name):  # RX 7000/9000
                return True
            if re.search(r'ARC\s*[AB][0-9]{3}', name):  # Intel Arc
                return True
            return False
        
        # CPU: Ryzen 7000/9000, Intel 12世代以降のみ
        if category == 'cpu':
            if re.search(r'RYZEN\s*[579]\s*(?:7[0-9]{3}|9[0-9]{3})', name):  # Ryzen 7000/9000
                return True
            if re.search(r'(?:CORE\s*(?:ULTRA|I[3579])[- ](?:1[2-9]|[2-9][0-9])|(?:1[2-9]|[2-9][0-9])TH\s*GEN)', name):  # Intel 12世代以降
                return True
            return False
        
        # その他のカテゴリは全て許可（マザボ、メモリ、SSDなど）
        return True
    
    all_products = [p for p in all_products if is_recent_product(p)]
    
    return all_products


def retrieve_parts(budget, game_name=None, resolution='FHD', quality='high', all_products=[]):
    """ユーザー条件でフィルタしてから渡す（本物のRAG設計）"""
    results = {}
    
    # 発売年フィルタ: 2022年以前は除外
    from datetime import datetime
    def is_recent_product(product):
        created_at = product.get('created_at', '')
        if not created_at:
            return True  # 日付不明なら許可（フィルタスキップ）
        try:
            # ISO 8601形式をパース
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return created_date.year >= 2022
        except:
            return True  # パース失敗なら許可
    
    # 2022年以降の製品のみに絞る
    all_products = [p for p in all_products if is_recent_product(p)]
    
    # 解像度別GPU予算比率（高解像度ほどGPUに多く配分）
    resolution_gpu_ratio = {
        '4K': 0.50,
        'WQHD': 0.45,
        'FHD': 0.40,
    }
    gpu_ratio = resolution_gpu_ratio.get(resolution, 0.40)

    # 予算配分（合計100%）
    budget_allocation = {
        'gpu': gpu_ratio,
        'cpu': 0.25,
        'mb': 0.15,
        'ram': 0.10,
        'psu': 0.07,
        'case': 0.05,
        'ssd': 0.02,
    }

    # 1. GPU: ゲーム推奨スペック + 予算でフィルタ
    gpu_budget = budget * budget_allocation['gpu']
    
    # 2024-2026年に推奨できるGPUのみ（GTX系は全除外）
    def is_modern_gpu(name):
        name_lower = name.lower()
        # NVIDIA: RTX 30xx/40xx/50xx系のみ（GTX系・RTX 20xx系は除外）
        if any(x in name_lower for x in ['rtx 30', 'rtx 40', 'rtx 50']):
            return True
        # AMD: RX 6000/7000/9000シリーズのみ
        if any(x in name_lower for x in ['rx 6', 'rx 7', 'rx 9', 'radeon rx 6', 'radeon rx 7', 'radeon rx 9']):
            return True
        # Intel: Arc A7xx以降
        if any(x in name_lower for x in ['arc a7', 'arc a8']):
            return True
        return False
    
    gpu_candidates = [
        p for p in all_products 
        if p.get('category') == 'gpu' 
        and is_modern_gpu(p.get('name', ''))
        and p.get('price_min', 0) >= 20000  # 最低2万円以上（エントリーGPUの現実的な価格）
    ]
    # 予算内（+20%の余裕あり）で高い順にソート→高性能GPUを優先的にClaudeに提示
    gpu_budget_relaxed = gpu_budget * 1.20  # 予算の20%超えまで許容（Claudeが最終判断）
    within_budget = [p for p in gpu_candidates if p.get('price_min', 999999) <= gpu_budget_relaxed]
    within_budget.sort(key=lambda x: x.get('price_min', 0), reverse=True)
    results['gpu'] = within_budget[:5]
    
    # 2. CPU: 予算でフィルタ
    cpu_budget = budget * budget_allocation['cpu']
    
    # DDR5/PCIe 5.0対応世代以降のみ
    def is_modern_cpu(name):
        name_lower = name.lower()
        # AMD: Ryzen 5000シリーズ以降（Zen3以降）
        if any(x in name_lower for x in ['ryzen 5 5', 'ryzen 7 5', 'ryzen 9 5', 'ryzen 5 7', 'ryzen 7 7', 'ryzen 9 7', 'ryzen 5 9', 'ryzen 7 9', 'ryzen 9 9']):
            return True
        # Intel: 第12世代以降（Alder Lake以降）
        if any(x in name_lower for x in ['i3-12', 'i5-12', 'i7-12', 'i9-12', 'i3-13', 'i5-13', 'i7-13', 'i9-13', 'i3-14', 'i5-14', 'i7-14', 'i9-14', 'i3-15', 'i5-15', 'i7-15', 'i9-15']):
            return True
        # Intel Core Ultra
        if 'core ultra' in name_lower:
            return True
        return False
    
    cpu_candidates = [
        p for p in all_products 
        if p.get('category') == 'cpu'
        and is_modern_cpu(p.get('name', ''))
        and p.get('price_min', 0) >= 10000  # 最低1万円以上（現実的な価格帯）
    ]
    cpu_candidates.sort(key=lambda x: x.get('price_min', 999999))
    results['cpu'] = [p for p in cpu_candidates if (p.get('price_min', 999999) <= cpu_budget)][:5]
    
    # 3. マザーボード: 予算でフィルタ（現代的なチップセットのみ）
    mb_budget = budget * budget_allocation['mb']
    
    def is_modern_motherboard(name):
        name_lower = name.lower()
        # Intel: B660/Z690以降（600/700/800シリーズ）
        if any(x in name_lower for x in ['b660', 'h670', 'z690', 'b760', 'h770', 'z790', 'b860', 'z890']):
            return True
        # AMD: B550/X570以降（500/600/700シリーズ）
        if any(x in name_lower for x in ['b550', 'x570', 'b650', 'x670', 'b850', 'x870']):
            return True
        # AM5ソケット（Ryzen 7000/9000対応）
        if 'am5' in name_lower:
            return True
        # LGA1700ソケット（Intel 12/13/14世代対応）
        if 'lga1700' in name_lower or 'lga 1700' in name_lower:
            return True
        return False
    
    mb_candidates = [
        p for p in all_products 
        if p.get('category') in ('mb', 'motherboard')
        and is_modern_motherboard(p.get('name', ''))
        and p.get('price_min', 0) >= 8000  # 最低8千円以上（現実的な価格帯）
    ]
    mb_candidates.sort(key=lambda x: x.get('price_min', 999999))
    results['mb'] = [p for p in mb_candidates if (p.get('price_min', 999999) <= mb_budget)][:5]
    
    # 4. RAM: DDR5優先、デスクトップ用のみ（SODIMMは除外）
    ram_budget = budget * budget_allocation['ram']
    ram_candidates = [
        p for p in all_products 
        if p.get('category') == 'ram'
        and 'sodimm' not in p.get('name', '').lower()  # ノートPC用SODIMMを除外
        and p.get('price_min', 0) >= 3000  # 最低3千円以上
    ]
    # DDR5を優先（名前にDDR5が含まれるものを先に）
    ram_ddr5 = [p for p in ram_candidates if 'ddr5' in p.get('name', '').lower()]
    ram_ddr4 = [p for p in ram_candidates if 'ddr4' in p.get('name', '').lower()]
    # DDR5を優先的に並べる
    ram_sorted = sorted(ram_ddr5, key=lambda x: x.get('price_min', 999999)) + sorted(ram_ddr4, key=lambda x: x.get('price_min', 999999))
    results['ram'] = [p for p in ram_sorted if (p.get('price_min', 999999) <= ram_budget)][:3]
    
    # 5. PSU: ATX 3.0 / 12VHPWR対応を優先
    psu_budget = budget * budget_allocation['psu']
    psu_candidates = [
        p for p in all_products 
        if p.get('category') == 'psu'
        and p.get('price_min', 0) >= 5000  # 最低5千円以上（信頼性確保）
    ]
    # ATX 3.0 / 12VHPWR対応を優先（名前に含まれるものを先に）
    psu_modern = [p for p in psu_candidates if any(kw in p.get('name', '').lower() for kw in ['atx 3.0', '12vhpwr', 'pcie 5.0'])]
    psu_standard = [p for p in psu_candidates if p not in psu_modern]
    psu_sorted = sorted(psu_modern, key=lambda x: x.get('price_min', 999999)) + sorted(psu_standard, key=lambda x: x.get('price_min', 999999))
    results['psu'] = [p for p in psu_sorted if (p.get('price_min', 999999) <= psu_budget)][:3]
    
    # 6. CASE / SSD: 価格フィルタ（price_minが未設定のケースも含める）
    case_budget = budget * budget_allocation['case']
    case_candidates = [
        p for p in all_products
        if p.get('category') == 'case'
        and (p.get('price_min') is None or p.get('price_min', 0) >= 3000)
    ]
    case_candidates.sort(key=lambda x: x.get('price_min') or 0)
    results['case'] = [
        p for p in case_candidates
        if (p.get('price_min') is None or p.get('price_min', 999999) <= case_budget * 3)
    ][:3]
    
    ssd_budget = budget * budget_allocation['ssd']
    ssd_candidates = [
        p for p in all_products 
        if p.get('category') == 'ssd'
        and p.get('price_min', 0) >= 3000  # 最低3千円以上
    ]
    ssd_candidates.sort(key=lambda x: x.get('price_min', 999999))
    results['ssd'] = [p for p in ssd_candidates if (p.get('price_min', 999999) <= ssd_budget)][:3]
    
    # 候補0件時フォールバック: 予算制限を緩和して再フィルタ（修正4）
    amazon_tag = os.environ.get('AMAZON_TAG', 'pccompat-22')

    _FALLBACK_QUERIES = {
        'gpu':  'RTX グラフィックボード',
        'cpu':  'Ryzen AMD CPU プロセッサ',
        'mb':   'ATX マザーボード',
        'ram':  'DDR5 メモリ 32GB デスクトップ',
        'psu':  '電源ユニット ATX 650W',
        'case': 'ATX ミドルタワー PCケース',
        'ssd':  'NVMe M.2 SSD 1TB',
    }

    for cat in list(results.keys()):
        if not results[cat]:
            # 予算2倍で再試行
            candidates = [p for p in all_products if p.get('category') == cat]
            budget_for_cat = budget * budget_allocation.get(cat, 0.10) * 2
            relaxed = [p for p in candidates if p.get('price_min', 999999) <= budget_for_cat]
            if relaxed:
                relaxed.sort(key=lambda x: x.get('price_min', 0), reverse=(cat == 'gpu'))
                results[cat] = relaxed[:3]
            else:
                # それでも0件ならAmazon検索フォールバックプレースホルダーを挿入
                query = _FALLBACK_QUERIES.get(cat, cat)
                q = urllib.parse.quote(query)
                results[cat] = [{
                    'name': f'[予算内で見つかりませんでした - Amazon で {query} を検索]',
                    'category': cat,
                    'price_min': None,
                    'specs': {},
                    'amazon_url': f'https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}',
                    '_fallback': True,
                }]

    # 辞書のまま返す（カテゴリ別に整理）
    return results


def _format_products_for_claude(products_dict):
    """製品辞書をClaude用に簡潔に整形する"""
    lines = []
    for category, products in products_dict.items():
        lines.append(f'\n## {category.upper()}')
        for p in products:
            name = p.get('name', '')
            price = p.get('price_min', None)
            specs = p.get('specs', {}) or {}
            
            # 価格表示
            price_str = f'¥{price:,}' if price else '価格不明'
            
            # カテゴリ別に重要スペックのみ抽出（互換チェックに必要な情報を必ず含める）
            if category == 'gpu':
                vram = specs.get('vram_gb', '?')
                length = specs.get('length_mm', '?')
                tdp = specs.get('tdp_w', '?')
                lines.append(f'- {name} ({price_str}, VRAM {vram}GB, 長さ{length}mm, TDP {tdp}W)')
            elif category == 'cpu':
                cores = specs.get('cores', '?')
                threads = specs.get('threads', '?')
                socket = specs.get('socket', '?')
                tdp = specs.get('tdp_w', '?')
                lines.append(f'- {name} ({price_str}, {cores}コア{threads}スレッド, ソケット:{socket}, TDP {tdp}W)')
            elif category in ('motherboard', 'mb'):
                socket = specs.get('socket', '?')
                chipset = specs.get('chipset', '?')
                mem_type = specs.get('memory_type', '?')
                lines.append(f'- {name} ({price_str}, ソケット:{socket}, {chipset}, メモリ:{mem_type})')
            elif category == 'ram':
                capacity = specs.get('capacity_gb', '?')
                mem_type = specs.get('memory_type', p.get('name', ''))
                # メモリタイプをname文字列から抽出（DDR5/DDR4）
                name_upper = p.get('name', '').upper()
                if 'DDR5' in name_upper:
                    mem_label = 'DDR5'
                elif 'DDR4' in name_upper:
                    mem_label = 'DDR4'
                else:
                    mem_label = str(mem_type)
                lines.append(f'- {name} ({price_str}, {mem_label}, {capacity}GB)')
            elif category == 'case':
                max_gpu = specs.get('max_gpu_length_mm', '?')
                ff = specs.get('form_factor', '?')
                lines.append(f'- {name} ({price_str}, GPU最大{max_gpu}mm, 対応:{ff})')
            elif category in ('psu', 'power_supply'):
                wattage = specs.get('wattage_w', '?')
                lines.append(f'- {name} ({price_str}, {wattage}W)')
            else:
                lines.append(f'- {name} ({price_str})')
    
    return '\n'.join(lines)


def get_or_create_session(session_id):
    """セッションを取得または作成する"""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            'confirmed_parts': {},  # {category: part_name} の形式
            # current_build: スペック付きの現在構成（依存関係チェック用）
            'current_build': {
                'cpu':         None,  # {name, socket, tdp_w, user_specified}
                'gpu':         None,  # {name, length_mm, tdp_w, user_specified}
                'motherboard': None,  # {name, socket, memory_type, form_factor, user_specified}
                'ram':         None,  # {name, memory_type, capacity_gb, user_specified}
                'case':        None,  # {name, max_gpu_length_mm, form_factor, user_specified}
                'psu':         None,  # {name, wattage_w, user_specified}
                'cooler':      None,  # {name, user_specified}
            },
            'recheck_flags': [],    # 再チェックが必要なカテゴリ
            'history': [],          # 会話履歴（直近10メッセージのみ保持）
            'stage': 'hearing',     # 'hearing' or 'recommending'
            'budget_yen': None,     # 抽出した予算
            'resolution': None,     # 抽出した解像度
            'quality': None,        # 抽出した画質
            'game_name': None,      # 抽出したゲーム名
            'fps_target': None      # 抽出したFPS目標
        }
    return _SESSIONS[session_id]


def _get_part_specs_from_db(part_name, category, all_products):
    """DBから製品名でスペック情報を取得する（current_build用）"""
    cat_aliases = {
        'cpu': ('cpu',),
        'gpu': ('gpu',),
        'motherboard': ('motherboard', 'mb'),
        'mb': ('motherboard', 'mb'),
        'ram': ('ram',),
        'case': ('case',),
        'psu': ('psu', 'power_supply'),
        'cooler': ('cooler', 'cpu_cooler'),
    }
    target_cats = cat_aliases.get(category.lower(), (category.lower(),))

    name_lower = part_name.lower()
    best = None
    best_diff = None
    for p in all_products:
        if p.get('category', '').lower() not in target_cats:
            continue
        db_name = p.get('name', '').lower()
        if db_name == name_lower:
            # 完全一致：即返す
            best = p
            break
        # 部分一致：AI名⊆DB名 または DB名⊆AI名
        if name_lower in db_name or db_name in name_lower:
            diff = abs(len(db_name) - len(name_lower))
            if best_diff is None or diff < best_diff:
                best = p
                best_diff = diff
    if best:
        specs = best.get('specs', {}) or {}
        return {
            'name': best['name'],
            'id': best.get('id'),
            'socket':            specs.get('socket'),
            'memory_type':       specs.get('memory_type'),
            'form_factor':       specs.get('form_factor'),
            'length_mm':         specs.get('length_mm'),
            'tdp_w':             specs.get('tdp_w'),
            'wattage_w':         specs.get('wattage_w'),
            'max_gpu_length_mm': specs.get('max_gpu_length_mm'),
            'capacity_gb':       specs.get('capacity_gb'),
            'vram_gb':           specs.get('vram_gb'),
        }
    # DBに見つからなかった場合は名前だけ返す
    return {'name': part_name}


# 依存関係マップ: {変更カテゴリ: [(影響カテゴリ, チェック種別), ...]}
_BUILD_DEPENDENCY_MAP = {
    'cpu':         [('motherboard', 'socket_reset'), ('ram', 'socket_reset'), ('cooler', 'recheck'), ('psu', 'recheck')],
    'gpu':         [('case', 'recheck'), ('psu', 'recheck')],
    'motherboard': [('ram', 'memtype_reset'), ('case', 'recheck')],
    'ram':         [],
    'case':        [],
    'psu':         [],
    'cooler':      [],
}


# ================================================================
# Function Calling型ツール定義 + ハンドラ
# ================================================================

SEARCH_PARTS_TOOL = {
    "name": "search_parts",
    "description": "PCパーツデータベースを検索する。カテゴリ、スペック条件、価格範囲で絞り込む。結果にはproduct_id、製品名、スペック、価格が含まれる。この結果に含まれる製品のみユーザーに提案できる。",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["gpu", "cpu", "motherboard", "ram", "case", "psu"],
                "description": "検索するパーツカテゴリ"
            },
            "socket": {
                "type": "string",
                "description": "CPUソケット（例: AM5, LGA1700）。MB検索時に使用"
            },
            "memory_type": {
                "type": "string",
                "description": "メモリタイプ（例: DDR5, DDR4）。RAM検索時に使用"
            },
            "min_wattage": {
                "type": "integer",
                "description": "最小ワット数。PSU検索時に使用"
            },
            "min_gpu_length_mm": {
                "type": "integer",
                "description": "最小GPU対応長（mm）。ケース検索時に使用"
            },
            "max_price": {
                "type": "integer",
                "description": "最大価格（円）"
            },
            "min_vram_gb": {
                "type": "integer",
                "description": "最小VRAM（GB）。GPU検索時に使用"
            },
            "form_factor": {
                "type": "string",
                "description": "フォームファクター（例: ATX, Micro-ATX）"
            }
        },
        "required": ["category"]
    }
}

CONFIRM_PART_TOOL = {
    "name": "confirm_part",
    "description": "ユーザーが選んだパーツを構成に確定登録する。product_idはsearch_partsの結果から取得したものを使うこと。",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["gpu", "cpu", "motherboard", "ram", "case", "psu"]
            },
            "product_id": {
                "type": "string",
                "description": "search_partsの結果に含まれるproduct_id"
            }
        },
        "required": ["category", "product_id"]
    }
}

GET_CURRENT_BUILD_TOOL = {
    "name": "get_current_build",
    "description": "現在確定済みの構成を取得する。未確定のパーツも含めて全カテゴリの状態を返す。",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}

AMAZON_SEARCH_TOOL = {
    "name": "amazon_search",
    "description": "データベースに候補がないパーツ（SSD、CPUクーラー等）のAmazon検索URLを生成する。",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "検索クエリ（例: NVMe M.2 SSD 1TB Gen4）"
            }
        },
        "required": ["query"]
    }
}

GET_BUILD_SUMMARY_TOOL = {
    "name": "get_build_summary",
    "description": "全パーツ確定後にサーバー側で正確なサマリーテーブルを生成する。合計金額・予算比較が正確に計算される。全パーツが確定したら必ずこのツールを呼ぶこと。自分でサマリーを書いてはいけない。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

FC_TOOLS = [SEARCH_PARTS_TOOL, CONFIRM_PART_TOOL, GET_CURRENT_BUILD_TOOL, AMAZON_SEARCH_TOOL, GET_BUILD_SUMMARY_TOOL]


def handle_search_parts(params, all_products, session=None):
    """AIからのツール呼び出しを処理してDB検索結果を返す。"""
    category = params['category']

    # ── current_build からの自動補完 ──
    # AIがフィルタ条件を付け忘れても互換性を担保する
    cb = (session or {}).get('current_build') or {}

    if category == 'motherboard' and not params.get('socket'):
        cpu = cb.get('cpu') or {}
        if cpu.get('socket'):
            params['socket'] = cpu['socket']

    if category == 'ram' and not params.get('memory_type'):
        mb = cb.get('motherboard') or {}
        if mb.get('memory_type'):
            params['memory_type'] = mb['memory_type']

    if category == 'case' and not params.get('min_gpu_length_mm'):
        gpu = cb.get('gpu') or {}
        if gpu.get('length_mm'):
            params['min_gpu_length_mm'] = gpu['length_mm']

    # max_price自動補完: AIが指定し忘れた場合、budget_yenの50%を設定
    if not params.get('max_price'):
        budget = (session or {}).get('budget_yen')
        if budget:
            params['max_price'] = int(budget * 0.5)

    # カテゴリエイリアス対応
    if category == 'motherboard':
        candidates = [p for p in all_products if p.get('category') in ('motherboard', 'mb')]
    else:
        candidates = [p for p in all_products if p.get('category') == category]

    # RAM: SODIMM（ノートPC用）を除外、2枚組を優先
    if category == 'ram':
        candidates = [p for p in candidates
                      if 'sodimm' not in p.get('name', '').lower()
                      and 'so-dimm' not in p.get('name', '').lower()]
        # 2枚組を先に、1枚売りを後ろに
        kit_2 = [p for p in candidates if '2枚' in p.get('name', '')]
        kit_1 = [p for p in candidates if '2枚' not in p.get('name', '')]
        candidates = kit_2 + kit_1

    # GPU: 業務用・HPC製品を除外
    if category == 'gpu':
        _WORKSTATION_KEYWORDS = ('H100', 'H200', 'A100', 'A800', 'L40',
                                 'RTX PRO', 'Quadro', 'Tesla', 'FirePro')
        candidates = [p for p in candidates
                      if not any(kw in p.get('name', '') for kw in _WORKSTATION_KEYWORDS)
                      and ((p.get('specs') or {}).get('vram_gb') or 0) <= 24]

    # フィルタ適用
    if params.get('socket'):
        candidates = [p for p in candidates
                      if (p.get('specs') or {}).get('socket') == params['socket']]

    if params.get('memory_type'):
        mem = params['memory_type'].upper()
        def _mem_match(p):
            spec_mem = (p.get('specs') or {}).get('memory_type')
            if spec_mem:
                if isinstance(spec_mem, list):
                    return any(mem in str(m).upper() for m in spec_mem)
                return mem in str(spec_mem).upper()
            # specsにない場合は名前から判定
            return mem in p.get('name', '').upper()
        candidates = [p for p in candidates if _mem_match(p)]

    if params.get('min_wattage'):
        candidates = [p for p in candidates
                      if ((p.get('specs') or {}).get('wattage_w') or 0) >= params['min_wattage']]

    if params.get('min_gpu_length_mm'):
        candidates = [p for p in candidates
                      if ((p.get('specs') or {}).get('max_gpu_length_mm') or 0) >= params['min_gpu_length_mm']]

    if params.get('max_price'):
        max_p = params['max_price']
        candidates = [p for p in candidates
                      if not p.get('price_min') or p['price_min'] <= max_p]
        # GPU: 安すぎる製品を除外（max_price の 60% を下限とする）
        if category == 'gpu':
            floor_price = int(max_p * 0.6)
            candidates = [p for p in candidates
                          if p.get('price_min') and p['price_min'] >= floor_price]

    if params.get('min_vram_gb'):
        candidates = [p for p in candidates
                      if ((p.get('specs') or {}).get('vram_gb') or 0) >= params['min_vram_gb']]

    if params.get('form_factor'):
        ff = params['form_factor']
        candidates = [p for p in candidates
                      if (p.get('specs') or {}).get('form_factor') == ff]

    # 価格データのない製品を除外（価格なし製品は提案不可）
    # ケース等で price_min=None の製品が混入して異常価格になる問題を防止
    candidates = [p for p in candidates if p.get('price_min') and p['price_min'] > 0]

    # ソート: GPUはVRAM降順→価格昇順（高性能＆安い順）、それ以外は価格昇順
    if category == 'gpu':
        candidates.sort(key=lambda p: (
            -(((p.get('specs') or {}).get('vram_gb')) or 0),
            p.get('price_min') or 999999
        ))
    else:
        candidates.sort(key=lambda p: p.get('price_min') or 999999)

    # 件数制限（固定20件。AIに件数を制御させない）
    candidates = candidates[:20]

    # 結果フォーマット
    results = []
    for p in candidates:
        specs = p.get('specs', {}) or {}
        entry = {
            'product_id': p.get('id', ''),
            'name': p['name'],
            'price_min': p.get('price_min'),
            'specs': {}
        }
        # カテゴリ別に重要スペックのみ返す（トークン節約）
        if category == 'gpu':
            for k in ('vram_gb', 'length_mm', 'tdp_w', 'chip'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        elif category == 'cpu':
            for k in ('socket', 'cores', 'threads', 'tdp_w', 'memory_type'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        elif category == 'motherboard':
            for k in ('socket', 'chipset', 'memory_type', 'form_factor'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        elif category == 'ram':
            for k in ('memory_type', 'capacity_gb', 'speed_mhz'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        elif category == 'case':
            for k in ('max_gpu_length_mm', 'form_factor'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        elif category == 'psu':
            for k in ('wattage_w', 'certification', 'modular'):
                if specs.get(k) is not None:
                    entry['specs'][k] = specs[k]
        results.append(entry)

    if not results:
        return {'results': [], 'message': f'{category}の条件に合う製品が見つかりませんでした。条件を緩めて再検索してください。'}

    return {'results': results, 'count': len(results)}


def handle_confirm_part(params, session, all_products):
    """AIが確定したパーツをsessionのcurrent_buildに登録する。"""
    category = params['category']
    product_id = params['product_id']

    # DBから製品を取得
    product = next((p for p in all_products if p.get('id') == product_id), None)
    if not product:
        return {'success': False, 'error': f'product_id {product_id} が見つかりません'}

    specs = product.get('specs', {}) or {}
    norm_cat = category if category != 'mb' else 'motherboard'

    # current_buildに登録
    build_entry = {
        'name': product['name'],
        'user_specified': True,
        'id': product_id,
    }
    # カテゴリ別にスペックをコピー
    for k in ('socket', 'memory_type', 'form_factor', 'length_mm', 'tdp_w',
              'wattage_w', 'max_gpu_length_mm', 'capacity_gb', 'vram_gb'):
        if specs.get(k) is not None:
            build_entry[k] = specs[k]
    if product.get('price_min'):
        build_entry['price_min'] = product['price_min']

    session['current_build'][norm_cat] = build_entry
    session['confirmed_parts'][category.upper()] = product['name']

    # 依存関係チェック（既存のロジック流用）
    old_part = {}  # 新規登録なので空
    reset_parts = []
    recheck_parts = []
    for dep_cat, dep_type in _BUILD_DEPENDENCY_MAP.get(norm_cat, []):
        if dep_type == 'socket_reset' and norm_cat == 'cpu':
            dep_part = session['current_build'].get(dep_cat)
            if dep_part and dep_part.get('socket') and build_entry.get('socket'):
                if dep_part['socket'] != build_entry['socket']:
                    session['current_build'][dep_cat] = None
                    session['confirmed_parts'].pop(dep_cat.upper(), None)
                    reset_parts.append(dep_cat)
        elif dep_type == 'memtype_reset':
            dep_part = session['current_build'].get(dep_cat)
            if dep_part and dep_part.get('memory_type') and build_entry.get('memory_type'):
                if dep_part['memory_type'] != build_entry['memory_type']:
                    session['current_build'][dep_cat] = None
                    session['confirmed_parts'].pop(dep_cat.upper(), None)
                    reset_parts.append(dep_cat)
        elif dep_type == 'recheck':
            recheck_parts.append(dep_cat)

    session['recheck_flags'] = list(set(session.get('recheck_flags', []) + recheck_parts))

    # ── 次ステップ先読みチェック ──
    _PART_ORDER = ['gpu', 'cpu', 'motherboard', 'ram', 'case', 'psu']
    cb = session['current_build']
    next_category = None
    for cat in _PART_ORDER:
        if not cb.get(cat):
            next_category = cat
            break

    next_candidates_count = None
    next_warning = None
    if next_category:
        # 次カテゴリの検索パラメータを自動構築
        preview_params = {'category': next_category}
        if next_category == 'motherboard' and cb.get('cpu', {}) and cb['cpu'].get('socket'):
            preview_params['socket'] = cb['cpu']['socket']
        elif next_category == 'ram' and cb.get('motherboard', {}) and cb['motherboard'].get('memory_type'):
            preview_params['memory_type'] = cb['motherboard']['memory_type']
        elif next_category == 'case' and cb.get('gpu', {}) and cb['gpu'].get('length_mm'):
            preview_params['min_gpu_length_mm'] = cb['gpu']['length_mm']
        elif next_category == 'psu' and cb.get('gpu', {}) and cb['gpu'].get('tdp_w'):
            preview_params['min_wattage'] = cb['gpu']['tdp_w'] + 200

        # budget_yenがあればmax_priceも設定
        budget = session.get('budget_yen')
        if budget:
            preview_params['max_price'] = int(budget * 0.5)

        preview_result = handle_search_parts(preview_params, all_products, session=session)
        next_candidates_count = preview_result.get('count', 0)
        if next_candidates_count == 0:
            next_warning = f'{next_category}の候補が0件です。Amazon検索を案内してください'
        elif next_candidates_count <= 3:
            next_warning = f'{next_category}の候補が{next_candidates_count}件しかありません'

    result = {
        'success': True,
        'confirmed': category,
        'product': product['name'],
        'price_min': product.get('price_min'),
        'reset_parts': reset_parts,
        'recheck_parts': recheck_parts,
        'current_build_summary': format_current_build_for_claude(session['current_build'], session.get('recheck_flags', [])),
    }
    if next_category:
        result['next_category'] = next_category
        result['next_candidates_count'] = next_candidates_count
        result['next_warning'] = next_warning
    else:
        # 全主要パーツが確定済み
        result['all_main_parts_confirmed'] = True
        result['instruction'] = '全パーツ確定！get_build_summaryツールを呼んでサマリーを表示してください。自分でサマリーを書かないこと。'

    return result


def execute_tool(tool_name, tool_input, session, all_products):
    """ツール名に応じてハンドラを呼び出す"""
    if tool_name == 'search_parts':
        return handle_search_parts(tool_input, all_products, session=session)
    elif tool_name == 'confirm_part':
        return handle_confirm_part(tool_input, session, all_products)
    elif tool_name == 'get_current_build':
        return {
            'current_build': {
                cat: ({'name': p['name'], 'specs': {k: v for k, v in p.items() if k not in ('name', 'user_specified', 'id')}} if p else None)
                for cat, p in session['current_build'].items()
            },
            'budget_yen': session.get('budget_yen'),
        }
    elif tool_name == 'get_build_summary':
        summary_text = generate_server_side_summary(session)
        return {'summary': summary_text}
    elif tool_name == 'amazon_search':
        amazon_tag = os.environ.get('AMAZON_TAG', 'pccompat-22')
        q = urllib.parse.quote(tool_input['query'])
        return {'url': f'https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}'}
    else:
        return {'error': f'Unknown tool: {tool_name}'}


# ================================================================
# 修正1: RAG取得後の互換性フィルタ
# ================================================================

def _is_form_factor_compatible(mb_form_factor, case_form_factor):
    """マザーボードがケースに物理的に入るか判定（MB <= ケースサイズならOK）"""
    FF_SIZE_ORDER = {
        'mini-itx': 1, 'mitx': 1,
        'micro-atx': 2, 'matx': 2, 'm-atx': 2,
        'atx': 3,
        'e-atx': 4, 'eatx': 4,
    }
    mb_size   = FF_SIZE_ORDER.get(mb_form_factor.lower().replace(' ', '-'), 0)
    case_size = FF_SIZE_ORDER.get(case_form_factor.lower().replace(' ', '-'), 0)
    if mb_size == 0 or case_size == 0:
        return True  # 不明な場合は通す
    return mb_size <= case_size


def filter_compatible_parts(products_dict, current_build):
    """
    RAGで取得した製品辞書から、current_buildと互換性のないものを除外する。
    AIに渡す前にコードで絞り込むことでハルシネーションと無駄な提案を防ぐ。

    products_dict: {category: [product, ...]} 形式
    """
    cpu_part  = current_build.get('cpu')  or {}
    mb_part   = current_build.get('motherboard') or {}
    case_part = current_build.get('case') or {}
    gpu_part  = current_build.get('gpu')  or {}

    result = {}
    for cat, products in products_dict.items():
        filtered = []
        for p in products:
            specs = p.get('specs', {}) or {}
            keep  = True

            # マザーボード → CPUソケットと一致するもののみ
            if cat in ('motherboard', 'mb') and cpu_part.get('socket'):
                mb_sock = specs.get('socket')
                if mb_sock and mb_sock != cpu_part['socket']:
                    keep = False

            # RAM → マザーボードのDDRタイプと一致するもののみ
            if cat == 'ram' and mb_part.get('memory_type'):
                ram_type = specs.get('memory_type')
                # specs.memory_typeがない場合は名前から判定
                if not ram_type:
                    name_up = p.get('name', '').upper()
                    if 'DDR5' in name_up:
                        ram_type = 'DDR5'
                    elif 'DDR4' in name_up:
                        ram_type = 'DDR4'
                if ram_type and ram_type != mb_part['memory_type']:
                    keep = False

            # GPU → ケースのmax_gpu_length_mmに収まるもののみ
            if cat == 'gpu' and case_part.get('max_gpu_length_mm'):
                gpu_len = specs.get('length_mm')
                if gpu_len and gpu_len >= case_part['max_gpu_length_mm']:
                    keep = False

            # ケース → GPUが入るサイズのもののみ
            if cat == 'case' and gpu_part.get('length_mm'):
                case_max = specs.get('max_gpu_length_mm')
                if case_max and case_max <= gpu_part['length_mm']:
                    keep = False

            # マザーボード → ケースのFFに適合するもののみ
            if cat in ('motherboard', 'mb') and case_part.get('form_factor'):
                mb_ff = specs.get('form_factor')
                if mb_ff and not _is_form_factor_compatible(mb_ff, case_part['form_factor']):
                    keep = False

            if keep:
                filtered.append(p)

        result[cat] = filtered

    return result


# ================================================================
# 修正4: 互換フィルタ後0件時のフォールバック情報生成
# ================================================================

def _generate_fallback_info(current_build, amazon_tag):
    """
    互換パーツが0件の場合、Amazonの検索URLをフォールバックとして生成する。
    AIには「DBに該当製品がない」ことを明示し、Amazon検索を案内させる。
    """
    lines = ["⚠️ データベースに互換性のある製品が見つかりませんでした。"]
    lines.append("以下のAmazon検索リンクをユーザーに案内してください：")
    lines.append("")

    cpu = current_build.get('cpu')  or {}
    mb  = current_build.get('motherboard') or {}
    gpu = current_build.get('gpu')  or {}

    if not current_build.get('motherboard') and cpu.get('socket'):
        q = urllib.parse.quote(f"{cpu['socket']} マザーボード")
        lines.append(f"- マザーボード: https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}")

    if not current_build.get('ram') and mb.get('memory_type'):
        q = urllib.parse.quote(f"{mb['memory_type']} メモリ 16GB")
        lines.append(f"- メモリ: https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}")

    if not current_build.get('case') and gpu.get('length_mm'):
        q = urllib.parse.quote(f"PCケース GPU {gpu['length_mm']}mm以上対応")
        lines.append(f"- ケース: https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}")

    lines.append("")
    lines.append(
        "「データベースにはぴったりの製品がなかったので、"
        "Amazonで探してみましょう」という形で案内してください。"
    )
    return "\n".join(lines)


# ================================================================
# 修正7-2: 迷走検知
# ================================================================

def _detect_stagnation(session):
    """5往復以上で構成が半分以上未確定の場合Trueを返す"""
    history_len = len(session.get('history', []))
    turns = history_len // 2
    if turns < 5:
        return False
    total     = len(session['current_build'])
    confirmed = sum(1 for v in session['current_build'].values() if v is not None)
    return confirmed < (total / 2)


# ================================================================
# 修正7-1: リセット処理
# ================================================================

def _reset_full(session):
    """全リセット: current_buildを全てNullに。チャット履歴は保持。"""
    for key in session['current_build']:
        session['current_build'][key] = None
    session['confirmed_parts'] = {}
    session['recheck_flags']   = []
    session['stage']           = 'hearing'
    session['budget_yen']      = None
    session['resolution']      = None
    session['quality']         = None

    return {
        'success': True,
        'reset_categories': list(session['current_build'].keys()),
        'current_build': {k: None for k in session['current_build']},
        'ai_message': (
            'まっさらな気持ちで行きましょう！\n'
            '何に使うPCを組みたいですか？ゲーム？動画編集？'
            '予算もあれば教えてもらえると助かります。'
        ),
    }


def _reset_partial(session, category):
    """
    個別リセット: 指定カテゴリと依存カテゴリをリセット。
    依存関係マップ（socket_reset / memtype_reset）に従って連動リセット。
    """
    norm_cat = category.lower()
    if norm_cat == 'mb':
        norm_cat = 'motherboard'

    if norm_cat not in session['current_build']:
        return {'success': False, 'error': f'Unknown category: {category}'}

    reset_cats = [norm_cat]
    for dep_cat, dep_type in _BUILD_DEPENDENCY_MAP.get(norm_cat, []):
        if dep_type in ('socket_reset', 'memtype_reset'):
            reset_cats.append(dep_cat)

    for cat in reset_cats:
        session['current_build'][cat] = None
        session['confirmed_parts'].pop(cat.upper(), None)
        session['confirmed_parts'].pop(cat, None)

    part_labels = {
        'cpu': 'CPU', 'gpu': 'GPU', 'motherboard': 'マザーボード',
        'ram': 'メモリ', 'case': 'ケース', 'psu': '電源', 'cooler': 'CPUクーラー',
    }
    reset_names = [part_labels.get(c, c) for c in reset_cats]

    if len(reset_cats) == 1:
        msg = f'{reset_names[0]}をリセットしました。新しい{reset_names[0]}を一緒に選びましょう！'
    else:
        main = reset_names[0]
        deps = '・'.join(reset_names[1:])
        msg = (
            f'{main}を変更しますね。'
            f'連動して{deps}も選び直す必要があります。一緒に決めていきましょう！'
        )

    return {
        'success': True,
        'reset_categories': reset_cats,
        'current_build': {
            cat: ({'name': p['name']} if p else None)
            for cat, p in session['current_build'].items()
        },
        'ai_message': msg,
    }


def update_current_build(session, category, part_name, all_products, user_specified=False):
    """
    current_buildを更新し、依存関係チェックを実行する。
    戻り値: {'reset_parts': [...], 'recheck_parts': [...]}
    """
    norm_cat = category.lower()
    if norm_cat == 'mb':
        norm_cat = 'motherboard'

    old_part = session['current_build'].get(norm_cat) or {}
    new_part = _get_part_specs_from_db(part_name, norm_cat, all_products)
    new_part['user_specified'] = user_specified
    session['current_build'][norm_cat] = new_part

    reset_parts = []
    recheck_parts = []

    for dep_cat, dep_type in _BUILD_DEPENDENCY_MAP.get(norm_cat, []):
        if dep_type == 'socket_reset':
            # CPUソケットが変わった → MB・RAMをリセット
            if norm_cat == 'cpu':
                old_socket = old_part.get('socket')
                new_socket = new_part.get('socket')
                if old_socket and new_socket and old_socket != new_socket:
                    session['current_build'][dep_cat] = None
                    session['confirmed_parts'].pop(dep_cat.upper(), None)
                    session['confirmed_parts'].pop(dep_cat, None)
                    reset_parts.append(dep_cat)
        elif dep_type == 'memtype_reset':
            # MBのDDRタイプが変わった → RAMをリセット
            old_mem = old_part.get('memory_type')
            new_mem = new_part.get('memory_type')
            if old_mem and new_mem and old_mem != new_mem:
                session['current_build']['ram'] = None
                session['confirmed_parts'].pop('RAM', None)
                session['confirmed_parts'].pop('ram', None)
                reset_parts.append('ram')
        elif dep_type == 'recheck':
            recheck_parts.append(dep_cat)

    # 電源の必要容量チェック（GPUとCPUのTDPから計算）
    gpu_part = session['current_build'].get('gpu') or {}
    cpu_part = session['current_build'].get('cpu') or {}
    psu_part = session['current_build'].get('psu') or {}
    gpu_tdp = gpu_part.get('tdp_w') or 0
    cpu_tdp = cpu_part.get('tdp_w') or 0
    psu_w   = psu_part.get('wattage_w') or 0
    required_w = (gpu_tdp * 1.3) + (cpu_tdp * 1.1) + 50
    if psu_w > 0 and psu_w < required_w and 'psu' not in recheck_parts:
        recheck_parts.append('psu')

    # GPU長さとケースのチェック
    case_part = session['current_build'].get('case') or {}
    gpu_len = gpu_part.get('length_mm') or 0
    case_max = case_part.get('max_gpu_length_mm') or 9999
    if gpu_len > 0 and gpu_len >= case_max and 'case' not in recheck_parts:
        recheck_parts.append('case')

    session['recheck_flags'] = list(set(session.get('recheck_flags', []) + recheck_parts))

    return {'reset_parts': reset_parts, 'recheck_parts': recheck_parts}


def format_current_build_for_claude(current_build, recheck_flags=None):
    """current_buildの構造化情報をAIへのプロンプトとして整形する"""
    if recheck_flags is None:
        recheck_flags = []

    part_labels = {
        'cpu':         'CPU',
        'gpu':         'GPU',
        'motherboard': 'マザーボード',
        'ram':         'RAM',
        'case':        'ケース',
        'psu':         '電源',
        'cooler':      'CPUクーラー',
    }

    lines = ["## 現在の構成（コード管理・確定済み）"]
    pending = []

    for key, label in part_labels.items():
        part = current_build.get(key)
        if part:
            name = part.get('name', '?')
            details = []
            if part.get('socket'):
                details.append(f"ソケット:{part['socket']}")
            if part.get('memory_type'):
                details.append(f"メモリ:{part['memory_type']}")
            if part.get('form_factor'):
                details.append(f"FF:{part['form_factor']}")
            if part.get('length_mm'):
                details.append(f"長さ:{part['length_mm']}mm")
            if part.get('tdp_w'):
                details.append(f"TDP:{part['tdp_w']}W")
            if part.get('wattage_w'):
                details.append(f"容量:{part['wattage_w']}W")
            if part.get('max_gpu_length_mm'):
                details.append(f"GPU最大:{part['max_gpu_length_mm']}mm")
            if part.get('price_min'):
                details.append(f"¥{int(part['price_min']):,}")

            status = '🔒' if part.get('user_specified') else '✅'
            recheck_note = ' ⚠️要再確認' if key in recheck_flags else ''
            detail_str = f" ({', '.join(details)})" if details else ''
            lines.append(f"{status} {label}: {name}{detail_str}{recheck_note}")
        else:
            pending.append(label)

    if pending:
        lines.append(f"\n⏳ 未決定（次に提案すべき）: {', '.join(pending)}")

    # 電源チェックサマリー
    gpu_p = current_build.get('gpu') or {}
    cpu_p = current_build.get('cpu') or {}
    psu_p = current_build.get('psu') or {}
    if gpu_p.get('tdp_w') and cpu_p.get('tdp_w'):
        req_w = int(gpu_p['tdp_w'] * 1.3 + cpu_p['tdp_w'] * 1.1 + 50)
        lines.append(f"\n📊 必要電源容量: {req_w}W以上（GPU {gpu_p['tdp_w']}W × 1.3 + CPU {cpu_p['tdp_w']}W × 1.1 + 50W）")
        if psu_p.get('wattage_w'):
            margin = psu_p['wattage_w'] - req_w
            status_icon = '✅' if margin >= 0 else '❌'
            lines.append(f"   {status_icon} 現在の電源: {psu_p['wattage_w']}W（余裕: {margin:+d}W）")

    # GPUとケースの物理適合チェック
    if gpu_p.get('length_mm') and current_build.get('case', {}) and current_build['case'].get('max_gpu_length_mm'):
        gpu_len = gpu_p['length_mm']
        case_max = current_build['case']['max_gpu_length_mm']
        margin = case_max - gpu_len
        status_icon = '✅' if margin > 0 else '❌'
        lines.append(f"   {status_icon} GPU物理適合: GPU {gpu_len}mm / ケース上限 {case_max}mm（余裕: {margin:+d}mm）")

    return "\n".join(lines) + "\n"


def generate_server_side_summary(session):
    """サーバー側でcurrent_buildから正確なサマリーテーブルを生成する。
    AIが自前でサマリーを書くと価格/製品名が乖離するため、コード側で生成する。"""
    build = session.get('current_build', {})
    budget = session.get('budget_yen')

    part_labels = {
        'gpu':         'GPU',
        'cpu':         'CPU',
        'motherboard': 'マザーボード',
        'ram':         'メモリ',
        'case':        'ケース',
        'psu':         '電源',
        'cooler':      'CPUクーラー',
    }

    lines = ["🎉 **構成が完成しました！**\n"]
    lines.append("| パーツ | 製品名 | 価格 |")
    lines.append("|--------|--------|------|")
    total = 0
    missing = []
    for key, label in part_labels.items():
        part = build.get(key)
        if part and part.get('name'):
            price = part.get('price_min')
            price_str = f"¥{int(price):,}" if price else "価格未取得"
            if price:
                total += int(price)
            lock = " 🔒" if part.get('user_specified') else ""
            lines.append(f"| {label} | {part['name']}{lock} | {price_str} |")
        else:
            missing.append(label)

    lines.append(f"| **合計** | | **¥{total:,}** |")

    if budget:
        diff = budget - total
        if diff >= 0:
            lines.append(f"\n💰 予算 ¥{budget:,} に対して **¥{diff:,} の余裕** があります。")
        else:
            lines.append(f"\n⚠️ 予算 ¥{budget:,} を **¥{abs(diff):,} 超過** しています。")

    if missing:
        lines.append(f"\n⏳ 未選択: {', '.join(missing)}")

    lines.append("\n右の「完成イメージを見る」で、AIがあなたのPCの完成予想図を作ります。")
    lines.append("変更したいパーツがあればいつでも言ってください。")

    return "\n".join(lines)


def format_confirmed_parts(confirmed_parts):
    """confirmed_partsを構造化テキストとしてフォーマット（約500トークン）"""
    if not confirmed_parts:
        return "## 確定済みパーツ\n（まだ選択されていません）\n"

    lines = ["## 確定済みパーツ"]
    for category, part_name in confirmed_parts.items():
        lines.append(f"- {category.upper()}: {part_name}")

    return "\n".join(lines) + "\n"


def format_history(history):
    """会話履歴を整形（直近10メッセージのみ）"""
    if not history:
        return ""
    
    lines = ["## 直近の会話"]
    for msg in history[-10:]:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        prefix = "ユーザー" if role == 'user' else "AI"
        lines.append(f"{prefix}: {content}")
    
    return "\n".join(lines) + "\n"


def call_claude_chat(system, messages):
    """Claude APIを呼び出してチャット応答を取得する"""
    req_body = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': 2000,
        'system': system,
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
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp_data = json.loads(resp.read().decode('utf-8'))
    
    content = resp_data.get('content', [{}])[0].get('text', '{}')
    return content


def call_claude_with_tools(session, user_message, all_products, system_prompt):
    """
    Claude Haikuをtool use付きで呼び出す。
    AIがツールを呼んだら、コード側で処理して結果を返す。ツールを呼ばなくなるまでループ。
    戻り値: (ai_message, confirmed_in_this_turn)
      ai_message: AIの最終テキスト応答
      confirmed_in_this_turn: このターンでconfirm_partされたパーツのリスト
    """
    import sys
    messages = []
    for h in session['history'][-100:]:
        if h.get('role') in ('user', 'assistant'):
            messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': user_message})

    confirmed_in_this_turn = []
    reset_parts_all = []
    recheck_parts_all = []
    tool_logs = []  # デバッグ用ツールログ
    max_iterations = 30  # 無限ループ防止（通常5-10回で完了）

    for _ in range(max_iterations):
        req_body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 2048,
            'system': system_prompt,
            'tools': FC_TOOLS,
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

        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))

        stop_reason = resp_data.get('stop_reason', '')
        content_blocks = resp_data.get('content', [])

        # ツール呼び出しがなければ完了
        if stop_reason != 'tool_use':
            break

        # ツール呼び出しを処理
        tool_results = []
        # assistant応答をシリアライズ可能な形式に変換
        assistant_content = []
        for block in content_blocks:
            if block.get('type') == 'text':
                assistant_content.append({'type': 'text', 'text': block.get('text', '')})
            elif block.get('type') == 'tool_use':
                assistant_content.append({
                    'type': 'tool_use',
                    'id': block['id'],
                    'name': block['name'],
                    'input': block['input'],
                })
                print(f"[TOOL_CALL] {block['name']} params={json.dumps(block['input'], ensure_ascii=False)}", flush=True, file=sys.stderr)
                result = execute_tool(block['name'], block['input'], session, all_products)
                # ツール結果のサマリーをログ出力
                log_entry = {'tool': block['name'], 'params': block['input']}
                if isinstance(result, dict) and 'results' in result:
                    names = [{'name': r.get('name',''), 'price': r.get('price_min')} for r in result['results'][:10]]
                    log_entry['result_count'] = result.get('count', 0)
                    log_entry['top10'] = names
                    print(f"[TOOL_RESULT] {block['name']} count={result.get('count',0)} top5={[n['name'][:40] for n in names[:5]]}", flush=True, file=sys.stderr)
                else:
                    log_entry['result'] = result
                    result_str = json.dumps(result, ensure_ascii=False)
                    print(f"[TOOL_RESULT] {block['name']} result={result_str[:300]}", flush=True, file=sys.stderr)
                tool_logs.append(log_entry)
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': block['id'],
                    'content': json.dumps(result, ensure_ascii=False)
                })
                # confirm_partの結果を追跡
                if block['name'] == 'confirm_part' and isinstance(result, dict) and result.get('success'):
                    confirmed_in_this_turn.append({
                        'category': block['input'].get('category', ''),
                        'product_id': block['input'].get('product_id', ''),
                        'name': result.get('product', ''),
                        'price_min': result.get('price_min'),
                    })
                    reset_parts_all.extend(result.get('reset_parts', []))
                    recheck_parts_all.extend(result.get('recheck_parts', []))

        # 結果をメッセージに追加して再度呼び出し
        messages.append({'role': 'assistant', 'content': assistant_content})
        messages.append({'role': 'user', 'content': tool_results})

    # 最終応答テキストを抽出
    ai_message = ''
    for block in content_blocks:
        if block.get('type') == 'text':
            ai_message += block.get('text', '')

    print(f"[AI_RESPONSE] len={len(ai_message)} text={ai_message[:200]}", flush=True, file=sys.stderr)
    return ai_message, confirmed_in_this_turn, reset_parts_all, recheck_parts_all, tool_logs


@app.route('/api/chat', methods=['POST'])
def chat():
    """Function Calling型チャットエンドポイント（セッション管理付き）"""
    try:
        data = request.get_json(force=True) or {}
        message = str(data.get('message', '')).strip()

        # セッションIDを取得（Web: session_id, Telegram: chat_id）
        session_id = data.get('session_id') or data.get('chat_id') or 'default'

        if not message:
            return jsonify({'error': 'message が空です'}), 400

        # セッションを取得または作成
        session = get_or_create_session(session_id)

        # 製品DBロード
        all_products = _load_all_pc_products()

        # 予算抽出（セッションに保存）
        user_inputs = [h.get('content', '') for h in session['history'][-100:] if h.get('role') == 'user']
        user_inputs.append(message)
        all_user_text = ' '.join(user_inputs).lower()

        if session['budget_yen'] is None:
            for ui in user_inputs:
                match = re.search(r'(\d+)\s*万', ui)
                if match:
                    session['budget_yen'] = int(match.group(1)) * 10000
                    break

        # ゲーム名抽出（セッションに保存）
        if session.get('game_name') is None:
            game_patterns = [
                r'(モンスターハンター\s*ワイルズ|モンハンワイルズ|MH\s*Wilds|Monster\s*Hunter\s*Wilds)',
                r'(FF\s*14|FF14|ファイナルファンタジー\s*14)',
                r'(FF\s*16|FF16|ファイナルファンタジー\s*16)',
                r'(原神|Genshin)',
                r'(Apex\s*Legends|エーペックス)',
                r'(Valorant|ヴァロラント)',
                r'(Fortnite|フォートナイト)',
                r'(エルデンリング|Elden\s*Ring)',
                r'(サイバーパンク|Cyberpunk\s*2077)',
                r'(Palworld|パルワールド)',
            ]
            for ui in user_inputs:
                for pattern in game_patterns:
                    m = re.search(pattern, ui, re.IGNORECASE)
                    if m:
                        session['game_name'] = m.group(1)
                        break
                if session.get('game_name'):
                    break

        # 解像度抽出（セッションに保存）
        if session.get('resolution') is None:
            res_patterns = {
                'FHD': r'(FHD|フルHD|1080p|1920\s*[x×]\s*1080)',
                'WQHD': r'(WQHD|2K|1440p|2560\s*[x×]\s*1440)',
                '4K': r'(4K|UHD|2160p|3840\s*[x×]\s*2160)',
            }
            for ui in user_inputs:
                for res_name, pattern in res_patterns.items():
                    if re.search(pattern, ui, re.IGNORECASE):
                        session['resolution'] = res_name
                        break
                if session.get('resolution'):
                    break

        # 画質抽出（セッションに保存）
        if session.get('quality') is None:
            quality_patterns = {
                '最高': r'(最高画質|ウルトラ|ultra|最高設定)',
                '高': r'(高画質|high|高設定)',
                '中': r'(中画質|medium|中設定)',
                '低': r'(低画質|low|低設定)',
            }
            for ui in user_inputs:
                for q_name, pattern in quality_patterns.items():
                    if re.search(pattern, ui, re.IGNORECASE):
                        session['quality'] = q_name
                        break
                if session.get('quality'):
                    break

        # FPS目標抽出（セッションに保存）
        if session.get('fps_target') is None:
            for ui in user_inputs:
                fps_match = re.search(r'(\d+)\s*fps', ui, re.IGNORECASE)
                if fps_match:
                    session['fps_target'] = int(fps_match.group(1))
                    break

        # 現在の構成情報をシステムプロンプトに含める
        current_build_text = format_current_build_for_claude(
            session['current_build'],
            session.get('recheck_flags', [])
        )

        # 迷走検知
        stagnation_hint = ''
        if _detect_stagnation(session):
            stagnation_hint = (
                "\n\n💡 ヒント: 会話が長くなっています。ユーザーに"
                "「ちょっと整理しましょうか？」と提案してください。"
                "今決まっているパーツを示し、"
                "「ここから一緒に組み立て直しましょう！」と声をかけてください。"
                "上から目線にならないこと。"
            )

        # 予算情報
        budget_hint = ''
        if session.get('budget_yen'):
            budget_hint = f"\n\n💰 ユーザーの予算: ¥{session['budget_yen']:,}\n"

        # コンテキストヒント（ゲーム・解像度・画質・FPS）
        context_hint = ''
        ctx_parts = []
        if session.get('game_name'):
            ctx_parts.append(f"ゲーム: {session['game_name']}")
        if session.get('resolution'):
            ctx_parts.append(f"解像度: {session['resolution']}")
        if session.get('quality'):
            ctx_parts.append(f"画質: {session['quality']}")
        if session.get('fps_target'):
            ctx_parts.append(f"FPS目標: {session['fps_target']}fps")
        if ctx_parts:
            context_hint = "\n\n🎮 ユーザーの要件: " + " / ".join(ctx_parts) + "\n"

        system_prompt = (
            current_build_text + stagnation_hint + budget_hint + context_hint + "\n"
            + _SHOP_CLERK_SYSTEM_PROMPT
        )

        # Function Calling型でClaude呼び出し
        ai_message, confirmed_in_this_turn, reset_parts_all, recheck_parts_all, tool_logs = \
            call_claude_with_tools(session, message, all_products, system_prompt)

        # 全パーツ確定チェック → AIがget_build_summaryを呼ばなかった場合、サーバー側で自動追加
        main_categories = ['gpu', 'cpu', 'motherboard', 'ram', 'case', 'psu']
        confirmed_count = sum(1 for cat in main_categories if session['current_build'].get(cat) is not None)
        already_has_summary = any(t.get('tool') == 'get_build_summary' for t in tool_logs)
        if confirmed_count >= len(main_categories) and not already_has_summary:
            # AIがサマリーを呼ばなかった場合、サーバー側で自動生成して追記
            import sys
            print(f"[AUTO_SUMMARY] All {confirmed_count} main parts confirmed, auto-generating summary", flush=True, file=sys.stderr)
            summary = generate_server_side_summary(session)
            ai_message = (ai_message or '') + "\n\n" + summary

        # フロントエンド互換のレスポンス構築
        amazon_tag = os.environ.get('AMAZON_TAG', 'pccompat-22')
        rakuten_a_id = os.environ.get('RAKUTEN_A_ID', '')
        rakuten_l_id = os.environ.get('RAKUTEN_L_ID', '')

        def _make_amzn(name):
            q = urllib.parse.quote(name)
            return f'https://www.amazon.co.jp/s?k={q}&tag={amazon_tag}'

        def _make_raku(name):
            q = urllib.parse.quote(name)
            if rakuten_a_id and rakuten_l_id:
                return (f'https://hb.afl.rakuten.co.jp/hgc/{rakuten_a_id}/{rakuten_l_id}/?'
                        f'pc=https://search.rakuten.co.jp/search/mall/{q}/&link_type=hybrid_url&ts=1')
            return f'https://search.rakuten.co.jp/search/mall/{q}/'

        response_data = {
            'message': ai_message or 'すみません、うまく処理できませんでした。もう一度お願いできますか？',
        }

        # confirm_partで確定されたパーツをrecommended_partsに変換（フロントエンド互換）
        if confirmed_in_this_turn:
            response_data['recommended_parts'] = []
            for part in confirmed_in_this_turn:
                cat = part.get('category', '').upper()
                name = part.get('name', '')
                response_data['recommended_parts'].append({
                    'category': cat,
                    'name': name,
                    'reason': '',
                    'price_range': f"¥{part['price_min']:,}" if part.get('price_min') else '',
                    'amazon_url': _make_amzn(name),
                    'rakuten_url': _make_raku(name),
                })

        # リセット・再確認情報
        if reset_parts_all:
            response_data['reset_parts'] = list(set(reset_parts_all))
        if recheck_parts_all:
            response_data['recheck_parts'] = list(set(recheck_parts_all))

        # current_buildをレスポンスに含める（右パネル更新用）
        response_data['current_build'] = {
            cat: ({
                'name': p['name'],
                'user_specified': p.get('user_specified', False),
                'price_min': p.get('price_min'),
            } if p else None)
            for cat, p in session['current_build'].items()
        }

        # セッションのconfirmed_partsもレスポンスに含める（price_min付き）
        if session['confirmed_parts'] and not response_data.get('recommended_parts'):
            response_data['confirmed_parts_session'] = []
            for cat, name in session['confirmed_parts'].items():
                if name:
                    entry = {'category': cat, 'name': name}
                    build_part = session['current_build'].get(cat)
                    if build_part and build_part.get('price_min'):
                        entry['price_min'] = build_part['price_min']
                    response_data['confirmed_parts_session'].append(entry)

        # recheck_flagsをクリア
        session['recheck_flags'] = []

        # 会話履歴を更新（直近100メッセージを保持）
        session['history'].append({'role': 'user', 'content': message})
        session['history'].append({'role': 'assistant', 'content': ai_message or ''})
        if len(session['history']) > 100:
            session['history'] = session['history'][-100:]

        # デバッグ用ツールログ（常に含める）
        response_data['_debug_tool_logs'] = tool_logs
        response_data['_code_version'] = 'v2-tool-logs'

        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"[chat] Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ================================================================
# 修正7-1: /api/reset エンドポイント
# ================================================================

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """
    構成リセット。
    {"type": "full"}                         → 全リセット
    {"type": "partial", "category": "cpu"}  → 個別リセット（依存パーツ連動）
    """
    try:
        data       = request.get_json() or {}
        reset_type = data.get('type', 'full')
        session_id = data.get('session_id', 'default')
        session    = get_or_create_session(session_id)

        if reset_type == 'full':
            result = _reset_full(session)
        elif reset_type == 'partial':
            category = data.get('category', '').lower()
            result   = _reset_partial(session, category)
        else:
            return jsonify({'error': 'Invalid reset type'}), 400

        return jsonify(result)

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


# ================================================================
# ゲームモード（/api/recommend）
# ================================================================

_STEAM_GAMES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'workspace', 'data', 'steam', 'games.jsonl'
)


def _load_steam_games():
    games = []
    try:
        with open(_STEAM_GAMES_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    games.append(json.loads(line))
    except Exception:
        pass
    return games


def _lookup_kakaku_price(name: str, category: str, all_products: list) -> int | None:
    """
    all_products から category に一致し name が部分マッチするエントリの
    最安 price_min を返す。見つからなければ None。
    """
    if not name:
        return None
    q_words = set(re.sub(r'[^a-z0-9]', ' ', name.lower()).split())
    best_price = None
    best_score = 0
    for p in all_products:
        if p.get('category') != category:
            continue
        price = p.get('price_min')
        if not price:
            continue
        p_words = set(re.sub(r'[^a-z0-9]', ' ', p.get('name', '').lower()).split())
        common = len(q_words & p_words)
        if common > best_score or (common == best_score and price < (best_price or 10**9)):
            best_score = common
            best_price = price
    return best_price if best_score >= 2 else None


def _calc_total_estimate(build: list, fallback: str = '') -> str:
    """推奨構成の price_range から合計目安を計算する（モジュールレベル共用版）。"""
    lo_sum = hi_sum = 0
    for item in build:
        nums = re.findall(r'[\d,]+', item.get('price_range', ''))
        vals = []
        for n in nums:
            try:
                vals.append(int(n.replace(',', '')))
            except ValueError:
                pass
        if len(vals) >= 2:
            lo_sum += vals[0]; hi_sum += vals[1]
        elif len(vals) == 1:
            lo_sum += vals[0]; hi_sum += vals[0]
    if lo_sum == 0:
        return fallback
    lo_man = round(lo_sum / 10000, 1)
    hi_man = round(hi_sum / 10000, 1)
    lo_str = str(int(lo_man)) if lo_man == int(lo_man) else str(lo_man)
    hi_str = str(int(hi_man)) if hi_man == int(hi_man) else str(hi_man)
    return f'¥{lo_str}万〜¥{hi_str}万'


def _compute_radar_scores(recommended_build: list, all_products: list, total_estimate_str: str) -> dict:
    """推奨構成からレーダーチャートスコア(1-10)を計算する"""

    gpu_item = next((x for x in recommended_build if x.get('category', '').upper() == 'GPU'), None)
    cpu_item = next((x for x in recommended_build if x.get('category', '').upper() == 'CPU'), None)
    ram_item = next((x for x in recommended_build if x.get('category', '').upper() == 'RAM'), None)

    # CPU スコア（キーワードマッチ）
    cpu_name = (cpu_item.get('name', '') if cpu_item else '').lower()
    if any(k in cpu_name for k in ['i9', 'ryzen 9', 'core ultra 9', 'threadripper']):
        cpu_score = 10
    elif any(k in cpu_name for k in ['i7', 'ryzen 7', 'core ultra 7']):
        cpu_score = 8
    elif any(k in cpu_name for k in ['i5', 'ryzen 5', 'core ultra 5']):
        cpu_score = 6
    elif any(k in cpu_name for k in ['i3', 'ryzen 3']):
        cpu_score = 4
    elif any(k in cpu_name for k in ['celeron', 'pentium', 'athlon']):
        cpu_score = 2
    else:
        cpu_score = 5

    # GPU スペックを all_products から名前の部分マッチで検索
    gpu_specs = {}
    if gpu_item:
        gpu_name_q = gpu_item.get('name', '').lower()
        q_words = set(re.sub(r'[^a-z0-9]', ' ', gpu_name_q).split())
        best_match = None
        best_score = 0
        for p in all_products:
            if p.get('category') == 'gpu':
                p_words = set(re.sub(r'[^a-z0-9]', ' ', p.get('name', '').lower()).split())
                common = len(q_words & p_words)
                if common > best_score:
                    best_score = common
                    best_match = p
        if best_match and best_score >= 2:
            gpu_specs = best_match.get('specs', {}) or {}

    # GPU スコア（TDP ベース）
    tdp_w = gpu_specs.get('tdp_w')
    if tdp_w is None:
        gpu_score = 5
    elif tdp_w >= 350:
        gpu_score = 10
    elif tdp_w >= 280:
        gpu_score = 9
    elif tdp_w >= 200:
        gpu_score = 7
    elif tdp_w >= 150:
        gpu_score = 6
    elif tdp_w >= 75:
        gpu_score = 4
    else:
        gpu_score = 3

    # VRAM スコア
    vram_gb = gpu_specs.get('vram_gb')
    vram_map = {24: 10, 16: 9, 12: 8, 8: 6, 6: 5, 4: 3}
    if vram_gb in vram_map:
        vram_score = vram_map[vram_gb]
    elif vram_gb and vram_gb > 24:
        vram_score = 10
    else:
        vram_score = 5

    # RAM スコア（名前から容量を抽出）
    ram_name = (ram_item.get('name', '') if ram_item else '')
    ram_match = re.search(r'(\d+)\s*GB', ram_name, re.IGNORECASE)
    ram_gb = int(ram_match.group(1)) if ram_match else None
    if ram_gb is None:
        ram_score = 5
    elif ram_gb >= 64:
        ram_score = 10
    elif ram_gb >= 32:
        ram_score = 8
    elif ram_gb >= 16:
        ram_score = 6
    elif ram_gb >= 8:
        ram_score = 4
    else:
        ram_score = 3

    # コスパ スコア
    # 1. kakaku 実価格から合計を算出（price_min あり優先）
    gpu_name = gpu_item.get('name', '') if gpu_item else ''
    cpu_name_full = cpu_item.get('name', '') if cpu_item else ''
    ram_name_full = ram_item.get('name', '') if ram_item else ''

    gpu_price = _lookup_kakaku_price(gpu_name, 'gpu', all_products)
    cpu_price = _lookup_kakaku_price(cpu_name_full, 'cpu', all_products)
    ram_price = _lookup_kakaku_price(ram_name_full, 'ram', all_products)

    actual_total = None
    if gpu_price or cpu_price or ram_price:
        actual_total = (gpu_price or 0) + (cpu_price or 0) + (ram_price or 0)

    # 2. 実価格が得られなければ total_estimate の文字列から推定
    if not actual_total:
        price_matches = re.findall(r'([\d.]+)万', total_estimate_str or '')
        if price_matches:
            try:
                prices = [float(x) for x in price_matches]
                actual_total = int(sum(prices) / len(prices) * 10000)
            except Exception:
                pass

    value_score = 5
    if actual_total and actual_total > 0:
        perf = (gpu_score + cpu_score) / 2
        value_score = min(10, max(1, round(perf / (actual_total / 150000) * 5)))

    return {
        'cpu': cpu_score,
        'gpu': gpu_score,
        'vram': vram_score,
        'ram': ram_score,
        'value': value_score,
    }


def _compute_game_req_scores(spec: dict) -> dict:
    """ゲームの推奨スペックをレーダーチャートスコア(1-10)に変換する"""

    # GPU モデル名 Tier テーブル（新→旧順）
    _GPU_TIERS = [
        (10, ['rtx 5090', 'rtx 4090', 'rx 9900 xt']),
        (9,  ['rtx 5080', 'rtx 4080', 'rx 7900 xtx', 'rx 9070 xt']),
        (8,  ['rtx 5070', 'rtx 4070 ti', 'rtx 4070 super', 'rx 7900 xt', 'rx 9070']),
        (7,  ['rtx 4070', 'rtx 3080', 'rx 7800 xt', 'rx 6800 xt', 'rx 9060 xt']),
        (6,  ['rtx 4060 ti', 'rtx 3070', 'rtx 2080', 'rx 7700 xt', 'rx 6700 xt']),
        (5,  ['rtx 4060', 'rtx 3060 ti', 'rtx 2070', 'rx 7600', 'rx 6600 xt', 'gtx 1080 ti', 'gtx 1080']),
        (4,  ['rtx 3060', 'rtx 2060', 'rx 6600', 'rx 5700 xt', 'gtx 1070 ti', 'gtx 1070']),
        (3,  ['rtx 3050', 'rx 6500 xt', 'rx 5600 xt', 'gtx 1060', 'gtx 980 ti', 'gtx 980']),
        (2,  ['gtx 1050 ti', 'gtx 1050', 'gtx 970', 'gtx 960', 'rx 580', 'rx 480']),
    ]

    # CPU スコア（キーワードマッチ）
    cpu_names = spec.get('cpu', []) or []
    cpu_text = ' '.join(cpu_names).lower()
    if any(k in cpu_text for k in ['i9', 'ryzen 9', 'core ultra 9', 'threadripper']):
        cpu_score = 10
    elif any(k in cpu_text for k in ['i7', 'ryzen 7', 'core ultra 7']):
        cpu_score = 8
    elif any(k in cpu_text for k in ['i5', 'ryzen 5', 'core ultra 5']):
        cpu_score = 6
    elif any(k in cpu_text for k in ['i3', 'ryzen 3']):
        cpu_score = 4
    elif any(k in cpu_text for k in ['celeron', 'pentium', 'athlon']):
        cpu_score = 2
    else:
        cpu_score = 5 if cpu_text else 0

    # GPU スコア（Tier テーブルマッチ）
    gpu_names = spec.get('gpu', []) or []
    gpu_text = ' '.join(gpu_names).lower()
    gpu_score = 0
    for score, keywords in _GPU_TIERS:
        if any(k in gpu_text for k in keywords):
            gpu_score = score
            break

    # VRAM スコア（GPU名からVRAMを推定）
    _VRAM_HINTS = [
        (10, ['24gb', '20gb']),
        (9,  ['16gb']),
        (8,  ['12gb']),
        (6,  ['8gb']),
        (5,  ['6gb']),
        (3,  ['4gb']),
    ]
    vram_score = 0
    for score, hints in _VRAM_HINTS:
        if any(h in gpu_text for h in hints):
            vram_score = score
            break
    # VRAM が不明な場合は GPU スコアから推定
    if vram_score == 0 and gpu_score > 0:
        vram_score = max(3, gpu_score - 2)

    # RAM スコア
    ram_gb = spec.get('ram_gb')
    if ram_gb is None:
        ram_score = 0
    elif ram_gb >= 64:
        ram_score = 10
    elif ram_gb >= 32:
        ram_score = 8
    elif ram_gb >= 16:
        ram_score = 6
    elif ram_gb >= 8:
        ram_score = 4
    else:
        ram_score = 3

    return {
        'cpu':   cpu_score,
        'gpu':   gpu_score,
        'vram':  vram_score,
        'ram':   ram_score,
        'value': None,  # ゲーム要件にコスパは非適用
    }


def _search_game(query: str, games: list):
    q = query.lower().strip()
    for g in games:
        if g['name'].lower() == q:
            return g
    for g in games:
        if q in g['name'].lower() or g['name'].lower() in q:
            return g
    words = [w for w in q.split() if len(w) > 2]
    for g in games:
        name_lower = g['name'].lower()
        if words and all(w in name_lower for w in words):
            return g
    return None


def _select_spec_tier(budget_yen: int, game_data: dict) -> tuple:
    """予算からスペック段階を選択する。"""
    specs = game_data.get('specs', {})

    # 新スキーマ対応
    if specs:
        tiers = [
            ('ultra', 250000, 'ウルトラ'),
            ('high', 150000, '高'),
            ('recommended', 100000, '推奨'),
            ('minimum', 0, '最低'),
        ]
        for tier_key, threshold, tier_label in tiers:
            if budget_yen >= threshold and tier_key in specs:
                spec = specs[tier_key]
                return spec, spec.get('label', tier_label)
        # フォールバック: 存在する最低段階
        for tier_key in ['minimum', 'recommended', 'high', 'ultra']:
            if tier_key in specs:
                spec = specs[tier_key]
                return spec, spec.get('label', tier_key)
        return {}, '不明'

    # 旧スキーマ互換（移行中のフォールバック）
    if budget_yen < 200000:
        spec = game_data.get('minimum') or game_data.get('recommended') or {}
        return spec, '最低'
    else:
        spec = game_data.get('recommended') or game_data.get('minimum') or {}
        return spec, '推奨'


def _lookup_kakaku_price(name: str, category: str, all_products: list) -> int | None:
    """
    all_productsからcategoryに一致＆nameが部分一致するエントリの
    最小price_minを返す。見つからなければNone。
    """
    import re
    
    # 名前を正規化（空白・記号除去で寛容なマッチング）
    def normalize_name(s):
        s = s.lower()
        s = re.sub(r'[\s\-_　]+', '', s)  # 空白・ハイフン・アンダースコア除去
        s = re.sub(r'[（）()]', '', s)    # 括弧除去
        return s
    
    name_norm = normalize_name(name)
    if not name_norm or len(name_norm) < 3:  # 短すぎる名前はスキップ
        return None
    
    candidates = []
    for p in all_products:
        if p.get('category') != category:
            continue
        p_name = p.get('name', '')
        p_name_norm = normalize_name(p_name)
        
        # 部分一致判定（より寛容に）
        if name_norm in p_name_norm or p_name_norm in name_norm:
            price = p.get('price_min')
            if price and isinstance(price, (int, float)) and price > 0:
                candidates.append(int(price))
    
    return min(candidates) if candidates else None


@app.route('/api/recommend', methods=['POST'])
def recommend():
    """ゲームのやりたいことからPC構成を提案する。"""
    try:
        data = request.get_json(force=True)
        message = data.get('message', '')

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

        # Step1: ゲーム名・予算をClaude Haikuで抽出
        extract_prompt = (
            'ユーザーの入力からゲーム名と予算を抽出してください。\n'
            f'入力: {message}\n'
            '以下のJSON形式だけで返してください（説明不要）:\n'
            '{"game_name":"ゲーム名","budget_yen":予算数値またはnull,"fps_target":"60fps"または"144fps"またはnull}'
        )
        extract_body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 200,
            'messages': [{'role': 'user', 'content': extract_prompt}]
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=extract_body,
            headers={
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            extract_result = json.loads(resp.read())
        extracted_text = extract_result['content'][0]['text'].strip()
        json_match = re.search(r'\{.*\}', extracted_text, re.DOTALL)
        extracted = _safe_parse_claude_json(json_match.group()) if json_match else {}

        game_name  = extracted.get('game_name', '') or ''
        budget_yen = extracted.get('budget_yen')
        fps_target = extracted.get('fps_target') or '60fps'
        # Phase 2-4: 予算未指定時はミドル帯（15〜20万）をデフォルト目安として使用
        effective_budget = budget_yen if budget_yen else 175000

        # Step2: games.jsonlからゲーム検索
        games_list = _load_steam_games()
        game_data  = _search_game(game_name, games_list) if game_name else None

        # Step3: 推奨スペック取得
        if game_data:
            spec, spec_tier = _select_spec_tier(effective_budget, game_data)
            rec_gpus = spec.get('gpu', []) or []
            rec_cpus = spec.get('cpu', []) or []
            rec_ram  = spec.get('ram_gb')
            rec_storage = spec.get('storage_gb')
            rec_vram = spec.get('gpu_vram_gb')
            target_desc = spec.get('target', '')
            game_info = (
                f'ゲーム名: {game_data["name"]}\n'
                f'対応段階: {spec_tier}（{target_desc}）\n'
                f'参考スペック: GPU {", ".join(rec_gpus[:3]) if rec_gpus else "不明"} / '
                f'CPU {", ".join(rec_cpus[:3]) if rec_cpus else "不明"} / '
                f'RAM {rec_ram}GB / VRAM {rec_vram}GB\n'
                f'※このDB値のみを参考に構成を提案すること。独自にスペック値を生成・変更しないこと\n'
                f'※上記の推奨GPUと同等以上の性能を持つ現行製品を選定すること\n'
                f'※予算内で推奨GPUより上位の製品が買える場合は、そちらを優先すること'
            )
        else:
            spec = {}
            game_info = f'ゲーム名: {game_name}（Steamデータ未収録）\n※推奨スペックが不明なため、公式サイトで確認するよう提案コメントに添えること'

        # Step4: DB内のGPU/CPU候補を取得
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

        # 予算ティアに応じたGPU候補を選出（TDPベースで性能帯を分類）
        all_gpus = [p for p in all_products if p.get('category') == 'gpu']
        _TDP_TIERS = [
            ('ultra',       280, 999),   # RTX 4080 SUPER / RX 7900 XTX 相当
            ('high',        200, 279),   # RTX 4070 Ti / RX 7800 XT 相当
            ('recommended', 120, 199),   # RTX 3060 / RX 6600 相当
            ('minimum',       0, 119),   # GTX 1660 / RX 5500 XT 相当
        ]
        # 選択されたスペック段階 + 1段上を候補に含める
        tier_order = ['minimum', 'recommended', 'high', 'ultra']
        selected_tier = spec_tier if game_data else '推奨'
        tier_map = {'最低': 'minimum', '推奨': 'recommended', '高': 'high', 'ウルトラ': 'ultra'}
        current_tier = tier_map.get(selected_tier, 'recommended')
        current_idx = tier_order.index(current_tier) if current_tier in tier_order else 1
        target_tiers = set(tier_order[max(0, current_idx):min(len(tier_order), current_idx + 2)])

        gpu_candidates = []
        seen_models = set()
        for tier_name, tdp_lo, tdp_hi in _TDP_TIERS:
            if tier_name not in target_tiers:
                continue
            for p in all_gpus:
                tdp = (p.get('specs') or {}).get('tdp_w') or 0
                if tdp_lo <= tdp <= tdp_hi:
                    # モデル名の重複排除（同一GPU型番の異メーカー版は1つだけ）
                    model_key = re.sub(r'(ASRock|ASUS|MSI|Gigabyte|ZOTAC|玄人志向|Palit|Gainward|PNY|Sapphire|PowerColor|Sparkle)\s*', '', p.get('name', ''), flags=re.IGNORECASE).strip()[:30]
                    if model_key not in seen_models:
                        seen_models.add(model_key)
                        gpu_candidates.append(p)
            if len(gpu_candidates) >= 6:
                break
        gpu_candidates = gpu_candidates[:6]

        cpu_candidates = [p for p in all_products if p.get('category') == 'cpu'][:3]

        def fmt_gpu(p):
            s = p.get('specs') or {}
            return f'- {p["name"]}: {s.get("length_mm","?")}mm / TDP {s.get("tdp_w","?")}W'

        def fmt_cpu(p):
            # Phase 2-2: コア数/スレッド数をDBから注入（Claude推測を防ぐ）
            s = p.get('specs') or {}
            detail = []
            if s.get('cores'):   detail.append(f'{s["cores"]}コア')
            if s.get('threads'): detail.append(f'{s["threads"]}スレッド')
            return f'- {p["name"]}' + (f' ({", ".join(detail)})' if detail else '')

        # Phase 2-4: 予算未指定時はミドル帯（15〜20万）をデフォルト提案
        # Step5: Claude APIで構成提案生成
        if budget_yen:
            budget_str = f'予算{budget_yen:,}円'
        else:
            budget_str = '予算未指定（デフォルト: ミドルレンジ15〜20万円を目安に提案すること）'

        build_prompt = (
            'PCゲームの推奨パーツ構成を提案してください。\n\n'
            f'## ユーザー要求\n{message}\n{budget_str}、{fps_target}目標\n\n'
            f'## Steamの推奨スペック\n{game_info}\n\n'
            f'## DBにある主なGPU候補\n' +
            '\n'.join(fmt_gpu(p) for p in gpu_candidates) +
            '\n\n## DBにある主なCPU候補\n' +
            '\n'.join(fmt_cpu(p) for p in cpu_candidates) +
            '\n\n## 指示\n'
            '- CPUのコア数・スレッド数はDB値（上記）をそのまま使用。独自に変更・生成しないこと\n'
            '- ゲームスペックのRAM値は上記DB値のみ参照。独自に生成しないこと\n'
            '- ユーザーが言及していない用途を勝手に追加しないこと\n'
            '- 推奨スペックは公式発表データであり、変更・省略しないこと\n'
            '- 「推奨スペック未公開」とは絶対に言わないこと（DBに存在する）\n'
            '- 【必須】フル構成を提案すること。recommended_buildには最低限以下のカテゴリを含めること：\n'
            '  GPU, CPU, MB（マザーボード）, RAM, PSU（電源）, CASE（ケース）, SSD/Storage, Cooler（CPUクーラー）\n'
            '\n以下のJSON形式だけで返してください（説明不要）:\n'
            '{"reply":"2〜3文の提案コメント（日本語・フレンドリー）",'
            '"recommended_build":['
            '{"category":"GPU","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"CPU","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"MB","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"RAM","name":"DDR5 32GB など","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"PSU","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"CASE","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"SSD","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"},'
            '{"category":"COOLER","name":"製品名","reason":"選定理由1文","price_range":"¥XX,000〜¥XX,000"}'
            '],"total_estimate":"¥XX万〜¥XX万",'
            '"tip":"追加アドバイス1文"}'
        )
        build_body = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 1500,  # 8カテゴリフル構成対応（元800→1500）
            'temperature': 0.3,  # Phase 2-3: 再現性向上（ブレを抑制）
            'messages': [{'role': 'user', 'content': build_prompt}]
        }).encode('utf-8')
        req2 = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=build_body,
            headers={
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            method='POST'
        )
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            build_result = json.loads(resp2.read())
        build_text = build_result['content'][0]['text'].strip()
        json_match2 = re.search(r'\{.*\}', build_text, re.DOTALL)
        build_data = _safe_parse_claude_json(json_match2.group()) if json_match2 else {}

        recommended_build = build_data.get('recommended_build', [])
        for item in recommended_build:
            item['amazon_url']  = make_amazon_url(item.get('name', ''))
            item['rakuten_url'] = make_rakuten_url(item.get('name', ''))
            item['confirmed']   = False  # ゲーム推奨はユーザー未承認なので ai_pending 扱い

        # price_range から数値を抽出して合計を計算（Claudeの誤算を防ぐ）
        def _calc_total(build):
            lo_sum = hi_sum = 0
            for item in build:
                nums = re.findall(r'[\d,]+', item.get('price_range', ''))
                vals = []
                for n in nums:
                    try:
                        vals.append(int(n.replace(',', '')))
                    except ValueError:
                        pass
                if len(vals) >= 2:
                    lo_sum += vals[0]; hi_sum += vals[1]
                elif len(vals) == 1:
                    lo_sum += vals[0]; hi_sum += vals[0]
            if lo_sum == 0:
                return build_data.get('total_estimate', '')
            lo_man = round(lo_sum / 10000, 1)
            hi_man = round(hi_sum / 10000, 1)
            lo_str = str(int(lo_man)) if lo_man == int(lo_man) else str(lo_man)
            hi_str = str(int(hi_man)) if hi_man == int(hi_man) else str(hi_man)
            return f'¥{lo_str}万〜¥{hi_str}万'

        total_estimate   = _calc_total(recommended_build)
        radar_scores     = _compute_radar_scores(recommended_build, all_products, total_estimate)
        game_req_scores  = _compute_game_req_scores(spec) if spec else None

        return jsonify({
            'type': 'recommendation',
            'game': {
                'name':       game_data['name'] if game_data else game_name,
                'appid':      game_data.get('appid') if game_data else None,
                'screenshot': game_data.get('screenshot') if game_data else None,
            },
            'required_specs':    spec,
            'recommended_build': recommended_build,
            'total_estimate':    total_estimate,
            'radar_scores':      radar_scores,
            'game_req_scores':   game_req_scores,
            'reply':             build_data.get('reply', ''),
            'tip':               build_data.get('tip', ''),
        })

    except Exception as e:
        return jsonify({'error': str(e), 'type': 'error'}), 500


# ================================================================
# 完成イメージ画像生成（FLUX API）
# ================================================================

def _translate_parts_to_english_prompt(parts: list) -> str:
    """
    構成パーツリストを英語プロンプトに変換する。
    例: [{"category":"GPU","name":"RTX 5070"}, ...] 
    → "Photorealistic gaming PC build with RTX 5070 GPU, Ryzen 7 9700X CPU..."
    """
    if not parts:
        return "High-end gaming PC build, RGB lighting, professional product photography"
    
    # カテゴリ別パーツ名を収集
    gpu_name  = next((p['name'] for p in parts if p.get('category', '').upper() == 'GPU'), None)
    cpu_name  = next((p['name'] for p in parts if p.get('category', '').upper() == 'CPU'), None)
    case_name = next((p['name'] for p in parts if p.get('category', '').upper() in ('CASE', 'ケース')), None)
    
    # 日本語ブランド名→英語（一部）
    def _clean_jp_brand(name: str) -> str:
        if not name:
            return ''
        # 「玄人志向」等の日本語ブランド名を除去（FLUXが理解しづらいため）
        name = re.sub(r'玄人志向|クロシコ', '', name)
        return name.strip()
    
    gpu_clean  = _clean_jp_brand(gpu_name)  if gpu_name  else None
    cpu_clean  = _clean_jp_brand(cpu_name)  if cpu_name  else None
    case_clean = _clean_jp_brand(case_name) if case_name else None
    
    # プロンプト構築
    prompt_parts = ["Photorealistic gaming PC build with"]
    
    if gpu_clean:
        prompt_parts.append(f"{gpu_clean} graphics card")
    if cpu_clean:
        prompt_parts.append(f"{cpu_clean} processor")
    if case_clean:
        prompt_parts.append(f"mounted in {case_clean} case")
    
    prompt_parts.extend([
        "RGB lighting",
        "high-end components",
        "professional product photography",
        "detailed hardware",
        "studio lighting"
    ])
    
    return ', '.join(prompt_parts)


@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """
    POST /api/generate-image
    リクエスト: {"parts": [{"category":"GPU","name":"RTX 5070"}, ...]}
    レスポンス: {"image_url": "https://...", "prompt": "..."}
    """
    try:
        if not REPLICATE_API_TOKEN:
            return jsonify({
                'error': 'REPLICATE_API_TOKEN が設定されていません。'
            }), 500

        data = request.get_json(force=True) or {}
        parts = data.get('parts', [])

        if not parts:
            return jsonify({'error': 'parts が空です'}), 400

        # プロンプト生成
        prompt = _translate_parts_to_english_prompt(parts)

        # FLUX.1-schnell モデルで画像生成（requests で直接呼び出し）
        import time
        pred_res = urllib.request.urlopen(
            urllib.request.Request(
                'https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions',
                data=json.dumps({
                    "input": {
                        "prompt": prompt,
                        "num_outputs": 1,
                        "aspect_ratio": "16:9",
                        "output_format": "webp",
                        "output_quality": 80,
                    }
                }).encode('utf-8'),
                headers={
                    'Authorization': f'Bearer {REPLICATE_API_TOKEN}',
                    'Content-Type': 'application/json',
                    'Prefer': 'wait',  # 完了まで待機（最大60秒）
                },
                method='POST',
            ),
            timeout=90,
        )
        pred_data = json.loads(pred_res.read().decode('utf-8'))

        # status が succeeded になるまでポーリング（Prefer:wait で通常は即完了）
        for _ in range(30):
            status = pred_data.get('status')
            if status == 'succeeded':
                break
            if status in ('failed', 'canceled'):
                return jsonify({'error': f'画像生成失敗: {pred_data.get("error", "unknown")}'}), 500
            if status in ('starting', 'processing'):
                time.sleep(2)
                poll_url = pred_data.get('urls', {}).get('get', '')
                if poll_url:
                    poll_res = urllib.request.urlopen(
                        urllib.request.Request(
                            poll_url,
                            headers={'Authorization': f'Bearer {REPLICATE_API_TOKEN}'},
                        ),
                        timeout=30,
                    )
                    pred_data = json.loads(poll_res.read().decode('utf-8'))
            else:
                break

        output = pred_data.get('output')
        image_url = output[0] if isinstance(output, list) and output else (output or None)

        if not image_url:
            return jsonify({'error': '画像生成に失敗しました'}), 500

        return jsonify({
            'image_url': str(image_url),
            'prompt': prompt,
        })

    except Exception as e:
        return jsonify({'error': f'画像生成エラー: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
