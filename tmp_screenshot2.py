import subprocess, time

# トップページ
r = subprocess.run([
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--headless', '--disable-gpu',
    r'--screenshot=C:\Users\iwashita.AKGNET\Pictures\Screenshots\render_top.png',
    '--window-size=1280,900',
    '--timeout=30000',
    'https://pc-compat-engine.onrender.com/'
], capture_output=True, text=True, timeout=40)
print('top rc:', r.returncode)

time.sleep(2)

# compatページ
r2 = subprocess.run([
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--headless', '--disable-gpu',
    r'--screenshot=C:\Users\iwashita.AKGNET\Pictures\Screenshots\render_compat.png',
    '--window-size=1280,900',
    '--timeout=30000',
    'https://pc-compat-engine.onrender.com/compat/index.html'
], capture_output=True, text=True, timeout=40)
print('compat rc:', r2.returncode)
