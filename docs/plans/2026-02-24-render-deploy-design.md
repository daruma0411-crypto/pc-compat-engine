# Render デプロイ設計 — PC互換性チェッカー

作成日: 2026-02-24

## 概要

`pc-compat-engine` の互換性チェッカーUI（`static/index.html` + `/api/diagnose`）を
Render（無料プラン）で外部公開するための設計。

## 要件

- デプロイ範囲: 互換チェッカーのみ（PIM-RAGエンジン全体は対象外）
- 認証: なし（完全公開）
- デプロイ先: Render Web Service（Python環境、無料プラン）
- 必要環境変数: `ANTHROPIC_API_KEY`

## アーキテクチャ

```
ブラウザ
  │  GET /
  ▼
Flask (app.py)
  ├── GET  /            → static/index.html
  ├── POST /api/diagnose → Claude Haiku診断
  └── GET  /api/health  → 200 OK（Renderヘルスチェック）
         │
         ▼
  _lookup_pc_specs()    ← workspace/data/*/products.jsonl
  _compute_prechecks()  ← 数値事前計算（GPU長/ソケット/RAM/TDP）
  _run_pc_diagnosis_with_claude() ← Anthropic API (claude-haiku-4-5-20251001)
```

## 追加ファイル

| ファイル | 役割 |
|---------|------|
| `app.py` | Flask Webサーバー（診断ロジック含む） |
| `requirements_render.txt` | 軽量依存関係（flask, gunicorn, anthropic, python-dotenv） |
| `render.yaml` | Render設定（Build/Start命令、環境変数定義） |

## 軽量化の方針

`requirements.txt` にある chromadb / playwright / tweepy / google-cloud-bigquery 等は
デプロイに不要なため `requirements_render.txt` には含めない。
Renderの無料プランは512MB RAMなので、軽量版で収まる（推定 ~120MB）。

## デプロイ手順

1. [render.com](https://render.com) でGitHubアカウントでサインアップ
2. New → Web Service → `daruma0411-crypto/pc-compat-engine` を選択
3. 以下を確認（render.yamlが自動反映される）:
   - Build Command: `pip install -r requirements_render.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
4. Environment Variables に `ANTHROPIC_API_KEY` を設定
5. Deploy をクリック

## 診断ロジックの出典

`app.py` の以下の関数は `AIサービス/proxy_server.py` から移植:
- `_lookup_pc_specs()` — 余分トークン最少優先マッチング（NH-D15誤マッチ修正済み）
- `_compute_prechecks()` — GPU/CPU/RAM/TDP事前計算
- `_run_pc_diagnosis_with_claude()` — Claude Haiku API呼び出し
