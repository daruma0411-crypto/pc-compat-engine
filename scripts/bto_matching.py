#!/usr/bin/env python3
"""
BTOマッチングアルゴリズム

自然言語入力 → スペック要件ベクトル生成 → 加重ユークリッド距離計算 → 松竹梅出力

Usage:
    from bto_matching import build_spec_vector, match_bto_products, select_goldilocks
"""

import json
import math
import os
import re

# ---------------------------------------------------------------------------
# データ読み込み
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, '..', 'workspace', 'data')


def load_bto_products(path=None):
    """BTOインベントリDBを読み込む"""
    path = path or os.path.join(_DATA_DIR, 'bto', 'products.jsonl')
    products = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))
    return products


def load_performance_scores(path=None):
    """パフォーマンススコアDBを読み込む"""
    path = path or os.path.join(_DATA_DIR, 'performance_scores.jsonl')
    scores = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                key = _normalize_part_name(entry['name'])
                scores[key] = entry
    return scores


def _normalize_part_name(name):
    """パーツ名を正規化して比較可能にする"""
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    # "NVIDIA " "AMD " "Intel " プレフィックス除去
    name = re.sub(r'^(nvidia|amd|intel)\s+', '', name)
    # "GeForce " プレフィックス除去
    name = re.sub(r'^geforce\s+', '', name)
    # "Core " → そのまま残す
    return name


# ---------------------------------------------------------------------------
# Steam DB → ゲーム要件の動的取得
# ---------------------------------------------------------------------------

# performance_scores.jsonl にないGPU の推定スコア（Steam要件解析用）
_GPU_SCORE_ESTIMATES = {
    'gtx 460': 6, 'gtx 560 ti': 8, 'gtx 560': 7,
    'gtx 660': 10, 'gtx 670': 11, 'gtx 680': 13,
    'gtx 750 ti': 14, 'gtx 760': 15,
    'gtx 770': 17, 'gtx 780': 19,
    'gtx 950': 16, 'gtx 960': 17, 'gtx 970': 20, 'gtx 980': 22,
    'gtx 1050 ti': 17, 'gtx 1050': 15, 'gtx 1060': 20,
    'gtx 1070 ti': 30, 'gtx 1070': 28, 'gtx 1080 ti': 35, 'gtx 1080': 32,
    'gtx 1650': 16, 'gtx 1660 ti': 22, 'gtx 1660': 20,
    'rtx 2060': 30, 'rtx 2070': 38, 'rtx 2080': 45,
    'rtx 3070': 50, 'rtx 3080': 60, 'rtx 3090': 70,
    'rx 480': 18, 'rx 570': 17, 'rx 580': 19,
    'rx 5600': 30, 'rx 5700': 35,
    'rx 6600 xt': 38, 'rx 6600': 35, 'rx 6700 xt': 42, 'rx 6800 xt': 55,
    'rx 7600': 38,
}


def _extract_gpu_from_text(gpu_texts):
    """GPU要件テキストからGPU名を抽出"""
    if not gpu_texts:
        return None
    combined = ' '.join(gpu_texts) if isinstance(gpu_texts, list) else str(gpu_texts)
    # 特殊文字除去
    combined = combined.replace('®', '').replace('™', '').replace('(R)', '').replace('（', '(')

    # GeForce / RTX / GTX パターン
    m = re.search(
        r'(?:GeForce\s+)?((?:RTX|GTX)\s+\d{3,4}(?:\s+(?:Ti|SUPER|XT))?)',
        combined, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Radeon RX パターン
    m = re.search(
        r'Radeon\s+(RX\s+\d{3,4}(?:\s+(?:XT|X))?)',
        combined, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None


def _gpu_name_to_score(gpu_name, perf_scores):
    """GPU名 → パフォーマンススコア（perf_scores参照 → 推定テーブル → None）"""
    if gpu_name is None:
        return None
    normalized = _normalize_part_name(gpu_name)
    entry = perf_scores.get(normalized)
    if entry:
        return entry['score']
    # 推定テーブルで部分一致（長いキーから先に照合）
    name_lower = gpu_name.lower().strip()
    for key in sorted(_GPU_SCORE_ESTIMATES, key=len, reverse=True):
        if key in name_lower:
            return _GPU_SCORE_ESTIMATES[key]
    return None


def load_game_requirements():
    """Steam DB (games.jsonl) からゲームタイトル→GPU要件スコアを動的生成"""
    games_path = os.path.join(_DATA_DIR, 'steam', 'games.jsonl')
    if not os.path.exists(games_path):
        return {}

    perf_scores = load_performance_scores()
    requirements = {}

    with open(games_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            game = json.loads(line)
            name = game.get('name', '')
            if not name:
                continue

            specs = game.get('specs', {})
            rec = specs.get('recommended') or specs.get('minimum') or {}
            gpu_texts = rec.get('gpu')
            if not gpu_texts:
                continue

            gpu_name = _extract_gpu_from_text(gpu_texts)
            gpu_score = _gpu_name_to_score(gpu_name, perf_scores)
            if gpu_score is not None:
                requirements[name.lower()] = gpu_score

    return requirements


# キャッシュ（モジュールレベル）
_steam_game_reqs_cache = None


def _get_steam_game_requirements():
    """Steam DB ゲーム要件をキャッシュ付きで取得"""
    global _steam_game_reqs_cache
    if _steam_game_reqs_cache is None:
        _steam_game_reqs_cache = load_game_requirements()
    return _steam_game_reqs_cache


# ---------------------------------------------------------------------------
# スペック要件ベクトル生成
# ---------------------------------------------------------------------------

# 解像度 → GPU負荷乗数
_RES_MULTIPLIER = {
    'FHD': 1.0, '1080p': 1.0,
    'WQHD': 1.6, '1440p': 1.6,
    '4K': 2.8, '2160p': 2.8,
}

# 画質 → GPU負荷乗数
_QUALITY_MULTIPLIER = {
    '低': 0.6, 'low': 0.6,
    '中': 0.8, 'medium': 0.8,
    '高': 1.0, 'high': 1.0,
    '最高': 1.3, 'ultra': 1.3, '最高画質': 1.3,
}

# FPS → GPU負荷乗数
_FPS_MULTIPLIER = {
    30: 0.7,
    60: 1.0,
    120: 1.4,
    144: 1.5,
    165: 1.55,
    240: 1.8,
}

# 用途キーワード → スペック傾向
_USE_CASE_PROFILES = {
    'gaming': {
        'gpu_weight': 1.0, 'cpu_weight': 0.6, 'vram_base': 8,
        'ram_base': 16, 'keywords': [
            'ゲーム', 'ゲーミング', 'gaming', 'fps', 'バトロワ',
            'mmorpg', 'オープンワールド', 'steam',
        ],
    },
    'creator': {
        'gpu_weight': 0.8, 'cpu_weight': 1.0, 'vram_base': 12,
        'ram_base': 32, 'keywords': [
            '動画編集', 'premiere', 'davinci', 'after effects',
            '3d', 'blender', 'maya', 'unreal', 'unity',
            '映像制作', 'モデリング', 'レンダリング',
        ],
    },
    'ai': {
        'gpu_weight': 0.9, 'cpu_weight': 0.5, 'vram_base': 16,
        'ram_base': 32, 'keywords': [
            'ai', '画像生成', 'stable diffusion', 'comfyui',
            '機械学習', 'llm', 'ローカルai', 'deep learning',
        ],
    },
    'streaming': {
        'gpu_weight': 0.9, 'cpu_weight': 0.9, 'vram_base': 8,
        'ram_base': 32, 'keywords': [
            '配信', 'obs', 'vtuber', 'streaming', '実況',
            'vtube studio', '生放送',
        ],
    },
    'work': {
        'gpu_weight': 0.3, 'cpu_weight': 0.7, 'vram_base': 4,
        'ram_base': 16, 'keywords': [
            '仕事', 'office', 'ビジネス', 'テレワーク',
            'web閲覧', 'ネット', 'マイクラ', 'minecraft', '軽い',
        ],
    },
}

# ゲームタイトル → 必要GPU性能レベル（0-100）
_GAME_GPU_REQUIREMENTS = {
    'cyberpunk 2077': 80, 'サイバーパンク': 80,
    'モンハンワイルズ': 75, 'monster hunter wilds': 75,
    'elden ring': 60, 'エルデンリング': 60,
    'ff14': 50, 'ファイナルファンタジー14': 50, 'final fantasy xiv': 50,
    'ff16': 70, 'ファイナルファンタジー16': 70,
    'apex legends': 45, 'apex': 45, 'エーペックス': 45,
    'valorant': 30, 'ヴァロラント': 30,
    'fortnite': 40, 'フォートナイト': 40,
    'minecraft': 25, 'マイクラ': 25, 'マインクラフト': 25,
    'call of duty': 65, 'cod': 65,
    'palworld': 55, 'パルワールド': 55,
    'gta v': 40, 'gta 5': 40,
    'gta vi': 80, 'gta 6': 80,
    'starfield': 65, 'スターフィールド': 65,
    'hogwarts legacy': 60, 'ホグワーツレガシー': 60,
    'armored core vi': 55, 'アーマードコア6': 55,
    'baldur\'s gate 3': 55, 'バルダーズゲート3': 55,
    'black myth wukong': 75, '黒神話': 75,
    'dragon\'s dogma 2': 65, 'ドラゴンズドグマ2': 65,
}


def _detect_use_case(user_input):
    """ユーザー入力から用途を判定"""
    text = user_input.lower()
    scores = {}
    for use_case, profile in _USE_CASE_PROFILES.items():
        score = sum(1 for kw in profile['keywords'] if kw in text)
        if score > 0:
            scores[use_case] = score

    if not scores:
        return 'gaming'  # デフォルトはゲーミング

    return max(scores, key=scores.get)


def _extract_budget(user_input):
    """予算を抽出（円）"""
    # 「25万」「25万円」「250000円」「250,000」
    m = re.search(r'(\d+)\s*万\s*円?', user_input)
    if m:
        return int(m.group(1)) * 10000

    m = re.search(r'(\d{1,3}(?:,\d{3})+)\s*円?', user_input)
    if m:
        return int(m.group(1).replace(',', ''))

    m = re.search(r'(\d{5,})\s*円?', user_input)
    if m:
        return int(m.group(1))

    return None


def _extract_resolution(user_input):
    """解像度を抽出"""
    text = user_input.upper()
    for key in ['4K', '2160P', 'WQHD', '1440P', 'FHD', '1080P']:
        if key in text:
            return key
    return 'FHD'


def _extract_fps(user_input):
    """FPS目標を抽出"""
    m = re.search(r'(\d+)\s*fps', user_input, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 60


def _extract_quality(user_input):
    """画質設定を抽出"""
    for q in ['最高画質', '最高', 'ultra', '高', 'high', '中', 'medium', '低', 'low']:
        if q in user_input.lower():
            return q
    return '高'


def _extract_game(user_input):
    """ゲーム名を抽出してGPU要件を返す

    優先順位: 1. ハードコード定義  2. Steam DB  3. None
    ハードコードは最新タイトルや日本語名の正確なマッピングを保証する。
    """
    text = user_input.lower()

    # 1. ハードコード辞書を先に検索（手動定義で精度が高い）
    for game_key, gpu_req in _GAME_GPU_REQUIREMENTS.items():
        if game_key in text:
            return game_key, gpu_req

    # 2. Steam DB からゲーム名を部分一致検索
    steam_reqs = _get_steam_game_requirements()
    best_match = None
    best_len = 0
    for game_name, gpu_score in steam_reqs.items():
        # ゲーム名がユーザー入力に含まれている（長い一致を優先）
        if game_name in text and len(game_name) > best_len:
            best_match = (game_name, gpu_score)
            best_len = len(game_name)
        # ユーザー入力がゲーム名の先頭に一致 or ワード境界で一致（3文字以上）
        elif len(text) >= 3 and re.search(r'\b' + re.escape(text) + r'\b', game_name):
            if len(game_name) > best_len:
                best_match = (game_name, gpu_score)
                best_len = len(game_name)

    if best_match:
        return best_match

    return None, None


def _closest_fps_multiplier(fps):
    """最も近いFPS乗数を返す"""
    if fps in _FPS_MULTIPLIER:
        return _FPS_MULTIPLIER[fps]
    # 線形補間
    keys = sorted(_FPS_MULTIPLIER.keys())
    if fps <= keys[0]:
        return _FPS_MULTIPLIER[keys[0]]
    if fps >= keys[-1]:
        return _FPS_MULTIPLIER[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= fps <= keys[i + 1]:
            ratio = (fps - keys[i]) / (keys[i + 1] - keys[i])
            return (_FPS_MULTIPLIER[keys[i]] * (1 - ratio)
                    + _FPS_MULTIPLIER[keys[i + 1]] * ratio)
    return 1.0


def build_spec_vector(user_input, budget_yen=None, game_name=None,
                      resolution=None, fps_target=None, quality=None):
    """
    自然言語入力からスペック要件ベクトルを生成

    Returns:
        dict: {
            'cpu_score': float,     # 0-100
            'gpu_score': float,     # 0-100
            'vram_gb': int,         # 8/12/16/24/32
            'ram_gb': int,          # 16/32/64
            'budget_min': int,      # 円
            'budget_max': int,      # 円
            'use_case': str,        # gaming/creator/ai/streaming/work
            'resolution': str,
            'fps_target': int,
            'quality': str,
            'game_detected': str | None,
        }
    """
    # 各パラメータ抽出（明示的な引数があれば優先）
    budget = budget_yen or _extract_budget(user_input)
    res = resolution or _extract_resolution(user_input)
    fps = fps_target or _extract_fps(user_input)
    qual = quality or _extract_quality(user_input)
    use_case = _detect_use_case(user_input)
    game_detected, game_gpu_req = _extract_game(user_input)

    # デフォルト予算（指定なし）
    if budget is None:
        budget = 250000  # 25万円をデフォルト

    # GPU性能要件の算出
    profile = _USE_CASE_PROFILES[use_case]

    if game_gpu_req is not None:
        # ゲームの要件ベースで計算
        base_gpu = game_gpu_req
    else:
        # 解像度×画質×FPSから推定
        res_mult = _RES_MULTIPLIER.get(res, 1.0)
        qual_mult = _QUALITY_MULTIPLIER.get(qual, 1.0)
        fps_mult = _closest_fps_multiplier(fps)
        base_gpu = 35 * res_mult * qual_mult * fps_mult

    # 用途別の最低GPU要件（AI/クリエイターは解像度/FPSに依存しない負荷がある）
    _USE_CASE_MIN_GPU = {
        'gaming': 25, 'creator': 45, 'ai': 65,
        'streaming': 40, 'work': 15,
    }
    base_gpu = max(base_gpu, _USE_CASE_MIN_GPU.get(use_case, 25))

    gpu_score = min(base_gpu * profile['gpu_weight'], 100)
    cpu_score = min(base_gpu * profile['cpu_weight'], 100)

    # VRAM要件
    vram_gb = profile['vram_base']
    if gpu_score >= 80:
        vram_gb = max(vram_gb, 16)
    elif gpu_score >= 60:
        vram_gb = max(vram_gb, 12)
    # AI用途は常にVRAM重視
    if use_case == 'ai':
        vram_gb = max(vram_gb, 16)

    # RAM要件
    ram_gb = profile['ram_base']
    if budget >= 300000:
        ram_gb = max(ram_gb, 32)
    if use_case in ('creator', 'ai', 'streaming'):
        ram_gb = max(ram_gb, 32)

    return {
        'cpu_score': round(cpu_score, 1),
        'gpu_score': round(gpu_score, 1),
        'vram_gb': vram_gb,
        'ram_gb': ram_gb,
        'budget_min': int(budget * 0.85),
        'budget_max': int(budget * 1.15),
        'use_case': use_case,
        'resolution': res,
        'fps_target': fps,
        'quality': qual,
        'game_detected': game_detected,
    }


# ---------------------------------------------------------------------------
# BTOマッチングアルゴリズム（加重ユークリッド距離）
# ---------------------------------------------------------------------------

# 各次元の正規化定数（スケール統一用）
_NORM = {
    'gpu_score': 100.0,
    'cpu_score': 100.0,
    'vram_gb': 32.0,
    'ram_gb': 64.0,
    'price': 1000000.0,
}

# デフォルトの次元別重み
_DEFAULT_WEIGHTS = {
    'gpu_score': 0.35,
    'cpu_score': 0.20,
    'vram_gb': 0.15,
    'ram_gb': 0.10,
    'price': 0.20,
}

# 用途別の重み調整
_USE_CASE_WEIGHT_OVERRIDES = {
    'gaming': {'gpu_score': 0.40, 'cpu_score': 0.15, 'vram_gb': 0.10,
               'ram_gb': 0.10, 'price': 0.25},
    'creator': {'gpu_score': 0.25, 'cpu_score': 0.30, 'vram_gb': 0.15,
                'ram_gb': 0.15, 'price': 0.15},
    'ai': {'gpu_score': 0.25, 'cpu_score': 0.10, 'vram_gb': 0.35,
           'ram_gb': 0.10, 'price': 0.20},
    'streaming': {'gpu_score': 0.30, 'cpu_score': 0.25, 'vram_gb': 0.10,
                  'ram_gb': 0.15, 'price': 0.20},
    'work': {'gpu_score': 0.10, 'cpu_score': 0.25, 'vram_gb': 0.05,
             'ram_gb': 0.15, 'price': 0.45},
}

# オーバースペックペナルティ係数
_OVERSHOOT_PENALTY = 0.3


def _bto_to_vector(bto_product, perf_scores):
    """BTO製品をスペックベクトルに変換"""
    specs = bto_product.get('specs', {})

    # GPU スコア検索
    gpu_name = _normalize_part_name(specs.get('gpu', {}).get('name', ''))
    gpu_entry = perf_scores.get(gpu_name, {})
    gpu_score = gpu_entry.get('score', 50)

    # CPU スコア検索
    cpu_name = _normalize_part_name(specs.get('cpu', {}).get('name', ''))
    cpu_entry = perf_scores.get(cpu_name, {})
    cpu_score = cpu_entry.get('score', 50)

    return {
        'gpu_score': gpu_score,
        'cpu_score': cpu_score,
        'vram_gb': specs.get('gpu', {}).get('vram_gb', 8),
        'ram_gb': specs.get('ram', {}).get('capacity_gb', 16),
        'price': bto_product.get('price_jpy', 200000),
    }


def match_bto_products(spec_vector, bto_products, perf_scores=None,
                       commission_bias=False):
    """
    スペック要件ベクトルに最も近いBTO製品を加重ユークリッド距離でランク付け

    Args:
        spec_vector: build_spec_vector() の出力
        bto_products: load_bto_products() の出力
        perf_scores: load_performance_scores() の出力
        commission_bias: 報酬率バイアスを適用するか（将来用）

    Returns:
        list of (product, score, distance, breakdown):
            - product: BTO製品dict
            - score: マッチスコア（0-1、高いほど良い）
            - distance: ユークリッド距離（低いほど良い）
            - breakdown: 各次元のペナルティ内訳dict
    """
    if perf_scores is None:
        perf_scores = load_performance_scores()

    use_case = spec_vector.get('use_case', 'gaming')
    weights = _USE_CASE_WEIGHT_OVERRIDES.get(use_case, _DEFAULT_WEIGHTS)

    # 理想スペックベクトル
    ideal = {
        'gpu_score': spec_vector['gpu_score'],
        'cpu_score': spec_vector['cpu_score'],
        'vram_gb': spec_vector['vram_gb'],
        'ram_gb': spec_vector['ram_gb'],
        'price': (spec_vector['budget_min'] + spec_vector['budget_max']) / 2,
    }

    scored = []

    for bto in bto_products:
        bto_vec = _bto_to_vector(bto, perf_scores)
        breakdown = {}
        distance_sq = 0.0

        for dim, weight in weights.items():
            need = ideal.get(dim, 0)
            have = bto_vec.get(dim, 0)
            norm = _NORM.get(dim, 1.0)

            # 正規化した差分
            diff = (have - need) / norm

            if dim == 'price':
                # 価格は「予算内に収まる」ことが重要
                # 予算超過 → 強ペナルティ
                # 予算未満 → 弱ペナルティ（安いのは良い）
                budget_max = spec_vector['budget_max']
                budget_min = spec_vector['budget_min']
                price = bto_vec['price']

                if price > budget_max:
                    # 予算超過: 超過額に応じた強ペナルティ
                    over = (price - budget_max) / norm
                    penalty = weight * (over * 2.0) ** 2
                elif price < budget_min:
                    # 予算の大幅下回り: 弱ペナルティ（安すぎるのも怪しい）
                    under = (budget_min - price) / norm
                    penalty = weight * (under * 0.5) ** 2
                else:
                    # 予算範囲内: ペナルティ最小
                    # 予算中央に近いほど良い
                    center = (budget_max + budget_min) / 2
                    penalty = weight * ((price - center) / norm * 0.2) ** 2

                breakdown[dim] = round(penalty, 4)
                distance_sq += penalty
            elif diff >= 0:
                # オーバースペック: 軽いペナルティ
                penalty = weight * (diff * _OVERSHOOT_PENALTY) ** 2
                breakdown[dim] = round(penalty, 4)
                distance_sq += penalty
            else:
                # アンダースペック: 強いペナルティ
                penalty = weight * diff ** 2
                breakdown[dim] = round(-penalty, 4)  # 負値で不足を表現
                distance_sq += penalty

        distance = math.sqrt(distance_sq)

        # マッチスコア（0-1、高いほど良い）
        score = 1.0 / (1.0 + distance * 10)

        # 報酬率バイアス（オプション）
        if commission_bias:
            rate = bto.get('affiliate', {}).get('commission_rate', 0)
            bias = min(rate / 100 * 0.5, 0.05)  # 最大5%ブースト
            score = min(score + bias, 1.0)

        scored.append((bto, round(score, 4), round(distance, 4), breakdown))

    # スコア降順でソート
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# 松竹梅（ゴルディロックス）選出
# ---------------------------------------------------------------------------

def select_goldilocks(scored_products, spec_vector):
    """
    松竹梅の3製品を選出

    - 梅（value）: 予算の85%以下で最高スコア → コスト重視
    - 竹（recommended）: 予算範囲内で最高スコア → おすすめ
    - 松（premium）: 予算の130%以下で最高スコア → 将来性重視

    Returns:
        dict: {'value': {...}, 'recommended': {...}, 'premium': {...}}
        各値は {'product': dict, 'score': float, 'distance': float,
                'breakdown': dict, 'tier_label': str} or None
    """
    budget_min = spec_vector['budget_min']
    budget_max = spec_vector['budget_max']
    budget_mid = (budget_min + budget_max) / 2

    value_candidates = []
    recommended_candidates = []
    premium_candidates = []

    for product, score, distance, breakdown in scored_products:
        price = product.get('price_jpy', 0)

        if price <= budget_mid:
            value_candidates.append((product, score, distance, breakdown))

        if budget_min * 0.8 <= price <= budget_max:
            recommended_candidates.append((product, score, distance, breakdown))

        if budget_max < price <= budget_max * 1.35:
            premium_candidates.append((product, score, distance, breakdown))

    def _best(candidates):
        if not candidates:
            return None
        # スコア最高のものを選択
        best = max(candidates, key=lambda x: x[1])
        return {
            'product': best[0],
            'score': best[1],
            'distance': best[2],
            'breakdown': best[3],
        }

    result = {
        'value': _best(value_candidates),
        'recommended': _best(recommended_candidates),
        'premium': _best(premium_candidates),
    }

    # ラベル付け
    labels = {
        'value': '💰 コスト重視',
        'recommended': '⭐ おすすめ',
        'premium': '🚀 ハイスペック',
    }
    for tier, label in labels.items():
        if result[tier]:
            result[tier]['tier_label'] = label

    # 推奨がない場合は全体ベストをフォールバック
    if result['recommended'] is None and scored_products:
        best = scored_products[0]
        result['recommended'] = {
            'product': best[0],
            'score': best[1],
            'distance': best[2],
            'breakdown': best[3],
            'tier_label': '⭐ おすすめ',
        }

    return result


# ---------------------------------------------------------------------------
# 結果フォーマット
# ---------------------------------------------------------------------------

def format_result(spec_vector, goldilocks):
    """結果を見やすいJSON構造にフォーマット"""
    result = {
        'spec_vector': {
            'gpu_score': spec_vector['gpu_score'],
            'cpu_score': spec_vector['cpu_score'],
            'vram_gb': spec_vector['vram_gb'],
            'ram_gb': spec_vector['ram_gb'],
            'budget_range': f"¥{spec_vector['budget_min']:,} 〜 ¥{spec_vector['budget_max']:,}",
            'use_case': spec_vector['use_case'],
            'resolution': spec_vector['resolution'],
            'fps_target': spec_vector['fps_target'],
            'game_detected': spec_vector.get('game_detected'),
        },
        'recommendations': {},
    }

    for tier in ['value', 'recommended', 'premium']:
        entry = goldilocks.get(tier)
        if entry is None:
            result['recommendations'][tier] = None
            continue

        p = entry['product']
        specs = p.get('specs', {})
        result['recommendations'][tier] = {
            'tier_label': entry['tier_label'],
            'maker': p['maker'],
            'series': p.get('series', ''),
            'model': p.get('model', ''),
            'price': f"¥{p['price_jpy']:,}",
            'price_jpy': p['price_jpy'],
            'match_score': entry['score'],
            'cpu': specs.get('cpu', {}).get('name', ''),
            'gpu': specs.get('gpu', {}).get('name', ''),
            'vram_gb': specs.get('gpu', {}).get('vram_gb', 0),
            'ram_gb': specs.get('ram', {}).get('capacity_gb', 0),
            'storage': ', '.join(
                f"{s['capacity_gb']}GB {s['type']}"
                for s in specs.get('storage', [])
            ),
            'psu': f"{specs.get('psu', {}).get('wattage', 0)}W "
                   f"{specs.get('psu', {}).get('certification', '')}",
            'url': p.get('url', ''),
            'affiliate_url': p.get('affiliate', {}).get('url', '') or p.get('url', ''),
            'commission_rate': p.get('affiliate', {}).get('commission_rate', 0),
            'warranty_years': p.get('warranty_years', 1),
            'tags': p.get('tags', []),
            'score_breakdown': entry['breakdown'],
        }

    return result


# ---------------------------------------------------------------------------
# メインパイプライン
# ---------------------------------------------------------------------------

def run_matching(user_input, budget_yen=None, game_name=None,
                 resolution=None, fps_target=None, quality=None,
                 commission_bias=False):
    """
    フルパイプライン: 自然言語 → スペックベクトル → マッチング → 松竹梅

    Args:
        user_input: 自然言語テキスト
        budget_yen: 予算（明示指定、Noneなら自動抽出）
        その他: 各パラメータの明示指定

    Returns:
        dict: format_result() の出力
    """
    # 1. スペック要件ベクトル生成
    spec = build_spec_vector(
        user_input, budget_yen=budget_yen, game_name=game_name,
        resolution=resolution, fps_target=fps_target, quality=quality,
    )

    # 2. データ読み込み
    products = load_bto_products()
    scores = load_performance_scores()

    # 3. マッチング
    matched = match_bto_products(spec, products, scores,
                                commission_bias=commission_bias)

    # 4. 松竹梅選出
    goldilocks = select_goldilocks(matched, spec)

    # 5. フォーマット
    return format_result(spec, goldilocks)


if __name__ == '__main__':
    # 簡易テスト
    import sys
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = 'モンハンワイルズを4K 60fpsで遊びたい。予算25万'

    result = run_matching(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
