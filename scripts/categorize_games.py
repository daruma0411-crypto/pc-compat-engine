"""
628ゲームを8ジャンルに分類して games_categorized.jsonl を出力。

使い方:
    python scripts/categorize_games.py [--limit N] [--start N]

入力: workspace/data/steam/games.jsonl
出力: workspace/data/steam/games_categorized.jsonl

各ゲームに matched_genres フィールド（list[str]）を追加。
複数ジャンル該当OK。該当なしは空配列。
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(WORKSPACE_DIR / ".env")
INPUT_PATH = WORKSPACE_DIR / "workspace" / "data" / "steam" / "games.jsonl"
OUTPUT_PATH = WORKSPACE_DIR / "workspace" / "data" / "steam" / "games_categorized.jsonl"

BATCH_SIZE = 20  # 1リクエストで何ゲーム分類するか

GENRE_DEFINITIONS = """
PCゲームを以下の8ジャンルに分類してください。複数該当OK。当てはまらない場合は空配列を返してください。

1. **fps** - 一人称シューター。Counter-Strike, Apex, VALORANT, Call of Duty型。「FPS」「シューター」「銃撃」が中心。
2. **mmorpg** - 大規模オンラインRPG。Final Fantasy XIV, World of Warcraft型。多人数同時オンライン+RPG要素。
3. **rpg** - RPG全般（MMORPGとアクションRPGはここに含める。FPS除く）。Elden Ring, Persona, Pokemon型。
4. **simulation** - シミュレーション。Microsoft Flight Simulator, Cities: Skylines, Football Manager, レース系シム等。リアルなシステム再現が中心。
5. **openworld** - オープンワールド。GTA, Elden Ring（複数該当OK）, Red Dead Redemption型。広大なマップを自由探索できる。
6. **fighting** - 格闘ゲーム。Street Fighter, Tekken, Mortal Kombat, スマブラ型。1対1の格闘が中心。
7. **strategy** - ストラテジー（RTS, ターン制, 4Xなど）。Civilization, Total War, StarCraft, Crusader Kings型。
8. **vr** - VRゲーム。Steam上の説明にVR/Oculus/Index等の記載がある、またはVR専用設計のゲーム。

複数該当の例:
- Elden Ring → ["rpg", "openworld"]
- GTA V → ["openworld"] (FPSではないので fps は不要)
- Battlefield 4 → ["fps"]
- Civilization VI → ["strategy"]
- Half-Life: Alyx → ["fps", "vr"]
- Microsoft Flight Simulator → ["simulation"]
"""


class GameGenres(BaseModel):
    appid: int
    matched_genres: List[Literal["fps", "mmorpg", "rpg", "simulation", "openworld", "fighting", "strategy", "vr"]] = Field(
        description="該当するジャンル全て（複数可）。該当なしは空配列。"
    )


class BatchResult(BaseModel):
    classifications: List[GameGenres]


def build_user_prompt(games: List[dict]) -> str:
    """Build a user prompt classifying multiple games."""
    lines = ["以下のゲームをそれぞれ8ジャンルに分類してください。\n"]
    for g in games:
        steam_genres = ", ".join(g.get("genres") or [])
        desc = (g.get("short_description") or "")[:300]
        lines.append(
            f"- appid={g['appid']}, name={g['name']!r}, "
            f"steam_genres=[{steam_genres}], description={desc!r}"
        )
    return "\n".join(lines)


def classify_batch(client: anthropic.Anthropic, games: List[dict]) -> dict:
    """Classify a batch of games. Returns {appid: matched_genres}."""
    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": GENRE_DEFINITIONS,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": build_user_prompt(games)}],
        output_format=BatchResult,
    )
    result = response.parsed_output
    return {c.appid: c.matched_genres for c in result.classifications}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="最初N件のみ処理（テスト用）")
    parser.add_argument("--start", type=int, default=0, help="開始位置")
    parser.add_argument("--dry-run", action="store_true", help="API呼ばず1件目だけ表示")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    games = []
    with INPUT_PATH.open(encoding="utf-8") as f:
        for line in f:
            games.append(json.loads(line))

    if args.start:
        games = games[args.start:]
    if args.limit:
        games = games[: args.limit]

    print(f"処理対象: {len(games)} ゲーム ({BATCH_SIZE}件/バッチ = {(len(games) + BATCH_SIZE - 1) // BATCH_SIZE} バッチ)")

    if args.dry_run:
        print("--- DRY RUN: 1バッチのプロンプト ---")
        print(build_user_prompt(games[:BATCH_SIZE]))
        return

    client = anthropic.Anthropic()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = {}
    total_input = 0
    total_output = 0
    total_cache_read = 0

    for i in range(0, len(games), BATCH_SIZE):
        batch = games[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        try:
            mapping = classify_batch(client, batch)
        except Exception as e:
            print(f"  バッチ {batch_num} 失敗: {e}")
            time.sleep(5)
            try:
                mapping = classify_batch(client, batch)
            except Exception as e2:
                print(f"  バッチ {batch_num} リトライも失敗: {e2}")
                continue

        results.update(mapping)
        # 簡易進捗
        appids = [g["appid"] for g in batch]
        missing = [a for a in appids if a not in mapping]
        sample = next(iter(mapping.items())) if mapping else None
        print(
            f"バッチ {batch_num}/{(len(games) + BATCH_SIZE - 1) // BATCH_SIZE} "
            f"完了 ({len(mapping)}/{len(batch)}) "
            f"missing={len(missing)} sample={sample}"
        )

    # 結果と元データをマージして出力
    by_appid = {g["appid"]: g for g in games}
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for appid, game in by_appid.items():
            game["matched_genres"] = results.get(appid, [])
            f.write(json.dumps(game, ensure_ascii=False) + "\n")

    print(f"\n完了: {OUTPUT_PATH}")
    print(f"分類済み: {len([a for a in by_appid if a in results])} / {len(by_appid)}")

    # ジャンル別件数
    from collections import Counter
    cnt = Counter()
    no_match = 0
    for appid, genres in results.items():
        if not genres:
            no_match += 1
        for g in genres:
            cnt[g] += 1
    print("\n--- ジャンル別件数 ---")
    for g, c in cnt.most_common():
        print(f"  {g}: {c}")
    print(f"  (該当なし): {no_match}")


if __name__ == "__main__":
    main()
