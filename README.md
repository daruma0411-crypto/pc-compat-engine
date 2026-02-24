# 🏗️ PIM-RAG Engine: Plan-and-Execute Architecture for Building Materials

建材カタログPIM化のための、Plan-and-Execute型RAGエンジン。
BigQuery（構造化データ）× PageIndex（階層型文書検索）× Vector DB（曖昧検索）を
LLMの推論で統合的に制御する。

## Architecture

```
ユーザー
  ↓
Planner（LLM + 建材ドメインプロンプト）
  ↓ 検索計画JSON
Executor（並列ツール実行）
  ├→ BigQuery（品番・寸法・スペック）
  ├→ PageIndex（マニュアル・仕様書PDF）
  └→ Vector DB（FAQ・過去問い合わせ）
  ↓ 結果集約
Validator（LLM）
  ├→ 情報十分 → Synthesizer → 最終回答
  └→ 情報不足 → Plannerに差し戻し（再計画）
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # API keys設定
python -m src.main "AX-900を水回りに使えるか？"
```

## Project Structure

```
src/
├── main.py              # エントリーポイント
├── config/
│   ├── settings.py      # 設定管理
│   └── domain_rules.py  # 建材ドメインルール
├── planner/
│   ├── planner.py       # 検索計画生成
│   └── prompts.py       # ドメインプロンプト
├── executor/
│   ├── executor.py      # 並列ツール実行
│   └── registry.py      # ツール登録管理
├── tools/
│   ├── base.py          # ツール基底クラス
│   ├── bigquery_tool.py # BigQuery検索
│   ├── pageindex_tool.py# PageIndex検索
│   └── vector_tool.py   # Vector DB検索
├── validator/
│   └── validator.py     # 結果検証・再計画判定
examples/
│   └── asahi_woodtec.py # 朝日ウッドテックPoC
tests/
    └── test_planner.py  # テスト
```
