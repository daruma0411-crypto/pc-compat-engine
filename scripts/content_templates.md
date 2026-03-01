# ゲームページ用コンテンツテンプレート

このファイルは、各ゲームページに追加するコンテンツのテンプレート集です。

---

## 📋 テンプレート1: FAQセクション

各ゲームページの下部に追加するFAQセクション：

```html
<section class="faq-section">
  <h2>よくある質問</h2>
  
  <div class="faq-item">
    <h3>Q1. {{GAME_NAME}}の推奨スペックは？</h3>
    <p>
      {{GAME_NAME}}のPC推奨スペックは以下の通りです：
    </p>
    <ul>
      <li><strong>CPU</strong>: {{RECOMMENDED_CPU}}</li>
      <li><strong>GPU</strong>: {{RECOMMENDED_GPU}}</li>
      <li><strong>メモリ</strong>: {{RECOMMENDED_RAM}}GB RAM</li>
      <li><strong>ストレージ</strong>: SSD {{STORAGE_GB}}GB</li>
    </ul>
    <p>
      これらのスペックを満たせば、高画質設定で60fps以上の快適なプレイが可能です。
    </p>
  </div>
  
  <div class="faq-item">
    <h3>Q2. 予算{{BUDGET}}万円で{{GAME_NAME}}用PCは組めますか？</h3>
    <p>
      はい、予算{{BUDGET}}万円で{{GAME_NAME}}を快適に遊べるPCを組むことが可能です。
    </p>
    <p><strong>推奨構成例</strong>：</p>
    <ul>
      <li>GPU: {{RECOMMENDED_GPU_MODEL}} (約{{GPU_PRICE}}万円)</li>
      <li>CPU: {{RECOMMENDED_CPU_MODEL}} (約{{CPU_PRICE}}万円)</li>
      <li>RAM: 16GB DDR4 (約0.8万円)</li>
      <li>SSD: 500GB NVMe (約0.6万円)</li>
      <li>電源・ケース: 約1.5万円</li>
    </ul>
    <p>合計：約{{BUDGET}}万円で、{{EXPECTED_FPS}}fpsの安定動作が期待できます。</p>
  </div>
  
  <div class="faq-item">
    <h3>Q3. {{GAME_NAME}}はグラボなしで動きますか？</h3>
    <p>
      {{GAME_NAME}}を快適に遊ぶには、専用グラフィックボード（GPU）が必須です。
    </p>
    <p>
      内蔵GPU（Intel UHD Graphics、Iris Xe、AMD Radeon統合グラフィックス）では、
      低画質設定でも快適な動作は期待できません。
    </p>
    <p><strong>最低でも以下のGPUを推奨</strong>：</p>
    <ul>
      <li>エントリー: GTX 1650 / RX 5500 XT (低～中画質30fps)</li>
      <li>推奨: RTX 4060 / RX 7600 (高画質60fps)</li>
      <li>快適: RTX 5070 / RX 7800 XT (最高画質144fps)</li>
    </ul>
  </div>
  
  <div class="faq-item">
    <h3>Q4. ノートPCでも{{GAME_NAME}}は遊べますか？</h3>
    <p>
      はい、ゲーミングノートPCなら{{GAME_NAME}}を快適に遊べます。
    </p>
    <p><strong>推奨ゲーミングノートスペック</strong>：</p>
    <ul>
      <li>GPU: RTX 4050 / RTX 4060 Laptop</li>
      <li>CPU: Core i5-13500H / Ryzen 7 7735HS 以上</li>
      <li>RAM: 16GB</li>
      <li>価格帯: 約12～18万円</li>
    </ul>
    <p>
      ただし、ノートPCは熱対策が重要です。長時間プレイする場合は、
      冷却パッドの使用や、電源接続時のパフォーマンスモード設定を推奨します。
    </p>
  </div>
  
  <div class="faq-item">
    <h3>Q5. {{GAME_NAME}}におすすめのGPUは？</h3>
    <p>
      2026年3月時点で{{GAME_NAME}}におすすめのGPUは以下の通りです：
    </p>
    <table class="gpu-comparison">
      <thead>
        <tr>
          <th>GPU</th>
          <th>価格</th>
          <th>1080p FPS</th>
          <th>WQHD FPS</th>
          <th>コスパ</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>RTX 4060</td>
          <td>約4.5万円</td>
          <td>{{FPS_4060_1080P}}fps</td>
          <td>{{FPS_4060_WQHD}}fps</td>
          <td>★★★★★</td>
        </tr>
        <tr>
          <td>RTX 5070</td>
          <td>約7.5万円</td>
          <td>{{FPS_5070_1080P}}fps</td>
          <td>{{FPS_5070_WQHD}}fps</td>
          <td>★★★★☆</td>
        </tr>
        <tr>
          <td>RX 7800 XT</td>
          <td>約6万円</td>
          <td>{{FPS_7800XT_1080P}}fps</td>
          <td>{{FPS_7800XT_WQHD}}fps</td>
          <td>★★★★★</td>
        </tr>
      </tbody>
    </table>
    <p>
      <strong>コスパ重視</strong>: RTX 4060（約4.5万円）<br>
      <strong>バランス重視</strong>: RTX 5070（約7.5万円）<br>
      <strong>AMD派</strong>: RX 7800 XT（約6万円）
    </p>
  </div>
</section>
```

---

## 💰 テンプレート2: 予算別構成例

```html
<section class="budget-builds">
  <h2>予算別PC構成例</h2>
  
  <div class="build-card">
    <h3>💵 予算8万円構成（最低動作）</h3>
    <ul class="parts-list">
      <li><strong>CPU</strong>: Ryzen 5 5600 (¥15,980)</li>
      <li><strong>GPU</strong>: GTX 1650 (¥18,000)</li>
      <li><strong>マザーボード</strong>: B550M (¥8,500)</li>
      <li><strong>RAM</strong>: 16GB DDR4 (¥8,000)</li>
      <li><strong>SSD</strong>: 500GB (¥6,000)</li>
      <li><strong>電源</strong>: 550W (¥7,500)</li>
      <li><strong>ケース</strong>: MicroATX (¥5,000)</li>
    </ul>
    <p class="build-total"><strong>合計</strong>: 約8万円</p>
    <p class="build-performance">
      <strong>期待性能</strong>: 1080p 低～中設定 60fps<br>
      <strong>おすすめ度</strong>: ★★☆☆☆（最低限）
    </p>
  </div>
  
  <div class="build-card recommended">
    <h3>🎮 予算12万円構成（推奨）</h3>
    <ul class="parts-list">
      <li><strong>CPU</strong>: Ryzen 5 7600 (¥28,000)</li>
      <li><strong>GPU</strong>: RTX 4060 (¥45,000)</li>
      <li><strong>マザーボード</strong>: B650M (¥15,000)</li>
      <li><strong>RAM</strong>: 16GB DDR5 (¥10,000)</li>
      <li><strong>SSD</strong>: 1TB NVMe (¥10,000)</li>
      <li><strong>電源</strong>: 650W 80+ Bronze (¥9,000)</li>
      <li><strong>ケース</strong>: ATX (¥8,000)</li>
    </ul>
    <p class="build-total"><strong>合計</strong>: 約12万円</p>
    <p class="build-performance">
      <strong>期待性能</strong>: 1080p 高設定 144fps / WQHD 60fps<br>
      <strong>おすすめ度</strong>: ★★★★★（コスパ最高）
    </p>
  </div>
  
  <div class="build-card">
    <h3>⚡ 予算15万円構成（高性能）</h3>
    <ul class="parts-list">
      <li><strong>CPU</strong>: Ryzen 7 7700X (¥42,000)</li>
      <li><strong>GPU</strong>: RTX 5070 (¥75,000)</li>
      <li><strong>マザーボード</strong>: B650 (¥18,000)</li>
      <li><strong>RAM</strong>: 32GB DDR5 (¥18,000)</li>
      <li><strong>SSD</strong>: 1TB NVMe Gen4 (¥12,000)</li>
      <li><strong>電源</strong>: 750W 80+ Gold (¥12,000)</li>
      <li><strong>ケース</strong>: ATX (¥10,000)</li>
    </ul>
    <p class="build-total"><strong>合計</strong>: 約15万円</p>
    <p class="build-performance">
      <strong>期待性能</strong>: 1080p 240fps / WQHD 144fps / 4K 60fps<br>
      <strong>おすすめ度</strong>: ★★★★☆（快適重視）
    </p>
  </div>
</section>
```

---

## 📊 テンプレート3: GPU別性能比較表

```html
<section class="gpu-comparison-section">
  <h2>GPU別性能比較</h2>
  <p>{{GAME_NAME}}における主要GPUの性能比較です（2026年3月時点）：</p>
  
  <table class="gpu-table">
    <thead>
      <tr>
        <th>GPU</th>
        <th>価格</th>
        <th>1080p<br>低設定</th>
        <th>1080p<br>高設定</th>
        <th>WQHD<br>高設定</th>
        <th>4K<br>高設定</th>
        <th>コスパ</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>GTX 1650</td>
        <td>¥18,000</td>
        <td>60fps</td>
        <td>45fps</td>
        <td>30fps</td>
        <td>20fps</td>
        <td>★★☆☆☆</td>
      </tr>
      <tr>
        <td>RTX 3050</td>
        <td>¥28,000</td>
        <td>90fps</td>
        <td>60fps</td>
        <td>40fps</td>
        <td>25fps</td>
        <td>★★★☆☆</td>
      </tr>
      <tr class="highlight">
        <td>RTX 4060</td>
        <td>¥45,000</td>
        <td>180fps</td>
        <td>144fps</td>
        <td>90fps</td>
        <td>50fps</td>
        <td>★★★★★</td>
      </tr>
      <tr>
        <td>RX 7800 XT</td>
        <td>¥60,000</td>
        <td>240fps</td>
        <td>200fps</td>
        <td>140fps</td>
        <td>80fps</td>
        <td>★★★★★</td>
      </tr>
      <tr class="highlight">
        <td>RTX 5070</td>
        <td>¥75,000</td>
        <td>280fps</td>
        <td>240fps</td>
        <td>165fps</td>
        <td>100fps</td>
        <td>★★★★☆</td>
      </tr>
      <tr>
        <td>RTX 5080</td>
        <td>¥120,000</td>
        <td>360fps</td>
        <td>300fps</td>
        <td>220fps</td>
        <td>144fps</td>
        <td>★★★☆☆</td>
      </tr>
    </tbody>
  </table>
  
  <div class="recommendation">
    <h3>🎯 おすすめGPU</h3>
    <ul>
      <li><strong>コスパ最優先</strong>: RTX 4060（¥45,000）- 1080p 144fps安定</li>
      <li><strong>WQHD快適</strong>: RTX 5070（¥75,000）- WQHD 165fps</li>
      <li><strong>4K対応</strong>: RTX 5080（¥120,000）- 4K 144fps</li>
      <li><strong>AMD派</strong>: RX 7800 XT（¥60,000）- コスパ◎</li>
    </ul>
  </div>
</section>
```

---

## 🔗 テンプレート4: 関連ゲームリンク

```html
<section class="related-games">
  <h2>このスペックで遊べる他のゲーム</h2>
  <p>{{GAME_NAME}}と同程度のスペックで快適に遊べるゲーム：</p>
  
  <div class="game-cards">
    <div class="game-card">
      <h4>より軽量</h4>
      <ul>
        <li><a href="/game/{{LIGHTER_GAME_1}}">{{LIGHTER_GAME_1_NAME}}</a></li>
        <li><a href="/game/{{LIGHTER_GAME_2}}">{{LIGHTER_GAME_2_NAME}}</a></li>
      </ul>
    </div>
    
    <div class="game-card">
      <h4>同程度</h4>
      <ul>
        <li><a href="/game/{{SIMILAR_GAME_1}}">{{SIMILAR_GAME_1_NAME}}</a></li>
        <li><a href="/game/{{SIMILAR_GAME_2}}">{{SIMILAR_GAME_2_NAME}}</a></li>
      </ul>
    </div>
    
    <div class="game-card">
      <h4>やや重い</h4>
      <ul>
        <li><a href="/game/{{HEAVIER_GAME_1}}">{{HEAVIER_GAME_1_NAME}}</a></li>
        <li><a href="/game/{{HEAVIER_GAME_2}}">{{HEAVIER_GAME_2_NAME}}</a></li>
      </ul>
    </div>
  </div>
</section>
```

---

## 📱 テンプレート5: CTA（行動喚起）セクション

```html
<section class="cta-section">
  <div class="cta-box">
    <h3>🤖 AIに相談してみませんか？</h3>
    <p>
      予算や用途に合わせて、最適なPC構成をAIショップ店員が無料で提案します。<br>
      14,000件以上の互換性データを基に、パーツの組み合わせもチェック。
    </p>
    <a href="/" class="cta-button">無料でAI診断を受ける</a>
  </div>
  
  <div class="features">
    <div class="feature">
      <span class="icon">✅</span>
      <p>予算内で最適な構成提案</p>
    </div>
    <div class="feature">
      <span class="icon">🔍</span>
      <p>パーツ互換性を自動チェック</p>
    </div>
    <div class="feature">
      <span class="icon">💬</span>
      <p>チャットで気軽に相談</p>
    </div>
    <div class="feature">
      <span class="icon">🆓</span>
      <p>完全無料、登録不要</p>
    </div>
  </div>
</section>
```

---

## 🎨 CSS（スタイル例）

```css
/* FAQセクション */
.faq-section {
  max-width: 800px;
  margin: 40px auto;
  padding: 20px;
}

.faq-item {
  background: #f9f9f9;
  border-left: 4px solid #007bff;
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.faq-item h3 {
  color: #333;
  margin-top: 0;
}

/* 予算別構成カード */
.budget-builds {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin: 40px 0;
}

.build-card {
  background: #fff;
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 20px;
}

.build-card.recommended {
  border-color: #007bff;
  box-shadow: 0 4px 12px rgba(0,123,255,0.2);
}

.parts-list {
  list-style: none;
  padding: 0;
}

.parts-list li {
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.build-total {
  font-size: 1.2em;
  color: #007bff;
  margin-top: 15px;
}

/* GPU比較表 */
.gpu-table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
}

.gpu-table th,
.gpu-table td {
  padding: 12px;
  text-align: center;
  border: 1px solid #ddd;
}

.gpu-table thead {
  background: #007bff;
  color: white;
}

.gpu-table tr.highlight {
  background: #e7f3ff;
  font-weight: bold;
}

/* CTAセクション */
.cta-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 40px;
  border-radius: 12px;
  text-align: center;
  margin: 40px 0;
}

.cta-button {
  display: inline-block;
  background: white;
  color: #667eea;
  padding: 15px 40px;
  border-radius: 50px;
  font-weight: bold;
  text-decoration: none;
  margin-top: 20px;
  transition: transform 0.2s;
}

.cta-button:hover {
  transform: scale(1.05);
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 30px;
}

.feature {
  text-align: center;
}

.feature .icon {
  font-size: 2em;
  display: block;
  margin-bottom: 10px;
}
```

---

## 📝 使い方

### 1. スクリプトで自動生成
```bash
python scripts/generate_game_schemas.py
```

### 2. 手動で各ゲームページに挿入
テンプレート内の`{{変数}}`を実際の値に置き換えて、各ゲームページのHTMLに挿入。

### 3. 変数の置き換え例
```
{{GAME_NAME}} → Apex Legends
{{RECOMMENDED_CPU}} → Intel Core i5-10600K / Ryzen 5 3600X
{{RECOMMENDED_GPU}} → NVIDIA GTX 970 / AMD Radeon R9 290
{{BUDGET}} → 10
{{GPU_PRICE}} → 4.5
```

---

## 🎯 期待効果

- **SEO**: FAQがGoogleのリッチリザルトに表示
- **AIO**: AI Overviewに引用される確率UP
- **UX**: ユーザーが欲しい情報がすぐに見つかる
- **CV**: CTA経由でAI診断利用率UP
