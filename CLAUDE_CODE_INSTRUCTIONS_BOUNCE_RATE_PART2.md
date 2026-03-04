# Claude Code 実装指示書: 直帰率対策 Part 2（未実装分）

## 📋 実装概要

**目的**: Part 1で未実装だった直帰率対策を追加実装

**未実装項目**:
1. トップページ サイドバー（人気TOP10・新着・ジャンル別）
2. Exit Intent Modal（マウス上端で表示）
3. Scroll 50% CTA（スクロールでスライドイン）
4. フッター強化（4セクション版）
5. 記事内CTA（スペック表・予算構成の下）
6. 画像遅延読み込み（loading="lazy"）
7. CSS/JSミニファイ

**実装時間**: 30-40分

---

## 🎯 施策1: トップページ サイドバー（15分）

### ファイル: `templates/index.html`

**追加場所**: メインコンテンツの横に追加（既存の3つのカードの右側）

```html
<!-- 既存の3つのカード（ゲームを快適に、パーツの互換性を確認、おすすめPCを探す）の後 -->

<div class="content-with-sidebar">
  <main class="main-content">
    <!-- 既存の3つのカードをここに移動 -->
  </main>
  
  <aside class="sidebar">
    <section class="sidebar-section">
      <h3>🔥 人気ゲームTOP10</h3>
      <ol class="popular-games-list">
        <li><a href="/game/baldurs-gate-3">Baldur's Gate 3</a></li>
        <li><a href="/game/elden-ring">Elden Ring</a></li>
        <li><a href="/game/palworld">Palworld</a></li>
        <li><a href="/game/helldivers-2">Helldivers 2</a></li>
        <li><a href="/game/final-fantasy-vii-rebirth">FF7 Rebirth</a></li>
        <li><a href="/game/dragons-dogma-2">Dragon's Dogma 2</a></li>
        <li><a href="/game/monster-hunter-wilds">Monster Hunter Wilds</a></li>
        <li><a href="/game/warhammer-40000-space-marine-2">Space Marine 2</a></li>
        <li><a href="/game/street-fighter-6">Street Fighter 6</a></li>
        <li><a href="/game/黒神話悟空">黒神話 悟空</a></li>
      </ol>
    </section>

    <section class="sidebar-section">
      <h3>✨ 新着ゲーム</h3>
      <ul class="new-games-list">
        <li><a href="/game/kingdom-come-deliverance-ii">Kingdom Come: Deliverance II</a></li>
        <li><a href="/game/civilization-vii">Civilization VII</a></li>
        <li><a href="/game/assetto-corsa-evo">Assetto Corsa EVO</a></li>
        <li><a href="/game/clair-obscur-expedition-33">Clair Obscur: Expedition 33</a></li>
        <li><a href="/game/death-stranding-2-on-the-beach">Death Stranding 2</a></li>
      </ul>
    </section>

    <section class="sidebar-section">
      <h3>🎮 ジャンル別</h3>
      <ul class="genre-list">
        <li><a href="#rpg">RPG</a></li>
        <li><a href="#fps">FPS・シューター</a></li>
        <li><a href="#racing">レーシング</a></li>
        <li><a href="#simulation">シミュレーション</a></li>
        <li><a href="#strategy">ストラテジー</a></li>
        <li><a href="#action">アクション</a></li>
      </ul>
    </section>
  </aside>
</div>
```

### CSS: `static/style.css`

```css
/* サイドバーレイアウト */
.content-with-sidebar {
  display: flex;
  max-width: 1400px;
  margin: 0 auto;
  gap: 24px;
  padding: 20px;
}

.main-content {
  flex: 1;
  min-width: 0;
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
  margin: 0 0 12px 0;
  color: #1a1a1a;
}

.popular-games-list {
  list-style: none;
  padding: 0;
  margin: 0;
  counter-reset: popular;
}

.popular-games-list li {
  counter-increment: popular;
  margin-bottom: 8px;
}

.popular-games-list li::before {
  content: counter(popular) ". ";
  font-weight: 600;
  color: #2563eb;
  margin-right: 4px;
}

.popular-games-list a,
.new-games-list a,
.genre-list a {
  color: #1a1a1a;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.popular-games-list a:hover,
.new-games-list a:hover,
.genre-list a:hover {
  color: #2563eb;
  text-decoration: underline;
}

.new-games-list,
.genre-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.new-games-list li,
.genre-list li {
  margin-bottom: 8px;
  padding-left: 16px;
  position: relative;
}

.new-games-list li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: #2563eb;
}

.genre-list li::before {
  content: "🎮";
  position: absolute;
  left: -4px;
}

/* レスポンシブ */
@media (max-width: 1024px) {
  .content-with-sidebar {
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

---

## 🎯 施策2: Exit Intent Modal + Scroll CTA（10分）

### 新規ファイル: `static/bounce-prevention.js`

```javascript
// Exit Intent Detection
let exitIntentShown = false;

document.addEventListener('mouseleave', (e) => {
  if (e.clientY <= 0 && !exitIntentShown && !sessionStorage.getItem('exitIntentShown')) {
    showExitIntentModal();
    exitIntentShown = true;
    sessionStorage.setItem('exitIntentShown', 'true');
  }
});

function showExitIntentModal() {
  const modal = document.createElement('div');
  modal.className = 'exit-intent-modal';
  modal.innerHTML = `
    <div class="exit-modal-overlay"></div>
    <div class="exit-modal-content">
      <button class="exit-modal-close" onclick="closeExitIntent()">&times;</button>
      <h2>ちょっと待って！</h2>
      <p>あなたのPCでゲームが動くか、<br>30秒で無料診断できます</p>
      <a href="/" class="exit-modal-cta">今すぐ診断する →</a>
    </div>
  `;
  document.body.appendChild(modal);
  setTimeout(() => modal.classList.add('show'), 10);
}

function closeExitIntent() {
  const modal = document.querySelector('.exit-intent-modal');
  if (modal) {
    modal.classList.remove('show');
    setTimeout(() => modal.remove(), 300);
  }
}

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

### CSS: `static/style.css` に追加

```css
/* Exit Intent Modal */
.exit-intent-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10000;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.exit-intent-modal.show {
  opacity: 1;
  pointer-events: auto;
}

.exit-modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
}

.exit-modal-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #ffffff;
  border-radius: 16px;
  padding: 40px 32px;
  max-width: 480px;
  text-align: center;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.exit-modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 32px;
  color: #666;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 32px;
  height: 32px;
}

.exit-modal-close:hover {
  color: #000;
}

.exit-modal-content h2 {
  font-size: 28px;
  margin: 0 0 16px 0;
  color: #1a1a1a;
}

.exit-modal-content p {
  font-size: 16px;
  line-height: 1.6;
  color: #666;
  margin: 0 0 24px 0;
}

.exit-modal-cta {
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

.exit-modal-cta:hover {
  background: #1d4ed8;
}

/* Scroll CTA */
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
  line-height: 1;
  padding: 0;
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

### HTML に追加: 全ページの `</body>` 直前

```html
<script src="/static/bounce-prevention.js"></script>
```

---

## 🎯 施策3: フッター強化（5分）

### ファイル: `templates/index.html` + 全ゲームページ

**既存のフッターを置き換え**:

```html
<footer class="site-footer-enhanced">
  <div class="footer-content">
    <div class="footer-section">
      <h4>PC互換チェッカーとは</h4>
      <p>14,000件以上のゲーム×PC構成の互換性データベース。あなたのPCでゲームが動くか瞬時に診断。</p>
    </div>
    
    <div class="footer-section">
      <h4>人気ジャンル</h4>
      <ul>
        <li><a href="#rpg">RPG</a></li>
        <li><a href="#fps">FPS・シューター</a></li>
        <li><a href="#racing">レーシング</a></li>
        <li><a href="#simulation">シミュレーション</a></li>
      </ul>
    </div>
    
    <div class="footer-section">
      <h4>おすすめ記事</h4>
      <ul>
        <li><a href="/guide">GPU選びガイド</a></li>
        <li><a href="/guide">予算別構成例</a></li>
        <li><a href="/guide">RAM容量の選び方</a></li>
        <li><a href="/guide">トラブルシューティング</a></li>
      </ul>
    </div>
    
    <div class="footer-section">
      <h4>お問い合わせ</h4>
      <ul>
        <li><a href="/about">サイトについて</a></li>
        <li><a href="/privacy">プライバシーポリシー</a></li>
        <li><a href="https://twitter.com/syoyutarou">Twitter</a></li>
      </ul>
    </div>
  </div>
  
  <div class="footer-bottom">
    <p>&copy; 2026 PC互換チェッカー. All rights reserved.</p>
  </div>
</footer>
```

### CSS: `static/style.css` に追加

```css
.site-footer-enhanced {
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
  margin: 0 0 16px 0;
  color: #2563eb;
}

.footer-section p {
  font-size: 14px;
  line-height: 1.6;
  color: #b0b0b0;
  margin: 0;
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

## 🎯 施策4: 画像遅延読み込み（5分）

### 対象ファイル: 全HTMLファイル

**一括置換**:

```
置換前: <img src=
置換後: <img loading="lazy" src=
```

**PowerShell コマンド**:
```powershell
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# トップページ
(Get-Content templates/index.html) -replace '<img src=', '<img loading="lazy" src=' | Set-Content templates/index.html

# 全ゲームページ
Get-ChildItem static/game/*.html | ForEach-Object {
    (Get-Content $_.FullName) -replace '<img src=', '<img loading="lazy" src=' | Set-Content $_.FullName
}
```

---

## 🎯 施策5: CSS/JSミニファイ（5分）

### 新規ファイル: `scripts/minify_assets.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

def minify_css(css):
    css = re.sub(r'/\*[\s\S]*?\*/', '', css)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};:,])\s*', r'\1', css)
    return css.strip()

def minify_js(js):
    js = re.sub(r'//.*?$', '', js, flags=re.MULTILINE)
    js = re.sub(r'/\*[\s\S]*?\*/', '', js)
    js = re.sub(r'\n\s*\n', '\n', js)
    return js

# CSS
css_path = Path('static/style.css')
if css_path.exists():
    original = css_path.read_text(encoding='utf-8')
    minified = minify_css(original)
    Path('static/style.min.css').write_text(minified, encoding='utf-8')
    print(f"✅ CSS: {len(original)} → {len(minified)} bytes ({100-len(minified)/len(original)*100:.1f}% reduction)")

# JS
for js_path in Path('static').glob('*.js'):
    if js_path.stem.endswith('.min'):
        continue
    original = js_path.read_text(encoding='utf-8')
    minified = minify_js(original)
    Path(f"static/{js_path.stem}.min.js").write_text(minified, encoding='utf-8')
    print(f"✅ {js_path.name}: {len(original)} → {len(minified)} bytes ({100-len(minified)/len(original)*100:.1f}% reduction)")
```

**実行**:
```powershell
python scripts/minify_assets.py
```

**HTML修正**: 全ページで

```html
<!-- 変更前 -->
<link rel="stylesheet" href="/static/style.css">
<script src="/static/bounce-prevention.js"></script>

<!-- 変更後 -->
<link rel="stylesheet" href="/static/style.min.css">
<script src="/static/bounce-prevention.min.js"></script>
```

---

## 🚀 実装手順

1. **トップページ サイドバー追加** (15分)
   - `templates/index.html` 修正
   - `static/style.css` に CSS追加

2. **Exit Intent + Scroll CTA** (10分)
   - `static/bounce-prevention.js` 作成
   - `static/style.css` に CSS追加
   - 全HTMLに `<script>` タグ追加

3. **フッター強化** (5分)
   - 既存フッターを4セクション版に置き換え
   - `static/style.css` に CSS追加

4. **画像遅延読み込み** (5分)
   - PowerShell一括置換実行

5. **CSS/JSミニファイ** (5分)
   - `scripts/minify_assets.py` 作成
   - 実行して `.min.css` / `.min.js` 生成
   - HTML を `.min` ファイルに変更

6. **動作確認** (5分)
   - ローカルサーバー起動
   - Exit Intent テスト（マウス上端移動）
   - Scroll CTA テスト（50%スクロール）
   - サイドバー表示確認

7. **Git commit & push**

---

## ✅ 完了チェックリスト

- [ ] トップページにサイドバー表示
- [ ] Exit Intent Modal 動作（マウス上端）
- [ ] Scroll CTA 表示（50%スクロール）
- [ ] フッター4セクション表示
- [ ] 全画像に `loading="lazy"` 追加
- [ ] `.min.css` / `.min.js` 生成
- [ ] HTML が `.min` ファイル読込

---

**実装時間目安**: 40分

**Co-Authored-By**: Claude Opus 4.6 <noreply@anthropic.com>
