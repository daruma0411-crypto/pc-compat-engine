# Twitter Bot 404エラー緊急修正

## 問題
- 現在のURLが長すぎてTwitterで途切れる
- `/game/ペルソナ５-ザ・ロイヤル` のような日本語URLがエンコードされて超長くなる
- 結果的にリンクが壊れて404エラー

## 修正内容

### 1. app.py に短縮URLルートを追加

```python
@app.route('/g/<int:steam_appid>')
def short_game_link(steam_appid):
    """ゲームID→詳細ページへのリダイレクト（短縮URL用）"""
    import json
    from pathlib import Path
    
    # games.jsonl からゲームを検索
    games_file = Path(__file__).parent / 'workspace' / 'data' / 'steam' / 'games.jsonl'
    
    with open(games_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                game = json.loads(line)
                appid = game.get('steam_appid') or game.get('appid')
                if appid == steam_appid:
                    # game_slug 関数で正しいスラッグを生成
                    slug = game_slug(game['name'])
                    return redirect(f'/game/{slug}')
    
    abort(404)

def game_slug(name):
    """ゲーム名からURLスラッグを生成"""
    slug = name.lower()
    slug = slug.replace(' ', '-').replace(':', '').replace('/', '-')
    slug = slug.replace('[', '').replace(']', '').replace('/', '')
    slug = slug.replace('\'', '').replace('"', '').replace(',', '')
    slug = slug.replace('--', '-').replace('--', '-')
    return slug.strip('-')
```

### 2. twitter_bot.py を修正

変更箇所（generate_tweet_patterns 関数内）：

```python
# 変更前
full_url = f"{SITE_URL}/game/{slug}"
short_url = shorten_url(full_url)

# 変更後
steam_appid = game.get('steam_appid') or game.get('appid')
full_url = f"{SITE_URL}/g/{steam_appid}"
short_url = shorten_url(full_url)
```

### 3. テスト実行

```bash
python scripts/twitter_bot.py --dry-run
```

生成されるURLが `/g/数字` 形式になっているか確認してください。

### 4. 動作確認後

```bash
git add app.py scripts/twitter_bot.py
git commit -m "fix: Twitter Bot 404エラー修正 - 短縮URL形式に変更 (/g/<appid>)"
git push origin main
```

## 重要情報
- games.jsonl の場所: `workspace/data/steam/games.jsonl`
- 各ゲームには `steam_appid` または `appid` フィールドがある
- 例: ペルソナ5 ザ・ロイヤル → `/g/1245620` (短い！)
