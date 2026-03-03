#!/usr/bin/env python3
"""
games.jsonl から全ゲームのランディングページを自動生成
AIO/SEO最適化済み - Phase 1 (2026-03-03)
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

# サイトベースURL（Railway本番環境）
SITE_URL = "https://pc-compat-engine-production.up.railway.app"

# Google Analytics ID
GA_ID = "G-PPNEBG625J"

# 予算別PC構成（固定値）
BUDGET_BUILDS = {
    "minimum": {
        "label": "8万円（最低動作）",
        "icon": "💵",
        "cpu": "Ryzen 5 5600",
        "cpu_price": 14980,
        "gpu": "RTX 3060",
        "gpu_price": 29800,
        "ram": "16GB DDR4",
        "ram_price": 5980,
        "storage": "500GB SSD",
        "storage_price": 5480,
        "other": 22000,
        "performance": "1080p 低〜中設定 30〜60fps",
        "color": "#607D8B",
    },
    "recommended": {
        "label": "12万円（推奨動作）",
        "icon": "💳",
        "cpu": "Ryzen 5 7600",
        "cpu_price": 25000,
        "gpu": "RTX 4060",
        "gpu_price": 45800,
        "ram": "16GB DDR5",
        "ram_price": 7980,
        "storage": "1TB NVMe SSD",
        "storage_price": 7480,
        "other": 26000,
        "performance": "1080p 高設定 60〜100fps / WQHD 中設定 60fps",
        "color": "#4CAF50",
        "badge": "おすすめ",
    },
    "premium": {
        "label": "18万円（快適動作）",
        "icon": "💎",
        "cpu": "Ryzen 7 7700",
        "cpu_price": 38000,
        "gpu": "RTX 4070",
        "gpu_price": 82800,
        "ram": "32GB DDR5",
        "ram_price": 13980,
        "storage": "1TB NVMe SSD",
        "storage_price": 7480,
        "other": 30000,
        "performance": "WQHD 高設定 100〜144fps / 4K 中設定 60fps",
        "color": "#FF9800",
    },
}

# GPU性能比較テーブル（固定値・一般的なゲームの目安）
GPU_COMPARISON = [
    {"name": "RTX 3060", "price": 29800, "fps_1080p": 70, "fps_wqhd": 45, "fps_4k": 27, "rating": 3},
    {"name": "RTX 4060", "price": 45800, "fps_1080p": 100, "fps_wqhd": 65, "fps_4k": 40, "rating": 4, "recommended": True},
    {"name": "RTX 4070", "price": 82800, "fps_1080p": 140, "fps_wqhd": 95, "fps_4k": 58, "rating": 4},
    {"name": "RTX 5070", "price": 102800, "fps_1080p": 170, "fps_wqhd": 120, "fps_4k": 72, "rating": 5},
    {"name": "RTX 5080", "price": 209800, "fps_1080p": 240, "fps_wqhd": 165, "fps_4k": 100, "rating": 5},
]


def slugify(text):
    """ゲーム名をURLスラッグに変換"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def format_spec_list(items):
    """スペックリストを文字列に変換"""
    if not items:
        return "情報なし"
    if isinstance(items, list):
        return " / ".join(str(x) for x in items[:2])
    return str(items)


def _get_specs(game):
    """新旧スキーマ両対応でスペックを取得"""
    specs = game.get('specs', {})
    if specs:
        return specs.get('recommended', {}), specs.get('minimum', {})
    return game.get('recommended', {}), game.get('minimum', {})


def calc_total(build):
    return build["cpu_price"] + build["gpu_price"] + build["ram_price"] + build["storage_price"] + build["other"]


def generate_budget_section(name):
    """予算別PC構成セクションを生成"""
    cards = []
    for key, b in BUDGET_BUILDS.items():
        total = calc_total(b)
        badge_html = f'<div class="budget-badge" style="background:{b["color"]};">{b["badge"]}</div>' if b.get("badge") else ""
        cards.append(f"""
    <div class="budget-card" style="border-color:{b['color']};">
      {badge_html}
      <h3>{b['icon']} {b['label']}</h3>
      <div class="build-specs">
        <div class="spec-item"><span class="spec-label">GPU:</span><span class="spec-value">{b['gpu']}</span><span class="spec-price">¥{b['gpu_price']:,}</span></div>
        <div class="spec-item"><span class="spec-label">CPU:</span><span class="spec-value">{b['cpu']}</span><span class="spec-price">¥{b['cpu_price']:,}</span></div>
        <div class="spec-item"><span class="spec-label">RAM:</span><span class="spec-value">{b['ram']}</span><span class="spec-price">¥{b['ram_price']:,}</span></div>
        <div class="spec-item"><span class="spec-label">SSD:</span><span class="spec-value">{b['storage']}</span><span class="spec-price">¥{b['storage_price']:,}</span></div>
        <div class="spec-item"><span class="spec-label">他:</span><span class="spec-value">MB・PSU・ケース等</span><span class="spec-price">¥{b['other']:,}</span></div>
      </div>
      <div class="build-total">合計 約¥{total:,}</div>
      <div class="build-perf">🎮 {b['performance']}</div>
      <a href="/?game={name}" class="btn-check">AIに構成を相談する →</a>
    </div>""")

    return f"""
<section id="budget-builds" class="seo-section">
  <h2>💰 予算別おすすめPC構成</h2>
  <p>{name}を快適にプレイできるPC構成を予算別に紹介します。価格はすべて目安です。</p>
  <div class="budget-cards">
    {''.join(cards)}
  </div>
  <p class="section-note">※ パーツ価格は変動します。AIに相談するとリアルタイムの価格でPC構成を提案します。</p>
</section>"""


def generate_gpu_section(name):
    """GPU比較テーブルセクションを生成"""
    rows = []
    for g in GPU_COMPARISON:
        stars = "★" * g["rating"] + "☆" * (5 - g["rating"])
        rec_class = ' class="gpu-rec-row"' if g.get("recommended") else ""
        rec_badge = ' <span class="rec-badge">おすすめ</span>' if g.get("recommended") else ""
        rows.append(f"""        <tr{rec_class}>
          <td><strong>{g['name']}</strong>{rec_badge}</td>
          <td>¥{g['price']:,}</td>
          <td>{g['fps_1080p']}fps</td>
          <td>{g['fps_wqhd']}fps</td>
          <td>{g['fps_4k']}fps</td>
          <td>{stars}</td>
        </tr>""")

    return f"""
<section id="gpu-comparison" class="seo-section">
  <h2>🎮 GPU別性能比較</h2>
  <p>{name}における主要GPUの性能比較です。FPS値は1080p高設定でのおおよその目安です。</p>
  <div class="table-scroll">
    <table class="gpu-table">
      <thead>
        <tr>
          <th>GPU</th>
          <th>価格（目安）</th>
          <th>1080p</th>
          <th>WQHD</th>
          <th>4K</th>
          <th>推奨度</th>
        </tr>
      </thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
  <div class="gpu-tips">
    <p><strong>💡 選び方ポイント:</strong></p>
    <ul>
      <li><strong>60fps安定:</strong> RTX 4060 以上を推奨</li>
      <li><strong>144fps以上:</strong> RTX 4070 以上を推奨</li>
      <li><strong>4K環境:</strong> RTX 5080 以上を推奨</li>
    </ul>
  </div>
</section>"""


def generate_faq_section(name, rec_gpu, min_gpu, rec_cpu, rec_ram):
    """FAQ セクション（6問）を生成"""
    faqs = [
        {
            "q": f"{name}の推奨スペックは？",
            "a": f"{name}の推奨スペックは、GPU: {rec_gpu}、CPU: {rec_cpu}、RAM: {rec_ram}GB です。上記スペックを満たすPCなら60fps以上で快適にプレイできます。",
        },
        {
            "q": f"予算10万円で{name}用PCは組める？",
            "a": f"はい、予算10万円前後で{name}用のPCを組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.5万円）+ 16GB RAM（約0.8万円）の構成で1080p 60fps以上が可能です。",
        },
        {
            "q": f"{name}は何fpsで遊べますか？",
            "a": f"最低スペック（{min_gpu}相当）で30〜60fps、推奨スペック（{rec_gpu}相当）で60〜90fps、RTX 4060で100〜144fps以上が期待できます。上のGPU比較表も参考にしてください。",
        },
        {
            "q": "ノートPCでも動きますか？",
            "a": "ゲーミングノートPCでも動作します。RTX 4060搭載モデル（12万円〜）なら1080p 60fps以上で快適にプレイ可能です。バッテリー駆動時は性能が低下するため、電源接続を推奨します。",
        },
        {
            "q": "内蔵GPU（グラボなし）でも遊べますか？",
            "a": f"内蔵GPU（Intel Iris Xe、AMD Radeon 780M等）では低設定・30fps前後になります。快適にプレイするには専用グラフィックボード（最低{min_gpu}以上）が必須です。",
        },
        {
            "q": f"{name}が重い・カクつく場合の対処法は？",
            "a": "①グラフィック設定を「低」に変更、②解像度を1080pに下げる、③バックグラウンドアプリを終了、④グラフィックドライバーを最新版に更新、⑤垂直同期をオフ — を順番に試してください。",
        },
    ]

    items = []
    for faq in faqs:
        items.append(f"""    <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
      <h3 class="faq-q" itemprop="name">{faq['q']}</h3>
      <div class="faq-a" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
        <p itemprop="text">{faq['a']}</p>
      </div>
    </div>""")

    return f"""
<section id="faq" class="seo-section" itemscope itemtype="https://schema.org/FAQPage">
  <h2>❓ よくある質問</h2>
{''.join(items)}
</section>"""


def generate_faq_schema(name, rec_gpu, min_gpu, rec_cpu, rec_ram):
    """FAQPage Schema.org（JSON-LD）を生成"""
    faqs = [
        {
            "q": f"{name}の推奨スペックは？",
            "a": f"{name}の推奨スペックは、GPU: {rec_gpu}、CPU: {rec_cpu}、RAM: {rec_ram}GB です。",
        },
        {
            "q": f"予算10万円で{name}用PCは組める？",
            "a": f"はい、RTX 4060 + Ryzen 5 7600 + 16GB RAM の構成（約10万円）で1080p 60fps以上が可能です。",
        },
        {
            "q": f"{name}は何fpsで遊べますか？",
            "a": f"推奨スペック（{rec_gpu}相当）で60〜90fps、RTX 4060で100〜144fpsが期待できます。",
        },
        {
            "q": "ノートPCでも動きますか？",
            "a": "RTX 4060搭載ゲーミングノートなら1080p 60fps以上で快適にプレイ可能です。",
        },
        {
            "q": "内蔵GPU（グラボなし）でも遊べますか？",
            "a": f"内蔵GPUでは低設定・30fps前後になります。快適なプレイには専用グラフィックボード（最低{min_gpu}以上）が必要です。",
        },
        {
            "q": f"{name}が重い・カクつく場合の対処法は？",
            "a": "グラフィック設定を低に変更、解像度を1080pに下げる、バックグラウンドアプリを終了、グラフィックドライバーを最新版に更新してください。",
        },
    ]
    entities = []
    for faq in faqs:
        entities.append({
            "@type": "Question",
            "name": faq["q"],
            "acceptedAnswer": {"@type": "Answer", "text": faq["a"]},
        })
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities},
                      ensure_ascii=False, indent=2)


def generate_troubleshooting_section():
    """トラブルシューティングセクションを生成"""
    return """
<section id="troubleshooting" class="seo-section">
  <h2>🔧 よくあるトラブルと解決策</h2>
  <div class="trouble-grid">
    <div class="trouble-card">
      <h3>⚠️ カクつく・重い場合</h3>
      <ol>
        <li>グラフィック設定を「低」に変更</li>
        <li>解像度を1080pに下げる</li>
        <li>バックグラウンドアプリを終了（Chrome・Discord等）</li>
        <li>グラフィックドライバーを最新版に更新</li>
        <li>垂直同期（VSync）をオフにする</li>
      </ol>
      <p class="trouble-tip">💡 改善しない場合は上の<a href="#gpu-comparison">GPU比較表</a>でアップグレードを検討</p>
    </div>
    <div class="trouble-card">
      <h3>🚫 動かない・起動しない場合</h3>
      <ol>
        <li>最低スペックを満たしているか<a href="#minimum">確認</a></li>
        <li>DirectXを最新版に更新</li>
        <li>Visual C++再頒布可能パッケージをインストール</li>
        <li>ゲームファイルの整合性チェック（Steam→右クリック→ローカルファイル→整合性確認）</li>
        <li>セキュリティソフトの除外設定に追加</li>
      </ol>
    </div>
    <div class="trouble-card">
      <h3>📉 FPSが出ない場合</h3>
      <ol>
        <li>フレームレート制限を解除（ゲーム設定）</li>
        <li>NVIDIAコントロールパネルで「最大パフォーマンス」に設定</li>
        <li>電源オプションを「高パフォーマンス」に変更</li>
        <li>Windowsゲームモードをオン</li>
        <li>バックグラウンド録画機能をオフ（GeForce Experience・Xbox Game Bar）</li>
      </ol>
    </div>
    <div class="trouble-card">
      <h3>🖥️ ノートPCで動かない場合</h3>
      <ol>
        <li>電源接続してプレイ（バッテリー駆動だと性能制限）</li>
        <li>専用GPU（NVIDIA/AMD）を使用しているか確認</li>
        <li>NVIDIAコントロールパネル→3D設定→優先GPU→高性能プロセッサ</li>
        <li>冷却パッドを使用（熱によるサーマルスロットリング回避）</li>
      </ol>
    </div>
  </div>
</section>"""


def generate_page_css():
    """ゲームページ用CSS"""
    return """
    /* ベース */
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 960px;
      margin: 0 auto;
      padding: 16px;
      line-height: 1.6;
      color: #333;
      background: #fafafa;
    }
    a { color: #4CAF50; }
    h1 { color: #1a1a1a; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
    h2 { color: #2c3e50; margin-top: 40px; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    time { color: #666; font-size: 0.9em; }
    .source { color: #666; font-size: 0.9em; margin-top: 10px; }

    /* ナビ */
    .site-nav { background: #1a1a1a; padding: 10px 16px; margin: -16px -16px 20px; display: flex; align-items: center; gap: 16px; }
    .site-nav a { color: #78FFCB; text-decoration: none; font-size: 14px; }
    .site-nav a:hover { text-decoration: underline; }
    .site-nav .nav-logo { font-weight: bold; font-size: 16px; }

    /* CTAボタン */
    .cta-button {
      display: inline-block;
      background: #4CAF50;
      color: white !important;
      padding: 14px 28px;
      text-decoration: none;
      border-radius: 6px;
      font-weight: bold;
      margin: 20px 0;
      font-size: 15px;
    }
    .cta-button:hover { background: #45a049; }

    /* SEOセクション共通 */
    .seo-section { margin: 40px 0; padding: 24px; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .seo-section h2 { margin-top: 0; }
    .section-note { color: #777; font-size: 13px; margin-top: 12px; }

    /* 予算カード */
    .budget-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin: 20px 0; }
    .budget-card { border: 2px solid #e0e0e0; border-radius: 10px; padding: 18px; background: #fff; position: relative; transition: transform 0.2s, box-shadow 0.2s; }
    .budget-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
    .budget-badge { position: absolute; top: -12px; right: 16px; color: white; padding: 3px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
    .budget-card h3 { margin: 0 0 12px; font-size: 16px; }
    .build-specs { margin: 12px 0; }
    .spec-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; gap: 4px; }
    .spec-label { font-weight: 600; color: #555; min-width: 36px; }
    .spec-value { flex: 1; padding: 0 8px; }
    .spec-price { color: #1976D2; font-weight: 600; white-space: nowrap; }
    .build-total { margin-top: 12px; padding: 10px; background: #f5f5f5; border-radius: 6px; text-align: center; font-size: 17px; font-weight: bold; }
    .build-perf { margin-top: 8px; padding: 8px; background: #e3f2fd; border-radius: 6px; text-align: center; color: #1565C0; font-size: 12px; }
    .btn-check { display: block; width: 100%; margin-top: 12px; padding: 10px; background: #4CAF50; color: white; text-align: center; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px; }
    .btn-check:hover { background: #45a049; }

    /* GPU比較表 */
    .table-scroll { overflow-x: auto; }
    .gpu-table { min-width: 520px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .gpu-table th { background: #2196F3; }
    .gpu-rec-row { background: #f0f9f0; }
    .rec-badge { background: #4CAF50; color: white; font-size: 11px; padding: 2px 6px; border-radius: 10px; margin-left: 6px; vertical-align: middle; }
    .gpu-tips { margin-top: 16px; padding: 14px 16px; background: #fffde7; border-left: 4px solid #FFC107; border-radius: 4px; }
    .gpu-tips ul { margin: 8px 0 0 20px; }
    .gpu-tips li { margin-bottom: 4px; }

    /* FAQ */
    .faq-item { border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; margin-bottom: 14px; }
    .faq-q { background: #f5f5f5; padding: 14px 16px; margin: 0; font-size: 15px; color: #333; }
    .faq-a { padding: 14px 16px; background: white; }
    .faq-a p { margin: 0; }

    /* トラブルシューティング */
    .trouble-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 16px; }
    .trouble-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; background: white; }
    .trouble-card h3 { color: #c62828; margin-top: 0; font-size: 15px; }
    .trouble-card ol { padding-left: 20px; line-height: 1.8; font-size: 13px; margin: 8px 0; }
    .trouble-tip { margin-top: 10px; padding: 8px 10px; background: #e8f5e9; border-radius: 4px; font-size: 13px; }

    /* フッター */
    .page-footer { margin-top: 40px; padding: 20px 0; border-top: 1px solid #e0e0e0; text-align: center; font-size: 13px; color: #777; }
    .page-footer a { color: #4CAF50; margin: 0 8px; }

    /* レスポンシブ */
    @media (max-width: 600px) {
      .budget-cards { grid-template-columns: 1fr; }
      .trouble-grid { grid-template-columns: 1fr; }
      .spec-item { flex-wrap: wrap; }
    }"""


def generate_structured_data(game, slug):
    """VideoGame 構造化データ（JSON-LD）を生成"""
    rec, _ = _get_specs(game)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "VideoGame",
        "name": game['name'],
        "url": f"{SITE_URL}/game/{slug}",
        "applicationCategory": "Game",
        "operatingSystem": "Windows",
        "systemRequirements": {
            "@type": "SoftwareApplication",
            "memoryRequirements": f"{rec.get('ram_gb', '不明')}GB RAM",
            "processorRequirements": format_spec_list(rec.get('cpu', ['不明'])),
            "storageRequirements": f"{rec.get('storage_gb', '不明')}GB",
            "graphicsRequirements": format_spec_list(rec.get('gpu', ['不明'])),
            "operatingSystem": "Windows 10/11"
        }
    }, ensure_ascii=False, indent=2)


def generate_page(game):
    """1ゲーム分のHTMLページを生成"""
    name = game['name']
    slug = game['slug']
    rec, min_spec = _get_specs(game)

    rec_gpu = format_spec_list(rec.get('gpu', ['不明']))
    rec_cpu = format_spec_list(rec.get('cpu', ['不明']))
    rec_ram = rec.get('ram_gb', '不明')
    rec_storage = rec.get('storage_gb', '不明')

    min_gpu = format_spec_list(min_spec.get('gpu', ['不明'])) if min_spec else '不明'
    min_cpu = format_spec_list(min_spec.get('cpu', ['不明'])) if min_spec else '不明'
    min_ram = min_spec.get('ram_gb', '不明') if min_spec else '不明'

    today = datetime.now().strftime('%Y-%m-%d')
    today_ja = datetime.now().strftime('%Y年%m月%d日')

    faq_schema = generate_faq_schema(name, rec_gpu, min_gpu, rec_cpu, rec_ram)
    video_game_schema = generate_structured_data(game, slug)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_ID}');
  </script>

  <title>{name} 推奨スペック・必要動作環境 | PC互換チェッカー</title>
  <meta name="description" content="{name}の推奨スペックと最低動作環境。予算別PC構成案（8万・12万・18万）、GPU性能比較、よくある質問も掲載。RTX 4060で何fpsでる？などのFAQに回答。">

  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="{name} 推奨スペック完全ガイド | PC互換チェッカー">
  <meta property="og:description" content="{name}を快適にプレイするための推奨スペックと最適PC構成。予算8万〜18万の3パターンを紹介。">
  <meta property="og:url" content="{SITE_URL}/game/{slug}">
  <meta property="og:site_name" content="PC互換チェッカー">

  <!-- 構造化データ: VideoGame -->
  <script type="application/ld+json">
  {video_game_schema}
  </script>

  <!-- 構造化データ: FAQPage -->
  <script type="application/ld+json">
  {faq_schema}
  </script>

  <style>
{generate_page_css()}
  </style>
</head>
<body>

<!-- ナビゲーション -->
<nav class="site-nav">
  <a href="{SITE_URL}/" class="nav-logo">🖥️ PC互換チェッカー</a>
  <a href="{SITE_URL}/guide">ガイド</a>
  <a href="{SITE_URL}/about">運営者情報</a>
</nav>

<article itemscope itemtype="https://schema.org/Article">
  <h1 itemprop="headline">{name} 推奨スペック・必要動作環境</h1>

  <time datetime="{today}" itemprop="dateModified">最終更新: {today_ja}</time>
  <p class="source">データソース: <a href="https://store.steampowered.com/" target="_blank" rel="noopener">Steam公式</a></p>

  <section id="recommended" itemprop="articleBody">
    <h2>推奨動作環境</h2>
    <p>{name}を快適にプレイするための推奨スペックです。60fps以上の安定したフレームレートを実現できます。</p>

    <table>
      <tr><th>項目</th><th>推奨スペック</th></tr>
      <tr><td><strong>GPU（グラフィックボード）</strong></td><td>{rec_gpu}</td></tr>
      <tr><td><strong>CPU（プロセッサ）</strong></td><td>{rec_cpu}</td></tr>
      <tr><td><strong>RAM（メモリ）</strong></td><td>{rec_ram}GB</td></tr>
      <tr><td><strong>ストレージ</strong></td><td>{rec_storage}GB（SSD推奨）</td></tr>
      <tr><td><strong>OS</strong></td><td>Windows 10/11 (64bit)</td></tr>
    </table>
  </section>

  <section id="minimum">
    <h2>最低動作環境</h2>
    <p>起動可能な最低限のスペックです。低設定・30fps前後での動作となるため、快適性は推奨スペック以上を推奨します。</p>

    <table>
      <tr><th>項目</th><th>最低スペック</th></tr>
      <tr><td><strong>GPU</strong></td><td>{min_gpu}</td></tr>
      <tr><td><strong>CPU</strong></td><td>{min_cpu}</td></tr>
      <tr><td><strong>RAM</strong></td><td>{min_ram}GB</td></tr>
    </table>
  </section>

  <section id="check">
    <h2>あなたのPCで{name}は動く？</h2>
    <p>AIショップ店員が、あなたの予算・ゲーム・用途に合わせた最適なPC構成を無料で提案します。</p>
    <a href="{SITE_URL}/?game={name}" class="cta-button">無料でAI診断を受ける →</a>
  </section>

  {generate_budget_section(name)}

  {generate_gpu_section(name)}

  {generate_faq_section(name, rec_gpu, min_gpu, rec_cpu, rec_ram)}

  {generate_troubleshooting_section()}

  <section style="text-align:center; margin-top: 40px; padding: 24px; background: #1a1a1a; border-radius: 8px;">
    <p style="color: #78FFCB; font-size: 18px; font-weight: bold; margin: 0 0 12px;">🖥️ {name}用PCを今すぐ相談する</p>
    <p style="color: #aaa; margin: 0 0 16px; font-size: 14px;">14,000件のパーツデータ × AIショップ店員が最適構成を提案</p>
    <a href="{SITE_URL}/?game={name}" class="cta-button">無料でAI診断を受ける →</a>
  </section>

</article>

<footer class="page-footer">
  <p>
    <a href="{SITE_URL}/">トップ</a>
    <a href="{SITE_URL}/guide">ガイド</a>
    <a href="{SITE_URL}/about">運営者情報</a>
    <a href="{SITE_URL}/privacy">プライバシーポリシー</a>
  </p>
  <p>© 2026 PC自作、もう迷わない All Rights Reserved.</p>
</footer>

</body>
</html>"""

    return html


def main():
    print(f"[START] ゲームページ生成 (SEO Phase 1)")
    print(f"入力: {GAMES_FILE}")
    print(f"出力: {OUTPUT_DIR}\n")

    if not GAMES_FILE.exists():
        print(f"[ERROR] games.jsonl が見つかりません: {GAMES_FILE}")
        return

    games = []
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                game = json.loads(line)
                game['slug'] = slugify(game['name'])
                games.append(game)

    print(f"[INFO] {len(games)}タイトル読み込み完了")

    generated = 0
    skipped = 0
    for i, game in enumerate(games, 1):
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

    print("\n[INFO] sitemap.xml 生成中...")
    generate_sitemap(games)


def generate_sitemap(games):
    """sitemap.xml を生成"""
    sitemap_file = WORKSPACE_DIR / "static" / "sitemap.xml"

    urls = [f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""]

    for game in games:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/game/{game['slug']}</loc>
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
