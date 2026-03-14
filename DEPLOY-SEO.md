# SEO強化施策 デプロイ手順書

**作成日**: 2026年3月1日  
**ブランチ**: feature/seo-schema  
**対象**: PC互換チェッカー（PC Compat Engine）

---

## 📋 実装済み内容

### トップページ（static/index.html）
1. ✅ **FAQPage Schema.org** - 6つのよくある質問
2. ✅ **SoftwareApplication Schema.org** - ★4.8評価表示
3. ✅ **Organization Schema.org** - 組織情報
4. ✅ **OGタグURL更新** - Railway.appに統一

### 自動生成ツール
1. ✅ **generate_game_schemas_v2.py** - 445ゲーム対応Schema生成
2. ✅ **meta_optimization.csv** - 主要20ゲームのメタ情報改善案
3. ✅ **content_templates.md** - FAQ・予算別構成・GPU比較表テンプレート
4. ✅ **test_schema_validation.py** - Schema.org検証ツール

### 生成済みファイル
- `scripts/generated_schemas_v2/` - 443ゲームのSchema（99.6%成功率）

---

## 🚀 デプロイ手順

### ステップ1: ブランチ確認

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine
git branch
# * feature/seo-schema であることを確認
```

### ステップ2: 変更内容を確認

```bash
git log --oneline -5 feature/seo-schema
git diff main feature/seo-schema --stat
```

### ステップ3: テスト実行（ローカル）

```bash
# Flaskサーバー起動
python app.py

# 別ターミナルで
python scripts/test_schema_validation.py
```

### ステップ4: mainブランチにマージ

```bash
# mainブランチに切り替え
git checkout main

# 最新を確認
git pull origin main

# feature/seo-schemaをマージ
git merge feature/seo-schema

# コンフリクトがあれば解決
```

### ステップ5: 本番環境にプッシュ

```bash
# 本番環境（Railway.app）にデプロイ
git push origin main
```

**⚠️ 注意**: Railway.appが自動的に再デプロイを開始します（1-3分）

---

## ⏱️ デプロイ後の確認（5-10分後）

### 1. サイトアクセス確認

```
https://pc-jisaku.com/
```

- [ ] ページが正常に表示される
- [ ] エラーが出ていない
- [ ] デザイン崩れがない

### 2. Schema.org確認

**方法A: Google Rich Results Test**

1. https://search.google.com/test/rich-results を開く
2. URLを入力: `https://pc-jisaku.com/`
3. 「URLをテスト」をクリック
4. 以下が検出されることを確認：
   - [ ] FAQPage（6つの質問）
   - [ ] SoftwareApplication（★4.8評価）
   - [ ] Organization
   - [ ] エラー0件

**方法B: ブラウザでHTMLソース確認**

1. https://pc-jisaku.com/ を開く
2. F12キー → Elementsタブ
3. `<head>`内に以下があることを確認：
   ```html
   <script type="application/ld+json">
     "@type": "FAQPage"
   </script>
   ```

### 3. Google Search Console確認

1. https://search.google.com/search-console を開く
2. プロパティ選択: `https://pc-jisaku.com/`
3. 左メニュー → **拡張** → **FAQ**
   - [ ] 数日後にFAQが検出される
4. **エクスペリエンス** → **ページエクスペリエンス**
   - [ ] エラーがないことを確認

---

## 🔄 ロールバック手順（問題発生時）

### 緊急ロールバック

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine

# 直前のコミットに戻す
git revert HEAD --no-edit

# 本番環境にプッシュ
git push origin main
```

### 完全ロールバック

```bash
# feature/seo-schema マージ前の状態に戻す
git reset --hard <マージ前のコミットハッシュ>

# 強制プッシュ（⚠️慎重に）
git push origin main --force
```

---

## 📊 効果測定（デプロイ後）

### 短期（1週間後）

1. **Google Search Console**
   - インプレッション数の変化
   - CTRの変化
   - 平均掲載順位

2. **Google Analytics**
   - オーガニック検索流入の増加
   - 直帰率の変化
   - 平均セッション時間

### 中期（1ヶ月後）

1. **AI Overview掲載**
   - Googleで関連キーワード検索
   - AI Overviewに引用されているか確認
   - 例: 「Apex Legends 推奨スペック」

2. **Rich Results表示**
   - FAQ枠に表示されているか
   - ★評価が検索結果に表示されているか

### 長期（3ヶ月後）

1. **インデックス数**
   - `site:pc-jisaku.com` で検索
   - 416ゲームページがインデックスされているか

2. **主要キーワード順位**
   - 「ゲーミングPC 推奨スペック」
   - 「自作PC 互換性」
   - 「GPU 選び方」
   - など

---

## 📈 KPI目標

### 1ヶ月後
- Google Search Console インプレッション: **1,000/日**
- クリック数: **50/日**
- CTR: **5%以上**
- 平均掲載順位: **20位以内**

### 3ヶ月後
- インプレッション: **5,000/日**
- クリック数: **300/日**
- CTR: **6%以上**
- 平均掲載順位: **10位以内**
- AI Overview掲載: **月10回以上**

### 6ヶ月後
- インプレッション: **10,000/日**
- クリック数: **800/日**
- CTR: **8%以上**
- 主要キーワード: **5位以内**

---

## 🛠️ トラブルシューティング

### Q1. Schema.orgが検出されない

**確認事項:**
- [ ] HTMLソースに`<script type="application/ld+json">`が存在するか
- [ ] JSON形式が正しいか（カンマ・括弧の閉じ忘れ）
- [ ] 文字化けしていないか

**対処:**
```bash
python scripts/test_schema_validation.py
```

### Q2. デプロイ後にサイトが動かない

**確認事項:**
- [ ] Railway.appのデプロイログにエラーがないか
- [ ] Pythonのバージョンが合っているか（3.11.11）
- [ ] 環境変数が設定されているか

**対処:**
```bash
# ローカルでテスト
python app.py
# エラーが出たらログを確認
```

### Q3. Google Search Consoleでエラー

**よくあるエラー:**
- 「必須プロパティがありません」 → Schema.orgの必須項目を追加
- 「無効な値」 → データ型を確認（文字列/数値/配列）

**対処:**
- Google Rich Results Testで詳細エラーを確認
- Schema.orgドキュメントと照合

---

## 📝 チェックリスト

### デプロイ前
- [ ] feature/seo-schemaブランチで作業完了
- [ ] ローカルテスト成功
- [ ] コミットメッセージが明確
- [ ] バックアップ取得（念のため）

### デプロイ中
- [ ] mainブランチにマージ
- [ ] コンフリクト解決
- [ ] git push origin main
- [ ] Railway.appデプロイ開始を確認

### デプロイ後
- [ ] サイトアクセス確認（https://pc-jisaku.com/）
- [ ] Schema.org検証（Google Rich Results Test）
- [ ] エラー確認（ブラウザコンソール）
- [ ] Google Search Console送信

---

## 📞 サポート

### ドキュメント
- OpenClaw: https://docs.openclaw.ai
- Schema.org: https://schema.org
- Google Search Central: https://developers.google.com/search

### コマンドクイックリファレンス

```bash
# ブランチ確認
git branch

# 変更確認
git status
git diff

# ローカルサーバー起動
python app.py

# Schema検証
python scripts/test_schema_validation.py

# ゲームSchema生成（全件）
python scripts/generate_game_schemas_v2.py

# Railway.appログ確認（ブラウザ）
https://railway.app/dashboard
```

---

**デプロイ準備完了！** 🚀

このドキュメントに従って、安全にSEO強化施策をデプロイしてください。
