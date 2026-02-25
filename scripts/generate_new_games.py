#!/usr/bin/env python3
"""新作ゲームページのみ生成"""
import sys
sys.path.insert(0, 'C:\\Users\\iwashita.AKGNET\\pc-compat-engine\\scripts')
from generate_game_pages import *

def main_new():
    print("[START] 新作ゲームページ生成")
    
    NEW_GAMES_FILE = WORKSPACE_DIR / "workspace" / "data" / "steam" / "new_games.jsonl"
    
    games = []
    with open(NEW_GAMES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                game = json.loads(line)
                game['slug'] = slugify(game['name'])
                games.append(game)
    
    print(f"[INFO] {len(games)}タイトル読み込み")
    
    generated = 0
    for game in games:
        if not game.get('recommended'):
            continue
        
        try:
            html = generate_page(game)
            output_file = OUTPUT_DIR / f"{game['slug']}.html"
            output_file.write_text(html, encoding='utf-8')
            generated += 1
            print(f"[OK] {game['name']}")
        except Exception as e:
            print(f"[ERROR] {game['name']}: {e}")
    
    print(f"\n[COMPLETE] {generated}ページ生成")

if __name__ == "__main__":
    main_new()
