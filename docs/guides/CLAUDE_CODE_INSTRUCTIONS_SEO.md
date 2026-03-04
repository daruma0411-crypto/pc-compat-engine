# Claude Code 実装指示書: SEO最適化 & コンテンツ拡充

## 📌 プロジェクト概要

**PC互換チェッカー**の既存443ゲームページに、SEO最適化コンテンツを追加して検索流入を増やす。

### 背景: 競合キーワード分析の結果
- **あなたの最大の強み**: 443ゲーム×14,000件の互換性データベース（他サイトにない）
- **Easy Winキーワード**: `[ゲーム名] 予算`、`[GPU名] [ゲーム名] 動く`、`[ゲーム名] GPU 比較`
- **競合の弱点**: 予算診断機能がない、GPU比較が浅い、トラブルシューティングが少ない

### 目標
1. **Phase 1 (即効性)**: 各ゲームページにコンテンツセクション追加 → 1,329ページのSEO強化
2. **Phase 2 (差別化)**: インタラクティブ診断機能追加 → 滞在時間UP + 独自性

### 制約事項
- ⚠️ **URL構造は変更しない**（SEO維持）
- ⚠️ **既存のSchema.org（443ゲーム分）は維持**
- ⚠️ **Google Analytics設定は維持**

---

## 🚀 Phase 1: コンテンツテンプレート追加（優先度: 最高）

### 目標
443ゲームページ全てに以下のセクションを自動生成して追加：
1. 予算別PC構成（3パターン）
2. GPU別性能比較表
3. よくある質問（FAQ）
4. トラブルシューティング

### 対象ファイル
- **テンプレート**: `templates/game.html`（既存）
- **データソース**: `workspace/data/steam/games.jsonl`（既存の443ゲーム）

---

## 📝 実装仕様

### タスク1.1: テンプレートにセクション追加

**ファイル:** `templates/game.html`

**追加位置:** 既存の推奨スペック表示の後、フッターの前

**追加セクション:**

```html
<!-- 予算別PC構成 -->
<section id="budget-builds" class="content-section">
  <h2>💰 予算別おすすめPC構成</h2>
  <p>{{ game.title }}を快適にプレイできるPC構成を予算別に提案します。</p>
  
  <div class="budget-cards">
    <!-- 予算8万円（最低動作） -->
    <div class="budget-card budget-minimum">
      <h3>💵 予算8万円（最低動作）</h3>
      <div class="build-specs">
        <div class="spec-item">
          <span class="spec-label">CPU:</span>
          <span class="spec-value">{{ budget_builds.minimum.cpu }}</span>
          <span class="spec-price">¥{{ budget_builds.minimum.cpu_price | number_format }}</span>
        </div>
        <div class="spec-item">
          <span class="spec-label">GPU:</span>
          <span class="spec-value">{{ budget_builds.minimum.gpu }}</span>
          <span class="spec-price">¥{{ budget_builds.minimum.gpu_price | number_format }}</span>
        </div>
        <div class="spec-item">
          <span class="spec-label">RAM:</span>
          <span class="spec-value">{{ budget_builds.minimum.ram }}</span>
          <span class="spec-price">¥{{ budget_builds.minimum.ram_price | number_format }}</span>
        </div>
        <div class="spec-item">
          <span class="spec-label">ストレージ:</span>
          <span class="spec-value">{{ budget_builds.minimum.storage }}</span>
          <span class="spec-price">¥{{ budget_builds.minimum.storage_price | number_format }}</span>
        </div>
      </div>
      <div class="build-total">
        <strong>合計:</strong> 約¥{{ budget_builds.minimum.total | number_format }}
      </div>
      <div class="build-performance">
        <strong>期待性能:</strong> {{ budget_builds.minimum.expected_performance }}
      </div>
      <button class="btn-affiliate" data-build="minimum">この構成を見る</button>
    </div>

    <!-- 予算12万円（推奨動作） -->
    <div class="budget-card budget-recommended">
      <div class="recommended-badge">おすすめ</div>
      <h3>💳 予算12万円（推奨動作）</h3>
      <div class="build-specs">
        <!-- 同様の構造 -->
      </div>
      <div class="build-total">
        <strong>合計:</strong> 約¥{{ budget_builds.recommended.total | number_format }}
      </div>
      <div class="build-performance">
        <strong>期待性能:</strong> {{ budget_builds.recommended.expected_performance }}
      </div>
      <button class="btn-affiliate" data-build="recommended">この構成を見る</button>
    </div>

    <!-- 予算18万円（快適動作） -->
    <div class="budget-card budget-premium">
      <h3>💎 予算18万円（快適動作）</h3>
      <div class="build-specs">
        <!-- 同様の構造 -->
      </div>
      <div class="build-total">
        <strong>合計:</strong> 約¥{{ budget_builds.premium.total | number_format }}
      </div>
      <div class="build-performance">
        <strong>期待性能:</strong> {{ budget_builds.premium.expected_performance }}
      </div>
      <button class="btn-affiliate" data-build="premium">この構成を見る</button>
    </div>
  </div>
</section>

<!-- GPU別性能比較表 -->
<section id="gpu-comparison" class="content-section">
  <h2>🎮 GPU別性能比較</h2>
  <p>{{ game.title }}における主要GPUの性能比較です。</p>
  
  <div class="table-responsive">
    <table class="gpu-comparison-table">
      <thead>
        <tr>
          <th>GPU</th>
          <th>価格（目安）</th>
          <th>1080p FPS</th>
          <th>WQHD FPS</th>
          <th>4K FPS</th>
          <th>推奨度</th>
        </tr>
      </thead>
      <tbody>
        {% for gpu in gpu_comparison %}
        <tr class="gpu-row {{ 'recommended' if gpu.is_recommended else '' }}">
          <td><strong>{{ gpu.name }}</strong></td>
          <td>¥{{ gpu.price | number_format }}</td>
          <td>{{ gpu.fps_1080p }}fps</td>
          <td>{{ gpu.fps_wqhd }}fps</td>
          <td>{{ gpu.fps_4k }}fps</td>
          <td>
            {% if gpu.rating == 5 %}
              ⭐⭐⭐⭐⭐
            {% elif gpu.rating == 4 %}
              ⭐⭐⭐⭐
            {% elif gpu.rating == 3 %}
              ⭐⭐⭐
            {% else %}
              ⭐⭐
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  
  <div class="gpu-notes">
    <p><strong>💡 選び方のポイント:</strong></p>
    <ul>
      <li><strong>60fps安定を目指す:</strong> {{ gpu_recommendation.for_60fps }}</li>
      <li><strong>144fps以上を目指す:</strong> {{ gpu_recommendation.for_144fps }}</li>
      <li><strong>4Kで遊びたい:</strong> {{ gpu_recommendation.for_4k }}</li>
    </ul>
  </div>
</section>

<!-- よくある質問（FAQ） -->
<section id="faq" class="content-section">
  <h2>❓ よくある質問</h2>
  
  <div class="faq-list">
    {% for faq in faqs %}
    <div class="faq-item">
      <h3 class="faq-question">{{ faq.question }}</h3>
      <div class="faq-answer">{{ faq.answer | safe }}</div>
    </div>
    {% endfor %}
  </div>
</section>

<!-- トラブルシューティング -->
<section id="troubleshooting" class="content-section">
  <h2>🔧 よくあるトラブルと解決策</h2>
  
  <div class="troubleshooting-grid">
    <div class="trouble-card">
      <h3>⚠️ カクつく・重い場合</h3>
      <ol>
        <li>グラフィック設定を「低」に変更</li>
        <li>解像度を1080pに下げる</li>
        <li>バックグラウンドアプリを終了（Chrome、Discord等）</li>
        <li>グラフィックドライバーを最新版に更新</li>
        <li>垂直同期（VSync）をオフにする</li>
      </ol>
      <p class="trouble-note">💡 それでも改善しない場合は、<a href="#gpu-comparison">GPU性能比較</a>でアップグレードを検討してください。</p>
    </div>

    <div class="trouble-card">
      <h3>🚫 動かない・起動しない場合</h3>
      <ol>
        <li>最低スペックを満たしているか<a href="#requirements">確認</a></li>
        <li>DirectXを最新版に更新</li>
        <li>Visual C++再頒布可能パッケージをインストール</li>
        <li>ゲームファイルの整合性チェック（Steam：右クリック→プロパティ→ローカルファイル→整合性確認）</li>
        <li>セキュリティソフトの除外設定に追加</li>
      </ol>
    </div>

    <div class="trouble-card">
      <h3>📉 FPSが出ない場合</h3>
      <ol>
        <li>フレームレート制限を解除（ゲーム設定）</li>
        <li>NVIDIAコントロールパネルで「最大パフォーマンス」に設定</li>
        <li>電源オプションを「高パフォーマンス」に変更</li>
        <li>Windowsゲームモードをオンにする</li>
        <li>バックグラウンドの録画機能をオフ（GeForce Experience、Xbox Game Bar）</li>
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
</section>
```

---

### タスク1.2: バックエンドでデータ生成

**ファイル:** `app.py`（またはゲームページのルートハンドラー）

**実装内容:**

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class BudgetBuild:
    """予算別PC構成"""
    cpu: str
    cpu_price: int
    gpu: str
    gpu_price: int
    ram: str
    ram_price: int
    storage: str
    storage_price: int
    total: int
    expected_performance: str

@dataclass
class GPUComparison:
    """GPU比較データ"""
    name: str
    price: int
    fps_1080p: int
    fps_wqhd: int
    fps_4k: int
    rating: int  # 1-5
    is_recommended: bool

def generate_budget_builds(game_data: dict) -> Dict[str, BudgetBuild]:
    """
    ゲームの推奨スペックから予算別PC構成を生成
    
    ロジック:
    - minimum: 最低スペックの1.2倍のGPU + エントリーCPU
    - recommended: 推奨スペックの1.5倍のGPU + ミドルCPU
    - premium: 推奨スペックの2.5倍のGPU + ハイエンドCPU
    """
    
    # ゲームの推奨GPUを取得
    recommended_gpu = game_data.get('recommended_gpu', 'GTX 1060')
    
    # GPUランクテーブル（簡略版、実際はもっと詳細に）
    GPU_RANKS = {
        'GTX 1050 Ti': {'rank': 10, 'price': 18000},
        'GTX 1060': {'rank': 15, 'price': 25000},
        'RTX 2060': {'rank': 20, 'price': 35000},
        'RTX 3050': {'rank': 18, 'price': 28000},
        'RTX 3060': {'rank': 25, 'price': 38000},
        'RTX 4050': {'rank': 23, 'price': 32000},
        'RTX 4060': {'rank': 30, 'price': 45000},
        'RTX 4060 Ti': {'rank': 35, 'price': 55000},
        'RTX 4070': {'rank': 45, 'price': 70000},
        'RTX 5060': {'rank': 32, 'price': 48000},
        'RTX 5070': {'rank': 50, 'price': 75000},
        'RTX 5080': {'rank': 65, 'price': 110000},
    }
    
    # 推奨GPUのランクを取得
    base_rank = GPU_RANKS.get(recommended_gpu, {}).get('rank', 20)
    
    # 各予算帯のGPUを選定
    def find_gpu_by_rank(target_rank: int) -> tuple:
        """ランクに最も近いGPUを検索"""
        closest_gpu = min(GPU_RANKS.items(), 
                         key=lambda x: abs(x[1]['rank'] - target_rank))
        return closest_gpu[0], closest_gpu[1]['price']
    
    # minimum: 最低スペックの1.2倍
    gpu_min, price_min = find_gpu_by_rank(int(base_rank * 0.8))
    
    # recommended: 推奨スペックの1.5倍
    gpu_rec, price_rec = find_gpu_by_rank(int(base_rank * 1.5))
    
    # premium: 推奨スペックの2.5倍
    gpu_pre, price_pre = find_gpu_by_rank(int(base_rank * 2.5))
    
    # CPU選定（GPUに合わせて）
    CPU_CONFIGS = {
        'entry': {'name': 'Ryzen 5 5600', 'price': 15980},
        'mid': {'name': 'Ryzen 5 7600', 'price': 28000},
        'high': {'name': 'Ryzen 7 7700X', 'price': 38000},
    }
    
    return {
        'minimum': BudgetBuild(
            cpu=CPU_CONFIGS['entry']['name'],
            cpu_price=CPU_CONFIGS['entry']['price'],
            gpu=gpu_min,
            gpu_price=price_min,
            ram='16GB DDR4',
            ram_price=8000,
            storage='500GB SSD',
            storage_price=6000,
            total=CPU_CONFIGS['entry']['price'] + price_min + 8000 + 6000 + 15000,  # +15000: マザボ等
            expected_performance='1080p 低設定 60fps'
        ),
        'recommended': BudgetBuild(
            cpu=CPU_CONFIGS['mid']['name'],
            cpu_price=CPU_CONFIGS['mid']['price'],
            gpu=gpu_rec,
            gpu_price=price_rec,
            ram='16GB DDR5',
            ram_price=10000,
            storage='1TB NVMe SSD',
            storage_price=10000,
            total=CPU_CONFIGS['mid']['price'] + price_rec + 10000 + 10000 + 20000,
            expected_performance='1080p 高設定 144fps / WQHD 中設定 100fps'
        ),
        'premium': BudgetBuild(
            cpu=CPU_CONFIGS['high']['name'],
            cpu_price=CPU_CONFIGS['high']['price'],
            gpu=gpu_pre,
            gpu_price=price_pre,
            ram='32GB DDR5',
            ram_price=15000,
            storage='2TB NVMe SSD',
            storage_price=18000,
            total=CPU_CONFIGS['high']['price'] + price_pre + 15000 + 18000 + 25000,
            expected_performance='WQHD 高設定 144fps / 4K 中設定 60fps'
        )
    }

def generate_gpu_comparison(game_data: dict) -> List[GPUComparison]:
    """
    ゲームに対するGPU性能比較を生成
    
    ロジック:
    - 14,000件の互換性データから、このゲームでのGPU別性能を抽出
    - FPS推定値を計算（ベンチマークデータベースから）
    """
    
    # 主要GPUリスト（実際はDBから動的に取得）
    MAIN_GPUS = [
        {'name': 'RTX 3050', 'price': 28000, 'rank': 18},
        {'name': 'RTX 4060', 'price': 45000, 'rank': 30},
        {'name': 'RTX 4060 Ti', 'price': 55000, 'rank': 35},
        {'name': 'RTX 5070', 'price': 75000, 'rank': 50},
        {'name': 'RTX 5080', 'price': 110000, 'rank': 65},
    ]
    
    # ゲームの推奨GPUランクを取得
    recommended_gpu = game_data.get('recommended_gpu', 'GTX 1060')
    base_rank = 20  # デフォルト値
    
    comparisons = []
    for gpu in MAIN_GPUS:
        # FPS推定（簡略版: rank差からスコアリング）
        performance_multiplier = gpu['rank'] / base_rank
        
        # 1080p: 推奨スペックで60fps想定
        fps_1080p = int(60 * performance_multiplier)
        fps_wqhd = int(fps_1080p * 0.65)  # WQHDは約65%
        fps_4k = int(fps_1080p * 0.40)     # 4Kは約40%
        
        # 推奨度（1-5）
        if 0.8 <= performance_multiplier < 1.2:
            rating = 3
        elif 1.2 <= performance_multiplier < 1.8:
            rating = 4
            is_recommended = True
        elif performance_multiplier >= 1.8:
            rating = 5
        else:
            rating = 2
        
        comparisons.append(GPUComparison(
            name=gpu['name'],
            price=gpu['price'],
            fps_1080p=min(fps_1080p, 240),  # 上限240fps
            fps_wqhd=min(fps_wqhd, 165),
            fps_4k=min(fps_4k, 120),
            rating=rating,
            is_recommended=rating >= 4
        ))
    
    return comparisons

def generate_faqs(game_data: dict) -> List[Dict[str, str]]:
    """
    ゲーム別FAQを生成
    
    テンプレート+ゲーム固有データを組み合わせ
    """
    game_title = game_data.get('title', 'このゲーム')
    min_gpu = game_data.get('minimum_gpu', 'GTX 1050 Ti')
    rec_gpu = game_data.get('recommended_gpu', 'GTX 1060')
    
    return [
        {
            'question': f'{game_title}の推奨スペックは？',
            'answer': f'{game_title}の推奨スペックは、GPU: {rec_gpu}、CPU: {game_data.get("recommended_cpu", "Core i5-6600K")}、メモリ: {game_data.get("recommended_ram", "8GB")}です。144fps安定を目指すならRTX 4060以上を推奨します。'
        },
        {
            'question': f'予算10万円で{game_title}用PCは組める？',
            'answer': f'はい、予算10万円で{game_title}用のPCを組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.8万円）+ 16GB RAM（約1.0万円）の構成で、1080p 144fps以上の動作が可能です。詳しくは<a href="#budget-builds">予算別PC構成</a>をご覧ください。'
        },
        {
            'question': f'{game_title}は何fpsで遊べますか？',
            'answer': f'最低スペック（{min_gpu}相当）で30-60fps、推奨スペック（{rec_gpu}相当）で60-90fps、RTX 4060で100-144fps、RTX 5070で144fps以上が期待できます。詳細は<a href="#gpu-comparison">GPU別性能比較</a>をご覧ください。'
        },
        {
            'question': 'ノートPCでも動きますか？',
            'answer': f'はい、ゲーミングノートでも動作します。RTX 4050搭載モデル（約12万円〜）なら1080p 60fps以上で快適にプレイできます。ただし、バッテリー駆動時は性能が制限されるため、電源接続を推奨します。'
        },
        {
            'question': 'グラボなしの内蔵GPUでも遊べますか？',
            'answer': f'内蔵GPU（Intel Iris Xe、AMD Radeon 780M等）では、低設定で30fps前後の動作になります。快適に遊ぶには専用グラフィックボード（最低でも{min_gpu}以上）が必須です。'
        },
        {
            'question': f'{game_title}が重い・カクつく場合の対処法は？',
            'answer': 'グラフィック設定を「低」に変更、解像度を1080pに下げる、バックグラウンドアプリを終了、グラフィックドライバーを最新版に更新、などを試してください。詳しくは<a href="#troubleshooting">トラブルシューティング</a>をご覧ください。'
        }
    ]

# ルートハンドラーに追加
@app.route('/game/<slug>')
def game_page(slug):
    # 既存のゲームデータ取得処理
    game_data = get_game_data(slug)
    
    # SEOコンテンツ生成
    budget_builds = generate_budget_builds(game_data)
    gpu_comparison = generate_gpu_comparison(game_data)
    faqs = generate_faqs(game_data)
    
    # GPU推奨アドバイス
    gpu_recommendation = {
        'for_60fps': f"{game_data.get('recommended_gpu', 'RTX 4060')} 以上を推奨",
        'for_144fps': "RTX 4060 Ti または RTX 5070 以上を推奨",
        'for_4k': "RTX 5080 以上を推奨"
    }
    
    return render_template('game.html',
                          game=game_data,
                          budget_builds=budget_builds,
                          gpu_comparison=gpu_comparison,
                          faqs=faqs,
                          gpu_recommendation=gpu_recommendation)
```

---

### タスク1.3: CSS追加

**ファイル:** `static/css/style.css`（または新規 `seo-sections.css`）

```css
/* 予算別PC構成カード */
.budget-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.budget-card {
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 20px;
  background: #ffffff;
  transition: all 0.3s ease;
  position: relative;
}

.budget-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  transform: translateY(-4px);
}

.budget-recommended {
  border-color: #4CAF50;
  background: linear-gradient(135deg, #f8fff8 0%, #ffffff 100%);
}

.recommended-badge {
  position: absolute;
  top: -12px;
  right: 20px;
  background: #4CAF50;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.build-specs {
  margin: 15px 0;
}

.spec-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.spec-label {
  font-weight: 600;
  color: #555;
}

.spec-value {
  flex: 1;
  text-align: center;
  color: #333;
}

.spec-price {
  color: #2196F3;
  font-weight: 600;
}

.build-total {
  margin-top: 15px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  text-align: center;
  font-size: 18px;
}

.build-performance {
  margin-top: 10px;
  padding: 10px;
  background: #e3f2fd;
  border-radius: 8px;
  text-align: center;
  color: #1976D2;
  font-size: 14px;
}

.btn-affiliate {
  width: 100%;
  margin-top: 15px;
  padding: 12px;
  background: #FF9800;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-affiliate:hover {
  background: #F57C00;
}

/* GPU比較表 */
.table-responsive {
  overflow-x: auto;
  margin: 20px 0;
}

.gpu-comparison-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.gpu-comparison-table th {
  background: #2196F3;
  color: white;
  padding: 12px;
  text-align: left;
  font-weight: 600;
}

.gpu-comparison-table td {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
}

.gpu-row.recommended {
  background: #f0f8ff;
  border-left: 4px solid #4CAF50;
}

.gpu-notes {
  margin-top: 20px;
  padding: 15px;
  background: #fffde7;
  border-left: 4px solid #FFC107;
  border-radius: 4px;
}

/* FAQ */
.faq-list {
  margin: 20px 0;
}

.faq-item {
  margin-bottom: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.faq-question {
  background: #f5f5f5;
  padding: 15px;
  margin: 0;
  font-size: 16px;
  color: #333;
  cursor: pointer;
  transition: background 0.3s ease;
}

.faq-question:hover {
  background: #eeeeee;
}

.faq-answer {
  padding: 15px;
  background: white;
  line-height: 1.6;
}

/* トラブルシューティング */
.troubleshooting-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.trouble-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  background: white;
}

.trouble-card h3 {
  color: #d32f2f;
  margin-top: 0;
}

.trouble-card ol {
  padding-left: 20px;
  line-height: 1.8;
}

.trouble-note {
  margin-top: 15px;
  padding: 10px;
  background: #e8f5e9;
  border-radius: 4px;
  font-size: 14px;
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
  .budget-cards {
    grid-template-columns: 1fr;
  }
  
  .troubleshooting-grid {
    grid-template-columns: 1fr;
  }
  
  .gpu-comparison-table {
    font-size: 12px;
  }
  
  .gpu-comparison-table th,
  .gpu-comparison-table td {
    padding: 8px;
  }
}
```

---

### タスク1.4: Schema.org 拡張

**ファイル:** `templates/game.html` のスキーマセクション

**既存のFAQPage Schemaを拡張:**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {% for faq in faqs %}
    {
      "@type": "Question",
      "name": "{{ faq.question }}",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "{{ faq.answer | striptags }}"
      }
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
</script>
```

---

## 🚀 Phase 2: インタラクティブ診断機能（優先度: 高）

### 目標
ユーザーエンゲージメントを高める3つの診断機能を追加：
1. **予算診断**: 予算入力 → 最適PC構成提案
2. **GPU比較ツール**: 2つのGPU選択 → 性能比較
3. **スペック診断**: 自分のPC入力 → 動作可否判定

---

### タスク2.1: 予算診断機能

**追加場所:** 各ゲームページの予算別PC構成セクションの下

**HTML:**

```html
<section id="budget-calculator" class="content-section">
  <h2>💰 予算診断ツール</h2>
  <p>あなたの予算に最適なPC構成を診断します。</p>
  
  <div class="calculator-container">
    <div class="input-group">
      <label for="budget-input">予算（税込）:</label>
      <input type="number" id="budget-input" placeholder="例: 120000" min="50000" max="500000" step="10000">
      <span class="unit">円</span>
    </div>
    
    <div class="input-group">
      <label for="target-fps">目標FPS:</label>
      <select id="target-fps">
        <option value="60">60fps（標準）</option>
        <option value="144" selected>144fps（高リフレッシュレート）</option>
        <option value="240">240fps（プロゲーマー）</option>
      </select>
    </div>
    
    <div class="input-group">
      <label for="target-resolution">解像度:</label>
      <select id="target-resolution">
        <option value="1080p" selected>1080p（フルHD）</option>
        <option value="1440p">1440p（WQHD）</option>
        <option value="4k">4K（UHD）</option>
      </select>
    </div>
    
    <button id="diagnose-budget" class="btn-primary">診断する</button>
  </div>
  
  <div id="diagnosis-result" class="diagnosis-result" style="display: none;">
    <!-- 診断結果がここに表示される -->
  </div>
</section>
```

**JavaScript:**

```javascript
// static/js/budget-calculator.js

document.getElementById('diagnose-budget').addEventListener('click', async function() {
  const budget = parseInt(document.getElementById('budget-input').value);
  const targetFps = parseInt(document.getElementById('target-fps').value);
  const resolution = document.getElementById('target-resolution').value;
  const gameSlug = window.location.pathname.split('/').pop();
  
  if (!budget || budget < 50000) {
    alert('予算を入力してください（最低5万円）');
    return;
  }
  
  // APIリクエスト
  const response = await fetch('/api/diagnose-budget', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      game_slug: gameSlug,
      budget: budget,
      target_fps: targetFps,
      resolution: resolution
    })
  });
  
  const result = await response.json();
  
  // 結果表示
  const resultDiv = document.getElementById('diagnosis-result');
  resultDiv.style.display = 'block';
  resultDiv.innerHTML = `
    <h3>${result.verdict_icon} ${result.verdict}</h3>
    <div class="recommended-build">
      <h4>おすすめ構成</h4>
      <ul>
        <li><strong>CPU:</strong> ${result.build.cpu} (¥${result.build.cpu_price.toLocaleString()})</li>
        <li><strong>GPU:</strong> ${result.build.gpu} (¥${result.build.gpu_price.toLocaleString()})</li>
        <li><strong>RAM:</strong> ${result.build.ram} (¥${result.build.ram_price.toLocaleString()})</li>
        <li><strong>ストレージ:</strong> ${result.build.storage} (¥${result.build.storage_price.toLocaleString()})</li>
      </ul>
      <div class="build-total">
        <strong>合計:</strong> ¥${result.build.total.toLocaleString()}
      </div>
      <div class="expected-performance">
        <strong>期待性能:</strong> ${result.build.expected_performance}
      </div>
    </div>
    <div class="diagnosis-notes">
      ${result.notes}
    </div>
  `;
  
  // スムーズスクロール
  resultDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
});
```

**バックエンドAPI:**

```python
# app.py

@app.route('/api/diagnose-budget', methods=['POST'])
def diagnose_budget():
    data = request.json
    game_slug = data.get('game_slug')
    budget = data.get('budget')
    target_fps = data.get('target_fps', 144)
    resolution = data.get('resolution', '1080p')
    
    # ゲームデータ取得
    game_data = get_game_data(game_slug)
    
    # 予算診断ロジック
    result = calculate_budget_build(game_data, budget, target_fps, resolution)
    
    return jsonify(result)

def calculate_budget_build(game_data, budget, target_fps, resolution):
    """
    予算・目標FPS・解像度から最適なPC構成を計算
    """
    
    # 必要性能を計算
    performance_score = calculate_required_performance(game_data, target_fps, resolution)
    
    # GPU選定
    gpu_data = select_gpu_for_budget(budget, performance_score)
    
    # CPU選定（GPUに合わせて）
    cpu_data = select_cpu_for_gpu(gpu_data, budget - gpu_data['price'])
    
    # その他パーツ
    remaining_budget = budget - gpu_data['price'] - cpu_data['price']
    ram_data = select_ram(remaining_budget)
    storage_data = select_storage(remaining_budget - ram_data['price'])
    
    total_cost = gpu_data['price'] + cpu_data['price'] + ram_data['price'] + storage_data['price'] + 20000  # マザボ等
    
    # 判定
    if total_cost <= budget:
        verdict = "✅ この予算で快適にプレイ可能です！"
        verdict_icon = "✅"
    elif total_cost <= budget * 1.1:
        verdict = "⚠️ 予算ギリギリですが可能です"
        verdict_icon = "⚠️"
    else:
        verdict = "❌ この予算では目標性能に届きません"
        verdict_icon = "❌"
    
    return {
        'verdict': verdict,
        'verdict_icon': verdict_icon,
        'build': {
            'cpu': cpu_data['name'],
            'cpu_price': cpu_data['price'],
            'gpu': gpu_data['name'],
            'gpu_price': gpu_data['price'],
            'ram': ram_data['name'],
            'ram_price': ram_data['price'],
            'storage': storage_data['name'],
            'storage_price': storage_data['price'],
            'total': total_cost,
            'expected_performance': f"{resolution} {target_fps}fps"
        },
        'notes': generate_budget_notes(total_cost, budget, verdict_icon)
    }

def generate_budget_notes(total_cost, budget, verdict_icon):
    """診断結果の補足説明"""
    if verdict_icon == "✅":
        return "この構成なら快適にプレイできます。BTOメーカーで購入する場合は、上記構成に近いモデルを選んでください。"
    elif verdict_icon == "⚠️":
        return f"予算を+¥{(total_cost - budget):,}すると、より安定した動作が可能です。または、目標FPSを下げることを検討してください。"
    else:
        shortage = total_cost - budget
        return f"目標性能には+¥{shortage:,}の予算が必要です。予算内で遊ぶには、目標FPSを60fpsに下げるか、解像度を1080pにすることをおすすめします。"
```

---

### タスク2.2: GPU比較ツール

**追加場所:** トップページまたは独立ページ `/gpu-comparison`

**HTML:**

```html
<section id="gpu-comparison-tool" class="content-section">
  <h2>🎮 GPU性能比較ツール</h2>
  <p>2つのGPUを選択して性能・価格・対応ゲーム数を比較できます。</p>
  
  <div class="comparison-selector">
    <div class="gpu-select-group">
      <label>GPU 1:</label>
      <select id="gpu1">
        <option value="">-- 選択してください --</option>
        <!-- GPUリストは動的生成 -->
      </select>
    </div>
    
    <div class="vs-icon">VS</div>
    
    <div class="gpu-select-group">
      <label>GPU 2:</label>
      <select id="gpu2">
        <option value="">-- 選択してください --</option>
      </select>
    </div>
  </div>
  
  <button id="compare-gpus" class="btn-primary">比較する</button>
  
  <div id="comparison-result" class="comparison-result" style="display: none;">
    <!-- 比較結果がここに表示される -->
  </div>
</section>
```

**JavaScript + API実装は同様のパターン**

---

### タスク2.3: スペック診断（「このPCで動く?」）

**追加場所:** 各ゲームページの上部

**HTML:**

```html
<section id="spec-checker" class="content-section highlight-section">
  <h2>🖥️ このPCで{{ game.title }}は動く？</h2>
  <p>あなたのPCスペックを入力して、動作可否を診断します。</p>
  
  <div class="spec-input-grid">
    <div class="input-group">
      <label>GPU:</label>
      <input type="text" id="user-gpu" placeholder="例: RTX 3060">
    </div>
    
    <div class="input-group">
      <label>CPU:</label>
      <input type="text" id="user-cpu" placeholder="例: Ryzen 5 5600">
    </div>
    
    <div class="input-group">
      <label>RAM:</label>
      <input type="number" id="user-ram" placeholder="16" min="4" max="128">
      <span class="unit">GB</span>
    </div>
    
    <div class="input-group">
      <label>解像度:</label>
      <select id="user-resolution">
        <option value="1080p">1080p</option>
        <option value="1440p">1440p</option>
        <option value="4k">4K</option>
      </select>
    </div>
  </div>
  
  <button id="check-spec" class="btn-primary">診断する</button>
  
  <div id="spec-result" class="spec-result" style="display: none;">
    <!-- 診断結果がここに表示される -->
  </div>
</section>
```

**診断ロジック:**

```python
@app.route('/api/check-spec', methods=['POST'])
def check_spec():
    data = request.json
    user_gpu = data.get('gpu')
    user_cpu = data.get('cpu')
    user_ram = data.get('ram')
    resolution = data.get('resolution', '1080p')
    game_slug = data.get('game_slug')
    
    # ゲーム要件取得
    game_data = get_game_data(game_slug)
    
    # 14,000件の互換性データから判定
    compatibility = check_compatibility(user_gpu, user_cpu, user_ram, game_data, resolution)
    
    return jsonify(compatibility)

def check_compatibility(user_gpu, user_cpu, user_ram, game_data, resolution):
    """
    14,000件の互換性データベースから判定
    
    返り値:
    - verdict: "動く" / "カクつく可能性" / "動かない"
    - expected_fps: 予想FPS
    - bottleneck: ボトルネック警告
    - upgrade_suggestion: アップグレード提案
    """
    
    # GPU性能スコア取得（14,000件のデータベースから）
    gpu_score = get_gpu_score(user_gpu)
    required_score = get_required_gpu_score(game_data, resolution)
    
    # CPU性能チェック
    cpu_score = get_cpu_score(user_cpu)
    required_cpu_score = get_required_cpu_score(game_data)
    
    # RAM容量チェック
    required_ram = game_data.get('recommended_ram_gb', 8)
    
    # 総合判定
    if gpu_score >= required_score * 1.2 and cpu_score >= required_cpu_score and user_ram >= required_ram:
        verdict = "✅ 快適に動作します"
        expected_fps = estimate_fps(gpu_score, required_score, resolution)
        color = "green"
    elif gpu_score >= required_score * 0.8:
        verdict = "⚠️ 動作しますが、カクつく可能性があります"
        expected_fps = estimate_fps(gpu_score, required_score, resolution) * 0.7
        color = "orange"
    else:
        verdict = "❌ スペック不足です"
        expected_fps = 30
        color = "red"
    
    # ボトルネック診断
    bottleneck = diagnose_bottleneck(gpu_score, cpu_score, user_ram, required_score, required_cpu_score, required_ram)
    
    # アップグレード提案
    upgrade = suggest_upgrade(user_gpu, user_cpu, user_ram, game_data, resolution)
    
    return {
        'verdict': verdict,
        'color': color,
        'expected_fps': int(expected_fps),
        'bottleneck': bottleneck,
        'upgrade_suggestion': upgrade
    }
```

---

## 📊 Phase 3: データ管理（優先度: 中）

### タスク3.1: GPU/CPUマスターデータ作成

**ファイル:** `workspace/data/hardware/gpus.json`

```json
[
  {
    "name": "RTX 3050",
    "manufacturer": "NVIDIA",
    "series": "RTX 30",
    "price": 28000,
    "performance_score": 18,
    "vram_gb": 8,
    "tdp_watts": 130,
    "release_year": 2022
  },
  {
    "name": "RTX 4060",
    "manufacturer": "NVIDIA",
    "series": "RTX 40",
    "price": 45000,
    "performance_score": 30,
    "vram_gb": 8,
    "tdp_watts": 115,
    "release_year": 2023
  },
  ...
]
```

**ファイル:** `workspace/data/hardware/cpus.json`

```json
[
  {
    "name": "Ryzen 5 5600",
    "manufacturer": "AMD",
    "series": "Ryzen 5000",
    "price": 15980,
    "performance_score": 20,
    "cores": 6,
    "threads": 12,
    "base_clock_ghz": 3.5,
    "boost_clock_ghz": 4.4,
    "release_year": 2022
  },
  ...
]
```

---

### タスク3.2: 互換性データベース統合

**ファイル:** `workspace/data/compatibility/gpu_game_compatibility.json`

**構造:**

```json
{
  "RTX 4060": {
    "apex-legends": {
      "fps_1080p": 180,
      "fps_1440p": 120,
      "fps_4k": 65,
      "settings": "高",
      "verified": true,
      "last_updated": "2026-03-01"
    },
    "cyberpunk-2077": {
      "fps_1080p": 90,
      "fps_1440p": 60,
      "fps_4k": 35,
      "settings": "高（レイトレなし）",
      "verified": true,
      "last_updated": "2026-03-01"
    }
  }
}
```

---

## 🎯 実装の優先順位

### Week 1（最優先）
1. ✅ **Phase 1 - タスク1.1**: テンプレートにセクション追加
2. ✅ **Phase 1 - タスク1.2**: バックエンドでデータ生成
3. ✅ **Phase 1 - タスク1.3**: CSS追加
4. ✅ **Phase 1 - タスク1.4**: Schema.org拡張

**目標**: 443ゲームページ全てにコンテンツ追加完了

---

### Week 2（高優先）
5. ✅ **Phase 2 - タスク2.1**: 予算診断機能
6. ✅ **Phase 2 - タスク2.3**: スペック診断（「このPCで動く?」）

**目標**: 2つの診断機能をリリース

---

### Week 3-4（中優先）
7. ✅ **Phase 2 - タスク2.2**: GPU比較ツール
8. ✅ **Phase 3**: データ管理（GPU/CPUマスターデータ）

**目標**: 全機能完成 + データベース整備

---

## 📈 効果測定

### KPI
1. **検索流入**: Google Search Console で `[ゲーム名] 予算` 等のキーワードでの流入増加
2. **滞在時間**: Google Analytics で平均滞在時間UP（診断機能の効果）
3. **直帰率**: 診断機能により直帰率DOWN
4. **SNSシェア**: Twitter/Reddit等でのシェア数

### 目標値（3ヶ月後）
- 検索流入: 現在の3倍
- 平均滞在時間: 2分→5分
- 直帰率: 70%→50%

---

## 🚨 注意事項

### SEO維持
- ⚠️ **URLは絶対に変更しない**（既に443ゲームのスキーマが検索エンジンにインデックス済み）
- ⚠️ **既存のSchema.orgは維持**（FAQPage, VideoGame, SoftwareApplication, Organization）
- ⚠️ **meta タグは維持**（title, description, keywords）

### パフォーマンス
- 診断機能はJavaScriptで非同期実行（ページロードを遅延させない）
- GPU/CPUマスターデータはキャッシュする
- 大量のDOM操作は避ける

### モバイル対応
- 全セクションはレスポンシブデザイン必須
- 表は横スクロール対応
- ボタンはタッチ操作を考慮（最小44x44px）

---

## ✅ チェックリスト

### Phase 1 完了条件
- [ ] 443ゲームページ全てに4つのセクションが追加されている
- [ ] 予算別PC構成が3パターン（8万/12万/18万）表示される
- [ ] GPU比較表が5-10種類のGPUで表示される
- [ ] FAQが6問表示される
- [ ] トラブルシューティングが4種類表示される
- [ ] CSSが適用されてデザインが整っている
- [ ] モバイルでも正常に表示される
- [ ] Schema.org（FAQPage）が正しく出力される

### Phase 2 完了条件
- [ ] 予算診断機能が動作する
- [ ] スペック診断機能が動作する
- [ ] 診断結果が適切に表示される
- [ ] エラーハンドリングが適切
- [ ] APIレスポンスが1秒以内

### Phase 3 完了条件
- [ ] GPU/CPUマスターデータが整備されている
- [ ] 互換性データベースが構築されている
- [ ] データ更新スクリプトが用意されている

---

## 📞 サポート

質問や不明点があれば、このファイルにコメントを追加するか、プロジェクトのREADME.mdを参照してください。

---

**作成日:** 2026年3月3日  
**最終更新:** 2026年3月3日  
**作成者:** OpenClaw AI  
**対象読者:** Claude Code（コーディングエージェント）
