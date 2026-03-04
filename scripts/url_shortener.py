#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL短縮サービス（Bitly API）
キャッシュ機能付き - 同じURLは再度APIを叩かない
"""

import os
import requests
import json
from pathlib import Path

BITLY_API_TOKEN = os.getenv('BITLY_API_TOKEN')
CACHE_FILE = Path(__file__).parent / 'url_shortener_cache.json'


def load_cache():
    """キャッシュ読み込み"""
    if not CACHE_FILE.exists():
        return {}
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_cache(cache):
    """キャッシュ保存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def shorten_url(long_url):
    """
    URLを短縮（Bitly API）
    キャッシュヒット時はAPIを叩かない
    BITLY_API_TOKEN未設定時は元URLを返す
    """
    cache = load_cache()

    # キャッシュヒット
    if long_url in cache:
        return cache[long_url]

    # Bitly API呼び出し
    if not BITLY_API_TOKEN:
        print("[WARN] BITLY_API_TOKEN not set, using long URL")
        return long_url

    headers = {
        'Authorization': f'Bearer {BITLY_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    data = {
        'long_url': long_url,
        'domain': 'bit.ly'
    }

    try:
        response = requests.post(
            'https://api-ssl.bitly.com/v4/shorten',
            headers=headers,
            json=data,
            timeout=10
        )

        if response.status_code in (200, 201):
            short_url = response.json()['link']
            cache[long_url] = short_url
            save_cache(cache)
            print(f"[OK] URL shortened: {long_url} -> {short_url}")
            return short_url
        else:
            print(f"[WARN] Bitly API error: {response.status_code} {response.text}")
            return long_url

    except Exception as e:
        print(f"[WARN] URL shortening failed: {e}")
        return long_url


if __name__ == '__main__':
    test_url = "https://pc-compat-engine-production.up.railway.app/game/elden-ring"
    short = shorten_url(test_url)
    print(f"Original: {test_url}")
    print(f"Shortened: {short}")
