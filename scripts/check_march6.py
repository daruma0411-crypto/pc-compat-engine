import json
from pathlib import Path

history_file = Path(__file__).parent / 'twitter_post_history.json'
with open(history_file, encoding='utf-8') as f:
    data = json.load(f)

print(f'Total posts: {len(data)}')

march6 = [d for d in data if d['posted_at'].startswith('2026-03-06')]
print(f'\nMarch 6 posts: {len(march6)}')
for p in march6:
    print(f"  {p['posted_at']} - {p.get('name', 'unknown')}")

# 3月5-7日の投稿数を比較
for day in ['2026-03-05', '2026-03-06', '2026-03-07']:
    count = len([d for d in data if d['posted_at'].startswith(day)])
    print(f"{day}: {count} posts")
