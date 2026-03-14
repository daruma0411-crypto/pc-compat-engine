# SEO/AIO セットアップチェックリスト

## ✅ 完了済み

- [x] ゲームランディングページ 415ページ生成
  - 410ページ（既存）
  - 5ページ（新作: モンハンワイルズ, GTA6, エルデンリング, Ghost of Tsushima, Palworld）
- [x] 構造化データ（Schema.org VideoGame）
- [x] OpenGraphタグ
- [x] FAQページ（Schema.org FAQPage）
- [x] sitemap.xml（416 URL）
- [x] robots.txt（AI Crawler許可）
- [x] 更新日時表示
- [x] データソース明記

---

## 🔲 次にやること

### 1. Googleサーチコンソール登録（30分）

#### 手順
1. https://search.google.com/search-console にアクセス
2. 「プロパティを追加」
3. URL: `https://pc-jisaku.com`
4. 所有権確認:
   - HTMLファイルアップロード、または
   - HTMLタグ（推奨）、または
   - DNS TXT レコード

5. sitemap.xml送信
   - `https://pc-jisaku.com/sitemap.xml`

6. インデックス登録リクエスト
   - 主要ページ10件を手動リクエスト:
     - トップページ
     - monster-hunter-wilds.html
     - grand-theft-auto-vi.html
     - elden-ring-shadow-of-the-erdtree.html
     - ghost-of-tsushima.html
     - palworld.html

#### 所有権確認用HTMLタグ（app.pyに追加）
```python
@app.route('/')
def index():
    html = ...
    # <head>内に以下を追加:
    # <meta name="google-site-verification" content="YOUR_CODE_HERE">
    return html
```

---

### 2. Bing Webmaster Tools登録（15分）

1. https://www.bing.com/webmasters/
2. サイト追加: `https://pc-jisaku.com`
3. sitemap.xml送信

---

### 3. Google Analytics 4設定（15分）

1. https://analytics.google.com/
2. プロパティ作成
3. 測定ID取得
4. app.py に GA4タグ追加

```python
GA4_MEASUREMENT_ID = os.environ.get('GA4_MEASUREMENT_ID', '')

def inject_analytics(html):
    if GA4_MEASUREMENT_ID:
        analytics_script = f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_MEASUREMENT_ID}');
</script>
"""
        html = html.replace('</head>', analytics_script + '</head>')
    return html
```

---

### 4. 内部リンク最適化（1時間）

既存14,000ページ（パーツ互換性）に「このパーツで動くゲーム」リンクを追加

例：
```html
<!-- rtx-4060.html -->
<section id="compatible-games">
  <h2>このGPUで快適に動くゲーム</h2>
  <ul>
    <li><a href="/game/monster-hunter-wilds.html">Monster Hunter Wilds</a> - 高設定60fps</li>
    <li><a href="/game/cyberpunk-2077.html">Cyberpunk 2077</a> - 中設定60fps</li>
  </ul>
</section>
```

---

### 5. パフォーマンス最適化（30分）

#### 画像最適化
- OGP画像（各ゲーム）: WebP変換
- サイズ: 1200x630

#### HTML圧縮
```python
# app.py
import minify_html

@app.route('/game/<slug>')
def game_page(slug):
    html = Path(f'static/game/{slug}.html').read_text()
    return minify_html.minify(html, minify_css=True, minify_js=True)
```

---

### 6. Core Web Vitals改善

- LCP（Largest Contentful Paint）: <2.5秒
- FID（First Input Delay）: <100ms
- CLS（Cumulative Layout Shift）: <0.1

対策：
- CSS/JSの遅延読み込み
- フォント最適化
- レイアウトシフト防止

---

## 📊 効果測定（2週間後）

### チェック項目
- [ ] Google検索でインデックス数確認: `site:pc-jisaku.com`
- [ ] 検索クエリ上位10件（サーチコンソール）
- [ ] トラフィック: 目標 10,000 PV/月
- [ ] 検索順位: 「モンハンワイルズ 推奨スペック」 → 1ページ目目標

---

## 🤖 AIO対策（追加施策）

### ChatGPT Search対策
- 引用されやすい簡潔な回答形式
- 「〜ですか？」→「〜です」の明確な回答

### Perplexity対策
- 数値データの明記
- 表形式の多用

### Google SGE対策
- Featured Snippet狙い（リスト形式、表形式）
- 「よくある質問」セクション強化

---

## 次のマイルストーン

### Week 1（完了）
- [x] 415ゲームページ生成
- [x] sitemap.xml
- [x] robots.txt

### Week 2（次週）
- [ ] Googleサーチコンソール登録
- [ ] GA4設定
- [ ] モンハンワイルズ発売日マーケティング

### Week 3-4
- [ ] インデックス状況確認
- [ ] 検索順位モニタリング
- [ ] 内部リンク最適化

### Month 2
- [ ] トラフィック分析
- [ ] コンバージョン最適化
- [ ] 次回新作対応（エルデンリングDLC）
