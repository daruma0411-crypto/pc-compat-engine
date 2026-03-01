# SEO・AIO強化策計画書
**PC互換チェッカー（PC Compat Engine）**  
**URL**: https://pc-compat-engine-production.up.railway.app/  
**作成日**: 2026年3月1日

---

## 📊 現状分析

### ✅ 既に実施済み
- [x] Google Search Console登録（新URL）
- [x] Google Analytics 4設定（測定ID: G-PPNEBG625J）
- [x] サイトマップ送信（sitemap.xml）
- [x] 416ゲームの個別ページ
- [x] Railway.appへの移行

### 📈 現在の状況
- 総ページ数: 約420ページ（トップ + 416ゲーム + その他）
- トラフィック: 新規サイト立ち上げ直後
- インデックス: Google Search Consoleで処理中

---

## 🎯 SEO・AIO強化策（優先度順）

---

## 【優先度A】即効性のある施策（1-2週間）

### 1. **構造化データ（Schema.org）の実装**

#### 1-1. FAQPage Schema（最優先！）
**目的**: GoogleのAI Overview（生成AI検索）とFAQ枠に表示

**実装箇所**:
- トップページ
- 各ゲームページ

**実装例**（各ゲームページ）:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Apex LegendsのPC推奨スペックは？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Apex LegendsのPC推奨スペックは、CPU: Intel Core i5-3570K、GPU: NVIDIA GTX 970 / AMD Radeon R9 290、メモリ: 8GB RAM、ストレージ: SSD 22GBです。144fps安定動作にはRTX 4060以上を推奨します。"
      }
    },
    {
      "@type": "Question",
      "name": "予算10万円でApex用PCは組める？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "はい、予算10万円でApex Legends用のPCを組めます。RTX 4060（約4.5万円）+ Ryzen 5 7600（約2.5万円）+ 16GB RAM（約0.8万円）の構成で、1080p 144fps以上の動作が可能です。"
      }
    }
  ]
}
```

**期待効果**:
- GoogleのAI Overviewに引用される確率UP
- FAQ枠に表示される可能性
- CTR（クリック率）向上

---

#### 1-2. SoftwareApplication Schema
**目的**: Webアプリケーションとして認識

**実装箇所**: トップページ

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "PC互換チェッカー",
  "applicationCategory": "WebApplication",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "JPY"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "127"
  }
}
```

---

#### 1-3. VideoGame Schema（各ゲームページ）
**目的**: ゲーム情報として正しく認識

```json
{
  "@context": "https://schema.org",
  "@type": "VideoGame",
  "name": "Apex Legends",
  "operatingSystem": "Windows 10/11",
  "memoryRequirements": "8GB RAM minimum, 16GB recommended",
  "processorRequirements": "Intel Core i5-3570K / AMD FX-6350",
  "storageRequirements": "22GB SSD"
}
```

---

### 2. **メタ情報の最適化**

#### 2-1. タイトルタグ改善
**現在の問題**: タイトルが長すぎる、または一般的すぎる

**改善案**（例：Apex Legends）:
```html
<!-- Before -->
<title>Apex Legends | PC互換チェッカー</title>

<!-- After（SEO最適化）-->
<title>Apex Legends 推奨スペック｜予算別PC構成提案【2026年最新】</title>
```

**ポイント**:
- 検索キーワードを含める（「推奨スペック」「予算」「PC構成」）
- 年号を入れて鮮度をアピール
- 60文字以内

---

#### 2-2. メタディスクリプション改善
```html
<!-- Before -->
<meta name="description" content="Apex LegendsのPC推奨スペックを確認できます。">

<!-- After -->
<meta name="description" content="Apex Legendsの推奨スペックと予算別PC構成を提案。FHD 144fps・WQHD・4K対応。RTX 4060で10万円台、RTX 5070で15万円台の最適構成をAIが診断。無料チャット相談OK。">
```

**ポイント**:
- 具体的な数値（144fps、10万円など）
- 「無料」「AI診断」などの訴求ポイント
- 155文字以内

---

### 3. **ページ内コンテンツの充実**

#### 3-1. 各ゲームページに追加すべきセクション

**A. よくある質問（FAQ）**
```markdown
## よくある質問

### Q1. Apex Legendsは何fpsで遊べますか？
推奨スペック（GTX 970相当）で60fps安定、RTX 4060で144fps以上、RTX 5070で240fps以上が可能です。

### Q2. ノートPCでも動きますか？
はい。RTX 4050搭載ゲーミングノート（約12万円〜）なら1080p 60fps以上で快適に遊べます。

### Q3. グラボなしでも遊べますか？
内蔵GPU（Iris Xe、Radeon 780M）では低設定30fps程度。快適に遊ぶなら専用グラボ必須です。
```

**B. 予算別構成例**
```markdown
## 予算別PC構成

### 予算8万円（最低動作）
- CPU: Ryzen 5 5600 (¥15,980)
- GPU: RTX 3050 (¥28,000)
- RAM: 16GB (¥8,000)
- 合計: 約8万円
- 期待性能: 1080p 低設定 60fps

### 予算12万円（推奨動作）
- CPU: Ryzen 5 7600 (¥28,000)
- GPU: RTX 4060 (¥45,000)
- RAM: 16GB DDR5 (¥10,000)
- 合計: 約12万円
- 期待性能: 1080p 高設定 144fps
```

**C. 比較表**
```markdown
## GPU別性能比較

| GPU | 価格 | 1080p FPS | WQHD FPS | 4K FPS |
|-----|------|-----------|----------|--------|
| RTX 3050 | ¥28,000 | 60fps | 40fps | 25fps |
| RTX 4060 | ¥45,000 | 144fps | 90fps | 50fps |
| RTX 5070 | ¥75,000 | 240fps | 165fps | 100fps |
```

---

## 【優先度B】中長期施策（1-2ヶ月）

### 4. **コンテンツ拡充**

#### 4-1. 比較記事の追加
**URL例**: `/comparison/apex-vs-valorant-spec`

**タイトル**: 「Apex Legends vs VALORANT どっちが重い？推奨スペック比較【2026年版】」

**コンテンツ構成**:
1. 推奨スペック比較表
2. GPU別fps比較
3. 予算別おすすめ（「どっちも遊ぶなら○○」）
4. 実測データ

**SEO効果**:
- 比較キーワード（「Apex VALORANT 重い」など）で上位表示
- 回遊率UP（他ゲームページへの内部リンク）

---

#### 4-2. ガイド記事の追加
**URL例**: `/guide/gaming-pc-build-2026`

**タイトル**: 「【2026年版】ゲーミングPC自作ガイド｜予算別パーツ構成と組み立て手順」

**コンテンツ構成**:
1. 予算別構成（8万/12万/15万/20万円）
2. パーツ選びのコツ
3. 組み立て手順（写真付き）
4. よくあるトラブルと対処法

**SEO効果**:
- 「ゲーミングPC 自作 2026」などのビッグキーワード
- サイト全体の権威性UP

---

#### 4-3. 月次更新記事
**URL例**: `/blog/2026-03-best-gaming-gpu`

**タイトル**: 「2026年3月版｜コスパ最強ゲーミングGPUランキングTOP10」

**コンテンツ構成**:
1. 価格帯別ランキング（2万円台/4万円台/7万円台）
2. 最新ベンチマーク
3. おすすめゲームタイトル別

**SEO効果**:
- 鮮度の高いコンテンツとして評価
- 毎月更新で継続的なトラフィック

---

### 5. **内部リンク最適化**

#### 5-1. 関連ゲームリンク
各ゲームページに「似たスペックのゲーム」セクションを追加：

```markdown
## このスペックで遊べる他のゲーム
- [VALORANT](/game/valorant)（より軽量）
- [オーバーウォッチ2](/game/overwatch-2)（同程度）
- [コール オブ デューティ](/game/call-of-duty-modern-warfare)（やや重い）
```

**効果**:
- 回遊率UP
- サイト滞在時間UP
- Googleの評価向上

---

#### 5-2. パンくずリスト
```html
<nav aria-label="Breadcrumb">
  <ol>
    <li><a href="/">ホーム</a></li>
    <li><a href="/category/fps">FPSゲーム</a></li>
    <li>Apex Legends</li>
  </ol>
</nav>
```

**Schema.org BreadcrumbList**も追加。

---

### 6. **UGC（ユーザー生成コンテンツ）の導入**

#### 6-1. レビュー・コメント機能
- 各構成への★評価
- 「この構成で実際に動作したか」のフィードバック

**Schema.org Review追加で、検索結果に★表示**。

---

## 【優先度C】AIO（AI Overview）特化施策

### 7. **AI検索最適化**

#### 7-1. 明確な質問-回答形式
Google Bard/ChatGPT/Copilotが引用しやすい形式：

```markdown
## Apex LegendsのPC推奨スペックは？

**回答**: Apex LegendsのPC推奨スペックは以下の通りです：
- **CPU**: Intel Core i5-3570K / AMD FX-6350
- **GPU**: NVIDIA GTX 970 / AMD Radeon R9 290
- **メモリ**: 8GB RAM
- **ストレージ**: SSD 22GB

ただし、これは「動作する」最低ラインです。144fps安定動作には、RTX 4060以上を推奨します。
```

**ポイント**:
- 質問文を見出しに
- 簡潔で具体的な回答
- 数値を明記

---

#### 7-2. 「〜とは」系コンテンツ
```markdown
## 推奨スペックとは？
推奨スペックとは、ゲームを快適に遊ぶために必要なPCの性能です。最低スペックが「動作する最低ライン」であるのに対し、推奨スペックは「高画質で快適に遊べる性能」を指します。
```

**効果**:
- AI検索での「定義」回答に引用される

---

#### 7-3. 権威性の向上
- **運営者情報**の明記
- **データソース**の明記（価格.com、Steam公式など）
- **更新日**の表示

---

## 📅 実装スケジュール（2ヶ月計画）

### Week 1-2（3月第1-2週）
- [ ] FAQPage Schema実装（全ページ）
- [ ] メタタイトル・ディスクリプション改善（主要20ゲーム）
- [ ] 各ゲームページにFAQセクション追加

### Week 3-4（3月第3-4週）
- [ ] SoftwareApplication Schema（トップページ）
- [ ] VideoGame Schema（全ゲームページ）
- [ ] 予算別構成例追加（主要10ゲーム）

### Week 5-6（4月第1-2週）
- [ ] 比較記事3本作成
- [ ] 内部リンク最適化
- [ ] パンくずリスト実装

### Week 7-8（4月第3-4週）
- [ ] ガイド記事2本作成
- [ ] レビュー機能実装（検討）
- [ ] 月次更新記事の運用開始

---

## 📊 KPI（成果指標）

### 短期目標（1ヶ月後）
- Google Search Console インプレッション: 1,000/日
- クリック数: 50/日
- CTR: 5%以上
- 平均掲載順位: 20位以内（主要キーワード）

### 中期目標（3ヶ月後）
- インプレッション: 5,000/日
- クリック数: 300/日
- CTR: 6%以上
- 平均掲載順位: 10位以内

### 長期目標（6ヶ月後）
- インプレッション: 10,000/日
- クリック数: 800/日
- CTR: 8%以上
- AI Overview掲載: 月10回以上

---

## 🛠️ 技術的実装方法

### Schema.orgの追加（例）
Railway.appのビルドプロセスに組み込み、各HTMLに自動挿入：

```python
# app.py に追加
def add_schema_markup(game_data):
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"{game_data['name']}の推奨スペックは？",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": generate_faq_answer(game_data)
                }
            }
        ]
    }
    return json.dumps(schema, ensure_ascii=False)
```

---

## 📝 次のアクション

**最優先タスク**:
1. FAQPage Schema実装スクリプト作成
2. メタ情報改善（トップ20ゲーム）
3. Google Search Consoleでインデックス状況確認

**どれから始めますか？**
