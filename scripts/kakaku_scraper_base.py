"""
価格.com スクレイパー 共通ベース
各カテゴリスクレイパーからimportして使う
"""
import urllib.request
import re
import json
import os
import sys
import time
import random

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'workspace', 'data')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

MAKER_NORMALIZE = {
    'asrock':    'asrock',
    'asus':      'asus',
    'gigabyte':  'gigabyte',
    'msi':       'msi',
    'intel':     'intel',
    'amd':       'amd',
    'corsair':   'corsair',
    'noctua':    'noctua',
    'be quiet':  'bequiet',
    'bequiet':   'bequiet',
    'nzxt':      'nzxt',
    'fractal':   'fractal',
    'lian li':   'lianli',
    'cooler master': 'coolermaster',
    'coolermaster':  'coolermaster',
    'thermaltake':   'thermaltake',
    'seasonic':  'seasonic',
    'super flower': 'superflower',
    'superflower':  'superflower',
    'antec':     'antec',
    'silverstone': 'silverstone',
    'deepcool':  'deepcool',
    'arctic':    'arctic',
    'thermalright': 'thermalright',
    'scythe':    'scythe',
    'id-cooling': 'idcooling',
    'crucial':   'crucial',
    'kingston':  'kingston',
    'samsung':   'samsung',
    'western digital': 'wd',
    'seagate':   'seagate',
    'sapphire':  'sapphire',
    'powercolor': 'powercolor',
    'xfx':       'xfx',
    'palit':     'palit',
    'gainward':  'gainward',
    'zotac':     'zotac',
    'pny':       'pny',
    'elsa':      'elsa',
    'inno3d':    'inno3d',
    'sparkle':   'sparkle',
    '玄人志向':  'kuroutoshikou',
}


def normalize_maker(raw: str) -> str:
    """メーカー名を小文字スラグに正規化"""
    s = raw.strip().lower()
    for key, val in MAKER_NORMALIZE.items():
        if key in s:
            return val
    # フォールバック: 英数字のみ小文字
    return re.sub(r'[^a-z0-9]', '', s) or 'unknown'


def fetch(url: str, retries: int = 3, delay_range=(0.5, 1.0)) -> str | None:
    """HTTPリクエスト with リトライ・指数バックオフ"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()
            time.sleep(random.uniform(*delay_range))
            return raw.decode('cp932', errors='replace')
        except Exception as e:
            wait = 2 ** attempt
            print(f'  [WARN] {url} attempt={attempt+1} error={e} → wait {wait}s')
            time.sleep(wait)
    return None


def get_all_codes(list_url: str) -> list[str]:
    """
    一覧ページを全ページ走査して製品コード(K0xxxxxxxxxx)を収集
    重複除去済みリストを返す
    """
    codes = []
    seen = set()

    # まず1ページ目で最大ページ数を確認
    html = fetch(list_url)
    if not html:
        print('[ERROR] 一覧ページ取得失敗')
        return []

    pages_found = re.findall(r'pdf_pg=(\d+)', html)
    max_page = max(int(p) for p in pages_found) if pages_found else 1
    print(f'  総ページ数: {max_page}')

    def extract_codes(html):
        return re.findall(r'K0\d{9}', html)

    for c in extract_codes(html):
        if c not in seen:
            seen.add(c)
            codes.append(c)

    for page in range(2, max_page + 1):
        url = f'{list_url}?pdf_pg={page}'
        html = fetch(url)
        if not html:
            print(f'  [WARN] page={page} 取得失敗')
            continue
        for c in extract_codes(html):
            if c not in seen:
                seen.add(c)
                codes.append(c)
        if page % 5 == 0:
            print(f'  page {page}/{max_page} 収集済み: {len(codes)}件')

    return codes


def get_raw_specs(code: str) -> dict:
    """
    /item/K0xxx/spec/ ページのスペック表をパースして
    {key: value} の辞書で返す
    """
    url = f'https://kakaku.com/item/{code}/spec/'
    html = fetch(url)
    if not html:
        return {}

    # 製品名取得
    title_m = re.search(r'価格\.com\s*-\s*(.+?)\s*スペック', html)
    name = title_m.group(1).strip() if title_m else ''

    # メーカー取得（breadcrumb または ckitemLink の span）
    maker_m = re.search(r'class="ckitemLink"[^>]*>.*?<span>([^<]+)</span>', html, re.DOTALL)
    maker_raw = maker_m.group(1).strip() if maker_m else ''

    # スペック表パース
    specs_raw = {}
    rows = re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL)
    for k, v in rows:
        k = re.sub(r'<[^>]+>', '', k).replace('\xa0', '').strip()
        # 「セクション名\n\n項目名」の形式→最後の項目名のみ使用
        k = k.split('\n')[-1].strip()
        v = re.sub(r'<[^>]+>', '', v).replace('\xa0', ' ').strip()
        v = re.sub(r'\s+', ' ', v)
        if k and k not in ('', ' ') and v and v not in ('', ' ', '-'):
            specs_raw[k] = v

    return {
        'code': code,
        'name': name,
        'maker_raw': maker_raw,
        'specs_raw': specs_raw,
        'source_url': f'https://kakaku.com/item/{code}/spec/',
    }


def load_existing_ids(jsonl_path: str) -> set:
    """既存JSONLファイルからIDセットを読み込む"""
    ids = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line).get('id', ''))
                    except Exception:
                        pass
    return ids


def save_entry(jsonl_path: str, entry: dict):
    """1件をJSONLファイルに追記"""
    with open(jsonl_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def make_id(prefix: str, code: str) -> str:
    return f'{prefix}_{code}'
