import urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://pc-compat-engine.onrender.com/compat/google235f90778117db07.html'
try:
    req = urllib.request.urlopen(url, context=ctx, timeout=15)
    body = req.read(200).decode('utf-8', errors='replace')
    print('Status:', req.status)
    print('Content:', body[:100])
except Exception as e:
    print('NG:', type(e).__name__, str(e))
