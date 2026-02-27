# Claude Code / Claude Desktop への重要な注意事項

**最終更新**: 2026-02-26 17:30  
**プロジェクト**: PC互換性チェッカー（pc-compat-engine）  
**本番環境**: https://pc-compat-engine-production.up.railway.app
**旧Render環境（停止中）**: https://pc-compat-engine-1.onrender.com/

---

## 🚨 絶対にやってはいけないこと

### 1. **バックグラウンド実行（`&`）禁止**

```bash
# ❌ NG例
python app.py &
gunicorn app:app &
node server.js &
```

**理由**: プロセスがゾンビ化し、コマンドプロンプトが定期的に開く「クルクル問題」が発生する。

**✅ 正しい方法**:
- フォアグラウンドで実行
- テスト完了後は `Ctrl+C` で停止
- または `ps aux | grep python` で確認後、手動停止

---

### 2. **VBSスクリプト作成禁止**

```vbs
' ❌ 絶対に作成しない
Set oShell = CreateObject("WScript.Shell")
oShell.Run "python app.py", 0, False
```

**理由**: ウィンドウなしで実行され、停止困難なゾンビプロセスになる。

**過去に削除したファイル**:
- `run_server.vbs`
- `run_kakaku.vbs`
- `tmp_server.vbs`
- その他7個のVBSスクリプト

---

### 3. **一時ファイル削除忘れ禁止**

```bash
# ❌ NG: 一時ファイルを残す
tmp_test.py
tmp_monitor.py
tmp_price_update.py
```

**✅ 正しい方法**:
- テストスクリプトは実行後すぐ削除
- または `test_*.py` のように命名（`.gitignore`対象）
- 一時ファイルはコミット前に削除

---

### 4. **Render環境でローカルサーバー起動禁止**

```bash
# ❌ NG: Render以外でapp.pyを起動
python app.py  # ローカルで実行
```

**理由**: ポート競合、意図しないトラフィック、デバッグ困難。

**✅ 正しい方法**:
- ローカルテストは **明示的に** `python app.py` 実行
- テスト完了後は **必ず停止**
- 本番はRenderのみで動作

---

## 📋 プロジェクト現状（2026-02-26）

### デプロイ状況
```
✅ 本番環境: Live (Render Standard $25/月)
✅ 最新デプロイ: 2f0b122 (2026-02-26 17:17)
✅ コミット: Revert "feat: サマリーカード価格表示..."
✅ 全417ページ配信中
```

### 構成
- **フレームワーク**: Flask (gunicorn)
- **ホスティング**: Render (Standard プラン)
- **データベース**: なし（JSONLファイル）
- **API**: Claude Anthropic (推奨構成生成)
- **Analytics**: Google Analytics 4
- **SEO**: Google Search Console, Bing Webmaster Tools

### ファイル構成
```
pc-compat-engine/
├── app.py                    # Flaskアプリ（メイン）
├── static/
│   ├── index.html           # トップページ
│   ├── style.css            # スタイル
│   ├── app.js               # フロントエンドJS
│   └── game/                # 415ゲームページ
├── workspace/data/          # パーツデータ（JSONL）
├── marketing-materials.md   # マーケティング素材
└── claude.md                # このファイル
```

---

## ⚠️ 過去に発生した問題

### 問題1: クルクル問題（コマンドプロンプトが定期的に開く）

**原因**:
1. VBSスクリプト（`run_server.vbs`）が `python app.py` をバックグラウンド起動
2. Bashゾンビプロセス 9個
3. Pythonゾンビプロセス 10個
4. Nodeゾンビプロセス 21個
5. 一時ファイル 25個（`tmp_*.py`）

**解決方法**:
- 全プロセス強制終了
- 全VBS/BAT/一時ファイル削除
- `.claude/` ディレクトリ削除

**再発防止**:
- バックグラウンド実行禁止
- VBSスクリプト作成禁止
- 一時ファイルは即座に削除

---

### 問題2: Render無限再起動ループ

**原因**:
- コミット `629b557` でコード変更
- gunicornが起動後すぐクラッシュ
- Renderがポート検出失敗 → 再起動 → 無限ループ

**解決方法**:
```bash
git revert 629b557
git push origin main
```

**教訓**:
- 本番環境への影響を考慮してコミット
- ローカルテスト徹底
- デプロイ後は必ずログ確認

---

## ✅ 開発時の推奨フロー

### 1. **ローカル開発**
```bash
# 1. 変更を加える
vim app.py

# 2. ローカルテスト（フォアグラウンド）
python app.py
# → http://127.0.0.1:5000 でテスト

# 3. 停止（Ctrl+C）

# 4. プロセス確認（念のため）
ps aux | grep python
# → ゾンビプロセスがないか確認

# 5. 一時ファイル削除
rm tmp_*.py

# 6. コミット
git add -A
git commit -m "feat: 〇〇機能追加"
git push origin main
```

### 2. **Renderデプロイ確認**
```bash
# 1. Renderダッシュボードで確認
# https://dashboard.render.com/

# 2. Eventsタブで "Deploy live" を確認

# 3. Logsタブでエラーがないか確認

# 4. ブラウザでアクセステスト
curl https://pc-compat-engine.onrender.com/
```

---

## 🎯 明日（2026-02-28）の重要イベント

### Monster Hunter Wilds 発売日マーケティング

**投稿タイミング**:
```
07:00  X/Twitter投稿
08:00  Reddit r/jisakupc投稿
08:30  5ch 自作PC板投稿
12:00  Yahoo知恵袋巡回開始
```

**目標KPI**:
- 初日PV: 500-1,000
- SNSエンゲージメント: 50件以上
- 互換性チェック実行: 100回以上

**投稿文**: `marketing-materials.md` 参照

---

## 📞 緊急時の対応

### サイトがダウンした場合

1. **Renderログ確認**
   ```
   https://dashboard.render.com/web/srv-d6elsr5m5p6s739ufkj0/logs
   ```

2. **エラーメッセージ確認**
   - 赤い文字のエラー
   - "Port scan timeout"
   - "Shutting down"

3. **ロールバック**
   ```bash
   git revert HEAD
   git push origin main
   ```

---

### プロセスが暴走した場合

```powershell
# 全Bash停止
Stop-Process -Name bash -Force

# 全Python停止
Stop-Process -Name python -Force

# 全Node停止（5分以上前のもの）
Get-Process node | Where-Object {$_.StartTime -lt (Get-Date).AddMinutes(-5)} | Stop-Process -Force
```

---

## 📝 その他の重要情報

### API Keys（環境変数）
```bash
ANTHROPIC_API_KEY=sk-ant-***  # Claude API
```

### Render環境変数
```bash
PORT=10000  # Renderが自動設定
WEB_CONCURRENCY=1  # Workerプロセス数
```

### Git管理
```bash
# 現在のブランチ: main
# リモート: https://github.com/daruma0411-crypto/pc-compat-engine.git
```

---

## 🙏 最後に

**このファイルを読んだら、以下を必ず守ってください**:

1. ✅ バックグラウンド実行禁止
2. ✅ VBSスクリプト作成禁止
3. ✅ 一時ファイルは即座に削除
4. ✅ ローカルテスト後は必ずプロセス停止確認
5. ✅ デプロイ後はログ確認

**問題が起きたら、すぐにこのファイルを見直してください。**

---

**作成者**: OpenClaw (2026-02-26)  
**連絡先**: Telegramセッション経由
