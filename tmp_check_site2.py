import urllib.request, ssl, os, glob

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = 'https://pc-compat-engine.onrender.com'

# 実在するSEOページのファイル名を1件取得
sample = os.listdir(r'C:\Users\iwashita.AKGNET\pc-compat-engine\static\compat')[0]

checks = [
    ('API health (GET)', '/api/health'),
    ('SEOページサンプル', f'/compat/{sample}'),
    ('sitemap-index', '/sitemap-index.xml'),
    ('robots.txt', '/robots.txt'),
]

for name, path in checks:
    try:
        req = urllib.request.urlopen(BASE + path, context=ctx, timeout=15)
        body = req.read(500).decode('utf-8', errors='replace')
        print(f'OK {name}: {req.status}')
        if 'sitemap' in path or 'robots' in path:
            print(f'   内容: {body[:200]}')
        elif 'compat' in path:
            has_breadcrumb = 'breadcrumb' in body.lower()
            has_jsonld = 'BreadcrumbList' in body
            print(f'   breadcrumb CSS: {has_breadcrumb}, JSON-LD: {has_jsonld}')
    except Exception as e:
        print(f'NG {name}: {type(e).__name__} {str(e)[:80]}')
