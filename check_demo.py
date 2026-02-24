"""デモ結果チェックスクリプト"""
import subprocess, sys, os

env = os.environ.copy()
env['PYTHONUTF8'] = '1'

result = subprocess.run(
    [sys.executable, '-m', 'examples.pc_demo'],
    capture_output=True, timeout=60, env=env,
    cwd=os.path.dirname(os.path.abspath(__file__))
)
txt = result.stdout.decode('utf-8', errors='replace')
err = result.stderr.decode('utf-8', errors='replace')

out = []
for line in (txt + err).split('\n'):
    lo = line.lower()
    if any(kw in lo for kw in ['health', 'demo ', '期待', '合計', '完了', 'error', 'traceback', 'ng', '判定', 'ok', 'warning']):
        out.append(line)
out.append('exit:' + str(result.returncode))

with open('C:/Users/iwashita.AKGNET/Downloads/demo_check.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('Saved to demo_check.txt, exit=' + str(result.returncode))
