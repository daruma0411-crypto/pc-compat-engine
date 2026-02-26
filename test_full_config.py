import requests
import json
import sys
import io

# UTF-8出力に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "https://pc-compat-engine.onrender.com/api/recommend"
payload = {"message": "予算15万円でモンハンワイルズを遊びたい"}

print("=" * 60)
print("テスト: フル構成推奨（8カテゴリ）")
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=30, verify=False)
    print(f"Status: {response.status_code}\n")
    data = response.json()
    
    if 'recommended_build' in data:
        build = data['recommended_build']
        print(f"✅ 推奨構成パーツ数: {len(build)}")
        
        # カテゴリ一覧を抽出
        categories = [part.get('category', '?') for part in build]
        print(f"\n📦 カテゴリ一覧:")
        for cat in categories:
            print(f"   - {cat}")
        
        # 必須カテゴリチェック
        required = ['GPU', 'CPU', 'MB', 'RAM', 'PSU', 'CASE', 'SSD', 'COOLER']
        missing = [cat for cat in required if cat not in categories]
        
        if missing:
            print(f"\n❌ 不足カテゴリ: {', '.join(missing)}")
        else:
            print(f"\n✅ 全必須カテゴリ含まれている！")
        
        # 詳細表示
        print(f"\n📋 詳細:")
        for part in build:
            cat = part.get('category', '?')
            name = part.get('name', '?')
            price = part.get('price_range', '?')
            print(f"   {cat:8} : {name[:40]:40} - {price}")
    
    if 'total_estimate' in data:
        print(f"\n💰 合計予算: {data['total_estimate']}")
        
    if 'reply' in data:
        print(f"\n💬 返信: {data['reply']}")
        
except Exception as e:
    print(f"❌ Error: {e}")
