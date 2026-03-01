#!/usr/bin/env python3
"""Schema.org検証スクリプト"""

import json
import re
from pathlib import Path

def extract_schemas(html_path):
    """HTMLからSchema.orgを抽出"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # <script type="application/ld+json">...</script> を抽出
    pattern = r'<script type="application/ld\+json">\s*(.*?)\s*</script>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    return matches

def validate_schema(schema_text):
    """Schema.orgのJSON検証"""
    try:
        schema = json.loads(schema_text)
        return True, schema, None
    except json.JSONDecodeError as e:
        return False, None, str(e)

def main():
    html_path = Path('static/index.html')
    
    if not html_path.exists():
        print(f"[ERROR] File not found: {html_path}")
        return
    
    print("[INFO] Schema.org validation started...\n")
    
    schemas = extract_schemas(html_path)
    
    if not schemas:
        print("[WARN] No Schema.org found")
        return
    
    print(f"[OK] Found {len(schemas)} Schema.org blocks\n")
    
    for i, schema_text in enumerate(schemas, 1):
        print(f"--- Schema #{i} ---")
        
        valid, schema, error = validate_schema(schema_text)
        
        if valid:
            schema_type = schema.get('@type', 'Unknown')
            print(f"[OK] Valid JSON: @type = {schema_type}")
            
            # 詳細情報
            if schema_type == 'FAQPage':
                questions = schema.get('mainEntity', [])
                print(f"   質問数: {len(questions)}")
                print("   質問一覧:")
                for q in questions:
                    print(f"     - {q.get('name', 'N/A')}")
            
            elif schema_type == 'SoftwareApplication':
                print(f"   アプリ名: {schema.get('name', 'N/A')}")
                print(f"   価格: {schema.get('offers', {}).get('price', 'N/A')}円")
                rating = schema.get('aggregateRating', {})
                if rating:
                    print(f"   評価: {rating.get('ratingValue', 'N/A')}/5 ({rating.get('reviewCount', 'N/A')}件)")
        
        else:
            print(f"[ERROR] Invalid JSON: {error}")
        
        print()
    
    print("[DONE] Validation completed!")

if __name__ == '__main__':
    main()
