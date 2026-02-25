import subprocess
r = subprocess.run([
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--headless', '--disable-gpu',
    r'--screenshot=C:\Users\iwashita.AKGNET\Pictures\Screenshots\render_site_check.png',
    '--window-size=1280,900',
    '--timeout=60000',
    'https://pc-compat-engine.onrender.com/'
], capture_output=True, text=True, timeout=70)
print('rc:', r.returncode)
print('stdout:', r.stdout[:300])
print('stderr:', r.stderr[:300])
