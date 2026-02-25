# 価格.com 価格バッチ更新設計書

作成: 2026-02-25

## 目的

GPU・CPU・RAM の実勢価格を価格.com から週1取得し、コスパ計算と予算目安を実データで計算する。

## データモデル

既存 JSONL エントリに `price_min`・`price_updated_at` を追加。

```json
{
  "id": "kakaku_K0001661801",
  "name": "AMD Ryzen 7 9800X3D BOX",
  "specs": {...},
  "price_min": 44800,
  "price_updated_at": "2026-02-25"
}
```

新ディレクトリ: `workspace/data/kakaku_gpu/`, `workspace/data/kakaku_ram/`

## スクリプト構成

```
scripts/
  kakaku_scraper_base.py    既存（extract_min_price() を追加）
  kakaku_scraper_gpu.py     新規（GPU list → K0xxx + price + specs）
  kakaku_scraper_ram.py     新規（RAM list → K0xxx + price + specs）
  kakaku_price_updater.py   新規（週1バッチ本体 + git push）
run_price_update.bat        新規（タスクスケジューラ用）
```

## 価格取得方法

kakaku.com スペックページ (`/item/K0xxx/spec/`) の HTML から最安値を抽出。

```python
patterns = [
    r'class="priceNum"[^>]*>\s*([\d,]+)',
    r'最安値[^¥]*¥\s*([\d,]+)',
    r'最安価格[：:]\s*¥?([\d,]+)',
]
```

## app.py 変更

`_lookup_kakaku_price(name, category, all_products)` を追加。
名前キーワードマッチで price_min を返す。

コスパ計算:
```python
actual_total = gpu_price + cpu_price + ram_price
value_score = min(10, round(perf / (actual_total / 150000) * 5))
```

価格が見つからない場合は Claude の total_estimate にフォールバック。

## 自動実行

- `run_price_update.bat` → Windows タスクスケジューラ、毎週月曜 AM6:00
- スクリプト末尾で `git add ... && git commit && git push` を実行

## 変更ファイル

| ファイル | 変更 |
|---|---|
| `scripts/kakaku_scraper_base.py` | `extract_min_price()` 追加 |
| `scripts/kakaku_scraper_gpu.py` | 新規作成 |
| `scripts/kakaku_scraper_ram.py` | 新規作成 |
| `scripts/kakaku_price_updater.py` | 新規作成 |
| `run_price_update.bat` | 新規作成 |
| `app.py` | `_lookup_kakaku_price()` 追加、コスパ計算修正 |
