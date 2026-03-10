#!/usr/bin/env python3
"""Generate sitemap.xml and robots.txt for pc-compat-engine"""
import os
from datetime import datetime
from pathlib import Path

BASE_URL = os.getenv('SITE_URL', 'https://pc-compat-engine-production.up.railway.app')
OUTPUT_DIR = Path(__file__).parent.parent  # project root

def generate_sitemap():
    """Generate sitemap.xml"""
    game_dir = OUTPUT_DIR / "static" / "game"
    game_files = sorted(game_dir.glob("*.html"))
    
    now = datetime.now().strftime("%Y-%m-%d")
    
    urls = []
    # Top page
    urls.append(f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")
    
    # Game pages
    for game_file in game_files:
        game_name = game_file.stem
        urls.append(f"""  <url>
    <loc>{BASE_URL}/game/{game_name}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")
    
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""
    
    sitemap_path = OUTPUT_DIR / "sitemap.xml"
    sitemap_path.write_text(sitemap_content, encoding="utf-8")
    print(f"[OK] Generated sitemap.xml ({len(game_files) + 1} URLs)")
    return len(game_files) + 1

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
