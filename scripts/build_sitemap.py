#!/usr/bin/env python3
"""sitemap.xml を作り直すための道具。

Google に見せるページだけを並べる。
自動生成した組み合わせページ（/compat/ の下、16万ページ）は入れない。
中身の薄いページを大量に出すと、サイト全体の評価が下がるため。

使い方:
    python scripts/build_sitemap.py
ルートの sitemap.xml を上書きする。
"""
import os
import re
from datetime import date

BASE = 'https://pc-jisaku.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, 'static')

# 日付つきのブログ名（20260304-... の形）から日付を取り出す
BLOG_DATE = re.compile(r'^(\d{4})(\d{2})(\d{2})-')


def html_slugs(subdir):
    """static/<subdir>/ の中の .html を名前順で返す（index.html は除く）"""
    d = os.path.join(STATIC, subdir)
    if not os.path.isdir(d):
        return []
    names = [f[:-5] for f in os.listdir(d)
             if f.endswith('.html') and f != 'index.html']
    return sorted(names)


def build_urls():
    """(URL, 更新日, 更新のめやす, 優先度) の一覧を作る"""
    today = date.today().isoformat()
    urls = [
        (f'{BASE}/', today, 'daily', '1.0'),
        (f'{BASE}/guide', today, 'monthly', '0.7'),
        (f'{BASE}/genre/', today, 'weekly', '0.8'),
        (f'{BASE}/blog/', today, 'daily', '0.8'),
        (f'{BASE}/about', None, 'yearly', '0.3'),
        (f'{BASE}/privacy', None, 'yearly', '0.2'),
    ]

    # ジャンル別のまとめページ
    for slug in html_slugs('genre'):
        urls.append((f'{BASE}/genre/{slug}', None, 'weekly', '0.7'))

    # ガイド記事
    for slug in html_slugs('guide'):
        urls.append((f'{BASE}/guide/{slug}', None, 'monthly', '0.6'))
    for slug in html_slugs('guides'):
        urls.append((f'{BASE}/guides/{slug}.html', None, 'monthly', '0.6'))

    # GPU別のゲーム一覧記事
    for slug in html_slugs('article'):
        urls.append((f'{BASE}/article/{slug}', None, 'monthly', '0.6'))

    # 予算別の構成例
    for slug in html_slugs('builds'):
        urls.append((f'{BASE}/builds/{slug}.html', None, 'monthly', '0.6'))

    # ブログ記事（名前の先頭の数字を更新日として使う）
    for slug in html_slugs('blog'):
        m = BLOG_DATE.match(slug)
        lastmod = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None
        urls.append((f'{BASE}/blog/{slug}', lastmod, 'monthly', '0.7'))

    return urls


def to_xml(urls):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, changefreq, priority in urls:
        lines.append('  <url>')
        lines.append(f'    <loc>{loc}</loc>')
        if lastmod:
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append(f'    <changefreq>{changefreq}</changefreq>')
        lines.append(f'    <priority>{priority}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


def main():
    urls = build_urls()
    out = os.path.join(ROOT, 'sitemap.xml')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(to_xml(urls))
    print(f'{out} を作り直した。ページ数: {len(urls)}')


if __name__ == '__main__':
    main()
