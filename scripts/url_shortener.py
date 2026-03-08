#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL短縮ラッパー

Bitly無料枠の月間上限に達したため、URL短縮を停止。
TwitterはフルURLを自動でt.co（23文字固定）に変換するため、
ツイート文字数への実質影響なし。
"""


def shorten_url(long_url):
    """
    URLをそのまま返す（Bitly廃止）
    Twitterが自動でt.co短縮するため不要
    """
    return long_url


if __name__ == '__main__':
    test_url = "https://pc-compat-engine-production.up.railway.app/game/elden-ring"
    short = shorten_url(test_url)
    print(f"Original: {test_url}")
    print(f"Result: {short}")
