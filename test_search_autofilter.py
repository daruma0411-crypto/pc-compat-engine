"""
handle_search_parts の自動補完テスト

current_buildの確定済みパーツから互換性フィルタ条件を自動補完し、
AIがパラメータを付け忘れても互換性が担保されることを検証する。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from app import handle_search_parts


# ── テスト用ダミー製品 ──────────────────────────────

DUMMY_PRODUCTS = [
    # MB: AM5
    {'id': 'mb_am5_1', 'name': 'ASUS TUF GAMING B650-PLUS', 'category': 'mb',
     'price_min': 22000, 'specs': {'socket': 'AM5', 'memory_type': 'DDR5', 'form_factor': 'ATX'}},
    {'id': 'mb_am5_2', 'name': 'MSI MAG B650 TOMAHAWK WIFI', 'category': 'mb',
     'price_min': 28000, 'specs': {'socket': 'AM5', 'memory_type': 'DDR5', 'form_factor': 'ATX'}},
    # MB: AM4 (旧世代)
    {'id': 'mb_am4_1', 'name': 'ASUS PRIME B550M-A', 'category': 'mb',
     'price_min': 8490, 'specs': {'socket': 'AM4', 'memory_type': 'DDR4', 'form_factor': 'Micro-ATX'}},
    # MB: LGA1700
    {'id': 'mb_lga1700', 'name': 'ASUS ROG STRIX Z790-F', 'category': 'mb',
     'price_min': 45000, 'specs': {'socket': 'LGA1700', 'memory_type': 'DDR5', 'form_factor': 'ATX'}},

    # RAM: DDR5
    {'id': 'ram_ddr5_1', 'name': 'CORSAIR CMK32GX5M2B5600C36 DDR5', 'category': 'ram',
     'price_min': 12000, 'specs': {'memory_type': 'DDR5', 'capacity_gb': 32}},
    # RAM: DDR4
    {'id': 'ram_ddr4_1', 'name': 'CORSAIR CMK16GX4M2B3200C16 DDR4', 'category': 'ram',
     'price_min': 5000, 'specs': {'memory_type': 'DDR4', 'capacity_gb': 16}},

    # CASE: GPU 400mm対応
    {'id': 'case_big', 'name': 'Fractal Design North XL', 'category': 'case',
     'price_min': 25000, 'specs': {'max_gpu_length_mm': 400, 'form_factor': 'ATX'}},
    # CASE: GPU 280mm対応 (短いGPUのみ)
    {'id': 'case_small', 'name': 'NZXT H5 Flow', 'category': 'case',
     'price_min': 12000, 'specs': {'max_gpu_length_mm': 280, 'form_factor': 'ATX'}},
    # CASE: GPU 350mm対応
    {'id': 'case_mid', 'name': 'Corsair 4000D Airflow', 'category': 'case',
     'price_min': 15000, 'specs': {'max_gpu_length_mm': 350, 'form_factor': 'ATX'}},
]


def _make_session(cpu=None, gpu=None, motherboard=None, **kwargs):
    """テスト用の簡易セッション生成"""
    cb = {
        'cpu': cpu, 'gpu': gpu, 'motherboard': motherboard,
        'ram': None, 'case': None, 'psu': None, 'cooler': None,
    }
    cb.update(kwargs)
    return {'current_build': cb}


# ================================================================
# テスト1: MB検索 - CPUソケット自動補完
# ================================================================

def test_mb_autofilter_am5():
    """CPU=AM5確定済み → MB検索でAM5のみ返る"""
    session = _make_session(cpu={'name': 'AMD Ryzen 5 9600X', 'socket': 'AM5'})
    result = handle_search_parts({'category': 'motherboard'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert 'mb_am5_1' in ids, f"AM5 MB が含まれるべき: {ids}"
    assert 'mb_am5_2' in ids, f"AM5 MB が含まれるべき: {ids}"
    assert 'mb_am4_1' not in ids, f"AM4 MB が除外されるべき: {ids}"
    assert 'mb_lga1700' not in ids, f"LGA1700 MB が除外されるべき: {ids}"
    print("PASS: test_mb_autofilter_am5")


def test_mb_autofilter_lga1700():
    """CPU=LGA1700確定済み → MB検索でLGA1700のみ返る"""
    session = _make_session(cpu={'name': 'Core i7-13700K', 'socket': 'LGA1700'})
    result = handle_search_parts({'category': 'motherboard'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert 'mb_lga1700' in ids, f"LGA1700 MB が含まれるべき: {ids}"
    assert 'mb_am5_1' not in ids, f"AM5 MB が除外されるべき: {ids}"
    assert 'mb_am4_1' not in ids, f"AM4 MB が除外されるべき: {ids}"
    print("PASS: test_mb_autofilter_lga1700")


def test_mb_no_autofilter_without_cpu():
    """CPU未確定 → MB検索で全て返る"""
    session = _make_session()
    result = handle_search_parts({'category': 'motherboard'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert len(ids) == 4, f"全4件返るべき: {ids}"
    print("PASS: test_mb_no_autofilter_without_cpu")


def test_mb_explicit_socket_overrides():
    """AIが明示的にsocket指定 → 自動補完しない"""
    session = _make_session(cpu={'name': 'AMD Ryzen 5 9600X', 'socket': 'AM5'})
    result = handle_search_parts(
        {'category': 'motherboard', 'socket': 'LGA1700'},
        DUMMY_PRODUCTS, session=session
    )
    ids = [r['product_id'] for r in result['results']]
    assert 'mb_lga1700' in ids, f"明示指定LGA1700が返るべき: {ids}"
    assert 'mb_am5_1' not in ids, f"AM5が除外されるべき: {ids}"
    print("PASS: test_mb_explicit_socket_overrides")


# ================================================================
# テスト2: RAM検索 - MBメモリタイプ自動補完
# ================================================================

def test_ram_autofilter_ddr5():
    """MB=DDR5確定済み → RAM検索でDDR5のみ返る"""
    session = _make_session(motherboard={'name': 'ASUS TUF B650', 'memory_type': 'DDR5'})
    result = handle_search_parts({'category': 'ram'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert 'ram_ddr5_1' in ids, f"DDR5 RAM が含まれるべき: {ids}"
    assert 'ram_ddr4_1' not in ids, f"DDR4 RAM が除外されるべき: {ids}"
    print("PASS: test_ram_autofilter_ddr5")


def test_ram_no_autofilter_without_mb():
    """MB未確定 → RAM検索で全て返る"""
    session = _make_session()
    result = handle_search_parts({'category': 'ram'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert len(ids) == 2, f"全2件返るべき: {ids}"
    print("PASS: test_ram_no_autofilter_without_mb")


# ================================================================
# テスト3: CASE検索 - GPU長自動補完
# ================================================================

def test_case_autofilter_gpu_length():
    """GPU=330mm確定済み → 330mm以上収容可のケースのみ返る"""
    session = _make_session(gpu={'name': 'RTX 5070', 'length_mm': 330})
    result = handle_search_parts({'category': 'case'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert 'case_big' in ids, f"400mm対応ケースが含まれるべき: {ids}"
    assert 'case_mid' in ids, f"350mm対応ケースが含まれるべき: {ids}"
    assert 'case_small' not in ids, f"280mm対応ケースは除外されるべき: {ids}"
    print("PASS: test_case_autofilter_gpu_length")


def test_case_no_autofilter_without_gpu():
    """GPU未確定 → CASE検索で全て返る"""
    session = _make_session()
    result = handle_search_parts({'category': 'case'}, DUMMY_PRODUCTS, session=session)

    ids = [r['product_id'] for r in result['results']]
    assert len(ids) == 3, f"全3件返るべき: {ids}"
    print("PASS: test_case_no_autofilter_without_gpu")


def test_case_explicit_min_gpu_overrides():
    """AIが明示的にmin_gpu_length_mm指定 → 自動補完しない"""
    session = _make_session(gpu={'name': 'RTX 5070', 'length_mm': 330})
    # AIが小さいケースを意図的に検索（200mm以上）
    result = handle_search_parts(
        {'category': 'case', 'min_gpu_length_mm': 200},
        DUMMY_PRODUCTS, session=session
    )
    ids = [r['product_id'] for r in result['results']]
    assert len(ids) == 3, f"200mm以上で全3件返るべき: {ids}"
    print("PASS: test_case_explicit_min_gpu_overrides")


# ================================================================
# テスト4: session=None（後方互換）
# ================================================================

def test_no_session():
    """session=None でも動作する（後方互換性）"""
    result = handle_search_parts({'category': 'motherboard'}, DUMMY_PRODUCTS, session=None)
    ids = [r['product_id'] for r in result['results']]
    assert len(ids) == 4, f"session=None で全4件返るべき: {ids}"
    print("PASS: test_no_session")


# ================================================================
# 実行
# ================================================================

if __name__ == '__main__':
    test_mb_autofilter_am5()
    test_mb_autofilter_lga1700()
    test_mb_no_autofilter_without_cpu()
    test_mb_explicit_socket_overrides()
    test_ram_autofilter_ddr5()
    test_ram_no_autofilter_without_mb()
    test_case_autofilter_gpu_length()
    test_case_no_autofilter_without_gpu()
    test_case_explicit_min_gpu_overrides()
    test_no_session()
    print("\n=== ALL 10 TESTS PASSED ===")
