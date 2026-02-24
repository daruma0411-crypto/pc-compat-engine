#!/usr/bin/env python3
"""
SEOページ自動生成スクリプト
============================
workspace/data/*/products.jsonl から GPU・ケースデータを読み込み、
全組み合わせの互換性チェックページを static/compat/ に生成する。

使い方:
    python scripts/generate_seo_pages.py

出力:
    static/compat/{gpu-slug}-vs-{case-slug}.html  個別ページ
    static/compat/gpu/{gpu-slug}.html             GPU別インデックス
    static/compat/case/{case-slug}.html           ケース別インデックス
    static/sitemap-1.xml〜sitemap-N.xml           分割サイトマップ
    static/sitemap-index.xml                      サイトマップインデックス
"""
import glob
import json
import os
import re
import sys

# ── パス設定 ────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR   = os.path.join(_ROOT, 'workspace', 'data')
_OUTPUT_DIR = os.path.join(_ROOT, 'static', 'compat')

# アフィリエイトタグ（Renderと同じプレースホルダー方式）
AMAZON_TAG   = '__AMAZON_TAG__'
RAKUTEN_A_ID = '__RAKUTEN_A_ID__'
RAKUTEN_L_ID = '__RAKUTEN_L_ID__'

_BASE_URL = 'https://pc-compat-engine.onrender.com'


# ── ユーティリティ ────────────────────────────────────────────

def slugify(name: str) -> str:
    """製品名をURLスラグに変換。例: 'RTX 4070 TUF OC' → 'rtx-4070-tuf-oc'"""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def esc(text: str) -> str:
    """HTMLエスケープ"""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def amazon_url(name: str) -> str:
    import urllib.parse
    q = urllib.parse.quote(name)
    return f'https://www.amazon.co.jp/s?k={q}&tag={AMAZON_TAG}'


def rakuten_url(name: str) -> str:
    import urllib.parse
    q = urllib.parse.quote(name)
    search = f'https://search.rakuten.co.jp/search/mall/{q}/'
    if RAKUTEN_A_ID and not RAKUTEN_A_ID.startswith('__'):
        return (f'https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_A_ID}/{RAKUTEN_L_ID}/'
                f'?pc={urllib.parse.quote(search)}')
    return search


# ── データ読み込み ────────────────────────────────────────────

def load_products() -> tuple[list, list]:
    """GPUとケースのリストを返す。(gpus, cases)"""
    gpus, cases = [], []
    for path in glob.glob(os.path.join(_DATA_DIR, '*', 'products.jsonl')):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cat = d.get('category', '')
                if cat == 'gpu':
                    length = (d.get('specs') or {}).get('length_mm') or d.get('length_mm')
                    if length is not None:
                        try:
                            d['_length_mm'] = float(str(length).replace('mm', '').strip())
                            gpus.append(d)
                        except (ValueError, TypeError):
                            pass
                elif cat == 'case':
                    max_len = (d.get('specs') or {}).get('max_gpu_length_mm') \
                              or d.get('max_gpu_length_mm')
                    if max_len is not None:
                        try:
                            d['_max_gpu_mm'] = float(str(max_len).replace('mm', '').strip())
                            cases.append(d)
                        except (ValueError, TypeError):
                            pass
    return gpus, cases


def calc_verdict(margin: float) -> tuple[str, str, str]:
    """(verdict, badge, css_class) を返す"""
    if margin <= 0:
        return 'NG', '❌ 入りません', 'ng'
    elif margin <= 20:
        return 'WARNING', '⚠️ 注意あり', 'warning'
    else:
        return 'OK', '✅ 入ります', 'ok'


# ── HTML テンプレート ─────────────────────────────────────────

_CSS = """
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Hiragino Sans",sans-serif;
  background:#f3f4f6;color:#111827;line-height:1.6}
.wrap{max-width:800px;margin:0 auto;padding:24px 16px}
.breadcrumb{padding:8px 16px;background:#f5f5f5;border-bottom:1px solid #ddd;font-size:.875rem}
.breadcrumb a{color:#4f46e5;text-decoration:none}
.breadcrumb a:hover{text-decoration:underline}
.breadcrumb .sep{margin:0 6px;color:#9ca3af}
header{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
  color:#fff;padding:16px 20px;margin-bottom:24px}
header a{color:#fff;text-decoration:none;font-size:.9rem;opacity:.8}
header h1{font-size:1rem;margin-top:4px;opacity:.9}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;
  box-shadow:0 1px 3px rgba(0,0,0,.08),0 4px 12px rgba(0,0,0,.06)}
.verdict{font-size:1.8rem;font-weight:700;margin-bottom:16px}
.verdict.ok{color:#16a34a}
.verdict.warning{color:#ca8a04}
.verdict.ng{color:#dc2626}
table{width:100%;border-collapse:collapse;margin:12px 0}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb}
th{background:#f9fafb;font-weight:600;font-size:.9rem;color:#374151}
.buy-wrap{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}
.buy-btn{display:inline-block;padding:10px 20px;border-radius:8px;
  color:#fff;font-weight:600;text-decoration:none;font-size:.95rem}
.buy-btn:hover{opacity:.85}
.buy-amazon{background:#FF9900}
.buy-rakuten{background:#BF0000}
.links{display:flex;flex-direction:column;gap:8px}
.links a{color:#4f46e5;text-decoration:none;font-size:.95rem}
.links a:hover{text-decoration:underline}
.cta{background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
  color:#fff;border-radius:12px;padding:20px 24px;text-align:center;margin-top:24px}
.cta a{color:#fff;font-weight:600;text-decoration:underline}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.item-card{background:#fff;border-radius:10px;padding:16px;
  box-shadow:0 1px 3px rgba(0,0,0,.06)}
.item-card.ok{border-left:4px solid #16a34a}
.item-card.warning{border-left:4px solid #ca8a04}
.item-card.ng{border-left:4px solid #dc2626}
.item-name{font-weight:600;margin-bottom:6px}
.item-detail{font-size:.85rem;color:#6b7280;margin-bottom:10px}
.section-title{font-size:1.1rem;font-weight:700;margin:20px 0 10px;color:#374151}
</style>
"""


def individual_page(gpu: dict, case: dict, margin: float,
                    verdict: str, badge: str, css_class: str) -> str:
    gpu_name  = gpu.get('name', '')
    case_name = case.get('name', '')
    gpu_len   = gpu['_length_mm']
    case_max  = case['_max_gpu_mm']
    gpu_slug  = slugify(gpu_name)
    case_slug = slugify(case_name)

    detail = (
        f'マージン {margin:.0f}mm（余裕あり）' if verdict == 'OK'
        else f'マージン {margin:.0f}mm（ケーブル干渉リスク）' if verdict == 'WARNING'
        else f'{abs(margin):.0f}mmオーバー'
    )

    canonical = f'{_BASE_URL}/compat/{esc(gpu_slug)}-vs-{esc(case_slug)}.html'

    breadcrumb_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": f"{gpu_name}対応ケース一覧",
             "item": f"{_BASE_URL}/compat/gpu/{gpu_slug}.html"},
            {"@type": "ListItem", "position": 3,
             "name": f"{gpu_name} × {case_name}"},
        ]
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(gpu_name)}は{esc(case_name)}に入る？互換性チェック結果</title>
<meta name="description" content="{esc(gpu_name)}（{gpu_len:.0f}mm）が{esc(case_name)}（最大{case_max:.0f}mm）に入るか計算した結果：{badge}。マージン{margin:.0f}mm。">
<link rel="canonical" href="{canonical}">
<script type="application/ld+json">{breadcrumb_ld}</script>
{_CSS}
</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a>
  <span class="sep">&rsaquo;</span>
  <a href="/compat/gpu/{esc(gpu_slug)}.html">{esc(gpu_name)}</a>
  <span class="sep">&rsaquo;</span>
  <span>{esc(gpu_name)} × {esc(case_name)}</span>
</nav>
<header>
  <a href="/">← PC互換チェッカー トップ</a>
  <h1>{esc(gpu_name)} × {esc(case_name)} 互換性チェック</h1>
</header>
<div class="wrap">

  <div class="card">
    <h2 style="font-size:1.3rem;margin-bottom:12px">{esc(gpu_name)}は{esc(case_name)}に入りますか？</h2>
    <div class="verdict {css_class}">{badge}</div>
    <table>
      <tr><th>項目</th><th>値</th></tr>
      <tr><td>GPU全長</td><td>{gpu_len:.0f} mm</td></tr>
      <tr><td>ケース最大GPU長</td><td>{case_max:.0f} mm</td></tr>
      <tr><td>マージン</td><td>{margin:.0f} mm</td></tr>
      <tr><td>判定</td><td>{badge}　{detail}</td></tr>
    </table>
    <div class="buy-wrap">
      <a class="buy-btn buy-amazon" href="{esc(amazon_url(gpu_name))}" target="_blank" rel="noopener">🛒 Amazonで{esc(gpu_name)}を見る</a>
      <a class="buy-btn buy-rakuten" href="{esc(rakuten_url(gpu_name))}" target="_blank" rel="noopener">🛍 楽天で探す</a>
    </div>
  </div>

  <div class="card">
    <p class="section-title">関連ページ</p>
    <div class="links">
      <a href="/compat/gpu/{esc(gpu_slug)}.html">▶ {esc(gpu_name)}が入る他のケース一覧</a>
      <a href="/compat/case/{esc(case_slug)}.html">▶ {esc(case_name)}に入る他のGPU一覧</a>
      <a href="/compat/index.html">▶ GPU・ケース互換性一覧トップ</a>
    </div>
  </div>

  <div class="cta">
    <p>CPU・電源・マザーボードも含めて<br>まとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p>
  </div>

</div>
</body>
</html>"""


def gpu_index_page(gpu: dict, results: list) -> str:
    """GPU別インデックスページ。results = [{'case':..,'margin':..,'verdict':..,'badge':..,'css':..}]"""
    gpu_name = gpu.get('name', '')
    gpu_len  = gpu['_length_mm']
    gpu_slug = slugify(gpu_name)

    ok_list      = [r for r in results if r['verdict'] == 'OK']
    warning_list = [r for r in results if r['verdict'] == 'WARNING']
    ng_list      = [r for r in results if r['verdict'] == 'NG']

    breadcrumb_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2,
             "name": f"{gpu_name}対応ケース一覧",
             "item": f"{_BASE_URL}/compat/gpu/{gpu_slug}.html"},
        ]
    }, ensure_ascii=False)

    def render_items(items):
        if not items:
            return '<p style="color:#6b7280;font-size:.9rem">該当なし</p>'
        html = '<div class="grid">'
        for r in sorted(items, key=lambda x: x['margin'], reverse=True):
            c = r['case']
            c_name = c.get('name', '')
            c_slug = slugify(c_name)
            html += f"""
<div class="item-card {r['css']}">
  <div class="item-name">{esc(c_name)}</div>
  <div class="item-detail">最大{c['_max_gpu_mm']:.0f}mm　マージン{r['margin']:.0f}mm　{r['badge']}</div>
  <a href="/compat/{esc(gpu_slug)}-vs-{esc(c_slug)}.html" style="color:#4f46e5;font-size:.85rem">詳細を見る →</a>
</div>"""
        html += '</div>'
        return html

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(gpu_name)}が入るケース一覧（{len(ok_list)}件OK）</title>
<meta name="description" content="{esc(gpu_name)}（全長{gpu_len:.0f}mm）が搭載できるPCケース一覧。OK {len(ok_list)}件、注意あり {len(warning_list)}件、NG {len(ng_list)}件。">
<script type="application/ld+json">{breadcrumb_ld}</script>
{_CSS}
</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a>
  <span class="sep">&rsaquo;</span>
  <a href="/compat/index.html">GPU・ケース互換性一覧</a>
  <span class="sep">&rsaquo;</span>
  <span>{esc(gpu_name)}</span>
</nav>
<header>
  <a href="/compat/index.html">← GPU・ケース互換性一覧</a>
  <h1>{esc(gpu_name)}（{gpu_len:.0f}mm）対応ケース一覧</h1>
</header>
<div class="wrap">

  <div class="card">
    <p>{esc(gpu_name)}の全長は <strong>{gpu_len:.0f}mm</strong> です。<br>
    OK: {len(ok_list)}件　⚠ 注意: {len(warning_list)}件　❌ NG: {len(ng_list)}件</p>
  </div>

  <p class="section-title">✅ 搭載可能なケース（{len(ok_list)}件）</p>
  {render_items(ok_list)}

  <p class="section-title">⚠️ 注意あり（{len(warning_list)}件）</p>
  {render_items(warning_list)}

  <p class="section-title">❌ 搭載不可（{len(ng_list)}件）</p>
  {render_items(ng_list)}

  <div class="cta">
    <p>CPU・電源も含めてまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p>
  </div>

</div>
</body>
</html>"""


def case_index_page(case: dict, results: list) -> str:
    """ケース別インデックスページ。results = [{'gpu':..,'margin':..,'verdict':..,'badge':..,'css':..}]"""
    case_name = case.get('name', '')
    case_max  = case['_max_gpu_mm']
    case_slug = slugify(case_name)

    ok_list      = [r for r in results if r['verdict'] == 'OK']
    warning_list = [r for r in results if r['verdict'] == 'WARNING']
    ng_list      = [r for r in results if r['verdict'] == 'NG']

    breadcrumb_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": f"{_BASE_URL}/"},
            {"@type": "ListItem", "position": 2,
             "name": f"{case_name}対応GPU一覧",
             "item": f"{_BASE_URL}/compat/case/{case_slug}.html"},
        ]
    }, ensure_ascii=False)

    def render_items(items):
        if not items:
            return '<p style="color:#6b7280;font-size:.9rem">該当なし</p>'
        html = '<div class="grid">'
        for r in sorted(items, key=lambda x: x['margin'], reverse=True):
            g = r['gpu']
            g_name = g.get('name', '')
            g_slug = slugify(g_name)
            html += f"""
<div class="item-card {r['css']}">
  <div class="item-name">{esc(g_name)}</div>
  <div class="item-detail">全長{g['_length_mm']:.0f}mm　マージン{r['margin']:.0f}mm　{r['badge']}</div>
  <a href="/compat/{esc(g_slug)}-vs-{esc(case_slug)}.html" style="color:#4f46e5;font-size:.85rem">詳細を見る →</a>
</div>"""
        html += '</div>'
        return html

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(case_name)}に入るGPU一覧（{len(ok_list)}件OK）</title>
<meta name="description" content="{esc(case_name)}（最大GPU長{case_max:.0f}mm）に搭載できるGPU一覧。OK {len(ok_list)}件、注意あり {len(warning_list)}件、NG {len(ng_list)}件。">
<script type="application/ld+json">{breadcrumb_ld}</script>
{_CSS}
</head>
<body>
<nav aria-label="breadcrumb" class="breadcrumb">
  <a href="/">ホーム</a>
  <span class="sep">&rsaquo;</span>
  <a href="/compat/index.html">GPU・ケース互換性一覧</a>
  <span class="sep">&rsaquo;</span>
  <span>{esc(case_name)}</span>
</nav>
<header>
  <a href="/compat/index.html">← GPU・ケース互換性一覧</a>
  <h1>{esc(case_name)}（最大{case_max:.0f}mm）対応GPU一覧</h1>
</header>
<div class="wrap">

  <div class="card">
    <p>{esc(case_name)}の最大GPU搭載長は <strong>{case_max:.0f}mm</strong> です。<br>
    OK: {len(ok_list)}件　⚠ 注意: {len(warning_list)}件　❌ NG: {len(ng_list)}件</p>
  </div>

  <p class="section-title">✅ 搭載可能なGPU（{len(ok_list)}件）</p>
  {render_items(ok_list)}

  <p class="section-title">⚠️ 注意あり（{len(warning_list)}件）</p>
  {render_items(warning_list)}

  <p class="section-title">❌ 搭載不可（{len(ng_list)}件）</p>
  {render_items(ng_list)}

  <div class="cta">
    <p>CPU・電源も含めてまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">複数パーツを一括診断する →</a></p>
  </div>

</div>
</body>
</html>"""


# ── ハブページ生成 ───────────────────────────────────────────

def _generate_hub_page(gpus: list, cases: list):
    """static/compat/index.html を生成する"""
    def item_li(name, url):
        return f'<li><a href="{esc(url)}">{esc(name)}</a></li>'

    gpu_items = ''.join(
        item_li(g.get('name', ''), f'/compat/gpu/{slugify(g.get("name",""))}.html')
        for g in sorted(gpus, key=lambda x: x.get('name', ''))
    )
    case_items = ''.join(
        item_li(c.get('name', ''), f'/compat/case/{slugify(c.get("name",""))}.html')
        for c in sorted(cases, key=lambda x: x.get('name', ''))
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PCパーツ互換性チェック一覧 | GPU×ケース対応表</title>
<meta name="description" content="GPU全{len(gpus)}種×PCケース全{len(cases)}種の互換性チェック結果一覧。RTX 4090・RX 9070などの最新GPUがどのケースに入るか数値で確認できます。">
{_CSS}
<style>
.grid{{columns:2;column-gap:24px}}
@media(min-width:640px){{.grid{{columns:3}}}}
@media(min-width:900px){{.grid{{columns:4}}}}
li{{list-style:none;margin-bottom:6px;break-inside:avoid}}
li a{{color:#4f46e5;text-decoration:none;font-size:.9rem}}
li a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<header>
  <a href="/">← PC互換チェッカー トップ</a>
  <h1>PCパーツ互換性チェック一覧</h1>
</header>
<div class="wrap">
  <div class="card">
    <p class="section-title">GPUから探す（{len(gpus)}種）</p>
    <ul class="grid">{gpu_items}</ul>
  </div>
  <div class="card">
    <p class="section-title">PCケースから探す（{len(cases)}種）</p>
    <ul class="grid">{case_items}</ul>
  </div>
  <div class="cta">
    <p>GPU・CPU・電源・ケースをまとめて互換性診断できます</p>
    <p style="margin-top:8px"><a href="/">チャットで一括診断する →</a></p>
  </div>
</div>
</body>
</html>"""

    out_path = os.path.join(_OUTPUT_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  → {out_path}')


# ── sitemap生成（分割） ─────────────────────────────────────

_SITEMAP_CHUNK = 50_000


def _generate_sitemap(gpus: list, cases: list, n_total: int):
    """sitemap-1.xml〜N.xml + sitemap-index.xml を生成する（50,000件/ファイル上限）"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    urls = [
        f'<url><loc>{_BASE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        f'<url><loc>{_BASE_URL}/compat/index.html</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
    ]

    # 個別ページ
    for gpu in gpus:
        g_slug = slugify(gpu.get('name', ''))
        for case in cases:
            c_slug = slugify(case.get('name', ''))
            urls.append(
                f'<url><loc>{_BASE_URL}/compat/{g_slug}-vs-{c_slug}.html</loc>'
                f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
            )

    # GPU別インデックス
    for gpu in gpus:
        g_slug = slugify(gpu.get('name', ''))
        urls.append(
            f'<url><loc>{_BASE_URL}/compat/gpu/{g_slug}.html</loc>'
            f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        )

    # ケース別インデックス
    for case in cases:
        c_slug = slugify(case.get('name', ''))
        urls.append(
            f'<url><loc>{_BASE_URL}/compat/case/{c_slug}.html</loc>'
            f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        )

    # チャンク分割してsitemap-N.xmlを生成
    chunks = [urls[i:i + _SITEMAP_CHUNK] for i in range(0, len(urls), _SITEMAP_CHUNK)]
    sitemap_files = []

    for i, chunk in enumerate(chunks, 1):
        sitemap_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + '\n'.join(chunk)
            + '\n</urlset>\n'
        )
        fname = f'sitemap-{i}.xml'
        out_path = os.path.join(_ROOT, 'static', fname)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(sitemap_xml)
        sitemap_files.append(fname)
        print(f'  → {out_path} ({len(chunk):,}件)')

    # sitemap-index.xml 生成
    index_entries = '\n'.join(
        f'  <sitemap><loc>{_BASE_URL}/{fname}</loc><lastmod>{today}</lastmod></sitemap>'
        for fname in sitemap_files
    )
    index_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + index_entries + '\n'
        + '</sitemapindex>\n'
    )
    index_path = os.path.join(_ROOT, 'static', 'sitemap-index.xml')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_xml)
    print(f'  → {index_path} ({len(sitemap_files)}ファイル参照)')

    # 旧 sitemap.xml を削除（存在する場合）
    old_path = os.path.join(_ROOT, 'static', 'sitemap.xml')
    if os.path.exists(old_path):
        os.remove(old_path)
        print(f'  → {old_path} 削除（分割ファイルに移行）')

    return sitemap_files


# ── メイン処理 ────────────────────────────────────────────────

def main():
    print('データ読み込み中...')
    gpus, cases = load_products()
    print(f'  GPU: {len(gpus)}件、ケース: {len(cases)}件')

    if not gpus or not cases:
        print('エラー: データが不足しています。スクレイパーを先に実行してください。')
        sys.exit(1)

    # 出力ディレクトリ作成
    os.makedirs(os.path.join(_OUTPUT_DIR, 'gpu'),  exist_ok=True)
    os.makedirs(os.path.join(_OUTPUT_DIR, 'case'), exist_ok=True)

    # 全組み合わせ計算
    print('ページ生成中...')
    n_individual = 0
    gpu_results  = {slugify(g.get('name', '')): [] for g in gpus}
    case_results = {slugify(c.get('name', '')): [] for c in cases}

    for gpu in gpus:
        g_slug = slugify(gpu.get('name', ''))
        for case in cases:
            c_slug  = slugify(case.get('name', ''))
            margin  = case['_max_gpu_mm'] - gpu['_length_mm']
            verdict, badge, css_class = calc_verdict(margin)

            # 個別ページ
            html = individual_page(gpu, case, margin, verdict, badge, css_class)
            out_path = os.path.join(_OUTPUT_DIR, f'{g_slug}-vs-{c_slug}.html')
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
            n_individual += 1

            # インデックス用データ蓄積
            gpu_results[g_slug].append({'case': case, 'margin': margin,
                                        'verdict': verdict, 'badge': badge, 'css': css_class})
            case_results[c_slug].append({'gpu': gpu, 'margin': margin,
                                         'verdict': verdict, 'badge': badge, 'css': css_class})

    # GPU別インデックスページ
    for gpu in gpus:
        g_slug = slugify(gpu.get('name', ''))
        html = gpu_index_page(gpu, gpu_results[g_slug])
        with open(os.path.join(_OUTPUT_DIR, 'gpu', f'{g_slug}.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    # ケース別インデックスページ
    for case in cases:
        c_slug = slugify(case.get('name', ''))
        html = case_index_page(case, case_results[c_slug])
        with open(os.path.join(_OUTPUT_DIR, 'case', f'{c_slug}.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    n_gpu_idx  = len(gpus)
    n_case_idx = len(cases)
    n_total    = n_individual + n_gpu_idx + n_case_idx

    # ハブページ（/compat/index.html）生成
    print('ハブページ生成中...')
    _generate_hub_page(gpus, cases)

    # sitemap 分割生成
    print('サイトマップ生成中（分割）...')
    sitemap_files = _generate_sitemap(gpus, cases, n_total)

    print(f'\n完了!')
    print(f'  個別ページ:           {n_individual:,}件')
    print(f'  GPU別インデックス:    {n_gpu_idx:,}件')
    print(f'  ケース別インデックス: {n_case_idx:,}件')
    print(f'  合計:                 {n_total:,}件')
    print(f'  サイトマップ:         {len(sitemap_files)}ファイル (sitemap-index.xml 含む)')
    print(f'\n出力先: {_OUTPUT_DIR}')
    print('\n次のステップ:')
    print(f'  git add static/compat/ static/sitemap-*.xml static/sitemap-index.xml')
    print(f'  git commit -m "feat: SEOページ再生成 {n_total}件 (パンくず+sitemap分割)"')
    print('  git push origin main')


if __name__ == '__main__':
    main()
