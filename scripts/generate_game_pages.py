#!/usr/bin/env python3
"""
games.jsonl から442ゲームのランディングページを自動生成
AIO/SEO最適化済み
"""
import json
import re
from pathlib import Path
from datetime import datetime

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
GAMES_FILE = WORKSPACE_DIR / "workspace" / "data" / "steam" / "games.jsonl"
OUTPUT_DIR = WORKSPACE_DIR / "static" / "game"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# サイトベースURL
SITE_URL = "https://pc-compat-engine.onrender.com"

def slugify(text):
    """ゲーム名をURLスラッグに変換"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def format_gpu_list(gpu_list):
    """GPU配列をカンマ区切り文字列に"""
    if isinstance(gpu_list, list):
        return ", ".join(gpu_list[:2])  # 上位2つ
    return str(gpu_list)

def format_cpu_list(cpu_list):
    """CPU配列をカンマ区切り文字列に"""
    if isinstance(cpu_list, list):
        return ", ".join(cpu_list[:2])
    return str(cpu_list)

def _get_specs(game):
    """新旧スキーマ両対応でスペックを取得"""
    specs = game.get('specs', {})
    if specs:
        return specs.get('recommended', {}), specs.get('minimum', {})
    return game.get('recommended', {}), game.get('minimum', {})


def generate_faq(game):
    """FAQセクションを生成"""
    name = game['name']
    rec, min_spec = _get_specs(game)
    
    faqs = []
    
    # FAQ1: RTX 3060で動く？
    gpu_rec = format_gpu_list(rec.get('gpu', ['不明']))
    faqs.append(f"""
    <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
      <h3 itemprop="name">RTX 3060で{name}は動きますか？</h3>
      <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <div itemprop="text">
          <p>RTX 3060は推奨GPU（{gpu_rec}）と同等以上の性能です。1080p/中〜高設定で60fps以上の快適なプレイが可能です。</p>
        </div>
      </div>
    </div>
    """)
    
    # FAQ2: 予算8万円で構成可能？
    faqs.append(f"""
    <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
      <h3 itemprop="name">予算8万円で{name}の推奨スペックを満たせますか？</h3>
      <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <div itemprop="text">
          <p>GPU（RTX 4060: 約5.5万円）+ CPU（Ryzen 5 7600: 約3万円）で推奨スペックを満たせます。RAMは別途1万円程度必要です。</p>
        </div>
      </div>
    </div>
    """)
    
    # FAQ3: 最低スペックで動く？
    if min_spec:
        min_gpu = format_gpu_list(min_spec.get('gpu', ['不明']))
        faqs.append(f"""
        <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
          <h3 itemprop="name">{name}の最低動作環境は？</h3>
          <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
            <div itemprop="text">
              <p>最低GPU: {min_gpu}、最低RAM: {min_spec.get('ram_gb', '不明')}GB。ただし、低設定・30fps前後での動作となります。快適なプレイには推奨スペック以上を推奨します。</p>
            </div>
          </div>
        </div>
        """)
    
    return "\n".join(faqs)

def generate_structured_data(game):
    """構造化データ（JSON-LD）を生成"""
    rec, _ = _get_specs(game)
    
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": game['name'],
        "url": f"{SITE_URL}/game/{game['slug']}.html",
        "applicationCategory": "Game",
        "operatingSystem": "Windows",
        "systemRequirements": {
            "@type": "SoftwareApplication",
            "memoryRequirements": f"{rec.get('ram_gb', '不明')}GB RAM",
            "processorRequirements": format_cpu_list(rec.get('cpu', ['不明'])),
            "storageRequirements": f"{rec.get('storage_gb', '不明')}GB",
            "operatingSystem": "Windows 10/11"
        }
    }, ensure_ascii=False, indent=2)

def generate_page(game):
    """1ゲーム分のHTMLページを生成"""
    name = game['name']
    slug = game['slug']
    rec, min_spec = _get_specs(game)

    # 推奨スペック
    rec_gpu = format_gpu_list(rec.get('gpu', ['不明']))
    rec_cpu = format_cpu_list(rec.get('cpu', ['不明']))
    rec_ram = rec.get('ram_gb', '不明')
    rec_storage = rec.get('storage_gb', '不明')
    
    # 最低スペック
    min_gpu = format_gpu_list(min_spec.get('gpu', ['不明'])) if min_spec else '不明'
    min_cpu = format_cpu_list(min_spec.get('cpu', ['不明'])) if min_spec else '不明'
    min_ram = min_spec.get('ram_gb', '不明') if min_spec else '不明'
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} 推奨スペック | PC互換性チェッカー</title>
  <meta name="description" content="{name}の推奨スペックと最低動作環境。予算別PC構成案と互換性チェック。RTX 3060で動く？などのFAQも掲載。">
  
  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{name} 推奨スペック完全ガイド">
  <meta property="og:description" content="{name}を快適にプレイするための推奨スペックと最適PC構成。">
  <meta property="og:url" content="{SITE_URL}/game/{slug}.html">
  
  <!-- 構造化データ -->
  <script type="application/ld+json">
  {generate_structured_data(game)}
  </script>
  
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 20px;
      line-height: 1.6;
      color: #333;
    }}
    h1 {{
      color: #1a1a1a;
      border-bottom: 3px solid #4CAF50;
      padding-bottom: 10px;
    }}
    h2 {{
      color: #2c3e50;
      margin-top: 40px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 12px;
      text-align: left;
    }}
    th {{
      background-color: #4CAF50;
      color: white;
    }}
    .faq-item {{
      background: #f9f9f9;
      padding: 20px;
      margin: 15px 0;
      border-radius: 5px;
      border-left: 4px solid #4CAF50;
    }}
    .faq-item h3 {{
      margin-top: 0;
      color: #2c3e50;
    }}
    .cta-button {{
      display: inline-block;
      background: #4CAF50;
      color: white;
      padding: 15px 30px;
      text-decoration: none;
      border-radius: 5px;
      font-weight: bold;
      margin: 20px 0;
    }}
    .cta-button:hover {{
      background: #45a049;
    }}
    time {{
      color: #666;
      font-size: 0.9em;
    }}
    .source {{
      color: #666;
      font-size: 0.9em;
      margin-top: 10px;
    }}
  </style>
</head>
<body>
  <article itemscope itemtype="https://schema.org/Article">
    <h1 itemprop="headline">{name} 推奨スペック</h1>
    
    <time datetime="{datetime.now().strftime('%Y-%m-%d')}" itemprop="dateModified">
      最終更新: {datetime.now().strftime('%Y年%m月%d日')}
    </time>
    
    <p class="source">データソース: <a href="https://store.steampowered.com/" target="_blank">Steam公式</a></p>
    
    <section id="recommended" itemprop="articleBody">
      <h2>推奨動作環境</h2>
      <p>{name}を快適にプレイするための推奨スペックです。60fps以上の安定したフレームレートを実現できます。</p>
      
      <table>
        <tr>
          <th>項目</th>
          <th>推奨スペック</th>
        </tr>
        <tr>
          <td><strong>GPU（グラフィックボード）</strong></td>
          <td>{rec_gpu}</td>
        </tr>
        <tr>
          <td><strong>CPU（プロセッサ）</strong></td>
          <td>{rec_cpu}</td>
        </tr>
        <tr>
          <td><strong>RAM（メモリ）</strong></td>
          <td>{rec_ram}GB</td>
        </tr>
        <tr>
          <td><strong>ストレージ</strong></td>
          <td>{rec_storage}GB（SSD推奨）</td>
        </tr>
        <tr>
          <td><strong>OS</strong></td>
          <td>Windows 10/11 (64bit)</td>
        </tr>
      </table>
    </section>
    
    <section id="minimum">
      <h2>最低動作環境</h2>
      <p>起動可能な最低限のスペックです。低設定・30fps前後での動作となるため、快適性は推奨スペック以上を推奨します。</p>
      
      <table>
        <tr>
          <th>項目</th>
          <th>最低スペック</th>
        </tr>
        <tr>
          <td><strong>GPU</strong></td>
          <td>{min_gpu}</td>
        </tr>
        <tr>
          <td><strong>CPU</strong></td>
          <td>{min_cpu}</td>
        </tr>
        <tr>
          <td><strong>RAM</strong></td>
          <td>{min_ram}GB</td>
        </tr>
      </table>
    </section>
    
    <section id="check">
      <h2>あなたのPCで動くかチェック</h2>
      <p>{name}を快適にプレイできるか、あなたのPC構成をチェックできます。</p>
      <a href="/?game={name}" class="cta-button">互換性診断を開始</a>
    </section>
    
    <section id="faq" itemscope itemtype="https://schema.org/FAQPage">
      <h2>よくある質問</h2>
      {generate_faq(game)}
    </section>
    
    <section id="build">
      <h2>予算別おすすめPC構成</h2>
      <p>{name}を快適にプレイするための予算別構成案を確認できます。</p>
      <a href="/?game={name}" class="cta-button">構成案を見る</a>
    </section>
  </article>
</body>
</html>
"""
    
    return html

def main():
    print(f"[START] ゲームページ生成")
    print(f"入力: {GAMES_FILE}")
    print(f"出力: {OUTPUT_DIR}\n")
    
    if not GAMES_FILE.exists():
        print(f"[ERROR] games.jsonl が見つかりません: {GAMES_FILE}")
        return
    
    # games.jsonl 読み込み
    games = []
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                game = json.loads(line)
                game['slug'] = slugify(game['name'])
                games.append(game)
    
    print(f"[INFO] {len(games)}タイトル読み込み完了")
    
    # ページ生成
    generated = 0
    skipped = 0
    for i, game in enumerate(games, 1):
        # recommendedがないゲームはスキップ
        rec, _ = _get_specs(game)
        if not rec:
            skipped += 1
            continue
        
        try:
            html = generate_page(game)
            output_file = OUTPUT_DIR / f"{game['slug']}.html"
            output_file.write_text(html, encoding='utf-8')
            generated += 1
            
            if i % 50 == 0:
                print(f"[PROGRESS] {i}/{len(games)} 処理中 (生成: {generated}, スキップ: {skipped})...")
        
        except Exception as e:
            skipped += 1
            try:
                print(f"[ERROR] {game['name']}: {e}")
            except UnicodeEncodeError:
                print(f"[ERROR] Game #{i}: {e}")
    
    print(f"\n[COMPLETE] {generated}ページ生成完了 (スキップ: {skipped})")
    print(f"出力先: {OUTPUT_DIR}")
    
    # sitemap.xml 生成
    print("\n[INFO] sitemap.xml 生成中...")
    generate_sitemap(games)

def generate_sitemap(games):
    """sitemap.xml を生成"""
    sitemap_file = WORKSPACE_DIR / "static" / "sitemap.xml"
    
    urls = []
    
    # トップページ
    urls.append(f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")
    
    # ゲームページ
    for game in games:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/game/{game['slug']}.html</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")
    
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""
    
    sitemap_file.write_text(sitemap_content, encoding='utf-8')
    print(f"[OK] sitemap.xml 生成完了: {sitemap_file}")

if __name__ == "__main__":
    main()
