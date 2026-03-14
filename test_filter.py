"""
修正1 互換フィルタのテスト
「Ryzen 5 7600X」を指定してAM5マザーボードのみが提案されることを確認
"""
import json
import urllib.request
import urllib.parse

BASE_URL = "https://pc-jisaku.com"
SESSION_ID = "test_filter_am5_001"


def chat(message):
    body = json.dumps({"message": message, "session_id": SESSION_ID}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_test():
    results = []

    # ターン1: CPU指定 + 予算 + 解像度 + 画質 → 提案フェーズへ移行させる
    print("=== ターン1: 全情報を一度に投入 ===")
    r1 = chat(
        "Ryzen 5 7600XでPC組みたい。"
        "予算20万円。"
        "モンハンワイルズを4Kで高画質60fpsでやりたい。"
        "4Kモニターはすでに持っています。"
    )
    print(f"AIメッセージ: {r1.get('message','')[:200]}")
    parts1 = r1.get("recommended_parts", [])
    print(f"推奨パーツ({len(parts1)}件): {[p.get('name') for p in parts1]}")
    print(f"current_build: {r1.get('current_build', {})}")
    results.append(("ターン1", parts1))
    print()

    # ターン2: MB明示依頼
    print("=== ターン2: マザーボードを提案してもらう ===")
    r2 = chat("マザーボードを提案してください。")
    print(f"AIメッセージ: {r2.get('message','')[:200]}")
    parts2 = r2.get("recommended_parts", [])
    print(f"推奨パーツ({len(parts2)}件): {[p.get('name') for p in parts2]}")
    print(f"current_build: {r2.get('current_build', {})}")
    results.append(("ターン2", parts2))
    print()

    # ターン3: さらに詳細を押す
    print("=== ターン3: 具体的なマザーボード提案を要求 ===")
    r3 = chat("AM5のマザーボードをいくつか具体的に挙げてください。")
    print(f"AIメッセージ: {r3.get('message','')[:200]}")
    parts3 = r3.get("recommended_parts", [])
    print(f"推奨パーツ({len(parts3)}件): {[p.get('name') for p in parts3]}")
    results.append(("ターン3", parts3))
    print()

    # 判定: 推奨されたMBがすべてAM5か確認
    print("=" * 60)
    print("=== テスト判定 ===")
    all_mb_parts = []
    for turn_name, parts in results:
        for p in parts:
            if p.get("category", "").upper() in ("MOTHERBOARD", "MB", "マザーボード"):
                all_mb_parts.append((turn_name, p.get("name", "")))

    if not all_mb_parts:
        print("⚠️  MBの推奨パーツなし（まだヒアリング段階か提案なし）")
    else:
        print(f"推奨MB合計: {len(all_mb_parts)}件")
        for turn, name in all_mb_parts:
            # AM5ソケット判定: 名前にAM5があるかチェック（簡易）
            is_am5 = "AM5" in name.upper() or "B650" in name.upper() or \
                     "X670" in name.upper() or "B840" in name.upper() or \
                     "X870" in name.upper() or "B850" in name.upper()
            status = "✅ AM5" if is_am5 else "❌ 非AM5または不明"
            print(f"  {status}: [{turn}] {name}")

    # hallucinated_partsの警告もチェック
    for r, name in [("ターン1", r1), ("ターン2", r2), ("ターン3", r3)]:
        if "データベースに登録がない" in r.get("message", ""):
            print(f"⚠️  [{name}] ハルシネーション警告が表示された")


if __name__ == "__main__":
    run_test()
