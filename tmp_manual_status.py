import json, pathlib

BASE = pathlib.Path('C:/Users/iwashita.AKGNET/pc-compat-engine/workspace/data')
makers = ['gigabyte_mb', 'asus_mb', 'msi_mb', 'asrock_mb']

header = "{:<15} {:>4} {:>11} {:>7} {:>11}".format(
    "maker", "登録", "manual_path", "txt取得", "constraints")
print(header)
print('-' * 55)

for m in makers:
    jsonl = BASE / m / 'products.jsonl'
    man_dir = BASE / m / 'manuals'

    total = has_manual = has_constraints = 0
    no_manual = []

    if jsonl.exists():
        for line in jsonl.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            total += 1
            d = json.loads(line)
            if d.get('manual_path') and d['manual_path'] != '':
                has_manual += 1
            else:
                no_manual.append(d.get('name', d.get('id', '?')))
            if d.get('constraints'):
                has_constraints += 1

    txt_count = len(list(man_dir.glob('*.txt'))) if man_dir.exists() else 0
    row = "{:<15} {:>4} {:>11} {:>7} {:>11}".format(
        m, total, has_manual, txt_count, has_constraints)
    print(row)
    if no_manual:
        for n in no_manual:
            print("  x {}".format(n))

print()
print("--- manual_path あり & txt なし（スクレイプ失敗）---")
for m in makers:
    jsonl = BASE / m / 'products.jsonl'
    man_dir = BASE / m / 'manuals'
    if not jsonl.exists():
        continue
    for line in jsonl.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        mp = d.get('manual_path', '')
        if not mp:
            continue
        txt_path = pathlib.Path('C:/Users/iwashita.AKGNET/pc-compat-engine') / mp.replace('\\\\', '/').replace('\\', '/')
        if not txt_path.exists():
            print("  {} / {}".format(m, d.get('name', '?')))
