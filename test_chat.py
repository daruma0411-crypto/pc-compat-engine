#!/usr/bin/env python3
import requests
import json

url = "https://pc-jisaku.com/api/chat"
data = {"message": "モンハンワイルズを60fpsで遊びたい、予算20万、WQHD"}

print("送信中...")
response = requests.post(url, json=data, timeout=120, verify=False)

print(f"ステータス: {response.status_code}")
result = response.json()
print(f"レスポンス:")
print(f"message: {result.get('message', '')}")
print(f"recommended_parts: {result.get('recommended_parts', [])}")
print(f"\nフルJSON:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
