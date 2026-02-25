import urllib.request, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = 'https://pc-compat-engine.onrender.com'
sample = os.listdir(r'C:\Users\iwashita.AKGNET\pc-compat-engine\static\compat')[0]

req = urllib.request.urlopen(BASE + f'/compat/{sample}', context=ctx, timeout=15)
body = req.read(5000).decode('utf-8', errors='replace')

print('breadcrumb CSS:', 'breadcrumb' in body.lower())
print('BreadcrumbList JSON-LD:', 'BreadcrumbList' in body)
print('nav tag:', '<nav' in body)
print('--- 先頭1000文字 ---')
print(body[:1000])
