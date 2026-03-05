# Claude Code 実装指示書: 収益化優先 3施策統合版

## 📋 実装概要

**目的**: ベンチマークDB構築を中止し、即座に収益につながる3施策を実装

**実装内容**:
1. 推測値の明記修正（30分）- 信頼性向上 + 法的リスク回避
2. 診断→チャット引き継ぎ（20分）- UX改善 + コンバージョン率向上
3. ブログ自動生成（2時間）- SEO流入+30% + アフィリエイト収益向上
4. 週1定点観測記事（40分）- 価格推移レポート + リピーター獲得
5. Twitter連動（30分）- ブログ自動投稿 + BOT感軽減

**合計実装時間**: 4時間

**期待効果**:
- 🔴 信頼性向上（推測値を正直に明記）
- 🔴 UX改善（診断結果からチャットへスムーズに遷移）
- 🔴 SEO流入+30%（月30記事自動生成）
- 🟡 PV増加 → アフィリエイト収益向上

---

## 🎯 施策1: 推測値の明記修正（30分）

### 問題点

**現在**:
```
予算12万円構成:
期待性能: 1080p 高設定 60〜100fps  ← 根拠なし（嘘くさい）

GPU比較表:
RTX 4060 | 100fps | 65fps | 40fps  ← 全て推測値
```

**問題**:
- ❌ 根拠のない数値を断定的に表示
- ❌ ユーザーが「本当？」と疑問を持つ
- ❌ 景品表示法リスク（優良誤認）

---

### 実装内容

#### 1-1. 予算別PC構成に免責事項追加

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: `BUDGET_BUILDS` 辞書

```python
BUDGET_BUILDS = {
    "minimum": {
        "label": "8万円（最低動作）",
        "cpu": "Ryzen 5 5600",
        "cpu_price": 14980,
        "gpu": "RTX 3060",
        "gpu_price": 29800,
        "ram": "16GB DDR4",
        "ram_price": 5980,
        "ssd": "500GB SSD",
        "ssd_price": 5480,
        "other": "MB・PSU・ケース等",
        "other_price": 22000,
        "total": 78240,
        "performance": "1080p 低〜中設定 30〜60fps前後",  # ← 「前後」追加
        "note": "※ 一般的なゲームでの目安です。実際のFPSはゲームタイトル・設定により大きく異なります。",  # ← 追加
    },
    "recommended": {
        "label": "12万円（推奨動作）",
        "cpu": "Ryzen 5 7600",
        "cpu_price": 25000,
        "gpu": "RTX 4060",
        "gpu_price": 45800,
        "ram": "16GB DDR5",
        "ram_price": 7980,
        "ssd": "1TB NVMe SSD",
        "ssd_price": 7480,
        "other": "MB・PSU・ケース等",
        "other_price": 26000,
        "total": 112260,
        "performance": "1080p 高設定 60〜100fps前後 / WQHD 中設定 60fps前後",  # ← 「前後」追加
        "note": "※ 一般的なゲームでの目安です。実際のFPSはゲームタイトル・設定により大きく異なります。",  # ← 追加
    },
    "premium": {
        "label": "18万円（快適動作）",
        "cpu": "Ryzen 7 7700",
        "cpu_price": 38000,
        "gpu": "RTX 4070",
        "gpu_price": 82800,
        "ram": "32GB DDR5",
        "ram_price": 13980,
        "ssd": "1TB NVMe SSD",
        "ssd_price": 7480,
        "other": "MB・PSU・ケース等",
        "other_price": 30000,
        "total": 172260,
        "performance": "WQHD 高設定 100〜144fps前後 / 4K 中設定 60fps前後",  # ← 「前後」追加
        "note": "※ 一般的なゲームでの目安です。実際のFPSはゲームタイトル・設定により大きく異なります。",  # ← 追加
    }
}
```

**HTMLテンプレート修正**:

```python
# generate_game_pages.py の generate_budget_builds_section() 関数内

budget_builds_html = f'''
    <section class="budget-builds">
        <h2>💰 予算別おすすめPC構成</h2>
        <p>{game_title}を快適にプレイできるPC構成を予算別に紹介します。価格はすべて目安です。</p>
        
        <div class="budget-cards">
            {"".join([
                f'''
                <div class="budget-card">
                    <h3>{build['label']}</h3>
                    <div class="specs">
                        <p><strong>GPU:</strong> {build['gpu']} <span class="price">¥{build['gpu_price']:,}</span></p>
                        <p><strong>CPU:</strong> {build['cpu']} <span class="price">¥{build['cpu_price']:,}</span></p>
                        <p><strong>RAM:</strong> {build['ram']} <span class="price">¥{build['ram_price']:,}</span></p>
                        <p><strong>SSD:</strong> {build['ssd']} <span class="price">¥{build['ssd_price']:,}</span></p>
                        <p><strong>他:</strong> {build['other']} <span class="price">¥{build['other_price']:,}</span></p>
                    </div>
                    <div class="total">合計 約¥{build['total']:,}</div>
                    <div class="performance">{build['performance']}</div>
                    <div class="note">{build.get('note', '')}</div>  <!-- 追加 -->
                    <a href="/" class="cta-button">AIに構成を相談する →</a>
                </div>
                '''
                for key, build in BUDGET_BUILDS.items()
            ])}
        </div>
        
        <div class="budget-disclaimer">
            <p><strong>⚠️ 注意事項</strong></p>
            <ul>
                <li>FPS値は一般的なゲームでの参考値です。{game_title}での実際の動作は設定・解像度により異なります。</li>
                <li>詳しい動作環境はAI診断チャットでご確認ください。</li>
                <li>価格は2026年3月時点の目安です。最新価格は各販売店でご確認ください。</li>
            </ul>
        </div>
    </section>
'''
```

**CSS追加**:

```css
/* static/style.css に追加 */

.note {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
  padding: 8px;
  background: #f8f8f8;
  border-left: 3px solid #ffa500;
  border-radius: 4px;
  line-height: 1.5;
}

.budget-disclaimer {
  margin-top: 24px;
  padding: 16px;
  background: #fff9e6;
  border: 1px solid #ffd700;
  border-radius: 8px;
}

.budget-disclaimer strong {
  color: #ff6600;
}

.budget-disclaimer ul {
  margin: 8px 0 0 20px;
  font-size: 14px;
  line-height: 1.6;
}

.budget-disclaimer li {
  margin-bottom: 4px;
}
```

---

#### 1-2. GPU比較表に免責事項追加

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: `generate_gpu_comparison_section()` 関数

```python
def generate_gpu_comparison_section(game_title):
    gpu_comparison_html = f'''
    <section class="gpu-comparison">
        <h2>🎮 GPU別性能比較</h2>
        <p>{game_title}を快適に遊ぶために必要なGPU性能を比較します。</p>
        
        <div class="comparison-table">
            <table>
                <thead>
                    <tr>
                        <th>GPU</th>
                        <th>1080p</th>
                        <th>WQHD</th>
                        <th>4K</th>
                        <th>価格帯</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([
                        f'''
                        <tr>
                            <td>{gpu['name']}</td>
                            <td>{gpu['fps_1080p']}fps前後</td>  <!-- 「前後」追加 -->
                            <td>{gpu['fps_wqhd']}fps前後</td>   <!-- 「前後」追加 -->
                            <td>{gpu['fps_4k']}fps前後</td>     <!-- 「前後」追加 -->
                            <td>{gpu['price']}</td>
                        </tr>
                        '''
                        for gpu in GPU_COMPARISON
                    ])}
                </tbody>
            </table>
        </div>
        
        <div class="comparison-note">
            <p><strong>📝 注意事項:</strong></p>
            <ul>
                <li>FPS値は高設定での一般的な目安です。{game_title}での実測値ではありません。</li>
                <li>グラフィック設定・解像度により大きく変動します。</li>
                <li>正確な動作確認はAI診断チャットをご利用ください。</li>
            </ul>
        </div>
    </section>
    '''
    return gpu_comparison_html
```

**CSS追加**:

```css
.comparison-note {
  margin-top: 16px;
  padding: 12px;
  background: #f0f8ff;
  border: 1px solid #4682b4;
  border-radius: 6px;
}

.comparison-note strong {
  color: #4682b4;
}

.comparison-note ul {
  margin: 8px 0 0 20px;
  font-size: 13px;
  line-height: 1.6;
}
```

---

#### 1-3. FAQ回答の修正

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: `generate_faq_section()` 関数

```python
def generate_faq_section(game_title, min_gpu, rec_gpu):
    faqs = [
        {
            "q": f"{game_title}は何fpsで遊べますか？",
            "a": f"PC構成により異なります。最低スペック（{min_gpu}相当）で30〜60fps前後、推奨スペック（{rec_gpu}相当）で60〜90fps前後が一般的な目安です。RTX 4060クラスで1080p高設定なら100fps前後が期待できます。※ゲームの最適化状況・設定により大きく変動します。正確な診断はAIチャットをご利用ください。",
        },
        {
            "q": f"予算10万円で{game_title}用PCは組める？",
            "a": f"はい、予算10万円前後で{game_title}を遊べるPCを組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.5万円）+ 16GB RAM（約0.8万円）の構成で1080p 60fps以上を狙えます。ただし、設定・解像度により性能は変動するため、AIチャットで詳しくご相談ください。",
        },
        # 他のFAQも同様に「前後」「目安」「AIチャット推奨」を追加
    ]
    
    # 以降のコード...
```

---

#### 1-4. 全ゲームページ再生成

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine
python scripts/generate_game_pages.py
```

**確認ポイント**:
- ✅ 予算別構成に「前後」「注意事項」表示
- ✅ GPU比較表に「前後」「注意事項」表示
- ✅ FAQ回答が曖昧な断言を避けている

---

## 🎯 施策2: 診断→チャット引き継ぎ（20分）

### 問題点

**現在のUX**:
```
予算診断ツール → 結果表示
              ↓
           （断絶）
              ↓
チャット診断 → ゼロから入力
```

**問題**:
- ❌ ユーザーが診断結果を見て満足 → 離脱
- ❌ チャットで再度入力が面倒
- ❌ コンバージョン率が低い

---

### 実装内容

#### 2-1. 予算診断結果に「この構成について相談する」ボタン追加

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: 予算診断ツールのHTML

```python
def generate_budget_calculator(game_title):
    calculator_html = f'''
    <section class="budget-calculator">
        <h3>💰 予算と目標を入力するだけで、{game_title}に最適なPC構成を診断します。</h3>
        
        <form id="budget-form">
            <label>予算（円）</label>
            <input type="number" id="budget-input" placeholder="150000" min="50000" max="500000">
            
            <label>目標FPS</label>
            <select id="fps-target">
                <option value="60">60fps（標準）</option>
                <option value="144">144fps（高リフレッシュ）</option>
                <option value="240">240fps（超高リフレッシュ）</option>
            </select>
            
            <label>解像度</label>
            <select id="resolution-target">
                <option value="1080p">1080p（フルHD）</option>
                <option value="1440p">1440p（WQHD）</option>
                <option value="4k">4K（UHD）</option>
            </select>
            
            <button type="submit">診断する</button>
        </form>
        
        <div id="budget-result" style="display:none;">
            <!-- 診断結果表示エリア -->
            <div id="result-content"></div>
            
            <!-- 新規追加: チャットへ誘導ボタン -->
            <div class="consult-cta">
                <button id="consult-btn" class="consult-button">
                    💬 この構成についてAIに相談する →
                </button>
                <p class="consult-note">診断結果を引き継いで、詳しくAIが回答します</p>
            </div>
        </div>
    </section>
    
    <script>
    // 診断ボタンのクリックイベント
    document.getElementById('budget-form').addEventListener('submit', function(e) {{
        e.preventDefault();
        
        const budget = document.getElementById('budget-input').value;
        const fps = document.getElementById('fps-target').value;
        const resolution = document.getElementById('resolution-target').value;
        
        // 診断ロジック（既存のまま）
        const result = calculateBudget(budget, fps, resolution);
        
        // 結果表示
        document.getElementById('result-content').innerHTML = result;
        document.getElementById('budget-result').style.display = 'block';
        
        // チャット引き継ぎデータを保存
        sessionStorage.setItem('diagnosisContext', JSON.stringify({{
            game: '{game_title}',
            budget: budget,
            targetFps: fps,
            resolution: resolution,
            timestamp: Date.now()
        }}));
    }});
    
    // 相談ボタンのクリックイベント
    document.getElementById('consult-btn').addEventListener('click', function() {{
        // チャットモーダルを開く + 診断結果を自動入力
        openChatWithContext();
    }});
    
    function openChatWithContext() {{
        const context = JSON.parse(sessionStorage.getItem('diagnosisContext'));
        
        if (!context) {{
            // コンテキストなし → 通常のチャット起動
            document.getElementById('chat-trigger').click();
            return;
        }}
        
        // チャットモーダルを開く
        document.getElementById('chat-trigger').click();
        
        // 少し待ってからメッセージを自動入力
        setTimeout(() => {{
            const chatInput = document.getElementById('chat-input');
            const prefilledMessage = `
{game_title}用のPC構成について相談があります。

【希望条件】
- 予算: ${{parseInt(context.budget).toLocaleString()}}円
- 目標FPS: ${{context.targetFps}}fps
- 解像度: ${{context.resolution}}

この条件で快適に遊べるPC構成を教えてください。
            `.trim();
            
            if (chatInput) {{
                chatInput.value = prefilledMessage;
                chatInput.focus();
            }}
        }}, 500);
    }}
    </script>
    '''
    return calculator_html
```

**CSS追加**:

```css
/* static/style.css */

.consult-cta {
  margin-top: 24px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  text-align: center;
}

.consult-button {
  background: #ffffff;
  color: #667eea;
  border: none;
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.consult-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.3);
}

.consult-note {
  color: #ffffff;
  font-size: 13px;
  margin-top: 8px;
  opacity: 0.9;
}
```

---

#### 2-2. スペック診断ツールも同様に改善

**ファイル**: `static/app.js`

**既存の診断結果表示関数に追加**:

```javascript
// 診断結果表示後にコンテキスト保存
function displayDiagnosisResult(gpu, ram, game, verdict) {
    // 既存の結果表示コード...
    
    // コンテキスト保存
    sessionStorage.setItem('diagnosisContext', JSON.stringify({
        game: game,
        gpu: gpu,
        ram: ram,
        verdict: verdict,
        timestamp: Date.now()
    }));
    
    // 相談ボタン追加
    const consultButton = `
        <div class="consult-cta">
            <button id="consult-spec-btn" class="consult-button">
                💬 この診断結果についてAIに相談する →
            </button>
            <p class="consult-note">より詳しいアドバイスをAIが提供します</p>
        </div>
    `;
    
    document.getElementById('diagnosis-result').innerHTML += consultButton;
    
    // イベントリスナー
    document.getElementById('consult-spec-btn').addEventListener('click', function() {
        const context = JSON.parse(sessionStorage.getItem('diagnosisContext'));
        
        // チャットモーダルを開く
        document.getElementById('chat-trigger').click();
        
        setTimeout(() => {
            const chatInput = document.getElementById('chat-input');
            const prefilledMessage = `
${context.game}の動作診断結果について相談があります。

【私のPC】
- GPU: ${context.gpu}
- RAM: ${context.ram}GB

診断結果: ${context.verdict}

このPCで${context.game}を快適に遊ぶためのアドバイスをください。
            `.trim();
            
            if (chatInput) {
                chatInput.value = prefilledMessage;
                chatInput.focus();
            }
        }, 500);
    });
}
```

---

## 🎯 施策3: ブログ自動生成（2時間）

### 目的

**月30記事自動生成 → SEO流入+30% → アフィリエイト収益向上**

---

### 実装内容

#### 3-1. 記事テンプレート定義

**新規ファイル**: `scripts/blog_templates.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事テンプレート
"""

BLOG_TEMPLATES = [
    {
        "id": "troubleshooting",
        "title": "「{game}」が動かない時の対処法7選",
        "keywords": ["{game} 動かない", "{game} 起動しない", "{game} トラブル"],
        "outline": """
1. スペック不足の確認
2. グラフィックドライバの更新
3. DirectX/Visual C++の再インストール
4. ウイルス対策ソフトの例外設定
5. 管理者権限で実行
6. ファイルの整合性チェック
7. セーブデータの移動
""",
        "prompt": """
以下のアウトラインに沿って、「{game}」が動かない時の対処法を1,500文字で執筆してください。

【アウトライン】
{outline}

【要件】
- 各対処法は具体的な手順を含める
- 初心者にもわかりやすい表現
- 最後に「それでも解決しない場合はAI診断チャットへ」と誘導
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "gpu_list",
        "title": "RTX {gpu_model}で遊べる最新ゲーム100選",
        "keywords": ["RTX {gpu_model} ゲーム", "RTX {gpu_model} おすすめ"],
        "outline": """
1. RTX {gpu_model}の性能概要
2. 1080p高設定で快適なゲーム（50本）
3. WQHD中設定で快適なゲーム（30本）
4. 4K低設定で遊べるゲーム（20本）
5. まとめ
""",
        "prompt": """
RTX {gpu_model}で快適に遊べるゲームリストを作成してください。

【要件】
- 各ゲームに期待FPS（目安）を記載
- ジャンル別に分類
- 最新ゲームと定番ゲームをバランス良く
- 1,800文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "budget_build",
        "title": "予算{budget}万円で組む最強ゲーミングPC構成",
        "keywords": ["予算{budget}万円 ゲーミングPC", "{budget}万円 PC構成"],
        "outline": """
1. 予算{budget}万円の構成概要
2. GPU選び
3. CPU選び
4. その他パーツ（RAM/SSD/マザボ/電源）
5. 組み立ての注意点
6. おすすめBTOショップ
""",
        "prompt": """
予算{budget}万円で組めるゲーミングPC構成を提案してください。

【要件】
- 2026年3月時点の最新パーツ
- コストパフォーマンス重視
- 初心者向けの説明
- 1,500文字程度
- 最後にBTOショップへのリンク誘導
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "benchmark",
        "title": "「{game}」の推奨スペックと実測FPS比較",
        "keywords": ["{game} 推奨スペック", "{game} FPS"],
        "outline": """
1. {game}の公式推奨スペック
2. 実際の動作環境（目安）
3. GPU別FPS比較（1080p/WQHD/4K）
4. CPU・RAMの影響
5. 快適に遊ぶための構成例
""",
        "prompt": """
「{game}」の推奨スペックと実際の動作環境を解説してください。

【要件】
- 公式スペックと実測値の違いを明記
- GPU別FPS表（目安）
- 1,200文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "laptop",
        "title": "ノートPCで「{game}」は快適に遊べる？",
        "keywords": ["{game} ノートPC", "{game} ゲーミングノート"],
        "outline": """
1. ノートPCでのプレイ可否
2. 推奨ゲーミングノートスペック
3. おすすめゲーミングノート3選
4. デスクトップとの比較
5. 外出先プレイの注意点
""",
        "prompt": """
ノートPCで「{game}」をプレイする際のポイントを解説してください。

【要件】
- ゲーミングノートの選び方
- おすすめ製品3つ（具体名）
- デスクトップとの性能差
- 1,400文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "high_res",
        "title": "「{game}」をWQHD/4Kで遊ぶために必要なGPU",
        "keywords": ["{game} WQHD", "{game} 4K"],
        "outline": """
1. WQHD/4Kプレイのメリット
2. WQHD推奨GPU（3種）
3. 4K推奨GPU（3種）
4. フレームレート目標別構成
5. コストパフォーマンス分析
""",
        "prompt": """
「{game}」を高解像度（WQHD/4K）で遊ぶためのGPU選びを解説してください。

【要件】
- 解像度ごとの推奨GPU
- フレームレート目標別の提案
- 1,300文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "performance",
        "title": "「{game}」が重い・カクつく原因と解決策",
        "keywords": ["{game} 重い", "{game} カクつく"],
        "outline": """
1. カクつきの主な原因
2. グラフィック設定の最適化
3. バックグラウンドアプリの終了
4. ドライバ更新
5. SSD/RAM不足の確認
6. それでも改善しない場合
""",
        "prompt": """
「{game}」が重い・カクつく時の解決策を解説してください。

【要件】
- 原因の診断方法
- 具体的な設定手順
- 初心者向けの説明
- 1,400文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "used_parts",
        "title": "中古パーツで組む「{game}」向けゲーミングPC",
        "keywords": ["{game} 中古パーツ", "{game} 格安PC"],
        "outline": """
1. 中古パーツのメリット・デメリット
2. 狙い目の中古GPU
3. 狙い目の中古CPU
4. 避けるべき中古パーツ
5. 予算別構成例
6. 購入時の注意点
""",
        "prompt": """
中古パーツで「{game}」を遊べるPCを組む方法を解説してください。

【要件】
- コストパフォーマンス重視
- リスク・注意点を明記
- 1,500文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "mod",
        "title": "「{game}」のMODを入れるために必要なスペック",
        "keywords": ["{game} MOD スペック", "{game} MOD 重い"],
        "outline": """
1. MOD導入の基礎知識
2. 軽量MOD向けスペック
3. グラフィックMOD向けスペック
4. 大型MOD向けスペック
5. おすすめ構成
""",
        "prompt": """
「{game}」にMODを導入する際の推奨スペックを解説してください。

【要件】
- MODの種類別にスペック提案
- VRAM容量の重要性
- 1,200文字程度
- SEOキーワード: {keywords}
""",
    },
    {
        "id": "ranking",
        "title": "2026年版 最新ゲーム推奨スペックランキング",
        "keywords": ["ゲーム 推奨スペック", "2026年 ゲーム 重い"],
        "outline": """
1. 最も重いゲームTOP10
2. 中程度の重さのゲームTOP10
3. 軽いゲームTOP10
4. ジャンル別推奨スペック
5. 今後のトレンド予測
""",
        "prompt": """
2026年最新ゲームの推奨スペックをランキング形式で紹介してください。

【要件】
- 各ゲームの推奨GPU/CPU
- グラフ・表で視覚化
- 2,000文字程度
- SEOキーワード: {keywords}
""",
    },
]
```

---

#### 3-2. ブログ自動生成スクリプト

**新規ファイル**: `scripts/blog_generator.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事自動生成
Claude APIを使用して月30記事生成
"""

import os
import json
import random
import time
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic

from blog_templates import BLOG_TEMPLATES

# 環境変数
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
BLOG_DIR = WORKSPACE_DIR / "static" / "blog"
BLOG_DIR.mkdir(exist_ok=True)

# Anthropic クライアント
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def get_trending_game():
    """
    旬のゲームを取得（Steam売上ランキング等から）
    
    優先順位:
    1. Steam新作（発売1週間以内）
    2. Steamトップセラー
    3. 話題のゲーム（Twitter/Reddit trending）
    4. 季節イベント（例: 年末年始セール）
    
    Returns:
        ゲーム名 or None
    """
    # 実装例（簡略版）
    # 実際はSteam API、Twitterトレンド、Reddit APIなどを使用
    
    # 2026年3月の注目ゲーム例
    trending_games = [
        "Monster Hunter Wilds",
        "Death Stranding 2",
        "Grand Theft Auto VI",
        "Civilization VII",
        "Kingdom Come: Deliverance II",
    ]
    
    # ランダムに1つ選択（本番ではAPI連携）
    import random
    return random.choice(trending_games)

def generate_blog_post(template, variables):
    """
    ブログ記事を生成（Opus使用・高品質）
    
    Args:
        template: 記事テンプレート
        variables: 変数辞書（game, gpu_model, budgetなど）
    
    Returns:
        生成された記事HTML
    """
    # タイトル生成
    title = template['title'].format(**variables)
    
    # キーワード生成
    keywords = [kw.format(**variables) for kw in template['keywords']]
    
    # アウトライン生成
    outline = template['outline'].format(**variables)
    
    # プロンプト生成
    prompt = template['prompt'].format(
        outline=outline,
        keywords=', '.join(keywords),
        **variables
    )
    
    print(f"📝 記事生成中: {title}")
    print(f"🎮 対象ゲーム: {variables.get('game', 'N/A')}")
    
    # Claude API 呼び出し（Opus使用 - 品質最優先）
    try:
        message = client.messages.create(
            model="claude-opus-4-20250514",  # ✅ Opus使用（高品質記事）
            max_tokens=4096,  # 長文対応
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        content = message.content[0].text
        
        # HTML生成
        html = generate_html(title, content, keywords)
        
        print(f"✅ 記事生成完了: {len(content)} 文字")
        
        return html
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def generate_html(title, content, keywords):
    """
    記事HTMLを生成
    """
    slug = title.lower().replace(' ', '-').replace('「', '').replace('」', '')
    
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | PC互換チェッカー</title>
    <meta name="description" content="{title} - PCゲーム互換性診断とおすすめPC構成">
    <meta name="keywords" content="{', '.join(keywords)}">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <h1>🖥️ <a href="/">PC互換チェッカー</a></h1>
        <nav>
            <a href="/">ホーム</a>
            <a href="/guide">ガイド</a>
        </nav>
    </header>
    
    <main class="blog-article">
        <article>
            <h1>{title}</h1>
            <div class="article-meta">
                <time datetime="{datetime.now().strftime('%Y-%m-%d')}">{datetime.now().strftime('%Y年%m月%d日')}</time>
            </div>
            
            <div class="article-content">
                {content}
            </div>
            
            <div class="article-cta">
                <h3>💬 あなたのPCで動くか診断</h3>
                <p>AI診断チャットで詳しく確認できます</p>
                <a href="/" class="cta-button">無料で診断する →</a>
            </div>
        </article>
    </main>
    
    <footer>
        <p>&copy; 2026 PC互換チェッカー</p>
    </footer>
</body>
</html>
'''
    
    return html

def save_blog_post(filename, html):
    """
    記事を保存
    """
    filepath = BLOG_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 保存完了: {filepath}")

def generate_daily_post():
    """
    毎日1本の記事生成（旬のゲーム優先）
    
    戦略:
    1. 旬のゲームを取得（Steam新作・トレンド）
    2. 適切なテンプレート選択
    3. Opus で高品質記事生成
    4. SEO最適化
    
    Returns:
        生成された記事のファイル名
    """
    # 旬のゲームを取得
    trending_game = get_trending_game()
    
    # テンプレート選択（優先順位付き）
    # - 新作ゲームなら「推奨スペック」「トラブルシューティング」
    # - 人気ゲームなら「GPU比較」「予算別構成」
    template = select_best_template(trending_game)
    
    # GPUリスト（最新世代優先）
    gpus = ["4060", "4070", "4080", "4090", "7800 XT", "7900 XTX"]
    
    # 予算リスト
    budgets = ["10", "12", "15", "18", "20", "25"]
    
    # 変数設定
    variables = {
        'game': trending_game,
        'gpu_model': random.choice(gpus),
        'budget': random.choice(budgets),
    }
    
    print(f"\n🎯 本日の記事テーマ:")
    print(f"  - ゲーム: {trending_game}")
    print(f"  - テンプレート: {template['title']}")
    
    # 記事生成（Opus使用）
    html = generate_blog_post(template, variables)
    
    if html:
        # ファイル名生成（日付ベース）
        timestamp = datetime.now().strftime('%Y%m%d')
        slug = trending_game.lower().replace(' ', '-').replace(':', '')
        filename = f"{timestamp}_{slug}_{template['id']}.html"
        
        # 保存
        save_blog_post(filename, html)
        
        print(f"\n✅ 本日の記事生成完了: {filename}")
        return filename
    else:
        print(f"\n❌ 記事生成失敗")
        return None

def select_best_template(game):
    """
    ゲームに最適なテンプレート選択
    
    Args:
        game: ゲーム名
    
    Returns:
        最適なテンプレート
    """
    # 新作ゲーム判定（簡略版）
    # 実際はリリース日をチェック
    new_releases = [
        "Monster Hunter Wilds",
        "Death Stranding 2",
        "Grand Theft Auto VI",
    ]
    
    if game in new_releases:
        # 新作なら基本情報系
        preferred = ["benchmark", "troubleshooting", "laptop"]
    else:
        # 既存ゲームなら応用系
        preferred = ["gpu_list", "budget_build", "high_res", "performance"]
    
    # 優先テンプレートから選択
    matching = [t for t in BLOG_TEMPLATES if t['id'] in preferred]
    
    if matching:
        return random.choice(matching)
    else:
        return random.choice(BLOG_TEMPLATES)

if __name__ == '__main__':
    # 毎日1本生成
    generate_daily_post()
```

---

#### 3-3. GitHub Actions で自動実行

**新規ファイル**: `.github/workflows/blog-generator.yml`

```yaml
name: Blog Auto Generator - Daily

on:
  schedule:
    - cron: '0 0 * * *'  # 毎日0時（UTC = 日本時間9時）に実行
  workflow_dispatch:  # 手動実行も可能

jobs:
  generate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install anthropic requests beautifulsoup4
    
    - name: Generate daily blog post
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        python scripts/blog_generator.py
    
    - name: Commit new post
      run: |
        git config user.name "GitHub Actions Bot"
        git config user.email "actions@github.com"
        git add static/blog/
        git diff --staged --quiet || git commit -m "chore: 本日のブログ記事自動生成 [skip ci]"
        git push
```

---

## ✅ 実装完了チェックリスト

### 施策1: 推測値の明記修正
- [ ] `BUDGET_BUILDS` に「前後」「note」追加
- [ ] 予算別構成HTML に免責事項追加
- [ ] GPU比較表に「前後」追加
- [ ] FAQ回答に「目安」「AIチャット推奨」追加
- [ ] 全ゲームページ再生成（413ページ）

### 施策2: 診断→チャット引き継ぎ
- [ ] 予算診断に「相談ボタン」追加
- [ ] `sessionStorage` でコンテキスト保存
- [ ] チャット自動入力機能実装
- [ ] スペック診断も同様に改善

### 施策3: ブログ自動生成
- [ ] `blog_templates.py` 作成（10テンプレート）
- [ ] `blog_generator.py` 作成
- [ ] `blog-generator.yml` 作成（GitHub Actions）
- [ ] テスト実行（3記事生成）
- [ ] 本番実行（30記事生成）

---

## 🚀 実装手順

### Phase 1: 推測値の明記修正（30分）
1. `scripts/generate_game_pages.py` 修正
2. 全ゲームページ再生成: `python scripts/generate_game_pages.py`
3. ローカル確認
4. Git commit & push

### Phase 2: 診断→チャット引き継ぎ（20分）
1. `scripts/generate_game_pages.py` の予算診断HTML修正
2. `static/app.js` のスペック診断修正
3. CSS追加
4. ローカルテスト
5. Git commit & push

### Phase 3: ブログ自動生成（2時間）
1. `scripts/blog_templates.py` 作成
2. `scripts/blog_generator.py` 作成
3. `.github/workflows/blog-generator.yml` 作成
4. ローカルテスト（3記事生成）: `python scripts/blog_generator.py`
5. GitHub Secrets に `ANTHROPIC_API_KEY` 追加
6. GitHub Actions 手動実行（workflow_dispatch）
7. 30記事生成確認
8. Git commit & push

---

## 📊 期待効果

| 施策 | 効果 |
|------|------|
| 推測値の明記修正 | 信頼性向上 + 法的リスク回避 + AI診断への誘導強化 |
| 診断→チャット引き継ぎ | UX改善 + コンバージョン率+10-20% |
| ブログ自動生成 | SEO流入+30% + PV増加 + アフィリエイト収益向上 |

---

**実装時間目安**: 2時間50分

**Co-Authored-By**: Claude Opus 4.6 <noreply@anthropic.com>
