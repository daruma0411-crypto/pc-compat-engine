# 🖥️ PC互換性チェッカー

ゲーム・動画編集・作業PC、用途から最適なPCを提案するWebアプリケーション。

**本番環境**: https://pc-jisaku.com/

---

## ⚠️ 開発者への重要な警告

**Claude Codeで作業する前に、必ず以下を実行してください：**

```
@claude.md を読んでから作業を開始してください。
```

**📄 `claude.md` には以下の重要情報があります：**
- 🚨 絶対にやってはいけないこと（バックグラウンド実行禁止など）
- 📋 プロジェクト現状
- ⚠️ 過去に発生した問題と解決方法
- ✅ 開発時の推奨フロー
- 📞 緊急時の対応マニュアル

**`claude.md` を読まずに作業すると、重大な問題が発生する可能性があります。**

---

## 🚀 クイックスタート

### ローカル開発
```bash
# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動（フォアグラウンド）
python app.py

# ブラウザで確認
# http://127.0.0.1:5000

# 停止: Ctrl+C
```

### 本番デプロイ
```bash
git add -A
git commit -m "feat: 新機能追加"
git push origin main
# → Renderが自動デプロイ
```

---

## 📁 プロジェクト構成

```
pc-compat-engine/
├── app.py                    # Flaskアプリ（メイン）
├── requirements.txt          # Python依存関係
├── static/
│   ├── index.html           # トップページ
│   ├── style.css            # スタイル
│   ├── app.js               # フロントエンドJS
│   └── game/                # 415ゲームページ
├── workspace/data/          # パーツデータ（JSONL）
├── marketing-materials.md   # マーケティング素材
├── claude.md                # ⚠️ 開発者必読
└── README.md                # このファイル
```

---

## 🛠️ 技術スタック

- **Backend**: Flask + gunicorn
- **Frontend**: Vanilla JS（フレームワークなし）
- **API**: 
  - Claude Anthropic（推奨構成生成）
  - Replicate（FLUX.1-schnell 画像生成） 🆕
- **Hosting**: Render（Standard $25/月）
- **Analytics**: Google Analytics 4
- **SEO**: Google Search Console, Bing Webmaster Tools

---

## 📊 データ

- **ゲーム情報**: 447タイトル（Steam公式データ）
- **パーツデータ**: 10,000+点（価格.com等）
- **互換性ページ**: 14,000ページ
- **ゲームページ**: 415ページ
- **合計**: 417ページ配信中

---

## 🎯 機能

1. **互換性チェック**
   - GPU/CPU/ケース/クーラー/PSUの互換性診断
   - 物理干渉チェック（GPU長、クーラー高さ）

2. **ゲーム推奨スペック**
   - 447ゲームの推奨/最低スペック
   - 予算別の最適PC構成提案

3. **AIアシスタント**
   - Claude APIで自然言語対応
   - 「予算10万円でモンハン」→ 最適構成提案

4. **完成イメージ画像生成** 🆕
   - FLUX.1-schnell（Replicate API）で構成の完成イメージをAI生成
   - 構成確定後、ダッシュボードから「🖼️ 完成イメージを見る」ボタンで生成
   - 約30秒で高品質な16:9画像を生成

5. **Twitter自動投稿Bot** 🆕
   - ゲーム互換性情報を自動ツイート
   - メタスコア優先選択 + 投稿履歴管理
   - GitHub Actionsで定期実行（1日3回）
   - 詳細: [docs/TWITTER_BOT.md](docs/TWITTER_BOT.md)

---

## 🚨 重要な注意事項（再掲）

### 絶対にやってはいけないこと

1. ❌ **バックグラウンド実行禁止**
   ```bash
   # NG例
   python app.py &
   ```

2. ❌ **VBSスクリプト作成禁止**
   ```vbs
   ' これを作るとプロセスがゾンビ化します
   Set oShell = CreateObject("WScript.Shell")
   oShell.Run "python app.py", 0, False
   ```

3. ❌ **一時ファイル削除忘れ禁止**
   ```bash
   # テスト後は必ず削除
   rm tmp_*.py
   ```

**詳細は `claude.md` を必ず読んでください。**

---

## 📞 トラブルシューティング

### サイトがダウンした

1. [Renderログ確認](https://dashboard.render.com/web/srv-d6elsr5m5p6s739ufkj0/logs)
2. エラーメッセージ確認
3. 必要なら `git revert HEAD && git push`

### プロセスが暴走した

```powershell
# 全プロセス停止
Stop-Process -Name bash,python,node -Force
```

---

## 📝 ライセンス

Private（個人プロジェクト）

---

## 👤 作成者

daruma0411-crypto

---

**最終更新**: 2026-02-26
