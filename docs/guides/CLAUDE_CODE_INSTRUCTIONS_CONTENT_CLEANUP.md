# Content Cleanup & Quality Improvement
**実装目標**: ハードコードされた推測値を削除し、誠実なコンテンツに改善する

## 🎯 Phase 1: ハードコード削除（今日実装）

### 1.1 予算別PC構成セクション（BUDGET_BUILDS）
**ファイル**: `scripts/generate_game_pages.py`

**問題箇所**:
```python
"performance": "1080p 高設定 60〜100fps前後"  # ← 実測データなしの推測値
```

**修正方針**:
- FPS値の記述を**完全削除**
- 代わりに「設定例」として表現

**修正後の例**:
```python
"performance": "1080p高設定でのプレイに対応"  # FPS値は言及しない
```

または:
```python
"performance": "フルHD環境での快適なプレイを想定"
```

**適用箇所**:
- `BUDGET_BUILDS["minimum"]["performance"]`
- `BUDGET_BUILDS["recommended"]["performance"]`
- `BUDGET_BUILDS["premium"]["performance"]`

---

### 1.2 GPU比較テーブル（GPU_COMPARISON）
**ファイル**: `scripts/generate_game_pages.py`

**問題箇所**:
```python
GPU_COMPARISON = [
    {"name": "RTX 3060", "fps_1080p": 70, "fps_wqhd": 45, "fps_4k": 27},  # ← 実測なし
    ...
]
```

**修正方針 A（推奨）**: FPS列を完全削除
```python
GPU_COMPARISON = [
    {"name": "RTX 3060", "price": 29800, "rating": 3},
    {"name": "RTX 4060", "price": 45800, "rating": 4, "recommended": True},
    ...
]
```

テーブルの表示列を変更:
- 削除: `1080p`, `WQHD`, `4K` 列
- 追加: `VRAM`, `TDP`, `コスパ` 列（これらは公式スペック）

**修正方針 B（代替案）**: 実測データソース明記
```python
{"name": "RTX 4060", "price": 45800, "rating": 4, "source": "TechPowerUp平均値"}
```

注釈を追加:
> ⚠️ FPS値は一般的なゲームの平均値です。{game_name}での実測値ではありません。

**今日の実装**: 修正方針Aで進める（FPS列削除）

---

### 1.3 FAQセクション
**ファイル**: `scripts/generate_game_pages.py` L203-252

**問題箇所**:
```python
{
    "q": f"{name}は何fpsで遊べますか？",
    "a": f"最低スペックで30〜60fps前後、推奨スペックで60〜90fps前後が..."  # ← 推測値
}
```

**修正方針**:
推測FPS値を削除し、誠実な回答に変更

**修正後の例**:
```python
{
    "q": f"{name}は何fpsで遊べますか？",
    "a": f"フレームレートはPC構成・グラフィック設定により大きく異なります。最低スペック（{min_gpu}）では30fps前後、推奨スペック（{rec_gpu}）では60fps以上を期待できますが、正確な値はAI診断チャットでご確認ください。"
}
```

**適用するFAQ**:
- Q: 「{name}の推奨スペックは？」 → "60fps前後で快適に" を削除
- Q: 「予算10万円で組める？」 → "1080p 60fps前後" を削除 or "快適動作を期待できます"
- Q: 「何fpsで遊べますか？」 → 上記の通り修正

---

### 1.4 サイドバー: ジャンル別セクション削除
**ファイル**: `index.html` or `static/` 配下のテンプレート

**対象**: スクリーンショットで確認したジャンル別リンク
```html
<!-- 削除対象 -->
<div class="sidebar-genres">
  <h3>🎮 ジャンル別</h3>
  <ul>
    <li>RPG</li>
    <li>FPS・シューター</li>
    <li>レーシング</li>
    ...
  </ul>
</div>
```

**理由**:
- 静的リスト（更新されない）
- ユーザー価値が低い
- 代わりに「人気ゲームTOP10」「新着ゲーム」を動的更新する（Phase 2）

**今日の実装**:
1. サイドバーからジャンルセクションを完全削除
2. 該当するCSS/JSも削除

---

## 🔄 Phase 2: 動的コンテンツ更新（次回実装）

### 2.1 人気ゲームTOP10の自動更新
**データソース**: Steam Charts (https://steamcharts.com/)

**実装概要**:
```python
# scripts/fetch_popular_games.py
import requests
from bs4 import BeautifulSoup

def fetch_steam_top10():
    """Steam Chartsから現在のTOP10を取得"""
    url = "https://steamcharts.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # TOP10を抽出（実装詳細は省略）
    top10 = [...]
    
    # workspace/data/popular_games.json に保存
    with open('workspace/data/popular_games.json', 'w') as f:
        json.dump(top10, f, ensure_ascii=False, indent=2)
```

**GitHub Actions設定**:
```yaml
# .github/workflows/update-popular-games.yml
name: Update Popular Games
on:
  schedule:
    - cron: '0 3 * * 0'  # 毎週日曜 3:00 AM JST
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: python scripts/fetch_popular_games.py
      - uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "chore: update popular games TOP10"
```

### 2.2 新着ゲームの自動更新
**データソース**: Steam Store API

**実装**: Phase 2で詳細設計

---

## 🤖 Phase 3: OPUSリライトフロー（次回実装）

### 3.1 低パフォーマンス記事の自動検出
**データソース**: Google Analytics 4 Data API

**条件**:
- 滞在時間 < 30秒
- 離脱率 > 80%
- 直近7日間のPV > 10

### 3.2 Claude OPUS APIでリライト
```python
# scripts/rewrite_articles.py
import anthropic

def rewrite_article(game_name, original_content):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    prompt = f"""
    以下のゲーム紹介記事を、より魅力的で読みやすく改善してください。
    
    【ゲーム名】: {game_name}
    【元の記事】:
    {original_content}
    
    【改善ポイント】:
    - 推測的な表現（"約〜fps"など）を削除
    - ユーザーの疑問に答える構成
    - 読みやすい文章構造
    """
    
    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text
```

### 3.3 PR自動生成
GitHub CLI (`gh`) でPR作成:
```bash
gh pr create \
  --title "content: OPUS rewrite for ${game_name}" \
  --body "GA4データに基づく低パフォーマンス記事の改善" \
  --label "content-improvement"
```

---

## ✅ 今日の実装チェックリスト

### Step 1: ハードコード削除
- [ ] `BUDGET_BUILDS` のFPS値削除 → 設定例に変更
- [ ] `GPU_COMPARISON` のFPS列削除 → VRAM/TDP列追加
- [ ] FAQ: 推測FPS値を削除 → 誠実な表現に変更
- [ ] サイドバー: ジャンルセクション削除

### Step 2: 動作確認
- [ ] ローカルで `python scripts/generate_game_pages.py` 実行
- [ ] 生成されたHTMLを確認（推測値が残っていないか）
- [ ] サイドバーの表示確認

### Step 3: コミット＆デプロイ
- [ ] `git add .`
- [ ] `git commit -m "content: remove hardcoded FPS estimates, improve honesty"`
- [ ] `git push origin main`
- [ ] Railway自動デプロイ確認

---

## 📝 実装時の注意事項

### 誠実さの基準
❌ **悪い例**: "RTX 4060なら60fps以上出ます"
✅ **良い例**: "RTX 4060は1080p高設定での快適なプレイに対応します"

❌ **悪い例**: "予算12万円で100fps確実"
✅ **良い例**: "予算12万円で高設定での快適なプレイが期待できます"

### 削除してはいけないもの
✅ **残す**: 公式スペック（RAM容量、VRAM容量、TDP）
✅ **残す**: パーツ価格（価格.com等で確認可能）
✅ **残す**: "目安"や"期待値"として明記した場合の参考値

❌ **削除**: 実測データのないFPS値
❌ **削除**: 推測に基づく性能主張

---

## 🚀 次回以降のロードマップ

1. **Week 1**: Phase 1完了（ハードコード削除）← 今日
2. **Week 2**: Phase 2実装（Steam連携で動的更新）
3. **Week 3**: Phase 3実装（GA4 + OPUS自動リライト）
4. **Week 4**: 効果測定（離脱率・滞在時間の改善確認）

---

## 💡 補足: なぜハードコードが問題なのか

### ユーザー視点
- 実測値でない情報 → 期待と現実のギャップ → 信頼損失
- 「60fpsって書いてあったのに30fpsしか出ない」→ クレーム

### SEO視点
- Googleは「E-E-A-T」（経験・専門性・権威性・信頼性）を重視
- 推測値だらけのコンテンツ → 低評価 → 検索順位低下

### 競合優位性
- TechPowerUp等は実測データを提供 → 信頼性で勝てない
- 差別化ポイント: "誠実さ" と "AI診断による個別対応"

---

**実装者**: Claude Code (Cursor/Windsurf)  
**レビュー**: 岩下さん  
**期限**: 2026-03-05（今日）  
**優先度**: 🔥 HIGH（信頼性に直結）
