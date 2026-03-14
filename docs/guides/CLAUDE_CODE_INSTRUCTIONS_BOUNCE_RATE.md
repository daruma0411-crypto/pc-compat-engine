# Claude Code 実装指示書: 直帰率対策 5施策 + ファイル整理

## 📋 実装概要

**目的**: 直帰率を下げ、サイト内回遊率を最大化する5つの施策を一括実装

**実装範囲**:
1. サイドバー・フッター強化（人気ランキング、新着、ジャンル別）
2. Exit Intent ポップアップ + スクロール50%CTA
3. 記事内CTA追加（診断ボタン2箇所）
4. パンくずリスト追加
5. 読み込み速度改善（画像遅延読み込み、ミニファイ）
6. 未コミットファイルの整理・コミット

**期待効果**:
- 直帰率: 70% → 50% (目標)
- ページ/セッション: 1.2 → 2.5+ (目標)
- 平均滞在時間: 45秒 → 2分+ (目標)

---

## 🎯 施策1: サイドバー・フッター強化

### 1-1. トップページにサイドバー追加

**ファイル**: `templates/index.html`

**実装内容**:
```html
<!-- メインコンテンツの後、</main> の前に追加 -->
<aside class="sidebar">
  <section class="sidebar-section">
    <h3>🔥 人気ゲームTOP10</h3>
    <ol class="popular-games">
      <!-- Python側で動的生成: games.db から page_views 上位10件 -->
      <li><a href="/game/baldurs-gate-3">Baldur's Gate 3</a></li>
      <li><a href="/game/elden-ring">Elden Ring</a></li>
      <li><a href="/game/palworld">Palworld</a></li>
      <li><a href="/game/helldivers-2">Helldivers 2</a></li>
      <li><a href="/game/final-fantasy-vii-rebirth">FF7 Rebirth</a></li>
      <li><a href="/game/dragons-dogma-2">Dragon's Dogma 2</a></li>
      <li><a href="/game/monster-hunter-wilds">Monster Hunter Wilds</a></li>
      <li><a href="/game/warhammer-40000-space-marine-2">Space Marine 2</a></li>
      <li><a href="/game/street-fighter-6">Street Fighter 6</a></li>
      <li><a href="/game/cyberpunk-2077">Cyberpunk 2077</a></li>
    </ol>
  </section>

  <section class="sidebar-section">
    <h3>✨ 新着ゲーム</h3>
    <ul class="new-games">
      <!-- Python側で動的生成: games.db から created_at 降順5件 -->
      <li><a href="/game/kingdom-come-deliverance-ii">Kingdom Come: Deliverance II</a></li>
      <li><a href="/game/civilization-vii">Civilization VII</a></li>
      <li><a href="/game/assetto-corsa-evo">Assetto Corsa EVO</a></li>
      <li><a href="/game/clair-obscur-expedition-33">Clair Obscur: Expedition 33</a></li>
      <li><a href="/game/death-stranding-2-on-the-beach">Death Stranding 2</a></li>
    </ul>
  </section>

  <section class="sidebar-section">
    <h3>🎮 ジャンル別</h3>
    <ul class="genre-links">
      <li><a href="/genre/rpg">RPG</a></li>
      <li><a href="/genre/fps">FPS・シューター</a></li>
      <li><a href="/genre/racing">レーシング</a></li>
      <li><a href="/genre/simulation">シミュレーション</a></li>
      <li><a href="/genre/strategy">ストラテジー</a></li>
      <li><a href="/genre/action">アクション</a></li>
    </ul>
  </section>
</aside>
```

**CSS追加** (`static/style.css`):
```css
/* サイドバー */
.main-container {
  display: flex;
  max-width: 1400px;
  margin: 0 auto;
  gap: 24px;
}

.sidebar {
  width: 280px;
  flex-shrink: 0;
}

.sidebar-section {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.sidebar-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1a1a1a;
}

.popular-games, .new-games, .genre-links {
  list-style: none;
  padding: 0;
  margin: 0;
}

.popular-games li {
  counter-increment: popular;
  margin-bottom: 8px;
}

.popular-games li::before {
  content: counter(popular) ". ";
  font-weight: 600;
  color: #2563eb;
}

.popular-games a, .new-games a, .genre-links a {
  color: #1a1a1a;
  text-decoration: none;
  font-size: 14px;
  display: block;
  padding: 4px 0;
  transition: color 0.2s;
}

.popular-games a:hover, .new-games a:hover, .genre-links a:hover {
  color: #2563eb;
}

.new-games li, .genre-links li {
  margin-bottom: 8px;
  padding-left: 12px;
  position: relative;
}

.new-games li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: #2563eb;
}

.genre-links li::before {
  content: "🎮";
  position: absolute;
  left: -8px;
}

/* レスポンシブ */
@media (max-width: 1024px) {
  .main-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    grid-template-columns: 1fr;
  }
}
```

### 1-2. フッター強化

**ファイル**: `templates/index.html` + `static/game/*.html`

**追加内容**:
```html
<footer class="site-footer">
  <div class="footer-content">
    <div class="footer-section">
      <h4>PC互換チェッカーとは</h4>
      <p>14,000件以上のゲーム×PC構成の互換性データベース。あなたのPCでゲームが動くか瞬時に診断。</p>
    </div>
    
    <div class="footer-section">
      <h4>人気ジャンル</h4>
      <ul>
        <li><a href="/genre/rpg">RPG</a></li>
        <li><a href="/genre/fps">FPS・シューター</a></li>
        <li><a href="/genre/racing">レーシング</a></li>
        <li><a href="/genre/simulation">シミュレーション</a></li>
      </ul>
    </div>
    
    <div class="footer-section">
      <h4>おすすめ記事</h4>
      <ul>
        <li><a href="/blog/budget-gaming-pc-2026">2026年版 予算別ゲーミングPC</a></li>
        <li><a href="/blog/gpu-comparison">GPU性能比較表</a></li>
        <li><a href="/blog/ram-guide">RAM容量の選び方</a></li>
        <li><a href="/blog/troubleshooting">ゲームが起動しない時の対処法</a></li>
      </ul>
    </div>
    
    <div class="footer-section">
      <h4>お問い合わせ</h4>
      <ul>
        <li><a href="/about">サイトについて</a></li>
        <li><a href="/privacy">プライバシーポリシー</a></li>
        <li><a href="https://twitter.com/syoyutarou">Twitter (@syoyutarou)</a></li>
      </ul>
    </div>
  </div>
  
  <div class="footer-bottom">
    <p>&copy; 2026 PC互換チェッカー. All rights reserved.</p>
  </div>
</footer>
```

**CSS** (`static/style.css`):
```css
.site-footer {
  background: #1a1a1a;
  color: #ffffff;
  margin-top: 60px;
  padding: 40px 20px 20px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 32px;
  margin-bottom: 32px;
}

.footer-section h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #2563eb;
}

.footer-section p {
  font-size: 14px;
  line-height: 1.6;
  color: #b0b0b0;
}

.footer-section ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-section ul li {
  margin-bottom: 8px;
}

.footer-section a {
  color: #b0b0b0;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.footer-section a:hover {
  color: #2563eb;
}

.footer-bottom {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #333;
}

.footer-bottom p {
  font-size: 13px;
  color: #888;
  margin: 0;
}

@media (max-width: 768px) {
  .footer-content {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}
```

---

## 🎯 施策2: Exit Intent ポップアップ + スクロール50%CTA

### 2-1. Exit Intent Modal

**新規ファイル**: `static/exit-intent.js`

```javascript
// Exit Intent Detection
let exitIntentShown = false;

document.addEventListener('mouseleave', (e) => {
  if (e.clientY < 50 && !exitIntentShown && !sessionStorage.getItem('exitIntentShown')) {
    showExitIntentModal();
    exitIntentShown = true;
    sessionStorage.setItem('exitIntentShown', 'true');
  }
});

function showExitIntentModal() {
  const modal = document.createElement('div');
  modal.className = 'exit-intent-modal';
  modal.innerHTML = `
    <div class="exit-intent-content">
      <button class="exit-intent-close" onclick="closeExitIntent()">&times;</button>
      <h2>ちょっと待って！</h2>
      <p>あなたのPCでゲームが動くか、<br>3ステップで診断できます</p>
      <a href="/" class="exit-intent-cta">無料で診断する →</a>
      <p class="exit-intent-note">所要時間: 約30秒</p>
    </div>
  `;
  document.body.appendChild(modal);
  
  // フェードイン
  setTimeout(() => modal.classList.add('show'), 10);
}

function closeExitIntent() {
  const modal = document.querySelector('.exit-intent-modal');
  if (modal) {
    modal.classList.remove('show');
    setTimeout(() => modal.remove(), 300);
  }
}

// モーダル外クリックで閉じる
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('exit-intent-modal')) {
    closeExitIntent();
  }
});
```

**CSS** (`static/style.css`に追加):
```css
.exit-intent-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  opacity: 0;
  transition: opacity 0.3s;
}

.exit-intent-modal.show {
  opacity: 1;
}

.exit-intent-content {
  background: #ffffff;
  border-radius: 16px;
  padding: 40px 32px;
  max-width: 480px;
  text-align: center;
  position: relative;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.exit-intent-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 32px;
  color: #666;
  cursor: pointer;
  transition: color 0.2s;
}

.exit-intent-close:hover {
  color: #000;
}

.exit-intent-content h2 {
  font-size: 28px;
  margin-bottom: 16px;
  color: #1a1a1a;
}

.exit-intent-content p {
  font-size: 16px;
  line-height: 1.6;
  color: #666;
  margin-bottom: 24px;
}

.exit-intent-cta {
  display: inline-block;
  background: #2563eb;
  color: #ffffff;
  padding: 14px 32px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  font-size: 16px;
  transition: background 0.2s;
}

.exit-intent-cta:hover {
  background: #1d4ed8;
}

.exit-intent-note {
  font-size: 13px;
  color: #999;
  margin-top: 12px;
  margin-bottom: 0;
}
```

### 2-2. スクロール50%でCTA表示

**同じく** `static/exit-intent.js` に追加:

```javascript
// Scroll 50% CTA
let scrollCtaShown = false;

window.addEventListener('scroll', () => {
  const scrollPercent = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
  
  if (scrollPercent > 50 && !scrollCtaShown && !sessionStorage.getItem('scrollCtaShown')) {
    showScrollCta();
    scrollCtaShown = true;
    sessionStorage.setItem('scrollCtaShown', 'true');
  }
});

function showScrollCta() {
  const cta = document.createElement('div');
  cta.className = 'scroll-cta';
  cta.innerHTML = `
    <div class="scroll-cta-content">
      <span class="scroll-cta-text">💡 あなたのPCスペックを診断してみませんか？</span>
      <a href="/" class="scroll-cta-button">今すぐ診断 →</a>
      <button class="scroll-cta-close" onclick="closeScrollCta()">&times;</button>
    </div>
  `;
  document.body.appendChild(cta);
  
  // スライドイン
  setTimeout(() => cta.classList.add('show'), 10);
}

function closeScrollCta() {
  const cta = document.querySelector('.scroll-cta');
  if (cta) {
    cta.classList.remove('show');
    setTimeout(() => cta.remove(), 300);
  }
}
```

**CSS** (`static/style.css`に追加):
```css
.scroll-cta {
  position: fixed;
  bottom: -100px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  transition: bottom 0.3s ease-out;
}

.scroll-cta.show {
  bottom: 20px;
}

.scroll-cta-content {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #ffffff;
  padding: 16px 24px;
  border-radius: 50px;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
  display: flex;
  align-items: center;
  gap: 16px;
  max-width: 90vw;
}

.scroll-cta-text {
  font-size: 15px;
  font-weight: 500;
}

.scroll-cta-button {
  background: #ffffff;
  color: #2563eb;
  padding: 8px 20px;
  border-radius: 50px;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  transition: transform 0.2s;
}

.scroll-cta-button:hover {
  transform: scale(1.05);
}

.scroll-cta-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #ffffff;
  font-size: 24px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
}

.scroll-cta-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

@media (max-width: 768px) {
  .scroll-cta-content {
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border-radius: 16px;
  }
  
  .scroll-cta-text {
    font-size: 14px;
    text-align: center;
  }
}
```

**HTMLに追加** (全ページの `</body>` 直前):
```html
<script src="/static/exit-intent.js"></script>
```

---

## 🎯 施策3: 記事内CTA追加

### 3-1. スペック表の下に診断ボタン

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: `generate_game_page()` 関数内、スペック表を生成した直後

```python
# 既存のスペック表生成コード（sys_req_html）の後に追加

cta_after_specs = f'''
    <div class="in-content-cta">
      <div class="cta-icon">🎮</div>
      <div class="cta-content">
        <h3>あなたのPCで{game_title}は動く？</h3>
        <p>30秒で診断できます。無料・会員登録不要</p>
      </div>
      <a href="/" class="cta-button">今すぐ診断する →</a>
    </div>
'''

# sys_req_html の後に挿入
```

### 3-2. 予算別PC構成の下に診断ボタン

**同じく** `generate_game_pages.py` の予算別PC構成セクションの後:

```python
# 既存の予算別PC構成コード（budget_builds_html）の後に追加

cta_after_budget = f'''
    <div class="in-content-cta alt">
      <div class="cta-icon">💰</div>
      <div class="cta-content">
        <h3>あなたに最適な構成を診断</h3>
        <p>予算・用途に合わせたPC構成を自動提案</p>
      </div>
      <a href="/" class="cta-button">無料で診断 →</a>
    </div>
'''

# budget_builds_html の後に挿入
```

**CSS** (`static/style.css`に追加):
```css
.in-content-cta {
  background: linear-gradient(135deg, #f0f7ff, #e0f2fe);
  border: 2px solid #2563eb;
  border-radius: 12px;
  padding: 24px;
  margin: 32px 0;
  display: flex;
  align-items: center;
  gap: 20px;
}

.in-content-cta.alt {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border-color: #f59e0b;
}

.cta-icon {
  font-size: 48px;
  flex-shrink: 0;
}

.cta-content {
  flex-grow: 1;
}

.cta-content h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a1a;
}

.cta-content p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.cta-button {
  background: #2563eb;
  color: #ffffff;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  transition: background 0.2s, transform 0.2s;
  flex-shrink: 0;
}

.in-content-cta.alt .cta-button {
  background: #f59e0b;
}

.cta-button:hover {
  background: #1d4ed8;
  transform: translateY(-2px);
}

.in-content-cta.alt .cta-button:hover {
  background: #d97706;
}

@media (max-width: 768px) {
  .in-content-cta {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .cta-button {
    width: 100%;
  }
}
```

---

## 🎯 施策4: パンくずリスト追加

### 4-1. 構造化データ（Schema.org）

**ファイル**: `scripts/generate_game_pages.py`

**追加**: `<head>` 内に BreadcrumbList Schema を挿入

```python
breadcrumb_schema = f'''
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{
      "@type": "ListItem",
      "position": 1,
      "name": "ホーム",
      "item": "https://pc-jisaku.com/"
    }},
    {{
      "@type": "ListItem",
      "position": 2,
      "name": "{genre if genre else 'ゲーム'}",
      "item": "https://pc-jisaku.com/genre/{genre.lower() if genre else 'all'}"
    }},
    {{
      "@type": "ListItem",
      "position": 3,
      "name": "{game_title}",
      "item": "https://pc-jisaku.com/game/{game_slug}"
    }}
  ]
}}
</script>
'''

# 既存の FAQPage schema の後に挿入
```

### 4-2. 視覚的なパンくずリスト

**HTML** (ページタイトルの直前に挿入):

```python
breadcrumb_html = f'''
<nav class="breadcrumb" aria-label="パンくずリスト">
  <ol>
    <li><a href="/">ホーム</a></li>
    <li><a href="/genre/{genre.lower() if genre else 'all'}">{genre if genre else 'ゲーム'}</a></li>
    <li aria-current="page">{game_title}</li>
  </ol>
</nav>
'''
```

**CSS** (`static/style.css`):
```css
.breadcrumb {
  margin: 20px 0 16px;
  font-size: 14px;
}

.breadcrumb ol {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.breadcrumb li {
  display: flex;
  align-items: center;
}

.breadcrumb li:not(:last-child)::after {
  content: "›";
  margin-left: 8px;
  color: #999;
}

.breadcrumb a {
  color: #2563eb;
  text-decoration: none;
  transition: color 0.2s;
}

.breadcrumb a:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.breadcrumb li[aria-current="page"] {
  color: #666;
}
```

---

## 🎯 施策5: 読み込み速度改善

### 5-1. 画像遅延読み込み (Lazy Loading)

**ファイル**: 全HTMLファイル（トップページ + ゲームページ）

**修正**: `<img>` タグに `loading="lazy"` 属性を追加

```python
# generate_game_pages.py 内
# 既存の img タグを探して修正

# 修正前:
# <img src="/static/game_images/{image_filename}" alt="{game_title}のスクリーンショット">

# 修正後:
# <img src="/static/game_images/{image_filename}" alt="{game_title}のスクリーンショット" loading="lazy">
```

**トップページの検索候補画像も同様**:
```html
<img src="/static/game_images/..." alt="..." loading="lazy">
```

### 5-2. CSS/JS ミニファイ

**新規ファイル**: `scripts/minify_assets.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSS/JS Minifier
static/style.css と static/*.js を圧縮してファイルサイズ削減
"""

import re
from pathlib import Path

def minify_css(css_content):
    """CSS を圧縮"""
    # コメント削除
    css_content = re.sub(r'/\*[\s\S]*?\*/', '', css_content)
    # 余分な空白削除
    css_content = re.sub(r'\s+', ' ', css_content)
    # セミコロン前後の空白削除
    css_content = re.sub(r'\s*{\s*', '{', css_content)
    css_content = re.sub(r'\s*}\s*', '}', css_content)
    css_content = re.sub(r'\s*:\s*', ':', css_content)
    css_content = re.sub(r'\s*;\s*', ';', css_content)
    css_content = re.sub(r'\s*,\s*', ',', css_content)
    # 行頭行末の空白削除
    css_content = css_content.strip()
    return css_content

def minify_js(js_content):
    """JS を圧縮（簡易版 - コメントと余分な改行のみ）"""
    # 単一行コメント削除
    js_content = re.sub(r'//.*?$', '', js_content, flags=re.MULTILINE)
    # 複数行コメント削除
    js_content = re.sub(r'/\*[\s\S]*?\*/', '', js_content)
    # 余分な改行削除
    js_content = re.sub(r'\n\s*\n', '\n', js_content)
    return js_content

def main():
    # CSS圧縮
    css_path = Path('static/style.css')
    if css_path.exists():
        original_css = css_path.read_text(encoding='utf-8')
        minified_css = minify_css(original_css)
        
        # .min.css として保存
        min_css_path = Path('static/style.min.css')
        min_css_path.write_text(minified_css, encoding='utf-8')
        
        original_size = len(original_css)
        minified_size = len(minified_css)
        reduction = ((original_size - minified_size) / original_size) * 100
        
        print(f"✅ CSS圧縮完了:")
        print(f"   {original_size:,} bytes → {minified_size:,} bytes ({reduction:.1f}% 削減)")
    
    # JS圧縮
    js_files = list(Path('static').glob('*.js'))
    for js_path in js_files:
        if js_path.name.endswith('.min.js'):
            continue  # 既に圧縮済みならスキップ
            
        original_js = js_path.read_text(encoding='utf-8')
        minified_js = minify_js(original_js)
        
        # .min.js として保存
        min_js_path = js_path.parent / f"{js_path.stem}.min.js"
        min_js_path.write_text(minified_js, encoding='utf-8')
        
        original_size = len(original_js)
        minified_size = len(minified_js)
        reduction = ((original_size - minified_size) / original_size) * 100
        
        print(f"✅ {js_path.name} 圧縮完了:")
        print(f"   {original_size:,} bytes → {minified_size:,} bytes ({reduction:.1f}% 削減)")

if __name__ == '__main__':
    main()
```

**HTML修正**: 全ページの `<head>` 内で `.min.css` / `.min.js` を読み込む

```html
<!-- 修正前 -->
<link rel="stylesheet" href="/static/style.css">
<script src="/static/exit-intent.js"></script>

<!-- 修正後 -->
<link rel="stylesheet" href="/static/style.min.css">
<script src="/static/exit-intent.min.js"></script>
```

### 5-3. 自動圧縮ワークフロー

**新規ファイル**: `.github/workflows/minify-assets.yml`

```yaml
name: Minify CSS/JS on Push

on:
  push:
    paths:
      - 'static/style.css'
      - 'static/*.js'
      - '!static/*.min.css'
      - '!static/*.min.js'

jobs:
  minify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run minify script
        run: python scripts/minify_assets.py
      
      - name: Commit minified files
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add static/*.min.css static/*.min.js
          git diff --staged --quiet || git commit -m "chore: auto-minify CSS/JS [skip ci]"
          git push
```

---

## 📦 施策6: 未コミットファイル整理

### 6-1. ドキュメントファイルの移動

**実行コマンド**:
```bash
# docs/ ディレクトリ作成（存在しない場合）
mkdir -p docs/guides

# ガイドドキュメントを移動
mv CLAUDE_CODE_INSTRUCTIONS_SEO.md docs/guides/
mv COMPETITOR_KEYWORD_ANALYSIS.md docs/guides/
mv EDDIE_PC_AUTOMATION.md docs/guides/
mv TWITTER_BOT_ENHANCEMENT.md docs/guides/

# テストスクリプトを削除（本番環境では不要）
rm scripts/test_telegram.py
rm scripts/test_telegram_v2.py
```

### 6-2. Git Commit

```bash
# ステージング
git add docs/logs/2026-03-04.md
git add docs/guides/

# コミット
git commit -m "docs: 直帰率対策実装ログ + ガイドドキュメント整理

- 2026-03-04 作業ログ追加
- SEO実装ガイド、競合分析、Eddie-PC設計書、Twitter強化ガイドを docs/guides/ へ移動
- テストスクリプト削除（本番環境クリーンアップ）
"
```

---

## 🚀 実装手順（Claude Code実行時）

### Phase 1: サイドバー・フッター（20分）
1. `templates/index.html` にサイドバー・フッター HTML追加
2. `static/style.css` に CSS追加
3. `scripts/generate_game_pages.py` 修正してゲームページにもフッター追加
4. 全413ゲームページ再生成: `python scripts/generate_game_pages.py`

### Phase 2: Exit Intent & Scroll CTA（15分）
1. `static/exit-intent.js` 作成
2. `static/style.css` に CSS追加
3. 全HTMLに `<script src="/static/exit-intent.js"></script>` 追加
4. テスト: ローカルでページ開いてマウス上端移動 → モーダル表示確認

### Phase 3: 記事内CTA（10分）
1. `scripts/generate_game_pages.py` 修正（2箇所にCTA挿入）
2. `static/style.css` に CSS追加
3. 全413ゲームページ再生成

### Phase 4: パンくずリスト（10分）
1. `scripts/generate_game_pages.py` に BreadcrumbList Schema + HTML追加
2. `static/style.css` に CSS追加
3. 全413ゲームページ再生成

### Phase 5: 速度改善（15分）
1. 全HTMLの `<img>` タグに `loading="lazy"` 追加
2. `scripts/minify_assets.py` 作成
3. `python scripts/minify_assets.py` 実行
4. 全HTMLの CSS/JS パスを `.min.css` / `.min.js` に変更
5. `.github/workflows/minify-assets.yml` 作成

### Phase 6: ファイル整理（5分）
1. `mkdir -p docs/guides`
2. ドキュメント4ファイルを移動
3. テストスクリプト2つ削除
4. `git add` + `git commit`

### Phase 7: 最終確認（5分）
1. ローカルでサーバー起動: `python app.py`
2. トップページ確認: サイドバー表示、フッター表示
3. ゲームページ確認: パンくず、CTA×2、関連ゲーム、フッター
4. Exit Intent テスト: マウス上端移動
5. Scroll CTA テスト: 50%スクロール
6. Git push

---

## 🎯 成功基準

### 定量指標（1週間後に測定）
- 直帰率: 70% → 50%以下
- ページ/セッション: 1.2 → 2.5以上
- 平均セッション時間: 45秒 → 2分以上
- Exit Intent転換率: 5%以上（モーダル表示→クリック）
- Scroll CTA転換率: 3%以上

### 定性確認
- ✅ 人気ゲームランキングが正しく表示される
- ✅ ジャンル別リンクが機能する
- ✅ Exit Intent が初回のみ表示（sessionStorage制御）
- ✅ Scroll 50%でCTAがスライドイン
- ✅ パンくずリストが Search Console で認識される
- ✅ 画像遅延読み込みで初期表示速度向上
- ✅ CSS/JS圧縮で転送量削減

---

## 📝 注意事項

### セッションストレージの制御
- Exit Intent と Scroll CTA は同一セッション内で1回のみ表示
- タブを閉じて再度開くと再表示される（意図的）
- ユーザーエクスペリエンスを損なわないバランス重視

### レスポンシブ対応
- 全施策はモバイル対応必須
- サイドバーは768px以下で縦積み
- CTAボタンは375pxでフル幅表示

### パフォーマンス
- 画像遅延読み込みで初期表示3秒以内（目標）
- CSS/JS圧縮で30-40%のファイルサイズ削減
- Google PageSpeed Insights スコア 80点以上（目標）

### SEO
- パンくずリストの Schema.org は Google Search Console で検証
- 内部リンク増加で crawl depth 削減
- フッターリンクで全ページへのアクセス改善

---

## 🔧 トラブルシューティング

### Exit Intent が動かない
- `sessionStorage.clear()` で強制リセット
- ブラウザの開発者ツールで `mouseleave` イベント確認

### Scroll CTA が表示されない
- `console.log(scrollPercent)` でスクロール率確認
- `sessionStorage.getItem('scrollCtaShown')` を削除

### 画像が遅延読み込みされない
- `loading="lazy"` が全 `<img>` タグに追加されているか確認
- 古いブラウザは非対応（IE11など）→ Intersection Observer Polyfill検討

### ミニファイ後にJSエラー
- `minify_js()` はシンプルな実装なので複雑なJSは手動確認
- 必要に応じて `terser` などの専用ツール導入

---

## 📊 期待される効果

### 直帰率削減メカニズム
1. **サイドバー**: トップページ訪問者に人気ゲームへの導線提供 → 回遊率+25%
2. **フッター**: 各ページ下部でジャンル・記事へ誘導 → 回遊率+15%
3. **Exit Intent**: 離脱直前に診断CTAで引き止め → 離脱防止率10%
4. **Scroll CTA**: 読了後に次のアクションを提示 → 回遊率+20%
5. **記事内CTA**: コンテンツ閲覧中に診断への導線 → 回遊率+30%
6. **パンくず**: 上位階層へ戻りやすく → 回遊率+10%

### 合計期待効果
- **直帰率**: 70% → **45-50%** (▲20-25pt)
- **ページ/セッション**: 1.2 → **2.8-3.2** (+1.6-2.0ページ)
- **診断ツール利用率**: 5% → **12-15%** (+7-10pt)

---

## ✅ 完了チェックリスト

実装完了後、以下を確認:

- [ ] サイドバー（人気TOP10・新着・ジャンル別）が表示される
- [ ] フッター（4セクション）が全ページに表示される
- [ ] Exit Intent モーダルがマウス上端で表示される
- [ ] Scroll 50% で CTA がスライドイン表示される
- [ ] ゲームページのスペック表下にCTA表示
- [ ] ゲームページの予算別構成下にCTA表示
- [ ] パンくずリストが全ゲームページに表示される
- [ ] パンくずの Schema.org が `<head>` 内に存在
- [ ] 全画像に `loading="lazy"` が追加されている
- [ ] `static/style.min.css` が生成されている
- [ ] `static/exit-intent.min.js` が生成されている
- [ ] 全HTMLが `.min.css` / `.min.js` を読み込んでいる
- [ ] docs/guides/ にドキュメント4ファイルが移動済み
- [ ] テストスクリプト2つが削除済み
- [ ] Git commit & push 完了

---

**実装時間目安**: 合計 **80分** (Claude Code ターボモード想定)

**Co-Authored-By**: Claude Opus 4.6 <noreply@anthropic.com>
