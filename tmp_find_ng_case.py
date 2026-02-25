import json, pathlib
BASE = pathlib.Path('C:/Users/iwashita.AKGNET/pc-compat-engine/workspace/data')
for path in BASE.glob('*/products.jsonl'):
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        d = json.loads(line)
        if d.get('category') != 'case': continue
        s = d.get('specs', {}) or {}
        max_len = s.get('max_gpu_length_mm') or d.get('max_gpu_length_mm')
        if max_len:
            try:
                v = float(str(max_len).replace('mm','').strip())
                if v < 336:
                    print("{} / max={}mm".format(d.get('name','?'), max_len))
            except:
                pass
