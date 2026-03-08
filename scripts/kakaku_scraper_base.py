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
            err_str = str(e)
            # 410 Gone（廃盤）/ 404 Not Found はリトライしても無駄
            if '410' in err_str or '404' in err_str:
                print(f'  [SKIP] {url} → {err_str.split(":")[0].strip()}')
                return None
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


def extract_min_price(html: str) -> int | None:
    """kakaku.com ページ HTML から最安値（円）を抽出する"""
    patterns = [
        r"price\s*:\s*'(\d{4,7})'",          # JS変数 price : '54790'
        r'最安価格[^:：]*[：:][^0-9]*([\d,]{4,})',  # og:description の最安価格(税込)：54,790円
        r'class="priceNum"[^>]*>\s*([\d,]{4,})',
        r'最安値[^¥\d]*([\d,]{4,})',
        r'"lowPrice":\s*"?([\d,]{4,})"?',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            try:
                price = int(m.group(1).replace(',', ''))
                if price >= 1000:   # 1000円未満は誤マッチとして除外
                    return price
            except Exception:
                pass
    return None


def migrate_entry(entry: dict, today: str) -> dict:
    """既存エントリに差分管理フィールドを追加（冪等）"""
    if 'status' not in entry:
        entry['status'] = 'active'
    if 'first_seen_at' not in entry:
        entry['first_seen_at'] = entry.get('created_at', today)
    if 'last_seen_at' not in entry:
        entry['last_seen_at'] = entry.get('price_updated_at', today)
    if 'price_history' not in entry:
        entry['price_history'] = []
        if entry.get('price_min'):
            entry['price_history'] = [{
                'date': entry.get('price_updated_at', today),
                'price': entry['price_min']
            }]
    return entry


def update_prices_with_diff(jsonl_path: str, today: str, active_codes: set = None) -> dict:
    """
    価格更新 + 差分検出。
    active_codes: 今回のスクレイプで見つかった kakaku コードのセット。
                  None の場合は廃盤検知をスキップ（従来互換）。
    戻り値: {'new': [...], 'price_changed': [...], 'delisted': [...], 'updated': int}
    """
    diff = {'new': [], 'price_changed': [], 'delisted': [], 'updated': 0}

    if not os.path.exists(jsonl_path):
        print(f'  [SKIP] ファイルなし: {jsonl_path}')
        return diff

    entries = []
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

    for entry in entries:
        # マイグレーション（未適用なら適用）
        migrate_entry(entry, today)

        # すでに今日更新済みならスキップ
        if entry.get('price_updated_at') == today:
            continue

        url = entry.get('source_url', '')
        code_m = re.search(r'(K0\d{9})', url)
        if not code_m:
            continue
        code = code_m.group(1)

        # 廃盤検知
        if active_codes is not None and code not in active_codes:
            if entry.get('status') != 'delisted':
                entry['status'] = 'delisted'
                diff['delisted'].append({
                    'id': entry.get('id', ''),
                    'name': entry.get('name', ''),
                    'last_price': entry.get('price_min'),
                })
            continue

        # activeなら last_seen_at を更新
        entry['last_seen_at'] = today
        entry['status'] = 'active'

        # 価格取得
        html = fetch(f'https://kakaku.com/item/{code}/spec/', delay_range=(1.0, 2.0))
        if not html:
            continue
        new_price = extract_min_price(html)
        if new_price and new_price > 0:
            old_price = entry.get('price_min')
            if old_price != new_price:
                # 価格変動
                entry['price_history'].append({'date': today, 'price': new_price})
                entry['price_history'] = entry['price_history'][-12:]  # 直近12回
                diff['price_changed'].append({
                    'id': entry.get('id', ''),
                    'name': entry.get('name', ''),
                    'old_price': old_price,
                    'new_price': new_price,
                })
            entry['price_min'] = new_price
            entry['price_updated_at'] = today
            diff['updated'] += 1

    # 全件書き直し
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'  価格更新: {diff["updated"]}件 / {len(entries)}件'
          f' (変動: {len(diff["price_changed"])} 廃盤: {len(diff["delisted"])}) [{jsonl_path}]')
    return diff


def save_diff_log(diff_log_dir: str, today: str, all_diffs: dict):
    """
    差分ログを JSONL ファイルに書き出す。
    all_diffs: {category: diff_dict, ...}
    """
    os.makedirs(diff_log_dir, exist_ok=True)
    log_path = os.path.join(diff_log_dir, f'{today}.jsonl')

    total_new = 0
    total_changed = 0
    total_delisted = 0

    with open(log_path, 'w', encoding='utf-8') as f:
        for category, diff in all_diffs.items():
            for item in diff.get('new', []):
                item['type'] = 'new'
                item['category'] = category
                item['date'] = today
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                total_new += 1
            for item in diff.get('price_changed', []):
                item['type'] = 'price_changed'
                item['category'] = category
                item['date'] = today
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                total_changed += 1
            for item in diff.get('delisted', []):
                item['type'] = 'delisted'
                item['category'] = category
                item['date'] = today
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                total_delisted += 1

        # サマリー行
        summary = {
            'type': 'summary',
            'date': today,
            'new_count': total_new,
            'price_changed_count': total_changed,
            'delisted_count': total_delisted,
        }
        f.write(json.dumps(summary, ensure_ascii=False) + '\n')

    print(f'\n差分ログ: {log_path}')
    print(f'  新規: {total_new} / 価格変動: {total_changed} / 廃盤: {total_delisted}')
    return log_path


def update_prices_in_jsonl(jsonl_path: str, today: str):
    """
    既存 JSONL ファイルの各エントリに price_min / price_updated_at を追記・上書きする。
    source_url から K0xxx コードを抽出して価格を取得。
    """
    if not os.path.exists(jsonl_path):
        print(f'  [SKIP] ファイルなし: {jsonl_path}')
        return 0

    entries = []
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

    updated = 0
    for entry in entries:
        # すでに今日更新済みならスキップ
        if entry.get('price_updated_at') == today:
            continue
        url = entry.get('source_url', '')
        code_m = re.search(r'(K0\d{9})', url)
        if not code_m:
            continue
        code = code_m.group(1)
        html = fetch(f'https://kakaku.com/item/{code}/spec/', delay_range=(1.0, 2.0))
        if not html:
            continue
        price = extract_min_price(html)
        if price and price > 0:
            entry['price_min'] = price
            entry['price_updated_at'] = today
            updated += 1

    # 全件書き直し
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'  価格更新: {updated}件 / {len(entries)}件 ({jsonl_path})')
    return updated
