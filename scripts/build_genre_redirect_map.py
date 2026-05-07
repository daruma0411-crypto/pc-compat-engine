"""
games_categorized.jsonl から /game/<slug> → /genre/<primary_genre> のマップを生成。

出力: workspace/data/steam/genre_redirect_map.json

primary genre は specificity priority で選ぶ:
  fps > vr > fighting > mmorpg > simulation > strategy > openworld > rpg

該当なしのゲームはマップに含めない（app.py 側でホームへ301）。
"""
import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
INPUT = WORKSPACE / "workspace" / "data" / "steam" / "games_categorized.jsonl"
OUTPUT = WORKSPACE / "workspace" / "data" / "steam" / "genre_redirect_map.json"
GAME_DIR = WORKSPACE / "static" / "game"

GENRE_PRIORITY = ["fps", "vr", "fighting", "mmorpg", "simulation", "strategy", "openworld", "rpg"]


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[\s'\":,!?®™©]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def find_game_slug(name: str) -> str | None:
    """static/game/ にある実ファイル名と一致する slug を返す。"""
    for cand in [
        slugify(name),
        slugify(name.replace(":", "")),
        slugify(name.replace("'", "")),
        slugify(name.replace("®", "").replace("™", "")),
    ]:
        if (GAME_DIR / f"{cand}.html").exists():
            return cand
    return None


def primary_genre(matched: list[str]) -> str | None:
    if not matched:
        return None
    for g in GENRE_PRIORITY:
        if g in matched:
            return g
    return None


def main():
    redirect_map = {}
    no_genre = 0
    no_slug_match = 0
    total = 0

    with INPUT.open(encoding="utf-8") as f:
        for line in f:
            total += 1
            game = json.loads(line)
            matched = game.get("matched_genres") or []

            primary = primary_genre(matched)
            if not primary:
                no_genre += 1
                continue

            slug = find_game_slug(game["name"])
            if not slug:
                no_slug_match += 1
                continue

            redirect_map[slug] = primary

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(redirect_map, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Total games: {total}")
    print(f"Mapped to genre: {len(redirect_map)}")
    print(f"No matched genre (該当なし): {no_genre}")
    print(f"No matching /game/ HTML file: {no_slug_match}")
    print(f"\nOutput: {OUTPUT}")

    # Per-genre count of redirects
    from collections import Counter
    by_g = Counter(redirect_map.values())
    print("\n--- Redirects per genre ---")
    for g in GENRE_PRIORITY:
        print(f"  {g}: {by_g.get(g, 0)}")


if __name__ == "__main__":
    main()
