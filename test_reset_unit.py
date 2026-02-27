"""
修正7 リセット機能のユニットテスト（サーバー不要）
_reset_full() / _reset_partial() / _detect_stagnation() を直接テスト
"""
import os, sys
os.environ.setdefault('ANTHROPIC_API_KEY', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import _reset_full, _reset_partial, _detect_stagnation, get_or_create_session, _BUILD_DEPENDENCY_MAP


def make_session(cpu=None, gpu=None, motherboard=None, ram=None,
                 case=None, psu=None, cooler=None, history_turns=0):
    """テスト用セッションを生成"""
    sid = f"unit_test_{id({})}"
    session = get_or_create_session(sid)
    session['current_build']['cpu']         = cpu
    session['current_build']['gpu']         = gpu
    session['current_build']['motherboard'] = motherboard
    session['current_build']['ram']         = ram
    session['current_build']['case']        = case
    session['current_build']['psu']         = psu
    session['current_build']['cooler']      = cooler
    session['confirmed_parts'] = {
        k.upper(): v['name']
        for k, v in session['current_build'].items()
        if v is not None
    }
    session['stage'] = 'recommending' if any([cpu, gpu, motherboard]) else 'hearing'
    # 履歴を指定ターン数埋める
    for i in range(history_turns * 2):
        role = 'user' if i % 2 == 0 else 'assistant'
        session['history'].append({'role': role, 'content': f'dummy {i}'})
    return session


def test(name, condition, detail=""):
    status = "OK" if condition else "NG"
    print(f"  [{status}] {name}")
    if not condition:
        print(f"       {detail}")
    return condition


results = []

# ────────────────────────────────────────
# テスト1: _reset_full() の基本動作
# ────────────────────────────────────────
print("=== テスト1: _reset_full() ===")
cpu_info = {'name': 'Ryzen 5 7600X', 'socket': 'AM5'}
gpu_info = {'name': 'RTX 5070 Ti', 'length_mm': 320}
s = make_session(cpu=cpu_info, gpu=gpu_info, history_turns=2)
assert s['current_build']['cpu'] is not None
assert len(s['history']) == 4  # 2ターン = 4メッセージ

result = _reset_full(s)

t1a = test("success=True", result.get('success') is True, str(result))
t1b = test("current_build が全て None",
           all(v is None for v in s['current_build'].values()),
           str(s['current_build']))
t1c = test("confirmed_parts が空",
           s['confirmed_parts'] == {}, str(s['confirmed_parts']))
t1d = test("stage が hearing に戻る",
           s['stage'] == 'hearing', s['stage'])
t1e = test("budget_yen が None に戻る",
           s['budget_yen'] is None, str(s['budget_yen']))
t1f = test("history は保持される（4件）",
           len(s['history']) == 4, str(len(s['history'])))
t1g = test("reset_categories が返る",
           bool(result.get('reset_categories')), str(result))
t1h = test("ai_message が返る",
           bool(result.get('ai_message')), str(result.get('ai_message')))
results += [t1a, t1b, t1c, t1d, t1e, t1f, t1g, t1h]

# ────────────────────────────────────────
# テスト2: _reset_partial(cpu) → CPU+MB+RAM+クーラーがリセット
# ────────────────────────────────────────
print("\n=== テスト2: _reset_partial(cpu) → 依存リセット ===")
cpu_info = {'name': 'Ryzen 5 7600X', 'socket': 'AM5'}
mb_info  = {'name': 'ASUS B650-A', 'socket': 'AM5', 'memory_type': 'DDR5'}
ram_info = {'name': 'Kingston DDR5-6000', 'memory_type': 'DDR5'}
gpu_info = {'name': 'RTX 5070 Ti'}
s2 = make_session(cpu=cpu_info, motherboard=mb_info, ram=ram_info, gpu=gpu_info)

# _BUILD_DEPENDENCY_MAP で cpu → [motherboard(socket_reset), ram(socket_reset), cooler(recheck), psu(recheck)]
result2 = _reset_partial(s2, 'cpu')

print(f"  reset_categories: {result2.get('reset_categories')}")
reset_cats = result2.get('reset_categories', [])
t2a = test("success=True", result2.get('success') is True, str(result2))
t2b = test("cpu がリセット対象", 'cpu' in reset_cats, str(reset_cats))
t2c = test("motherboard がリセット対象（socket依存）",
           'motherboard' in reset_cats, str(reset_cats))
t2d = test("ram がリセット対象（socket依存）",
           'ram' in reset_cats, str(reset_cats))
t2e = test("cpu current_build が None",
           s2['current_build']['cpu'] is None, str(s2['current_build']['cpu']))
t2f = test("motherboard current_build が None",
           s2['current_build']['motherboard'] is None)
t2g = test("gpu は影響なし",
           s2['current_build']['gpu'] is not None, str(s2['current_build']['gpu']))
t2h = test("ai_message に複数パーツの案内",
           bool(result2.get('ai_message')), str(result2.get('ai_message')))
results += [t2a, t2b, t2c, t2d, t2e, t2f, t2g, t2h]

# ────────────────────────────────────────
# テスト3: _reset_partial(gpu) → GPUのみ（CPUに依存なし）
# ────────────────────────────────────────
print("\n=== テスト3: _reset_partial(gpu) → GPUのみ ===")
s3 = make_session(cpu=cpu_info, gpu=gpu_info)
result3 = _reset_partial(s3, 'gpu')
reset3 = result3.get('reset_categories', [])

t3a = test("gpu がリセット対象", 'gpu' in reset3, str(reset3))
t3b = test("cpu は影響なし", 'cpu' not in reset3, str(reset3))
t3c = test("motherboard は影響なし", 'motherboard' not in reset3, str(reset3))
t3d = test("gpu current_build が None",
           s3['current_build']['gpu'] is None)
t3e = test("cpu current_build は保持",
           s3['current_build']['cpu'] is not None)
results += [t3a, t3b, t3c, t3d, t3e]

# ────────────────────────────────────────
# テスト4: _reset_partial(motherboard) → MB+RAMがリセット
# ────────────────────────────────────────
print("\n=== テスト4: _reset_partial(motherboard) → MB+RAM ===")
s4 = make_session(cpu=cpu_info, motherboard=mb_info, ram=ram_info)
result4 = _reset_partial(s4, 'motherboard')
reset4 = result4.get('reset_categories', [])

t4a = test("motherboard がリセット対象", 'motherboard' in reset4, str(reset4))
t4b = test("ram がリセット対象（memtype依存）",
           'ram' in reset4, str(reset4))
t4c = test("cpu は影響なし", 'cpu' not in reset4, str(reset4))
results += [t4a, t4b, t4c]

# ────────────────────────────────────────
# テスト5: _reset_partial(mb) → 'mb'エイリアス
# ────────────────────────────────────────
print("\n=== テスト5: _reset_partial('mb') エイリアス ===")
s5 = make_session(cpu=cpu_info, motherboard=mb_info, ram=ram_info)
result5 = _reset_partial(s5, 'mb')  # 'mb' は 'motherboard' に正規化
t5a = test("'mb'が'motherboard'に正規化される",
           result5.get('success') is True, str(result5))
t5b = test("motherboard がリセット対象",
           'motherboard' in result5.get('reset_categories', []),
           str(result5.get('reset_categories')))
results += [t5a, t5b]

# ────────────────────────────────────────
# テスト6: 不正カテゴリ
# ────────────────────────────────────────
print("\n=== テスト6: 不正カテゴリ ===")
s6 = make_session()
result6 = _reset_partial(s6, 'invalid_category')
t6a = test("success=False", result6.get('success') is False, str(result6))
t6b = test("error メッセージ", bool(result6.get('error')), str(result6))
results += [t6a, t6b]

# ────────────────────────────────────────
# テスト7: _detect_stagnation()
# ────────────────────────────────────────
print("\n=== テスト7: _detect_stagnation() ===")
# 4往復、全パーツ未確定 → 迷走なし（5往復未満）
s7a = make_session(history_turns=4)
t7a = test("4往復では迷走検知なし", not _detect_stagnation(s7a), str(len(s7a['history'])))

# 5往復、全パーツ未確定 → 迷走検知
s7b = make_session(history_turns=5)
t7b = test("5往復・全未確定で迷走検知", _detect_stagnation(s7b),
           str({'turns': len(s7b['history'])//2, 'confirmed': 0}))

# 5往復、パーツ半数確定 → 迷走なし
s7c = make_session(cpu=cpu_info, gpu=gpu_info, motherboard=mb_info,
                   ram=ram_info, history_turns=5)
t7c = test("5往復・半数確定では迷走検知なし",
           not _detect_stagnation(s7c),
           str({'confirmed': sum(1 for v in s7c['current_build'].values() if v)}))

results += [t7a, t7b, t7c]

# ────────────────────────────────────────
print(f"\n{'='*50}")
passed = sum(results)
total  = len(results)
print(f"結果: {passed}/{total} PASS {'全テスト通過' if passed == total else '失敗あり'}")
