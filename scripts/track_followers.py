#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""フォロワー追跡 - 増減を記録"""
import os, sys, json, urllib.parse
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

import urllib3, requests
urllib3.disable_warnings()
_old = requests.Session.request
def _p(self, *a, **kw):
    kw['verify'] = False
    return _old(self, *a, **kw)
requests.Session.request = _p

HISTORY_FILE = Path(__file__).parent / 'followers_history.json'

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'snapshots': []}

def save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    import tweepy
    bearer = urllib.parse.unquote(os.environ.get('TWITTER_BEARER_TOKEN', ''))
    client = tweepy.Client(bearer_token=bearer)
    
    me = client.get_user(username='syoyutarou')
    followers = client.get_users_followers(
        me.data.id, max_results=100,
        user_fields=['username', 'name', 'public_metrics']
    )
    
    current = {}
    for u in (followers.data or []):
        fc = u.public_metrics.get('followers_count', 0) if u.public_metrics else 0
        current[u.username] = {'name': u.name, 'followers': fc}
    
    history = load_history()
    prev_usernames = set()
    if history['snapshots']:
        prev_usernames = set(history['snapshots'][-1].get('usernames', {}).keys())
    
    current_usernames = set(current.keys())
    new = current_usernames - prev_usernames
    lost = prev_usernames - current_usernames
    
    print(f"📊 フォロワー: {len(current)}人")
    
    if new:
        print(f"\n🆕 新規フォロワー ({len(new)}人):")
        for u in new:
            info = current[u]
            print(f"  @{u} ({info['followers']}人) {info['name']}")
    
    if lost:
        print(f"\n❌ フォロー解除 ({len(lost)}人):")
        for u in lost:
            print(f"  @{u}")
    
    if not new and not lost and prev_usernames:
        print("  変動なし")
    
    history['snapshots'].append({
        'date': datetime.now().isoformat(),
        'count': len(current),
        'usernames': current,
    })
    history['snapshots'] = history['snapshots'][-30:]
    save_history(history)

if __name__ == '__main__':
    main()
