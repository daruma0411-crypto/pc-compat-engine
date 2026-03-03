# マーケティング包括実装指示書

## 🎯 目的

BTO アフィリエイトへの移行に先立ち、SEO・コンテンツマーケティングを強化し、オーガニック流入を月間100人以上に増やす。

---

## 📊 フェーズ1: 競合・キーワード分析（即実行）

### タスク1.1: 競合サイト分析

**ツール:** SimilarWeb, Ubersuggest（無料版）

**対象競合:**
1. パソコン工房（www.pc-koubou.jp）
2. ドスパラ（www.dospara.co.jp）
3. 「BTO おすすめ」で検索1位のアフィリサイト

**取得データ:**
- 流入キーワードTOP 50
- 月間訪問者数
- 直帰率
- 主な流入元（検索/SNS/直接）

**出力:** `marketing/competitor_analysis.csv`

```csv
keyword,search_volume,difficulty,our_rank,competitor_rank
"BTO おすすめ ゲーミング",5400,85,圏外,1
"Premiere Pro BTO 推奨",720,45,圏外,圏外
"配信用PC スペック",880,52,圏外,3
```

---

### タスク1.2: ロングテールキーワード抽出

**抽出基準:**
- 検索ボリューム: 100-1000/月
- 競合難易度: 低-中（1-50）
- 購買意図: 高（「おすすめ」「選び方」「比較」を含む）

**カテゴリ別分類:**

#### A. ゲーム特化（20個）
```
Cyberpunk 2077 快適 BTO
Elden Ring 推奨スペック PC
Apex Legends 144fps BTO
原神 最高画質 PC
Valorant 240fps PC
...
```

#### B. クリエイター向け（15個）
```
Premiere Pro 4K編集 BTO
Stable Diffusion ローカル実行 PC
Blender レンダリング 速い PC
DaVinci Resolve 推奨スペック
...
```

#### C. 配信者向け（10個）
```
OBS 配信 エンコード PC
VTuber 配信 スペック
YouTube 動画編集 BTO
...
```

#### D. 予算別（10個）
```
予算15万 ゲーミングPC BTO
20万円以内 動画編集PC
コスパ最強 BTO 2026
...
```

**出力:** `marketing/longtail_keywords.csv`

---

## 📝 フェーズ2: ゲームページSEO強化（自動化）

### タスク2.1: 全443ゲームページへのコンテンツ追加

**スクリプト:** `scripts/seo/add_bto_content.py`

**追加するセクション:**

```html
<!-- 各ゲームページの</article>直前に挿入 -->
<section class="bto-recommendation" itemscope itemtype="https://schema.org/Article">
  <h2 itemprop="headline">「{{game_name}}」を快適にプレイできるおすすめBTO PC</h2>
  
  <p itemprop="description">
    {{game_name}}の推奨スペック（GPU: {{recommended_gpu}}, CPU: {{recommended_cpu}}, RAM: {{recommended_ram}}GB）
    を満たし、快適に動作するBTO PCをお探しですか？
    当サイトのAI診断なら、あなたの予算と目的に最適なゲーミングPCを即座に提案します。
  </p>
  
  <h3>予算別おすすめ構成</h3>
  <div class="budget-tiers">
    <div class="tier">
      <h4>【15万円】エントリーモデル</h4>
      <ul>
        <li>解像度: 1080p（Full HD）</li>
        <li>フレームレート: 60fps</li>
        <li>画質設定: 中〜高</li>
      </ul>
    </div>
    
    <div class="tier recommended">
      <h4>【25万円】スタンダードモデル ⭐推奨</h4>
      <ul>
        <li>解像度: 1440p（WQHD）</li>
        <li>フレームレート: 144fps</li>
        <li>画質設定: 最高</li>
      </ul>
    </div>
    
    <div class="tier">
      <h4>【35万円】ハイエンドモデル</h4>
      <ul>
        <li>解像度: 4K（Ultra HD）</li>
        <li>フレームレート: 60fps以上</li>
        <li>画質設定: ウルトラ + レイトレ</li>
      </ul>
    </div>
  </div>
  
  <a href="/?game={{game_name}}" class="cta-button">
    AI診断で最適なBTO PCを見つける
  </a>
</section>

<!-- Schema.org 追加 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{{game_name}}を快適にプレイできるおすすめBTO PC",
  "description": "{{game_name}}の推奨スペックを満たすBTOパソコンの選び方",
  "author": {
    "@type": "Organization",
    "name": "PC互換チェッカー"
  }
}
</script>
```

**CSS追加:** `static/style.css`

```css
/* BTO推奨セクション */
.bto-recommendation {
  margin: 40px 0;
  padding: 30px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 8px;
}

.budget-tiers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.tier {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.3s;
}

.tier:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.tier.recommended {
  border: 3px solid #4CAF50;
  position: relative;
}

.tier.recommended::before {
  content: "最もお得";
  position: absolute;
  top: -15px;
  right: 20px;
  background: #4CAF50;
  color: white;
  padding: 5px 15px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 0.9em;
}

.cta-button {
  display: inline-block;
  background: #4CAF50;
  color: white;
  padding: 15px 40px;
  border-radius: 30px;
  text-decoration: none;
  font-weight: bold;
  margin-top: 20px;
  transition: all 0.3s;
}

.cta-button:hover {
  background: #45a049;
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
}
```

---

### タスク2.2: meta descriptionの最適化

**全443ゲームページのmeta descriptionを更新:**

```html
<!-- Before -->
<meta name="description" content="{{game_name}}の推奨スペックと最低動作環境">

<!-- After -->
<meta name="description" content="{{game_name}}を快適にプレイできるBTO PCを予算別に紹介。AI診断で推奨スペック（GPU: {{gpu}}, CPU: {{cpu}}）を満たす最適なゲーミングPCを即座に提案。">
```

---

## ✍️ フェーズ3: ブログ記事作成（10本）

### 記事リスト

**ディレクトリ:** `content/blog/`

#### 記事1: 予算別総合ガイド
**ファイル:** `budget-guide-2026.md`
**タイトル:** 【2026年版】予算別BTO PC完全ガイド - 15万円/25万円/35万円で選ぶ最強構成
**キーワード:** 予算別 BTO, ゲーミングPC 価格, コスパ最強 PC
**文字数:** 3,000-4,000字

**構成:**
```markdown
# 【2026年版】予算別BTO PC完全ガイド

## はじめに：なぜBTOがおすすめなのか
- 自作 vs BTO の比較
- 保証・サポートのメリット

## 予算15万円：エントリークラス
### おすすめ構成
- CPU: Core i5-14400F
- GPU: RTX 4060
- RAM: 16GB
- ストレージ: 500GB NVMe SSD

### できること
- フルHD/60fps でほぼ全てのゲーム
- 軽い動画編集
- ブラウジング・オフィス作業

### おすすめBTOモデル
1. パソコン工房 LEVEL-M7P5
2. ドスパラ GALLERIA RM5C-R46
3. FRONTIER GAシリーズ

## 予算25万円：スタンダードクラス（最もおすすめ）
### おすすめ構成
- CPU: Core i7-14700F
- GPU: RTX 4070
- RAM: 32GB
- ストレージ: 1TB NVMe SSD

### できること
- WQHD/144fps で快適ゲーミング
- 4K動画編集
- 配信（エンコード）
- AI画像生成（Stable Diffusion）

### おすすめBTOモデル
1. パソコン工房 LEVEL-R779
2. ドスパラ GALLERIA XA7C-R47
3. サイコム G-Master

## 予算35万円：ハイエンドクラス
（同様の構成）

## まとめ：AI診断で最適なPCを見つけよう
→ サイトトップへの誘導
```

---

#### 記事2-5: ゲーム特化記事

**記事2:** `cyberpunk-2077-bto.md`
**タイトル:** Cyberpunk 2077を最高画質でプレイ！推奨BTO PC 2026年版
**キーワード:** Cyberpunk 2077 BTO, サイバーパンク PC スペック

**記事3:** `elden-ring-bto.md`
**タイトル:** Elden Ring 快適プレイのための推奨BTO PC【60fps安定】
**キーワード:** Elden Ring BTO, エルデンリング PC

**記事4:** `apex-legends-144fps.md`
**タイトル:** Apex Legends 144fps安定！競技向けゲーミングPC選び
**キーワード:** Apex Legends 144fps, FPS ゲーミングPC

**記事5:** `valorant-240fps.md`
**タイトル:** VALORANT 240fps出せるゲーミングPCスペックとおすすめBTO
**キーワード:** VALORANT 240fps, バロラント PC

---

#### 記事6-8: クリエイター向け

**記事6:** `premiere-pro-bto.md`
**タイトル:** Premiere Pro 4K編集が快適なBTO PC【2026年版】予算別おすすめ
**キーワード:** Premiere Pro BTO, 動画編集PC おすすめ

**記事7:** `stable-diffusion-local.md`
**タイトル:** Stable Diffusion ローカル実行に最適なPC構成【VRAM別比較】
**キーワード:** Stable Diffusion PC, AI画像生成 ローカル

**記事8:** `blender-rendering-pc.md`
**タイトル:** Blender レンダリングが爆速になるBTO PC【GPU/CPU比較】
**キーワード:** Blender レンダリング PC, 3DCG パソコン

---

#### 記事9-10: 配信者向け

**記事9:** `obs-streaming-pc.md`
**タイトル:** 配信者必見！OBSエンコードが軽くなるゲーミングPC選び
**キーワード:** OBS 配信 PC, 配信用 BTO

**記事10:** `vtuber-pc-spec.md`
**タイトル:** VTuber活動に必要なPCスペックとおすすめBTO【2026年版】
**キーワード:** VTuber PC スペック, Live2D 推奨環境

---

## 🔧 フェーズ4: 技術実装

### タスク4.1: ブログ機能実装

**ファイル:** `app.py`

```python
@app.route('/blog')
def blog_list():
    """ブログ記事一覧"""
    articles = load_blog_articles()
    return render_template('blog/index.html', articles=articles)

@app.route('/blog/<slug>')
def blog_article(slug):
    """個別ブログ記事"""
    article = load_article(slug)
    if not article:
        abort(404)
    return render_template('blog/article.html', article=article)
```

**テンプレート:** `templates/blog/index.html`

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>ブログ記事一覧 | PC互換チェッカー</title>
</head>
<body>
  <h1>PC選びに役立つ情報</h1>
  
  <div class="article-grid">
    {% for article in articles %}
    <article class="article-card">
      <img src="{{ article.thumbnail }}" alt="{{ article.title }}">
      <h2><a href="/blog/{{ article.slug }}">{{ article.title }}</a></h2>
      <p>{{ article.excerpt }}</p>
      <time>{{ article.date }}</time>
    </article>
    {% endfor %}
  </div>
</body>
</html>
```

---

### タスク4.2: 内部リンク最適化

**全ページに追加:**

```html
<!-- フッターに追加 -->
<nav class="footer-links">
  <h3>お役立ち情報</h3>
  <ul>
    <li><a href="/blog/budget-guide-2026">予算別BTO PCガイド</a></li>
    <li><a href="/blog/premiere-pro-bto">動画編集向けPC選び</a></li>
    <li><a href="/blog/obs-streaming-pc">配信者向けPC選び</a></li>
  </ul>
</nav>
```

---

## 📊 フェーズ5: 効果測定

### Google Analytics イベント設定

**トラッキングイベント:**

```javascript
// ブログ記事からのCTA クリック
gtag('event', 'blog_cta_click', {
  'article_slug': '{{slug}}',
  'cta_position': 'article_end'
});

// ゲームページのBTO推奨セクションクリック
gtag('event', 'bto_section_click', {
  'game_name': '{{game_name}}',
  'budget_tier': '25万円'
});

// AI診断開始
gtag('event', 'diagnosis_start', {
  'source': 'blog',  // or 'game_page'
});
```

---

### 成果指標（1ヶ月後）

| KPI | 現状 | 目標 | 計測 |
|-----|------|------|------|
| オーガニック流入 | 15人/週 | 100人/週 | GA4 |
| ブログPV | 0 | 200/週 | GA4 |
| ゲームページ滞在時間 | 12分 | 15分 | GA4 |
| BTO推奨セクションCTR | - | 15% | イベント |
| AI診断開始率 | - | 10% | イベント |

---

## 🚀 実装スケジュール

### Week 1（今週）
- [ ] タスク1.1: 競合分析
- [ ] タスク1.2: キーワード抽出
- [ ] タスク2.1: ゲームページSEO強化（443ページ）
- [ ] タスク4.2: GA4イベント設定

### Week 2
- [ ] 記事1-3作成
- [ ] 記事4-6作成
- [ ] タスク4.1: ブログ機能実装

### Week 3
- [ ] 記事7-10作成
- [ ] 内部リンク最適化
- [ ] sitemap.xml更新

### Week 4
- [ ] A/Bテスト開始
- [ ] 効果測定・レポート作成
- [ ] 改善施策立案

---

以上がマーケティング包括実装の全体像です。
