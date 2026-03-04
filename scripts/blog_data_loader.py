#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事用データローダー
JSONL から実データを読み込み、テンプレート別の要約テキストを生成する。
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

DATA_ROOT = Path(__file__).parent.parent / "workspace" / "data"

# --- キャッシュ（セッション中1回だけ読み込む） ---
_cache = {}


def _load_jsonl(path):
    """JONLファイルを読み込みリストで返す"""
    items = []
    if not os.path.exists(path):
        return items
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# =========================================
# 個別データローダー
# =========================================

def load_gpu_prices():
    """GPU価格をチップ名で集約して返す"""
    if 'gpu_prices' in _cache:
        return _cache['gpu_prices']

    items = _load_jsonl(DATA_ROOT / "kakaku_gpu" / "products.jsonl")
    chips = defaultdict(list)
    for item in items:
        chip = item.get('specs', {}).get('gpu_chip', '')
        price = item.get('price_min')
        if chip and price and price > 0:
            # チップ名を正規化（例: "NVIDIAGeForce RTX 4060" → "RTX 4060"）
            chip_short = re.sub(r'(?:NVIDIA|AMD|GeForce|Radeon)\s*', '', chip).strip()
            chips[chip_short].append({
                'name': item['name'],
                'price': price,
                'vram_gb': item.get('specs', {}).get('vram_gb'),
                'tdp_w': item.get('specs', {}).get('tdp_w'),
            })

    # 各チップの最安値でソート
    result = {}
    for chip, products in chips.items():
        products.sort(key=lambda x: x['price'])
        result[chip] = {
            'min_price': products[0]['price'],
            'max_price': products[-1]['price'],
            'count': len(products),
            'cheapest': products[0]['name'],
            'vram_gb': products[0].get('vram_gb'),
            'tdp_w': products[0].get('tdp_w'),
        }

    _cache['gpu_prices'] = result
    return result


def load_cpu_prices():
    """CPU価格を返す"""
    if 'cpu_prices' in _cache:
        return _cache['cpu_prices']

    items = _load_jsonl(DATA_ROOT / "kakaku_cpu" / "products.jsonl")
    result = []
    for item in items:
        price = item.get('price_min')
        if price and price > 0:
            result.append({
                'name': item['name'],
                'price': price,
                'cores': item.get('specs', {}).get('cores'),
                'threads': item.get('specs', {}).get('threads'),
                'socket': item.get('specs', {}).get('socket'),
                'tdp_w': item.get('specs', {}).get('tdp_w'),
            })
    result.sort(key=lambda x: x['price'])

    _cache['cpu_prices'] = result
    return result


def load_ram_prices():
    """RAMを容量・タイプ別の最安値で集約"""
    if 'ram_prices' in _cache:
        return _cache['ram_prices']

    items = _load_jsonl(DATA_ROOT / "kakaku_ram" / "products.jsonl")
    groups = defaultdict(list)
    for item in items:
        price = item.get('price_min')
        mem_type = item.get('specs', {}).get('memory_type', '')
        capacity = item.get('specs', {}).get('capacity_gb')
        if price and price > 0 and mem_type and capacity:
            key = f"{mem_type} {capacity}GB"
            groups[key].append(price)

    result = {}
    for key, prices in groups.items():
        prices.sort()
        result[key] = {'min_price': prices[0], 'count': len(prices)}

    _cache['ram_prices'] = result
    return result


def load_category_min_prices():
    """MB/PSU/Case/Coolerの最安値サマリー"""
    if 'category_mins' in _cache:
        return _cache['category_mins']

    result = {}
    for cat_name, subdir in [('マザーボード', 'kakaku_mb'), ('電源', 'kakaku_psu'),
                              ('ケース', 'kakaku_case'), ('CPUクーラー', 'kakaku_cooler')]:
        items = _load_jsonl(DATA_ROOT / subdir / "products.jsonl")
        prices = [i['price_min'] for i in items if i.get('price_min') and i['price_min'] > 0]
        if prices:
            prices.sort()
            result[cat_name] = {
                'min_price': prices[0],
                'median_price': prices[len(prices) // 2],
                'count': len(prices),
            }

    _cache['category_mins'] = result
    return result


def load_game_specs(game_name):
    """特定ゲームのスペック情報を返す"""
    if 'all_games' not in _cache:
        _cache['all_games'] = _load_jsonl(DATA_ROOT / "steam" / "games.jsonl")

    name_lower = game_name.lower()
    for g in _cache['all_games']:
        if g.get('name', '').lower() == name_lower:
            return g
    # 部分一致
    for g in _cache['all_games']:
        if name_lower in g.get('name', '').lower():
            return g
    return None


def load_performance_scores():
    """GPU/CPU性能スコアを返す"""
    if 'perf_scores' in _cache:
        return _cache['perf_scores']

    items = _load_jsonl(DATA_ROOT / "performance_scores.jsonl")
    gpus = [i for i in items if i.get('type') == 'gpu']
    cpus = [i for i in items if i.get('type') == 'cpu']
    gpus.sort(key=lambda x: x.get('score', 0), reverse=True)
    cpus.sort(key=lambda x: x.get('score', 0), reverse=True)

    _cache['perf_scores'] = {'gpu': gpus, 'cpu': cpus}
    return _cache['perf_scores']


def load_weekly_diff():
    """直近の週次価格差分ログを読み込む"""
    if 'weekly_diff' in _cache:
        return _cache['weekly_diff']

    diff_dir = DATA_ROOT / "diff_logs"
    if not diff_dir.exists():
        _cache['weekly_diff'] = None
        return None

    # 最新のdiffファイルを探す
    diff_files = sorted(diff_dir.glob("*.jsonl"), reverse=True)
    if not diff_files:
        _cache['weekly_diff'] = None
        return None

    items = _load_jsonl(diff_files[0])
    diff_date = diff_files[0].stem  # e.g. "2026-03-02"

    result = {
        'date': diff_date,
        'price_changed': [i for i in items if i.get('type') == 'price_changed'],
        'new': [i for i in items if i.get('type') == 'new'],
        'delisted': [i for i in items if i.get('type') == 'delisted'],
    }

    _cache['weekly_diff'] = result
    return result


# =========================================
# テンプレート別データコンテキスト生成
# =========================================

def _format_price(price):
    """価格をカンマ区切りで表示"""
    return f"{price:,}円"


def _gpu_price_summary(chips_to_show=None):
    """GPU価格サマリーテキスト"""
    gpu = load_gpu_prices()
    lines = []
    if chips_to_show:
        for chip in chips_to_show:
            for key, data in gpu.items():
                if chip.lower() in key.lower():
                    lines.append(f"- {key}: 最安{_format_price(data['min_price'])}（VRAM {data['vram_gb']}GB, {data['count']}製品）")
                    break
    else:
        # 主要チップを表示
        major = ['RTX 5090', 'RTX 5080', 'RTX 5070 Ti', 'RTX 5070', 'RTX 5060',
                 'RTX 4090', 'RTX 4080', 'RTX 4070 Ti', 'RTX 4070', 'RTX 4060 Ti', 'RTX 4060',
                 'RTX 3060', 'RX 9070 XT', 'RX 9070', 'RX 7800 XT', 'RX 7600']
        for chip in major:
            for key, data in gpu.items():
                if chip.lower() in key.lower():
                    lines.append(f"- {key}: 最安{_format_price(data['min_price'])}")
                    break
    return '\n'.join(lines)


def _game_spec_text(game_name):
    """ゲームスペック情報のテキスト"""
    game = load_game_specs(game_name)
    if not game:
        return f"※ {game_name}のスペック情報はデータベースにありません。一般的な情報で記述してください。"

    specs = game.get('specs', {})
    rec = specs.get('recommended', {})
    min_s = specs.get('minimum', {})
    lines = [f"■ {game['name']} 公式スペック（Steam掲載）"]

    if min_s:
        lines.append("【最低】")
        if min_s.get('gpu'):
            lines.append(f"  GPU: {', '.join(min_s['gpu'][:2])}")
        if min_s.get('cpu'):
            lines.append(f"  CPU: {', '.join(min_s['cpu'][:2])}")
        if min_s.get('ram_gb'):
            lines.append(f"  RAM: {min_s['ram_gb']}GB")
        if min_s.get('storage_gb'):
            lines.append(f"  ストレージ: {min_s['storage_gb']}GB")

    if rec:
        lines.append("【推奨】")
        if rec.get('gpu'):
            lines.append(f"  GPU: {', '.join(rec['gpu'][:2])}")
        if rec.get('cpu'):
            lines.append(f"  CPU: {', '.join(rec['cpu'][:2])}")
        if rec.get('ram_gb'):
            lines.append(f"  RAM: {rec['ram_gb']}GB")
        if rec.get('storage_gb'):
            lines.append(f"  ストレージ: {rec['storage_gb']}GB")

    if game.get('metacritic_score'):
        lines.append(f"Metacritic: {game['metacritic_score']}")

    return '\n'.join(lines)


def _perf_score_table():
    """性能スコア表テキスト"""
    scores = load_performance_scores()
    lines = ["■ GPU性能スコア（100点満点）"]
    for g in scores['gpu'][:12]:
        lines.append(f"  {g['name']}: {g['score']}点 (VRAM {g.get('vram_gb', '?')}GB)")
    return '\n'.join(lines)


def _budget_build_data(budget_man):
    """予算別構成向けデータ"""
    budget_yen = int(budget_man) * 10000
    gpu = load_gpu_prices()
    cpu = load_cpu_prices()
    ram = load_ram_prices()
    cats = load_category_min_prices()

    lines = [f"■ 予算{budget_man}万円向け 実際の市場価格"]

    # GPU: 予算の40%以内で買えるGPU
    gpu_budget = budget_yen * 0.4
    lines.append(f"\n【GPU（予算目安: {_format_price(int(gpu_budget))}以内）】")
    gpu_candidates = [(k, v) for k, v in gpu.items() if v['min_price'] <= gpu_budget]
    gpu_candidates.sort(key=lambda x: x[1]['min_price'], reverse=True)
    for chip, data in gpu_candidates[:5]:
        lines.append(f"  {chip}: {_format_price(data['min_price'])}〜 (VRAM {data['vram_gb']}GB)")

    # CPU: 予算の15%以内
    cpu_budget = budget_yen * 0.15
    lines.append(f"\n【CPU（予算目安: {_format_price(int(cpu_budget))}以内）】")
    cpu_candidates = [c for c in cpu if c['price'] <= cpu_budget]
    cpu_candidates.sort(key=lambda x: x['price'], reverse=True)
    for c in cpu_candidates[:5]:
        cores_info = f" ({c['cores']}コア)" if c.get('cores') else ""
        lines.append(f"  {c['name']}: {_format_price(c['price'])}{cores_info}")

    # RAM
    lines.append("\n【メモリ最安値】")
    for key in ['DDR5 SDRAM 32GB', 'DDR5 SDRAM 16GB', 'DDR4 SDRAM 32GB', 'DDR4 SDRAM 16GB']:
        if key in ram:
            lines.append(f"  {key}: {_format_price(ram[key]['min_price'])}〜 ({ram[key]['count']}製品)")

    # その他
    lines.append("\n【その他パーツ中央値】")
    for cat_name, data in cats.items():
        lines.append(f"  {cat_name}: 中央値{_format_price(data['median_price'])}（最安{_format_price(data['min_price'])}）")

    return '\n'.join(lines)


def _weekly_diff_text():
    """週次差分のテキスト"""
    diff = load_weekly_diff()
    if not diff:
        return "※ 今週の価格差分データはありません。"

    lines = [f"■ 今週の価格変動（{diff['date']}更新）"]

    # 値下げTOP
    price_down = [p for p in diff['price_changed']
                  if p.get('old_price') and p.get('new_price') and p['new_price'] < p['old_price']]
    price_down.sort(key=lambda x: x['old_price'] - x['new_price'], reverse=True)

    if price_down:
        lines.append("\n【値下げ注目】")
        for p in price_down[:10]:
            diff_yen = p['old_price'] - p['new_price']
            cat = p.get('category', '')
            lines.append(f"  [{cat}] {p['name'][:40]}: {_format_price(p['old_price'])}→{_format_price(p['new_price'])}（-{_format_price(diff_yen)}）")

    # 値上げ
    price_up = [p for p in diff['price_changed']
                if p.get('old_price') and p.get('new_price') and p['new_price'] > p['old_price']]
    if price_up:
        lines.append(f"\n【値上げ】 {len(price_up)}件")
        for p in price_up[:5]:
            diff_yen = p['new_price'] - p['old_price']
            lines.append(f"  [{p.get('category', '')}] {p['name'][:40]}: +{_format_price(diff_yen)}")

    # 新登場
    if diff['new']:
        lines.append(f"\n【新登場】 {len(diff['new'])}件")
        for p in diff['new'][:5]:
            lines.append(f"  [{p.get('category', '')}] {p.get('name', '')[:40]}: {_format_price(p.get('price_min', 0))}")

    # 廃盤
    if diff['delisted']:
        lines.append(f"\n【廃盤・取扱終了】 {len(diff['delisted'])}件")

    return '\n'.join(lines)


def _weekly_report_data():
    """週刊レポート用の全データ"""
    lines = []

    # 1. 差分データ
    lines.append(_weekly_diff_text())

    # 2. GPU最安値表
    lines.append("\n" + _gpu_price_summary())

    # 3. CPU売れ筋
    cpu = load_cpu_prices()
    lines.append("\n■ CPU価格（安い順TOP10）")
    for c in cpu[:10]:
        cores_info = f" ({c['cores']}C/{c['threads']}T)" if c.get('cores') else ""
        lines.append(f"  {c['name']}: {_format_price(c['price'])}{cores_info}")

    # 4. メモリ
    ram = load_ram_prices()
    lines.append("\n■ メモリ最安値")
    for key in sorted(ram.keys()):
        if 'DDR5' in key or 'DDR4' in key:
            lines.append(f"  {key}: {_format_price(ram[key]['min_price'])}")

    return '\n'.join(lines)


# =========================================
# メイン API
# =========================================

def get_data_context(template_id, variables):
    """テンプレートIDに応じた実データコンテキストを返す"""

    if template_id == 'budget_build':
        return _budget_build_data(variables.get('budget', '15'))

    elif template_id == 'benchmark':
        game_text = _game_spec_text(variables.get('game', ''))
        perf_text = _perf_score_table()
        return f"{game_text}\n\n{perf_text}"

    elif template_id == 'gpu_list':
        gpu_model = variables.get('gpu_model', '4060')
        chip_name = f"RTX {gpu_model}"
        gpu_text = _gpu_price_summary([chip_name])
        perf = load_performance_scores()
        score_line = ""
        for g in perf['gpu']:
            if gpu_model in g['name']:
                score_line = f"\n{g['name']}: 性能スコア {g['score']}/100"
                break
        return f"■ {chip_name} 市場情報\n{gpu_text}{score_line}"

    elif template_id == 'high_res':
        game_text = _game_spec_text(variables.get('game', ''))
        # ハイエンドGPUの価格
        high_chips = ['RTX 5090', 'RTX 5080', 'RTX 5070 Ti', 'RTX 5070', 'RTX 4080', 'RTX 4070 Ti']
        gpu_text = _gpu_price_summary(high_chips)
        perf_text = _perf_score_table()
        return f"{game_text}\n\n■ ハイエンドGPU価格\n{gpu_text}\n\n{perf_text}"

    elif template_id in ('troubleshooting', 'laptop'):
        return _game_spec_text(variables.get('game', ''))

    elif template_id == 'performance':
        game_text = _game_spec_text(variables.get('game', ''))
        perf_text = _perf_score_table()
        return f"{game_text}\n\n{perf_text}"

    elif template_id == 'used_parts':
        game_text = _game_spec_text(variables.get('game', ''))
        # 旧世代GPU
        old_chips = ['RTX 3060', 'RTX 3070', 'RTX 3080', 'GTX 1660', 'RX 6600']
        gpu_text = _gpu_price_summary(old_chips)
        return f"{game_text}\n\n■ 中古市場で人気の旧世代GPU（新品最安）\n{gpu_text}"

    elif template_id == 'mod':
        game_text = _game_spec_text(variables.get('game', ''))
        # VRAM別GPU一覧
        gpu = load_gpu_prices()
        vram_lines = ["■ VRAM別GPU最安値"]
        for vram in [8, 12, 16, 24]:
            candidates = [(k, v) for k, v in gpu.items() if v.get('vram_gb') == vram]
            if candidates:
                candidates.sort(key=lambda x: x[1]['min_price'])
                chip, data = candidates[0]
                vram_lines.append(f"  VRAM {vram}GB: {chip} {_format_price(data['min_price'])}〜")
        return f"{game_text}\n\n" + '\n'.join(vram_lines)

    elif template_id == 'ranking':
        # 全ゲームの推奨GPUで「重い順」ソート
        if 'all_games' not in _cache:
            _cache['all_games'] = _load_jsonl(DATA_ROOT / "steam" / "games.jsonl")
        games = _cache['all_games']
        scored = []
        for g in games:
            rec = g.get('specs', {}).get('recommended', {})
            if rec.get('gpu'):
                gpu_name = rec['gpu'][0] if isinstance(rec['gpu'], list) else str(rec['gpu'])
                scored.append((g['name'], gpu_name, rec.get('ram_gb', '?')))
        lines = ["■ ゲーム推奨GPU一覧（データベースより）"]
        for name, gpu_name, ram in scored[:25]:
            lines.append(f"  {name}: GPU={gpu_name}, RAM={ram}GB")
        return '\n'.join(lines)

    elif template_id == 'weekly_report':
        return _weekly_report_data()

    return ""


def get_source_note():
    """出典表記テキストを返す"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    return f"価格.com調べ・{date_str}時点"
