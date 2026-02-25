import urllib.request, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = 'https://pc-compat-engine.onrender.com'

checks = [
    ('トップページ', '/'),
    ('compatインデックス', '/compat/index.html'),
    ('sitemap-index', '/sitemap-index.xml'),
    ('sitemap-1', '/sitemap-1.xml'),
    ('robots.txt', '/robots.txt'),
    ('API diagnose', '/api/diagnose'),
    ('個別SEOページ', '/compat/msi-geforce-rtx-4090-gaming-x-trio-24g-vs-fractal-design-define-7.html'),
]

for name, path in checks:
    try:
        req = urllib.request.urlopen(BASE + path, context=ctx, timeout=15)
        body = req.read(300).decode('utf-8', errors='replace')
        print(f'OK {name}: {req.status} ({len(body)}chars)')
    except Exception as e:
        print(f'NG {name}: {type(e).__name__} {str(e)[:60]}')
