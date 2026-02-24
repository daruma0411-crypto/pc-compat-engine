"""
PC工房・ツクモ・ドスパラのGPU一覧ページをスクレイピングして
既存データとの差分を抽出するスクリプト
"""
import glob
import json
import re
import ssl
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
}

# ================================================================
# 共通ユーティリティ
# ================================================================

def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=20) as r:
            raw = r.read()
            # charsetを判定
            for enc in ('utf-8', 'shift_jis', 'euc-jp', 'cp932'):
                try:
                    return raw.decode(enc)
                except Exception:
                    continue
            return raw.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [fetch error] {url}: {e}")
        return ""


def load_existing_gpus() -> list:
    """workspace/data/ から既存GPU名一覧を返す"""
    paths = glob.glob('workspace/data/*/products.jsonl')
    gpus = []
    for p in paths:
        with open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get('category') == 'gpu':
                    name = d.get('name', '')
                    if name:
                        gpus.append(name)
    return gpus


def normalize(s: str) -> str:
    """比較用正規化（小文字・記号除去・空白統一）"""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def tokenize(s: str) -> set:
    return set(normalize(s).split())


def is_new(name: str, existing_norms: list) -> bool:
    """既存GPUと一致しなければTrue"""
    n_toks = tokenize(name)
    if len(n_toks) < 2:
        return True
    for ex_toks in existing_norms:
        # 相互包含チェック
        if n_toks <= ex_toks or ex_toks <= n_toks:
            return False
        # 共通トークン 70% 以上 → 同一とみなす
        common = n_toks & ex_toks
        if len(common) / max(len(n_toks), len(ex_toks)) >= 0.70:
            return False
    return True


# ================================================================
# PC工房
# ================================================================

PC_KOUBOU_URLS = [
    'https://www.pc-koubou.jp/category/047902.html',
    'https://www.pc-koubou.jp/category/047902.html?offset=40',
    'https://www.pc-koubou.jp/category/047902.html?offset=80',
]


def scrape_pc_koubou() -> list:
    """PC工房 GPU一覧から製品名を抽出"""
    found = []
    for url in PC_KOUBOU_URLS:
        print(f"  [PC工房] fetching {url}")
        html = fetch_html(url)
        if not html:
            continue
        # 製品名パターン: <p class="name"> or data-product-name or title属性
        patterns = [
            r'<p[^>]+class="[^"]*productName[^"]*"[^>]*>(.*?)</p>',
            r'<h2[^>]+class="[^"]*product[^"]*"[^>]*>(.*?)</h2>',
            r'<span[^>]+class="[^"]*item_name[^"]*"[^>]*>(.*?)</span>',
            r'class="product_name"[^>]*>(.*?)</(?:p|span|h)',
            r'<a[^>]+title="([^"]*(?:RTX|GTX|RX|Radeon|GeForce|VEGA)[^"]*)"',
            r'title="([^"]*(?:RTX|GTX|RX \d|Radeon|GeForce)[^"]*)"',
        ]
        names = set()
        for pat in patterns:
            for m in re.finditer(pat, html, re.IGNORECASE | re.DOTALL):
                txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                txt = txt.replace('\n', ' ').replace('\r', '')
                txt = re.sub(r'\s+', ' ', txt).strip()
                if len(txt) > 5 and any(k in txt.upper() for k in ['RTX', 'GTX', 'RX ', 'RADEON', 'GEFORCE', 'ARC']):
                    names.add(txt)
        found.extend(names)
        # ページに製品が無ければ打ち切り
        if not names:
            break
    return list(set(found))


# ================================================================
# ツクモ (e-TSUKUMO)
# ================================================================

TSUKUMO_URLS = [
    'https://shop.tsukumo.co.jp/goods/pc/gpu/',
    'https://shop.tsukumo.co.jp/goods/pc/gpu/?page=2',
    'https://shop.tsukumo.co.jp/goods/pc/gpu/?page=3',
]


def scrape_tsukumo() -> list:
    found = []
    for url in TSUKUMO_URLS:
        print(f"  [ツクモ] fetching {url}")
        html = fetch_html(url)
        if not html:
            continue
        patterns = [
            r'class="goods_name"[^>]*>(.*?)</(?:p|span|h|a)',
            r'<p[^>]+class="[^"]*goods_name[^"]*"[^>]*>(.*?)</p>',
            r'<a[^>]+class="[^"]*goods[^"]*"[^>]*>(.*?)</a>',
            r'<h2[^>]+class="[^"]*goods[^"]*"[^>]*>(.*?)</h2>',
            r'title="([^"]*(?:RTX|GTX|RX \d|Radeon|GeForce|Arc)[^"]*)"',
        ]
        names = set()
        for pat in patterns:
            for m in re.finditer(pat, html, re.IGNORECASE | re.DOTALL):
                txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                txt = re.sub(r'\s+', ' ', txt).strip()
                if len(txt) > 5 and any(k in txt.upper() for k in ['RTX', 'GTX', 'RX ', 'RADEON', 'GEFORCE', 'ARC']):
                    names.add(txt)
        found.extend(names)
        if not names:
            break
    return list(set(found))


# ================================================================
# ドスパラ
# ================================================================

DOSPARA_URLS = [
    'https://www.dospara.co.jp/5shopping/search.php?sc_category1=3&sc_category2=11',
    'https://www.dospara.co.jp/5shopping/search.php?sc_category1=3&sc_category2=11&page=2',
    'https://www.dospara.co.jp/5shopping/search.php?sc_category1=3&sc_category2=11&page=3',
]


def scrape_dospara() -> list:
    found = []
    for url in DOSPARA_URLS:
        print(f"  [ドスパラ] fetching {url}")
        html = fetch_html(url)
        if not html:
            continue
        patterns = [
            r'class="product-name"[^>]*>(.*?)</(?:p|span|h|a)',
            r'class="item_title"[^>]*>(.*?)</(?:p|span|h|a)',
            r'<p[^>]+class="[^"]*name[^"]*"[^>]*>(.*?)</p>',
            r'title="([^"]*(?:RTX|GTX|RX \d|Radeon|GeForce|Arc)[^"]*)"',
            r'alt="([^"]*(?:RTX|GTX|RX \d|Radeon|GeForce)[^"]*)"',
        ]
        names = set()
        for pat in patterns:
            for m in re.finditer(pat, html, re.IGNORECASE | re.DOTALL):
                txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                txt = re.sub(r'\s+', ' ', txt).strip()
                if len(txt) > 5 and any(k in txt.upper() for k in ['RTX', 'GTX', 'RX ', 'RADEON', 'GEFORCE', 'ARC']):
                    names.add(txt)
        found.extend(names)
        if not names:
            break
    return list(set(found))


# ================================================================
# メイン
# ================================================================

if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')

    print("=== 既存データ読み込み ===")
    existing = load_existing_gpus()
    existing_norms = [tokenize(g) for g in existing]
    print(f"既存GPU: {len(existing)}件")

    all_found = {}
    errors = []

    print("\n=== PC工房スクレイピング ===")
    try:
        pc_koubou = scrape_pc_koubou()
        all_found['PC工房'] = pc_koubou
        print(f"  取得: {len(pc_koubou)}件")
    except Exception as e:
        errors.append(f"PC工房: {e}")
        all_found['PC工房'] = []

    print("\n=== ツクモスクレイピング ===")
    try:
        tsukumo = scrape_tsukumo()
        all_found['ツクモ'] = tsukumo
        print(f"  取得: {len(tsukumo)}件")
    except Exception as e:
        errors.append(f"ツクモ: {e}")
        all_found['ツクモ'] = []

    print("\n=== ドスパラスクレイピング ===")
    try:
        dospara = scrape_dospara()
        all_found['ドスパラ'] = dospara
        print(f"  取得: {len(dospara)}件")
    except Exception as e:
        errors.append(f"ドスパラ: {e}")
        all_found['ドスパラ'] = []

    # 全ショップの統合ユニーク化
    all_names = set()
    for shop, names in all_found.items():
        for n in names:
            all_names.add(n)

    print(f"\n=== 全ショップ合計ユニーク: {len(all_names)}件 ===")

    # 未登録フィルタ
    new_gpus = [(n, [s for s, ns in all_found.items() if n in ns])
                for n in sorted(all_names) if is_new(n, existing_norms)]

    print(f"\n=== 未登録GPU: {len(new_gpus)}件 ===")
    for name, shops in new_gpus:
        print(f"  [{'/'.join(shops)}] {name}")

    # 結果をJSONで保存
    result = {
        'existing_count': len(existing),
        'shops': {k: sorted(v) for k, v in all_found.items()},
        'new_gpus': [{'name': n, 'shops': s} for n, s in new_gpus],
        'errors': errors,
    }
    out_path = 'workspace/data/analysis/shop_gpu_diff.json'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n結果を保存: {out_path}")
