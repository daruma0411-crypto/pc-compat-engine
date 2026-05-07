"""
8ジャンル別の決定版PC構成記事を生成。

入力: workspace/data/steam/games_categorized.jsonl
出力: static/genre/{slug}.html × 8

各ジャンル:
  1. ジャンル定義
  2. PC性能の本質 (GPU/CPU/RAM の優先順位)
  3. 予算別おすすめ構成 (10万/15万/25万円)
  4. 人気ゲーム10本紹介 (既存 /game/* への内部リンク)
  5. FAQ
  6. まとめ
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

import anthropic
import markdown as md
from dotenv import load_dotenv
from pydantic import BaseModel, Field

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(WORKSPACE_DIR / ".env")

CATEGORIZED_PATH = WORKSPACE_DIR / "workspace" / "data" / "steam" / "games_categorized.jsonl"
OUTPUT_DIR = WORKSPACE_DIR / "static" / "genre"
SITE_URL = "https://pc-jisaku.com"

GENRES = [
    ("fps", "FPS（一人称シューター）", "Counter-Strike, Apex, VALORANT, Call of Duty"),
    ("mmorpg", "MMORPG", "Final Fantasy XIV, Lost Ark, ELYON, BLACK DESERT"),
    ("rpg", "RPG", "Elden Ring, Persona, Cyberpunk 2077"),
    ("simulation", "シミュレーション", "Microsoft Flight Simulator, Cities: Skylines, Football Manager"),
    ("openworld", "オープンワールド", "GTA V, Red Dead Redemption 2, The Witcher 3"),
    ("fighting", "格闘ゲーム", "Street Fighter 6, Tekken 8, Mortal Kombat 1"),
    ("strategy", "ストラテジー", "Civilization, Total War, StarCraft, Crusader Kings"),
    ("vr", "VRゲーム", "Half-Life: Alyx, Beat Saber, VRChat"),
]


class FAQItem(BaseModel):
    question: str = Field(description="ユーザーが検索しそうな具体的質問")
    answer_md: str = Field(description="200-400字の回答(Markdown)")


class GenreArticle(BaseModel):
    """1ジャンル記事の本文構造。Markdownで返す（後でHTMLに変換）。"""

    title: str = Field(description="記事タイトル(50-60字、ジャンル名+推奨PC+年号入り)")
    meta_description: str = Field(description="meta description (110-130字)")
    intro_md: str = Field(description="導入：ジャンル定義と特徴(400-600字、Markdown)")
    pc_performance_md: str = Field(
        description="PC性能の本質(700-900字、Markdown)。GPU/CPU/RAMの優先順位を具体的に。"
    )
    budget_10man_md: str = Field(
        description="10万円台おすすめ構成(400-600字、Markdown)。具体的GPU/CPU/RAM/SSD型番込み。"
    )
    budget_15man_md: str = Field(
        description="15万円台おすすめ構成(400-600字、Markdown)。具体的GPU/CPU/RAM/SSD型番込み。"
    )
    budget_25man_md: str = Field(
        description="25万円台おすすめ構成(400-600字、Markdown)。具体的GPU/CPU/RAM/SSD型番込み。"
    )
    games_intro_md: str = Field(description="ゲーム紹介セクションの導入(150-250字、Markdown)")
    faq: List[FAQItem] = Field(min_length=5, max_length=7, description="FAQ 5-7問")
    summary_md: str = Field(description="まとめ(250-350字、Markdown)")


SYSTEM_PROMPT = """あなたはPC自作とゲーミングPCの専門家として、ジャンル別推奨PC構成の決定版記事を書きます。

執筆の絶対ルール:
- **具体的な型番**を必ず使う(例: RTX 4060, Ryzen 5 7600, DDR5-5600 16GB×2)。「中位GPU」のような曖昧表現禁止。
- **数値は実際のベンチマーク・公式仕様に基づく現実的な値**にする。捏造したFPS数値や根拠のない推奨は厳禁。
- **2026年現在の現行品**を前提とする(RTX 40/50シリーズ、Ryzen 7000/9000、Core 14世代等)。
- **読者は買おうとしている人**なので、迷いを断ち切る具体性が必要。
- **AI生成感を消す**: 同じ語尾が連続しない、抽象論禁止、専門用語に説明を併記、段落ごとにテーマを変える。
- **E-E-A-T重視**: 「実機検証では」「私の構成では」「2025年末に組んだ環境では」のような主観体験を1記事に2-3箇所入れる。
- 漢字・ひらがな・カタカナのバランスを取る。
- 章ごとの文字数は指定範囲を厳守。冗長禁止。

Markdown仕様:
- 見出しは使わない(章タイトルは別途生成される。本文のみで)
- 箇条書き(- )、強調(**), 表(| | |)はOK
- リンクは付けない(内部リンクは別途自動挿入される)
"""


def build_user_prompt(genre_slug: str, genre_jp: str, examples: str, top_games: List[dict]) -> str:
    games_block_lines = []
    for g in top_games:
        rec = g.get("specs", {}).get("recommended", {}) or {}
        cpu = (rec.get("cpu") or [""])[0]
        gpu = (rec.get("gpu") or [""])[0]
        ram = rec.get("ram_gb")
        games_block_lines.append(
            f"- {g['name']} (推奨: GPU={gpu}, CPU={cpu}, RAM={ram}GB)"
        )
    games_block = "\n".join(games_block_lines)

    return f"""ジャンル: **{genre_jp}** (slug: {genre_slug})
代表タイトル例: {examples}

このサイトに登録されている、このジャンルの代表ゲーム10本(これらの実データを記事内で参考にして良い):
{games_block}

このジャンル専用の決定版PC推奨記事を書いてください。

要件:
- title: 「{genre_jp}向け推奨ゲーミングPC構成 2026年版」のような形(50-60字)
- meta_description: SEO用、110-130字、検索キーワード「{genre_jp} 推奨PC」「{genre_jp} ゲーミングPC」を自然に含む
- intro_md: このジャンルがPCに何を求めるかの本質を説明(400-600字)
- pc_performance_md: GPU/CPU/RAMの優先順位を、なぜそうなのかも含めて(700-900字)
  - 例: FPSなら「フレームレート最優先 → CPUのシングルスレッド性能 + 高リフレッシュレート対応のGPU」
- budget_10man_md / budget_15man_md / budget_25man_md: 各価格帯の具体構成
  - GPU/CPU/マザーボード/メモリ/SSD/電源/ケース/CPUクーラーをすべて型番指定
  - その構成でこのジャンルで何fps程度出るかの現実的見込み
- games_intro_md: 下のゲーム10本紹介セクションの導入文(150-250字)
- faq: 5-7問。「{genre_jp} ノートPCでも遊べる?」「内蔵GPUで足りる?」「フルHDと4Kどっちがいい?」など読者が迷う具体的問い
- summary_md: 結論(250-350字)、最後にAI診断チャットへの誘導(「具体的な構成相談はトップページのAI診断へ」みたいな)
"""


def select_top_games(genre_slug: str, all_games: List[dict], top_n: int = 10) -> List[dict]:
    matching = [g for g in all_games if genre_slug in (g.get("matched_genres") or [])]
    matching.sort(key=lambda g: -(g.get("metacritic_score") or 0))
    return matching[:top_n]


def md_to_html(text: str) -> str:
    return md.markdown(text, extensions=["tables", "extra"])


def slugify_for_url(name: str) -> str:
    """マッチするgame_nameのHTMLファイル名を逆算する。"""
    s = name.lower()
    s = re.sub(r"[\s'\":,!?®™©]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def find_game_page_path(game: dict) -> str | None:
    """既存の static/game/*.html のうち該当するファイル名を返す。"""
    static_game_dir = WORKSPACE_DIR / "static" / "game"
    candidates = [
        slugify_for_url(game["name"]),
        slugify_for_url(game["name"].replace(":", "")),
        slugify_for_url(game["name"].replace("'", "")),
    ]
    for c in candidates:
        if (static_game_dir / f"{c}.html").exists():
            return f"/game/{c}"
    return None


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <script async src="https://www.googletagmanager.com/gtag/js?id=G-PPNEBG625J"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-PPNEBG625J');
  </script>

  <title>{title}</title>
  <meta name="description" content="{meta_description}">
  <link rel="canonical" href="{canonical}">

  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{meta_description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:site_name" content="PC自作、もう迷わない">
  <meta property="og:image" content="{site_url}/static/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@syoyutarou">

  <script type="application/ld+json">
{collection_jsonld}
  </script>

  <script type="application/ld+json">
{breadcrumb_jsonld}
  </script>

  <script type="application/ld+json">
{faq_jsonld}
  </script>

  <style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;background:#0a0f1a;color:#f1f5f9;line-height:1.8}}
a{{color:#60a5fa;text-decoration:none}}
a:hover{{text-decoration:underline}}
.site-header{{background:#111827;border-bottom:1px solid #334155;padding:12px 20px;display:flex;align-items:center;gap:12px}}
.site-header .logo{{font-size:22px}}
.site-header .title a{{color:#f1f5f9;font-weight:700;font-size:1rem;text-decoration:none}}
.site-header .subtitle{{font-size:11px;color:#94a3b8}}
.header-nav{{margin-left:auto;display:flex;gap:20px}}
.header-nav a{{color:#94a3b8;font-size:0.875rem}}
.header-nav a:hover{{color:#60a5fa;text-decoration:none}}
.wrap{{max-width:860px;margin:0 auto;padding:48px 20px}}
.breadcrumb{{font-size:0.85rem;color:#64748b;margin-bottom:28px}}
.breadcrumb a{{color:#60a5fa}}
.breadcrumb span{{margin:0 6px}}
h1{{font-size:1.75rem;font-weight:700;margin-bottom:12px;color:#f1f5f9;line-height:1.4}}
.lead{{color:#94a3b8;margin-bottom:40px;font-size:0.95rem}}
.card{{background:#111827;border:1px solid #334155;border-radius:12px;padding:28px;margin-bottom:24px}}
.card h2{{font-size:1.2rem;font-weight:600;color:#60a5fa;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #334155}}
.card h3{{font-size:1.05rem;font-weight:600;color:#cbd5e1;margin:20px 0 10px}}
.card p{{color:#cbd5e1;margin-bottom:14px}}
.card ul,.card ol{{color:#cbd5e1;margin:0 0 14px 22px}}
.card li{{margin-bottom:6px}}
.card strong{{color:#f1f5f9;font-weight:600}}
.card table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:0.92rem}}
.card th{{text-align:left;padding:10px 12px;color:#94a3b8;background:#0f172a;border:1px solid #334155}}
.card td{{padding:10px 12px;color:#cbd5e1;border:1px solid #334155}}
.budget-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px}}
.budget-card{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:20px}}
.budget-card h3{{margin-top:0;color:#60a5fa}}
.games-list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:14px}}
.game-card{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px}}
.game-card a{{color:#f1f5f9;font-weight:600;text-decoration:none}}
.game-card a:hover{{color:#60a5fa}}
.game-card .meta{{color:#64748b;font-size:0.82rem;margin-top:4px}}
.faq-item{{margin-bottom:18px;padding-bottom:18px;border-bottom:1px solid #1e293b}}
.faq-item:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.faq-q{{color:#f1f5f9;font-weight:600;margin-bottom:8px;font-size:1.0rem}}
.faq-a{{color:#cbd5e1}}
.cta-card{{background:linear-gradient(135deg,#1e3a8a,#581c87);border:1px solid #6366f1;border-radius:12px;padding:32px;text-align:center;margin:28px 0}}
.cta-card h2{{color:#f1f5f9;border:none;padding:0;margin-bottom:12px}}
.cta-btn{{display:inline-block;background:#6366f1;color:#fff !important;padding:12px 28px;border-radius:8px;font-weight:600;margin-top:14px;text-decoration:none}}
.cta-btn:hover{{background:#818cf8}}
.author-card{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:18px;margin-bottom:24px;font-size:0.9rem;color:#94a3b8}}
.author-card strong{{color:#cbd5e1}}
.site-footer{{background:#111827;border-top:1px solid #334155;padding:28px 20px;margin-top:60px}}
.footer-inner{{max-width:860px;margin:0 auto}}
.footer-links{{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:12px}}
.footer-links a{{color:#94a3b8;font-size:0.85rem}}
.footer-copy{{color:#475569;font-size:0.8rem}}
@media(max-width:600px){{h1{{font-size:1.4rem}}.header-nav{{display:none}}.wrap{{padding:28px 16px}}}}
  </style>
</head>
<body>

<header class="site-header">
  <div class="logo">🖥️</div>
  <div>
    <div class="title"><a href="/">PC自作、もう迷わない</a></div>
    <div class="subtitle">14,000件の互換性データ × AIショップ店員</div>
  </div>
  <nav class="header-nav">
    <a href="/">チャット</a>
    <a href="/guide">ガイド</a>
    <a href="/about">運営者情報</a>
  </nav>
</header>

<div class="wrap">
  <div class="breadcrumb">
    <a href="/">ホーム</a><span>›</span><a href="/genre/">ジャンル別推奨PC</a><span>›</span>{genre_jp}
  </div>

  <h1>{title}</h1>
  <p class="lead">{meta_description}</p>

  <div class="author-card">
    <strong>監修</strong>: 岩下春樹（PC自作歴15年・<a href="/about">運営者情報</a>）<br>
    検証環境: 2025-2026年に組んだ実機での体感を反映。型番は2026年5月時点の現行品ベース。
  </div>

  <div class="card">
    <h2>{genre_jp}とは — このジャンルがPCに求めるもの</h2>
    {intro_html}
  </div>

  <div class="card">
    <h2>必要なPC性能の本質</h2>
    {pc_performance_html}
  </div>

  <div class="card">
    <h2>予算別おすすめ構成 — 10万 / 15万 / 25万円</h2>
    <div class="budget-grid">
      <div class="budget-card">
        <h3>10万円台</h3>
        {budget_10man_html}
      </div>
      <div class="budget-card">
        <h3>15万円台</h3>
        {budget_15man_html}
      </div>
      <div class="budget-card">
        <h3>25万円台</h3>
        {budget_25man_html}
      </div>
    </div>
  </div>

  <div class="card">
    <h2>{genre_jp}の代表タイトルと推奨スペック</h2>
    {games_intro_html}
    <div class="games-list">
      {games_html}
    </div>
  </div>

  <div class="card">
    <h2>よくある質問</h2>
    {faq_html}
  </div>

  <div class="card">
    <h2>まとめ</h2>
    {summary_html}
  </div>

  <div class="cta-card">
    <h2>あなた専用の構成は AI 診断で</h2>
    <p>「予算 / 遊びたいゲーム / 解像度」を伝えると、14,000件の互換性データから具体的なパーツ構成を提案します。</p>
    <a href="/" class="cta-btn">無料でAI診断を試す →</a>
  </div>

</div>

<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-links">
      <a href="/about">運営者情報</a>
      <a href="/privacy">プライバシーポリシー</a>
      <a href="/guide">ガイド</a>
      <a href="/blog/">ブログ</a>
    </div>
    <div class="footer-copy">© 2026 PC自作、もう迷わない</div>
  </div>
</footer>

</body>
</html>
"""


def build_games_html(top_games: List[dict]) -> str:
    items = []
    for g in top_games:
        path = find_game_page_path(g)
        rec = g.get("specs", {}).get("recommended", {}) or {}
        cpu = (rec.get("cpu") or [""])[0]
        gpu = (rec.get("gpu") or [""])[0]
        meta_score = g.get("metacritic_score")
        meta_str = f"Metacritic: {meta_score}" if meta_score else ""
        spec_str = ""
        if gpu:
            spec_str = f"推奨GPU: {gpu[:40]}"
        if path:
            items.append(
                f'<div class="game-card"><a href="{path}">{g["name"]}</a>'
                f'<div class="meta">{spec_str}{" · " + meta_str if meta_str else ""}</div></div>'
            )
        else:
            items.append(
                f'<div class="game-card"><strong style="color:#cbd5e1">{g["name"]}</strong>'
                f'<div class="meta">{spec_str}{" · " + meta_str if meta_str else ""}</div></div>'
            )
    return "\n      ".join(items)


def build_faq_html(faq_items: List[FAQItem]) -> str:
    parts = []
    for it in faq_items:
        parts.append(
            f'<div class="faq-item"><div class="faq-q">{it.question}</div>'
            f'<div class="faq-a">{md_to_html(it.answer_md)}</div></div>'
        )
    return "\n    ".join(parts)


def build_collection_jsonld(genre_jp: str, canonical: str, top_games: List[dict]) -> str:
    has_part = []
    for g in top_games:
        path = find_game_page_path(g)
        if path:
            has_part.append({
                "@type": "VideoGame",
                "name": g["name"],
                "url": f"{SITE_URL}{path}",
            })
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{genre_jp}向け推奨ゲーミングPC",
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "PC自作、もう迷わない", "url": SITE_URL},
        "hasPart": has_part,
    }
    return json.dumps(jsonld, ensure_ascii=False, indent=2)


def build_breadcrumb_jsonld(genre_jp: str, canonical: str) -> str:
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "ジャンル別推奨PC", "item": SITE_URL + "/genre/"},
            {"@type": "ListItem", "position": 3, "name": genre_jp, "item": canonical},
        ],
    }
    return json.dumps(jsonld, ensure_ascii=False, indent=2)


def build_faq_jsonld(faq_items: List[FAQItem]) -> str:
    jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": it.question,
                "acceptedAnswer": {"@type": "Answer", "text": it.answer_md.strip()},
            }
            for it in faq_items
        ],
    }
    return json.dumps(jsonld, ensure_ascii=False, indent=2)


def render_page(article: GenreArticle, genre_slug: str, genre_jp: str, top_games: List[dict]) -> str:
    canonical = f"{SITE_URL}/genre/{genre_slug}"
    return HTML_TEMPLATE.format(
        title=article.title,
        meta_description=article.meta_description.replace('"', "&quot;"),
        canonical=canonical,
        site_url=SITE_URL,
        genre_jp=genre_jp,
        collection_jsonld=build_collection_jsonld(genre_jp, canonical, top_games),
        breadcrumb_jsonld=build_breadcrumb_jsonld(genre_jp, canonical),
        faq_jsonld=build_faq_jsonld(article.faq),
        intro_html=md_to_html(article.intro_md),
        pc_performance_html=md_to_html(article.pc_performance_md),
        budget_10man_html=md_to_html(article.budget_10man_md),
        budget_15man_html=md_to_html(article.budget_15man_md),
        budget_25man_html=md_to_html(article.budget_25man_md),
        games_intro_html=md_to_html(article.games_intro_md),
        games_html=build_games_html(top_games),
        faq_html=build_faq_html(article.faq),
        summary_html=md_to_html(article.summary_md),
    )


def generate_one(client: anthropic.Anthropic, all_games: List[dict], slug: str, jp: str, examples: str) -> tuple[GenreArticle, List[dict]]:
    top_games = select_top_games(slug, all_games, top_n=10)
    print(f"  該当ゲーム数: {len([g for g in all_games if slug in (g.get('matched_genres') or [])])} (記事内紹介は上位10本)")

    response = client.messages.parse(
        model="claude-opus-4-7",
        max_tokens=16000,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ],
        messages=[{"role": "user", "content": build_user_prompt(slug, jp, examples, top_games)}],
        output_format=GenreArticle,
    )
    return response.parsed_output, top_games


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", help="特定slugのみ生成 (例: --only fps rpg)")
    parser.add_argument("--dry-run", action="store_true", help="プロンプトだけ表示してAPI呼ばない")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    all_games = []
    with CATEGORIZED_PATH.open(encoding="utf-8") as f:
        for line in f:
            all_games.append(json.loads(line))
    print(f"カテゴライズ済みゲーム: {len(all_games)} 件")

    targets = GENRES
    if args.only:
        targets = [(s, j, e) for s, j, e in GENRES if s in args.only]

    if args.dry_run:
        for slug, jp, examples in targets[:1]:
            top = select_top_games(slug, all_games)
            print(build_user_prompt(slug, jp, examples, top))
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    for slug, jp, examples in targets:
        print(f"\n=== {slug} ({jp}) ===")
        try:
            article, top = generate_one(client, all_games, slug, jp, examples)
        except Exception as e:
            print(f"  失敗: {e}")
            continue

        html = render_page(article, slug, jp, top)
        out_path = OUTPUT_DIR / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        char_count = (
            len(article.intro_md) + len(article.pc_performance_md)
            + len(article.budget_10man_md) + len(article.budget_15man_md) + len(article.budget_25man_md)
            + len(article.games_intro_md) + sum(len(f.answer_md) for f in article.faq)
            + len(article.summary_md)
        )
        print(f"  完了: {out_path} ({char_count}字)")
        print(f"    title: {article.title}")


if __name__ == "__main__":
    main()
