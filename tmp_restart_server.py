"""サーバー再起動スクリプト"""
import subprocess, time, sys, os

# ポート10000で待機中のPIDを取得して停止
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, encoding='cp932', errors='replace')
pids_to_kill = set()
for line in result.stdout.splitlines():
    if ':10000' in line and 'LISTENING' in line:
        parts = line.split()
        if parts:
            try:
                pids_to_kill.add(int(parts[-1]))
            except ValueError:
                pass

print(f'停止対象PID: {pids_to_kill}')
for pid in pids_to_kill:
    subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
    print(f'  停止: {pid}')

time.sleep(3)

# 新サーバー起動
os.chdir(r'C:\Users\iwashita.AKGNET\pc-compat-engine')
with open('tmp_server.log', 'w', encoding='utf-8') as f:
    proc = subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=f, stderr=f,
        cwd=r'C:\Users\iwashita.AKGNET\pc-compat-engine'
    )
print(f'新サーバーPID: {proc.pid}')

time.sleep(5)

# 起動確認
import urllib.request
try:
    with urllib.request.urlopen('http://localhost:10000/api/health', timeout=5) as r:
        print(f'ヘルスチェック: {r.read().decode()}')
except Exception as e:
    print(f'ヘルスチェック失敗: {e}')
    with open('tmp_server.log', encoding='utf-8') as f:
        print(f.read()[-500:])
