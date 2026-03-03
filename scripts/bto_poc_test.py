#!/usr/bin/env python3
"""
BTO マッチング PoC 検証スクリプト

5つのテストケースで松竹梅出力の妥当性を検証する。

Usage:
    python scripts/bto_poc_test.py
"""

import json
import os
import sys

# スクリプトの場所からの相対パスでインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bto_matching import (
    build_spec_vector,
    load_bto_products,
    load_performance_scores,
    match_bto_products,
    select_goldilocks,
    format_result,
    run_matching,
)


# ---------------------------------------------------------------------------
# テストケース定義
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        'name': 'TC1: モンハンワイルズ 4K 60fps（ハイエンド）',
        'input': 'モンハンワイルズを4K 60fpsで遊びたい。予算25万',
        'expected': {
            'use_case': 'gaming',
            'gpu_score_min': 60,
            'game_detected': 'モンハンワイルズ',
            'recommended_price_range': (170000, 350000),
            'description': 'GPU性能重視。RTX 5070以上を搭載したBTOが推奨に来るべき。',
        },
    },
    {
        'name': 'TC2: Apex Legends 快適プレイ（ミドル）',
        'input': 'Apex Legendsを快適にプレイしたい。できれば144fps出したい。予算20万',
        'expected': {
            'use_case': 'gaming',
            'gpu_score_min': 40,
            'game_detected': 'apex legends',
            'recommended_price_range': (150000, 280000),
            'description': 'Apexは軽量なので、RTX 5060でも十分。エントリー〜ミドルが推奨。',
        },
    },
    {
        'name': 'TC3: 動画編集+ゲーム両方（クリエイター）',
        'input': 'Premiere Proで4K動画編集しながら、たまにゲームもしたい。予算30万',
        'expected': {
            'use_case': 'creator',
            'gpu_score_min': 50,
            'game_detected': None,
            'recommended_price_range': (200000, 400000),
            'description': 'CPU/RAM重視。Core i7以上、32GB RAM搭載のBTOが推奨。',
        },
    },
    {
        'name': 'TC4: マイクラとネット閲覧（エントリー）',
        'input': 'マイクラとネット閲覧がメイン。あまりお金かけたくない。予算15万',
        'expected': {
            'use_case': 'work',
            'gpu_score_min': 4,
            'game_detected': 'マイクラ',
            'recommended_price_range': (100000, 260000),
            'description': '軽量用途。最も安価なBTOが推奨。価格重みが最大。',
        },
    },
    {
        'name': 'TC5: AI画像生成 Stable Diffusion（VRAM重視）',
        'input': 'Stable DiffusionをローカルでComfyUI使って回したい。予算35万',
        'expected': {
            'use_case': 'ai',
            'gpu_score_min': 50,
            'game_detected': None,
            'recommended_price_range': (250000, 500000),
            'description': 'VRAM重視（16GB以上必須）。RTX 5070 Ti以上、RAM 32GB。',
        },
    },
]


# ---------------------------------------------------------------------------
# テスト実行
# ---------------------------------------------------------------------------

def run_test(test_case, products, scores):
    """単一テストケースを実行"""
    tc = test_case
    expected = tc['expected']

    print(f"\n{'='*80}")
    print(f"📋 {tc['name']}")
    print(f"{'='*80}")
    print(f"入力: 「{tc['input']}」")
    print(f"期待: {expected['description']}")
    print()

    # 1. スペックベクトル生成
    spec = build_spec_vector(tc['input'])
    print(f"--- スペック要件ベクトル ---")
    print(f"  用途判定:    {spec['use_case']}")
    print(f"  GPUスコア:   {spec['gpu_score']}")
    print(f"  CPUスコア:   {spec['cpu_score']}")
    print(f"  VRAM要件:    {spec['vram_gb']}GB")
    print(f"  RAM要件:     {spec['ram_gb']}GB")
    print(f"  予算範囲:    ¥{spec['budget_min']:,} 〜 ¥{spec['budget_max']:,}")
    print(f"  解像度:      {spec['resolution']}")
    print(f"  FPS目標:     {spec['fps_target']}")
    print(f"  画質:        {spec['quality']}")
    print(f"  ゲーム検出:  {spec['game_detected']}")

    # 検証
    errors = []
    if spec['use_case'] != expected['use_case']:
        errors.append(f"用途判定: 期待={expected['use_case']}, 実際={spec['use_case']}")
    if spec['gpu_score'] < expected['gpu_score_min']:
        errors.append(f"GPUスコア不足: 期待>={expected['gpu_score_min']}, "
                      f"実際={spec['gpu_score']}")
    if expected['game_detected'] is not None:
        if spec['game_detected'] is None:
            errors.append(f"ゲーム未検出: 期待={expected['game_detected']}")

    # 2. マッチング
    matched = match_bto_products(spec, products, scores)

    print(f"\n--- マッチング結果（上位5件）---")
    for i, (prod, score, dist, breakdown) in enumerate(matched[:5]):
        specs_s = prod.get('specs', {})
        print(f"  #{i+1} [{score:.4f}] {prod['maker']} {prod.get('series','')} "
              f"{prod.get('model','')}  ¥{prod['price_jpy']:,}")
        print(f"       GPU: {specs_s.get('gpu',{}).get('name','?')} "
              f"({specs_s.get('gpu',{}).get('vram_gb','?')}GB)  "
              f"CPU: {specs_s.get('cpu',{}).get('name','?')}  "
              f"RAM: {specs_s.get('ram',{}).get('capacity_gb','?')}GB")
        print(f"       Breakdown: {breakdown}")

    # 3. 松竹梅選出
    goldilocks = select_goldilocks(matched, spec)

    print(f"\n--- 松竹梅（ゴルディロックス）選出 ---")
    for tier in ['value', 'recommended', 'premium']:
        entry = goldilocks[tier]
        if entry is None:
            print(f"  {tier:>12}: (該当なし)")
            continue

        p = entry['product']
        specs_s = p.get('specs', {})
        print(f"  {entry['tier_label']:>14}: {p['maker']} {p.get('model','')}  "
              f"¥{p['price_jpy']:,}  [score={entry['score']:.4f}]")
        print(f"{'':>16}  GPU: {specs_s.get('gpu',{}).get('name','?')} "
              f"({specs_s.get('gpu',{}).get('vram_gb','?')}GB)  "
              f"CPU: {specs_s.get('cpu',{}).get('name','?')}  "
              f"RAM: {specs_s.get('ram',{}).get('capacity_gb','?')}GB")

    # 推奨の価格チェック
    rec = goldilocks.get('recommended')
    if rec:
        price = rec['product']['price_jpy']
        pmin, pmax = expected['recommended_price_range']
        if not (pmin <= price <= pmax):
            errors.append(f"推奨価格範囲外: 期待=¥{pmin:,}〜¥{pmax:,}, "
                          f"実際=¥{price:,}")

    # 結果判定
    print()
    if errors:
        print(f"  ❌ FAIL ({len(errors)}件の不一致)")
        for err in errors:
            print(f"     - {err}")
        return False
    else:
        print(f"  ✅ PASS")
        return True


def main():
    print("=" * 80)
    print("BTO マッチング PoC 検証")
    print(f"テストケース: {len(TEST_CASES)}件")
    print("=" * 80)

    # データ読み込み
    products = load_bto_products()
    scores = load_performance_scores()
    print(f"\nBTO製品: {len(products)}件")
    print(f"パフォーマンススコア: {len(scores)}件")

    # 全テスト実行
    results = []
    for tc in TEST_CASES:
        passed = run_test(tc, products, scores)
        results.append((tc['name'], passed))

    # サマリー
    print(f"\n{'='*80}")
    print(f"📊 テストサマリー")
    print(f"{'='*80}")
    passed = sum(1 for _, p in results if p)
    total = len(results)
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"  {status}  {name}")
    print(f"\n  結果: {passed}/{total} パス")
    print(f"{'='*80}")

    # フル出力JSON（デバッグ用）
    print(f"\n{'='*80}")
    print(f"📄 フルJSON出力（TC1のサンプル）")
    print(f"{'='*80}")
    result_json = run_matching(TEST_CASES[0]['input'])
    print(json.dumps(result_json, ensure_ascii=False, indent=2))

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
