import requests
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "https://pc-jisaku.com/api/recommend"
payload = {"message": "予算15万円でモンハンワイルズを遊びたい"}

print("=" * 60)
print("生レスポンス確認")
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=30, verify=False)
    print(f"Status: {response.status_code}\n")
    
    # 生JSONをそのまま表示
    print("Raw JSON:")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
