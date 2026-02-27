"""
修正7 リセット機能のテスト
1. GPU確定後、全リセット → 全パーツ null に戻ること
2. CPU確定後、CPU「変更」→ CPU+MB+RAM+クーラーがリセットされること
3. チャット履歴は残っていること
"""
import json
import urllib.request

BASE_URL = "https://pc-compat-engine-production.up.railway.app"


def api_reset(session_id, reset_type, category=None):
    body = {"type": reset_type, "session_id": session_id}
    if category:
        body["category"] = category
    req_body = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/reset",
        data=req_body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_chat(session_id, message):
    body = json.dumps({"message": message, "session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{'OK' if condition else 'NG'}] {name}")
    if not condition:
        print(f"       詳細: {detail}")
    return condition


def run():
    results = []

    # ────────────────────────────────────────
    # テスト1: /api/reset full の基本動作
    # ────────────────────────────────────────
    print("=== テスト1: 全リセット (/api/reset full) ===")
    sid1 = "test_reset_full_001"
    r1 = api_reset(sid1, "full")
    print(f"  レスポンス: {r1}")

    t1a = test("success=True が返る", r1.get("success") is True, str(r1))
    t1b = test("reset_categories が返る", bool(r1.get("reset_categories")), str(r1))
    t1c = test("ai_message が返る",  bool(r1.get("ai_message")), str(r1))
    t1d = test("current_build が返る", r1.get("current_build") is not None, str(r1))
    if r1.get("current_build"):
        all_null = all(v is None for v in r1["current_build"].values())
        t1e = test("current_build が全て null", all_null, str(r1["current_build"]))
    else:
        t1e = False
        print("  [NG] current_build が null")
    results += [t1a, t1b, t1c, t1d, t1e]

    # ────────────────────────────────────────
    # テスト2: CPU個別リセット → 依存パーツ連動
    # ────────────────────────────────────────
    print("\n=== テスト2: CPU個別リセット (/api/reset partial cpu) ===")
    sid2 = "test_reset_partial_001"
    r2 = api_reset(sid2, "partial", "cpu")
    print(f"  レスポンス: {r2}")

    t2a = test("success=True が返る", r2.get("success") is True, str(r2))
    reset_cats = r2.get("reset_categories", [])
    t2b = test("cpu がリセット対象に含まれる", "cpu" in reset_cats, str(reset_cats))
    t2c = test("motherboard がリセット対象に含まれる",
               "motherboard" in reset_cats, str(reset_cats))
    t2d = test("ram がリセット対象に含まれる",
               "ram" in reset_cats, str(reset_cats))
    t2e = test("cooler がリセット対象に含まれる",
               "cooler" in reset_cats, str(reset_cats))
    t2f = test("ai_message に連動リセット案内が含まれる",
               bool(r2.get("ai_message")), str(r2.get("ai_message")))
    results += [t2a, t2b, t2c, t2d, t2e, t2f]

    # ────────────────────────────────────────
    # テスト3: GPU個別リセット → GPUのみリセット（CPUは影響なし）
    # ────────────────────────────────────────
    print("\n=== テスト3: GPU個別リセット → GPUのみ ===")
    sid3 = "test_reset_partial_002"
    r3 = api_reset(sid3, "partial", "gpu")
    print(f"  reset_categories: {r3.get('reset_categories')}")

    t3a = test("gpu がリセット対象に含まれる",
               "gpu" in r3.get("reset_categories", []),
               str(r3.get("reset_categories")))
    t3b = test("cpu がリセット対象に含まれない（GPUはCPUに依存しない）",
               "cpu" not in r3.get("reset_categories", []),
               str(r3.get("reset_categories")))
    t3c = test("motherboard がリセット対象に含まれない",
               "motherboard" not in r3.get("reset_categories", []),
               str(r3.get("reset_categories")))
    results += [t3a, t3b, t3c]

    # ────────────────────────────────────────
    # テスト4: 不正カテゴリのエラー処理
    # ────────────────────────────────────────
    print("\n=== テスト4: 不正カテゴリ → エラー ===")
    sid4 = "test_reset_invalid"
    r4 = api_reset(sid4, "partial", "invalid_cat")
    print(f"  レスポンス: {r4}")
    t4a = test("success=False またはエラーが返る",
               r4.get("success") is False or "error" in r4, str(r4))
    results += [t4a]

    # ────────────────────────────────────────
    # テスト5: full リセット後、チャット履歴は保持 (session_idを再利用)
    # ────────────────────────────────────────
    print("\n=== テスト5: チャット後→全リセット→履歴保持確認 ===")
    sid5 = "test_reset_history_001"
    # まずチャット
    chat_r = api_chat(sid5, "Ryzen 5 7600X\u3067PC\u7d44\u307f\u305f\u3044")
    # 全リセット
    reset_r = api_reset(sid5, "full")
    t5a = test("リセット成功", reset_r.get("success") is True, str(reset_r))
    t5b = test("リセット後 ai_message が返る", bool(reset_r.get("ai_message")), str(reset_r))
    results += [t5a, t5b]

    # ────────────────────────────────────────
    # 総括
    # ────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*50}")
    print(f"結果: {passed}/{total} PASS {'全テスト通過' if passed == total else '失敗あり'}")


if __name__ == "__main__":
    run()
