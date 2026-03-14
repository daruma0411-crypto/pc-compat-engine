# Claude Code 実装指示書: BTO アフィリエイト移行

## 📌 プロジェクト概要

PC互換性チェッカーを、**パーツ診断型から BTO PC 推薦型へ移行**する。

### 現状
- ゲーム推奨スペックを表示 → Amazon/楽天のパーツリンク
- 443ゲームのスペックデータあり（`workspace/data/steam/games.jsonl`）
- Flask + Claude API で動作

### 目標
- ゲーム名 + 予算 → 最適な BTO PC を推薦
- アフィリエイトリンク: BTO メーカー（ドスパラ、マウス、パソコン工房等）
- **URL構造は変更しない**（SEO維持のため）
- 既存の Schema.org / Analytics は維持

---

## 🎯 実装タスク（優先順位順）

### フェーズ1: BTOデータベース構築

#### タスク1.1: スクレイピングスクリプト作成

**ファイル:** `scripts/scrape_bto.py`

**実装内容:**
```python
"""
BTO メーカーから製品データをスクレイピング

対象メーカー:
- ドスパラ（GALLERIA シリーズ）
- マウスコンピューター（G-Tune シリーズ）
- パソコン工房（LEVEL∞ シリーズ）

取得データ:
- 製品名
- 価格（税込）
- CPU（型番 + スペック）
- GPU（型番 + VRAM）
- RAM（容量 + 種類 + 速度）
- ストレージ（容量 + 種類）
- 電源（ワット数 + 認証）
- 製品URL
- 画像URL
- 最終更新日時

出力: workspace/data/bto/products.json
"""

# ターゲットURL例:
# https://www.dospara.co.jp/5shopping/search.php?tg=4&tc=142
# https://www.mouse-jp.co.jp/store/brand/g-tune/
# https://www.pc-koubou.jp/products/

# 必要ライブラリ: requests, beautifulsoup4, lxml

# 注意事項:
# - robots.txt を確認
# - User-Agent を設定
# - レート制限（1秒に1リクエスト以下）
# - エラーハンドリング（404, タイムアウト等）
```

**データスキーマ:**
```json
{
  "products": [
    {
      "id": "dospar_galleria_xa7c_r47",
      "maker": "ドスパラ",
      "series": "GALLERIA",
      "model": "XA7C-R47",
      "price_jpy": 249980,
      "price_updated_at": "2026-03-03T12:00:00+09:00",
      "specs": {
        "cpu": {
          "name": "Intel Core i7-14700F",
          "cores": 20,
          "threads": 28
        },
        "gpu": {
          "name": "NVIDIA GeForce RTX 4070",
          "vram_gb": 12
        },
        "ram": {
          "capacity_gb": 32,
          "type": "DDR4",
          "speed_mhz": 3200
        },
        "storage": [
          {
            "type": "NVMe SSD",
            "capacity_gb": 1000
          }
        ],
        "psu": {
          "wattage": 750,
          "certification": "80 PLUS GOLD"
        }
      },
      "performance": {
        "target_resolution": "1440p",
        "target_fps": 144
      },
      "url": "https://www.dospara.co.jp/...",
      "image_url": "https://...",
      "tags": ["ゲーミング", "コスパ", "初心者向け"]
    }
  ]
}
```

---

#### タスク1.2: データベーススキーマ検証

**ファイル:** `scripts/validate_bto_data.py`

```python
"""
BTO製品データの整合性チェック

検証項目:
- 必須フィールドの存在確認
- 価格が正の数値
- URL の有効性
- 画像URLの有効性（HTTP 200確認）
- スペック値の妥当性（CPUコア数 > 0 等）

エラー時: 該当製品をスキップ or 警告表示
"""
```

---

### フェーズ2: API エンドポイント実装

#### タスク2.1: `/api/recommend` エンドポイント

**ファイル:** `app.py`

**実装内容:**
```python
@app.route('/api/recommend', methods=['POST'])
def recommend_bto():
    """
    BTO PC 推薦エンドポイント
    
    Request Body:
    {
      "game": "Cyberpunk 2077",  # ゲーム名（任意）
      "budget": 250000,          # 予算（円）
      "resolution": "1440p",     # 解像度（1080p/1440p/4K）
      "target_fps": 144          # 目標FPS
    }
    
    Response:
    {
      "recommendations": [
        {
          "rank": 1,
          "product": { BTO製品データ },
          "match_score": 95,
          "reasons": [
            "予算内に収まる（¥249,980）",
            "推奨スペックを満たす",
            "コスパが良い"
          ],
          "affiliate_link": "https://..."  # ASP経由のアフィリエイトリンク
        },
        ...
      ],
      "game_requirements": {
        "minimum": { CPU, GPU, RAM },
        "recommended": { CPU, GPU, RAM }
      }
    }
    
    推薦ロジック:
    1. ゲーム名から推奨スペックを取得（games.jsonl）
    2. 予算内のBTO製品をフィルタリング
    3. スペックマッチングスコア計算:
       - GPU性能（重み: 50%）
       - CPU性能（重み: 30%）
       - RAM容量（重み: 10%）
       - 価格コスパ（重み: 10%）
    4. 上位3製品を返す
    """
    pass
```

**GPU性能比較テーブル（簡易版）:**
```python
GPU_PERFORMANCE_SCORE = {
    # RTX 50 series
    "RTX 5090": 100,
    "RTX 5080": 85,
    "RTX 5070 Ti": 75,
    "RTX 5070": 70,
    
    # RTX 40 series
    "RTX 4090": 95,
    "RTX 4080": 80,
    "RTX 4070 Ti": 72,
    "RTX 4070": 65,
    "RTX 4060 Ti": 55,
    "RTX 4060": 50,
    
    # RTX 30 series
    "RTX 3090": 85,
    "RTX 3080": 75,
    "RTX 3070": 60,
    "RTX 3060 Ti": 52,
    "RTX 3060": 48,
    
    # AMD
    "RX 7900 XTX": 88,
    "RX 7900 XT": 78,
    "RX 7800 XT": 68,
    "RX 7700 XT": 58,
}
```

---

#### タスク2.2: アフィリエイトリンク生成

**ファイル:** `utils/affiliate.py`

```python
"""
ASPアフィリエイトリンク生成

設定（環境変数）:
- A8_AFFILIATE_ID
- VALUECOMMERCE_AFFILIATE_ID
- MOSHIMO_AFFILIATE_ID

メーカー別ASPマッピング:
- ドスパラ → A8.net
- マウス → バリューコマース
- パソコン工房 → もしもアフィリエイト

関数:
- generate_affiliate_link(product_url, maker) → アフィリエイトURL
"""

def generate_affiliate_link(product_url: str, maker: str) -> str:
    """
    製品URLをアフィリエイトリンクに変換
    
    例:
    https://www.dospara.co.jp/... 
    → https://px.a8.net/svt/ejp?a8mat=...&a8ejpredirect=https://www.dospara.co.jp/...
    """
    pass
```

---

### フェーズ3: フロントエンド改修

#### タスク3.1: トップページUI変更

**ファイル:** `static/index.html`, `static/app.js`, `static/style.css`

**変更内容:**

**Before:**
```
AI ショップ店員が自作PCを最適提案
→ パーツ診断
→ Amazon/楽天リンク
```

**After:**
```
AIがあなたに最適なゲーミングPCを診断
→ ゲーム名 + 予算入力
→ BTO製品カード3枚表示（購入ボタン付き）
```

**UIコンポーネント:**
```html
<!-- 入力フォーム -->
<form id="bto-recommend-form">
  <input type="text" placeholder="ゲーム名（例: Cyberpunk 2077）">
  <input type="number" placeholder="予算（円）" value="250000">
  <select name="resolution">
    <option value="1080p">1080p (Full HD)</option>
    <option value="1440p">1440p (WQHD)</option>
    <option value="4K">4K (Ultra HD)</option>
  </select>
  <button type="submit">最適なPCを診断</button>
</form>

<!-- BTO製品カード -->
<div class="bto-card">
  <img src="product_image_url">
  <h3>ドスパラ GALLERIA XA7C-R47</h3>
  <div class="price">¥249,980</div>
  <div class="specs">
    <p>CPU: Intel Core i7-14700F</p>
    <p>GPU: RTX 4070 (12GB)</p>
    <p>RAM: 32GB DDR4</p>
  </div>
  <div class="match-info">
    <span class="match-score">マッチ度: 95%</span>
    <ul class="reasons">
      <li>予算内に収まる</li>
      <li>推奨スペックを満たす</li>
    </ul>
  </div>
  <a href="affiliate_link" class="btn-purchase">このPCを購入</a>
</div>
```

**JavaScript:**
```javascript
// /api/recommend を呼び出し
async function recommendBTO() {
  const response = await fetch('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      game: document.querySelector('[name="game"]').value,
      budget: parseInt(document.querySelector('[name="budget"]').value),
      resolution: document.querySelector('[name="resolution"]').value,
      target_fps: 144
    })
  });
  
  const data = await response.json();
  renderBTOCards(data.recommendations);
}
```

---

#### タスク3.2: ゲームページ改修

**ファイル:** `templates/game.html`（存在しない場合は新規作成）

**変更内容:**

**Before:**
```
推奨スペック表 → Amazonパーツリンク
```

**After:**
```
推奨スペック表

このゲームを快適にプレイできるおすすめPC:
【予算15万円】ドスパラ GALLERIA RM5C-R46T
【予算25万円】マウス G-Tune DG-I7G70
【予算35万円】パソコン工房 LEVEL∞ i9-RTX4070Ti

→ 各BTOアフィリエイトリンク
```

**実装:**
```python
@app.route('/game/<game_slug>')
def game_page(game_slug):
    """
    ゲームページ
    
    1. games.jsonl からゲーム情報取得
    2. /api/recommend で3つの価格帯のBTO推薦
       - 低価格: 15万円
       - 中価格: 25万円
       - 高価格: 35万円
    3. テンプレートレンダリング
    """
    pass
```

---

### フェーズ4: 既存機能の維持

#### タスク4.1: Schema.org 維持

- トップページの FAQPage, SoftwareApplication Schema → 維持
- ゲームページの VideoGame Schema → 維持
- 新規: BTO製品に Product Schema 追加

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "ドスパラ GALLERIA XA7C-R47",
  "offers": {
    "@type": "Offer",
    "price": "249980",
    "priceCurrency": "JPY",
    "url": "https://..."
  }
}
```

#### タスク4.2: Google Analytics 維持

- トラッキングコード（G-PPNEBG625J）維持
- 新規イベント追加:
  - `bto_recommend_view` - BTO推薦表示
  - `bto_affiliate_click` - アフィリエイトリンククリック

---

## 🚫 制約事項

### 絶対に変更してはいけないもの

1. **URL構造**
   - ✅ `/` → トップページ
   - ✅ `/game/<game_slug>` → ゲームページ
   - ❌ `/game/<game_id>` に変更しない
   - ❌ `/products/<bto_id>` などの新規URLを作らない

2. **既存ファイル**
   - ✅ `workspace/data/steam/games.jsonl` → 読み取り専用、削除・変更禁止
   - ✅ `static/index.html` の Schema.org タグ → 維持
   - ✅ Google Analytics タグ → 維持

3. **環境変数**
   - ✅ `ANTHROPIC_API_KEY` → 既存診断ロジックで使用中、維持
   - ✅ `REPLICATE_API_TOKEN` → 画像生成機能で使用中、維持
   - ✅ 新規追加OK: `A8_AFFILIATE_ID` 等

---

## 📦 依存ライブラリ

**追加インストール必要:**
```bash
pip install beautifulsoup4 lxml requests
```

**既存（維持）:**
- Flask
- python-dotenv
- （その他 requirements.txt 参照）

---

## ✅ 完了条件

### フェーズ1完了:
- [ ] `workspace/data/bto/products.json` に50製品以上のデータ
- [ ] 価格・スペック・URL が全て取得できている
- [ ] バリデーションスクリプトでエラーなし

### フェーズ2完了:
- [ ] `/api/recommend` エンドポイントが動作
- [ ] ゲーム名 + 予算で適切なBTO製品を推薦
- [ ] アフィリエイトリンクが正しく生成される

### フェーズ3完了:
- [ ] トップページで BTO推薦UIが表示
- [ ] ゲームページでおすすめPCが3つ表示
- [ ] URL構造は変更なし
- [ ] Schema.org, Analytics 維持

---

## 🎯 優先順位

**高:**
1. タスク1.1（BTOスクレイピング）
2. タスク2.1（/api/recommend）
3. タスク3.1（トップページUI）

**中:**
4. タスク3.2（ゲームページ改修）
5. タスク4.1（Schema.org追加）

**低:**
6. タスク1.2（データバリデーション）
7. タスク4.2（Analytics イベント）

---

## 📝 実装メモ

### スクレイピング時の注意

**robots.txt を確認:**
```bash
curl https://www.dospara.co.jp/robots.txt
curl https://www.mouse-jp.co.jp/robots.txt
curl https://www.pc-koubou.jp/robots.txt
```

**User-Agent 設定例:**
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) PC-Compat-Engine/1.0 (+https://pc-jisaku.com/)'
}
```

### GPU名の正規化

製品ページの表記揺れ対策:
```python
# "GeForce RTX 4070" → "RTX 4070"
# "NVIDIA RTX4070" → "RTX 4070"
# "RTX4070 12GB" → "RTX 4070"

def normalize_gpu_name(gpu_str):
    gpu_str = gpu_str.upper()
    gpu_str = re.sub(r'NVIDIA|GEFORCE|AMD|RADEON', '', gpu_str)
    gpu_str = re.sub(r'\s+', ' ', gpu_str).strip()
    # RTX4070 → RTX 4070
    gpu_str = re.sub(r'(RTX|RX)(\d)', r'\1 \2', gpu_str)
    return gpu_str
```

---

## 🚀 実装開始コマンド

Claude Code で実装する場合:

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# フェーズ1: BTOデータベース構築
claude "この指示書（CLAUDE_CODE_INSTRUCTIONS.md）のフェーズ1を実装してください。
ドスパラ、マウス、パソコン工房から BTO製品データをスクレイピングし、
workspace/data/bto/products.json に保存してください。"

# フェーズ2: API実装
claude "フェーズ2を実装してください。/api/recommend エンドポイントを追加し、
ゲーム名と予算から最適なBTO製品を推薦する機能を作成してください。"

# フェーズ3: UI改修
claude "フェーズ3を実装してください。トップページとゲームページのUIを
BTO推薦型に変更してください。URL構造は変更しないでください。"
```

---

## 📞 質問・不明点

実装中に不明点があれば、以下を確認:

1. **ゲームデータの構造**: `workspace/data/steam/games.jsonl` を参照
2. **既存API**: `app.py` の `/api/diagnose` を参考
3. **フロントエンド**: `static/app.js`, `static/style.css` を参照

---

以上です。実装頑張ってください！ 🚀
