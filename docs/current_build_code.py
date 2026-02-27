"""
current_build / confirmed_parts / API呼び出し 関連コード抜粋
ソース: app.py（2026-02-28時点）

このファイルは参照・設計検討用。実際の動作コードは app.py を参照。
"""

# ================================================================
# セッション構造（get_or_create_session より）
# ================================================================

SESSION_STRUCTURE = {
    'confirmed_parts': {},      # {category_str: part_name_str}
                                # 例: {'GPU': 'GeForce RTX 5070 Ti 16G GAMING TRIO OC'}
    'current_build': {
        'cpu':         None,    # {name, socket, tdp_w, user_specified}
        'gpu':         None,    # {name, length_mm, tdp_w, vram_gb, user_specified}
        'motherboard': None,    # {name, socket, memory_type, form_factor, user_specified}
        'ram':         None,    # {name, memory_type, capacity_gb, user_specified}
        'case':        None,    # {name, max_gpu_length_mm, form_factor, user_specified}
        'psu':         None,    # {name, wattage_w, user_specified}
        'cooler':      None,    # {name, user_specified}
    },
    'recheck_flags': [],        # 再チェックが必要なカテゴリリスト
    'history': [],              # 会話履歴（直近10メッセージのみ保持）
    'stage': 'hearing',         # 'hearing' or 'recommending'
    'budget_yen': None,         # 抽出した予算（整数）
    'resolution': None,         # 抽出した解像度（'FHD'/'WQHD'/'4K'）
    'quality': None,            # 抽出した画質
}


# ================================================================
# DBからスペックを取得（_get_part_specs_from_db）
# ================================================================

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
    for p in all_products:
        if p.get('category', '').lower() in target_cats:
            if p.get('name', '').lower() == name_lower:
                specs = p.get('specs', {}) or {}
                return {
                    'name': p['name'],
                    'id': p.get('id'),
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


# ================================================================
# 依存関係マップ
# ================================================================

# {変更カテゴリ: [(影響カテゴリ, チェック種別), ...]}
_BUILD_DEPENDENCY_MAP = {
    'cpu':         [('motherboard', 'socket_reset'), ('ram', 'socket_reset'),
                    ('cooler', 'recheck'), ('psu', 'recheck')],
    'gpu':         [('case', 'recheck'), ('psu', 'recheck')],
    'motherboard': [('ram', 'memtype_reset'), ('case', 'recheck')],
    'ram':         [],
    'case':        [],
    'psu':         [],
    'cooler':      [],
}

# チェック種別の意味:
#   socket_reset  : ソケット不一致の場合、依存パーツをNullリセット
#   memtype_reset : DDRタイプ不一致の場合、RAMをNullリセット
#   recheck       : 再確認フラグを立てる（自動リセットはしない）


# ================================================================
# current_build更新 + 依存関係チェック（update_current_build）
# ================================================================

def update_current_build(session, category, part_name, all_products, user_specified=False):
    """
    current_buildを更新し、依存関係チェックを実行する。

    引数:
        session       : セッション辞書
        category      : パーツカテゴリ ('cpu', 'gpu', 'mb', 'ram', 'case', 'psu', 'cooler')
        part_name     : 製品名（DB照合キー）
        all_products  : 全製品リスト
        user_specified: ユーザーが型番直指定した場合True

    戻り値:
        {'reset_parts': [...], 'recheck_parts': [...]}

    reset_parts  : UIからリセットすべきカテゴリのリスト（互換性破綻）
    recheck_parts: 再確認が必要なカテゴリのリスト（TDP/サイズ変化）
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
    gpu_tdp   = gpu_part.get('tdp_w') or 0
    cpu_tdp   = cpu_part.get('tdp_w') or 0
    psu_w     = psu_part.get('wattage_w') or 0
    required_w = (gpu_tdp * 1.3) + (cpu_tdp * 1.1) + 50
    if psu_w > 0 and psu_w < required_w and 'psu' not in recheck_parts:
        recheck_parts.append('psu')

    # GPU長さとケースのチェック
    case_part = session['current_build'].get('case') or {}
    gpu_len   = gpu_part.get('length_mm') or 0
    case_max  = case_part.get('max_gpu_length_mm') or 9999
    if gpu_len > 0 and gpu_len >= case_max and 'case' not in recheck_parts:
        recheck_parts.append('case')

    session['recheck_flags'] = list(set(session.get('recheck_flags', []) + recheck_parts))

    return {'reset_parts': reset_parts, 'recheck_parts': recheck_parts}


# ================================================================
# current_build → AIプロンプト文字列生成（format_current_build_for_claude）
# ================================================================

def format_current_build_for_claude(current_build, recheck_flags=None):
    """
    current_buildの構造化情報をAIへのプロンプトとして整形する。

    出力例:
        ## 現在の構成（コード管理・確定済み）
        ✅ GPU: GeForce RTX 5070 Ti 16G GAMING TRIO OC (長さ:320mm, TDP:300W)
        ✅ CPU: Ryzen 9 9900X (ソケット:AM5, TDP:120W)
        ⏳ 未決定（次に提案すべき）: マザーボード, RAM, ケース, 電源, CPUクーラー

        📊 必要電源容量: 522W以上（GPU 300W × 1.3 + CPU 120W × 1.1 + 50W）
    """
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
            name    = part.get('name', '?')
            details = []
            if part.get('socket'):            details.append(f"ソケット:{part['socket']}")
            if part.get('memory_type'):       details.append(f"メモリ:{part['memory_type']}")
            if part.get('form_factor'):       details.append(f"FF:{part['form_factor']}")
            if part.get('length_mm'):         details.append(f"長さ:{part['length_mm']}mm")
            if part.get('tdp_w'):             details.append(f"TDP:{part['tdp_w']}W")
            if part.get('wattage_w'):         details.append(f"容量:{part['wattage_w']}W")
            if part.get('max_gpu_length_mm'): details.append(f"GPU最大:{part['max_gpu_length_mm']}mm")

            status       = '🔒' if part.get('user_specified') else '✅'
            recheck_note = ' ⚠️要再確認' if key in recheck_flags else ''
            detail_str   = f" ({', '.join(details)})" if details else ''
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
            margin      = psu_p['wattage_w'] - req_w
            status_icon = '✅' if margin >= 0 else '❌'
            lines.append(f"   {status_icon} 現在の電源: {psu_p['wattage_w']}W（余裕: {margin:+d}W）")

    # GPUとケースの物理適合チェック
    if (gpu_p.get('length_mm')
            and current_build.get('case')
            and current_build['case'].get('max_gpu_length_mm')):
        gpu_len  = gpu_p['length_mm']
        case_max = current_build['case']['max_gpu_length_mm']
        margin   = case_max - gpu_len
        status_icon = '✅' if margin > 0 else '❌'
        lines.append(f"   {status_icon} GPU物理適合: GPU {gpu_len}mm / ケース上限 {case_max}mm（余裕: {margin:+d}mm）")

    return "\n".join(lines) + "\n"


# ================================================================
# confirmed_parts → AIプロンプト文字列生成（format_confirmed_parts）
# ================================================================

def format_confirmed_parts(confirmed_parts):
    """
    confirmed_partsを構造化テキストとしてフォーマット。

    confirmed_parts 構造:
        {'GPU': 'GeForce RTX 5070 Ti 16G GAMING TRIO OC', 'CPU': 'Ryzen 9 9900X', ...}
        ※キーは大文字のカテゴリ名

    出力例:
        ## 確定済みパーツ
        - GPU: GeForce RTX 5070 Ti 16G GAMING TRIO OC
        - CPU: Ryzen 9 9900X
    """
    if not confirmed_parts:
        return "## 確定済みパーツ\n（まだ選択されていません）\n"

    lines = ["## 確定済みパーツ"]
    for category, part_name in confirmed_parts.items():
        lines.append(f"- {category.upper()}: {part_name}")

    return "\n".join(lines) + "\n"
