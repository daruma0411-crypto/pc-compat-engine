#!/usr/bin/env python3
"""Generate sitemap.xml and robots.txt for pc-compat-engine"""
import os
from datetime import datetime
from pathlib import Path

BASE_URL = os.getenv('SITE_URL', 'https://pc-compat-engine-production.up.railway.app')
OUTPUT_DIR = Path(__file__).parent.parent  # project root

def generate_sitemap():
    """Generate sitemap.xml (ゲーム・ブログ・記事を含む)"""
    game_dir = OUTPUT_DIR / "static" / "game"
    blog_dir = OUTPUT_DIR / "static" / "blog"
    article_dir = OUTPUT_DIR / "static" / "article"
    
    game_files = sorted(game_dir.glob("*.html")) if game_dir.exists() else []
    blog_files = sorted(blog_dir.glob("*.html")) if blog_dir.exists() else []
    article_files = sorted(article_dir.glob("*.html")) if article_dir.exists() else []
    
    now = datetime.now().strftime("%Y-%m-%d")
    
    urls = []
    # Top page (最高優先度、毎日更新)
    urls.append(f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")
    
    # Blog index (高優先度、毎日更新)
    urls.append(f"""  <url>
    <loc>{BASE_URL}/blog/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")
    
    # Game pages (高優先度、週次更新)
    for game_file in game_files:
        game_name = game_file.stem
        urls.append(f"""  <url>
    <loc>{BASE_URL}/game/{game_name}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")
    
    # Blog posts (中優先度、月次更新)
    for blog_file in blog_files:
        if blog_file.name == 'generation_history.json':
            continue
        blog_name = blog_file.stem
        urls.append(f"""  <url>
    <loc>{BASE_URL}/blog/{blog_file.name}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>""")
    
    # Longtail articles (高優先度、週次更新)
    for article_file in article_files:
        article_name = article_file.stem
        urls.append(f"""  <url>
    <loc>{BASE_URL}/article/{article_file.name}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>""")
    
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""
    
    sitemap_path = OUTPUT_DIR / "sitemap.xml"
    sitemap_path.write_text(sitemap_content, encoding="utf-8")
    total_urls = 2 + len(game_files) + len(blog_files) + len(article_files)  # トップ + ブログindex + 各ページ
    print(f"[OK] Generated sitemap.xml")
    print(f"  - Game pages: {len(game_files)}")
    print(f"  - Blog posts: {len(blog_files)}")
    print(f"  - Articles: {len(article_files)}")
    print(f"  - Total URLs: {total_urls}")
    return total_urls

def generate_robots():
    """Generate robots.txt"""
    robots_content = """# Allow all crawlers including AI
User-agent: *
Allow: /

# AI Crawlers
User-agent: CCBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: GPTBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://pc-compat-engine-production.up.railway.app/sitemap.xml
"""
    
    robots_path = OUTPUT_DIR / "robots.txt"
    robots_path.write_text(robots_content, encoding="utf-8")
    print(f"[OK] Generated robots.txt")

if __name__ == "__main__":
    url_count = generate_sitemap()
    generate_robots()
    print(f"\n[SUCCESS] Sitemap and robots.txt generated!")
    print(f"Total URLs: {url_count}")
