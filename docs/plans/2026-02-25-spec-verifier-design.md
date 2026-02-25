# スペック検証・修正スクリプト設計書

作成日: 2026-02-25

## 背景・課題

`source_url: null` のデータはLLM生成値であり、NZXT H510の `max_gpu_length_mm: 381→369` 誤りで実証されたハルシネーションリスクがある。

### 対象件数（合計141件）

| フェーズ | カテゴリ | メーカー | 件数 | 検証フィールド |
|---|---|---|---|---|
| 1 | case | NZXT / CoolerMaster / Fractal Design | 15件 | max_gpu_length_mm, max_cpu_cooler_height_mm, form_factor |
| 2 | psu | Corsair / Seasonic / SilverStone | 15件 | wattage_w |
| 3 | gpu | 13メーカー | 96件 | card_length_mm のみ |

実行優先度: フェーズ1（ケース）→ フェーズ2（PSU）→ フェーズ3（GPU）

RAM 15件は互換チェックへの影響が小さいため対象外。

---

## アーキテクチャ

### ディレクトリ構成

```
scripts/spec_verifier/
├── __init__.py
├── base.py        # 共通: HTTP取得・JSONL更新・diff表示
├── config.py      # 製品ごとのURL・CSSセレクター定義
└── run.py         # エントリーポイント（CLI）
```

### 処理フロー

```
1. JSONL読み込み → source_url: null レコード抽出
2. config.py の PRODUCT_CONFIG にURLが定義されているか確認
3. Playwright（non-headless or headless）でページ取得
4. CSSセレクター or テキストパターンでスペック値抽出
5. 単位変換（"369 mm" → 369）
6. 既存値とのdiff表示
7. products.jsonl に source_url・スペック値を上書き更新
```

### CLIオプション

```bash
python -m scripts.spec_verifier.run --phase 1          # ケース全件
python -m scripts.spec_verifier.run --phase 1 --dry-run  # 確認のみ（更新しない）
python -m scripts.spec_verifier.run --id nzxt_nzxt-h510  # 1件のみ
```

---

## config.py 設計

製品数が限られるため（フェーズ1+2で30件）、URLは手動で設定ファイルに定義する。

```python
PRODUCT_CONFIG = {
    # --- フェーズ1: ケース ---
    "nzxt_nzxt-h510": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h510",
        "spec_fields": {
            "max_gpu_length_mm":       {"pattern": r"GPU.*?(\d+)\s*mm", "section": "仕様"},
            "max_cpu_cooler_height_mm":{"pattern": r"CPUクーラー.*?(\d+)\s*mm", "section": "仕様"},
        }
    },
    "nzxt_nzxt-h200i": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h200i",
        ...
    },
    # CoolerMaster, Fractal Design も同様
    # --- フェーズ2: PSU ---
    "corsair_rm850x-2021": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/...",
        "spec_fields": {
            "wattage_w": {"pattern": r"(\d+)\s*W", "section": "定格出力"},
        }
    },
    ...
}
```

---

## base.py 設計

```python
class SpecVerifier:
    def fetch_page(url, headless=True) -> str          # Playwright HTML取得
    def extract_spec(html, pattern, section) -> str    # 正規表現抽出
    def parse_number(raw_str) -> int                   # "369 mm" → 369
    def load_jsonl(path) -> list[dict]                 # JSONL読み込み
    def save_jsonl(path, records)                      # JSONL書き出し
    def apply_fix(record, field, new_val, source_url)  # レコード更新
    def print_diff(name, field, old, new)              # 変更差分表示
```

---

## フェーズ1: ケース スペック対照表（手動調査値）

スクリプト実行前に公式サイトで確認済みの値をconfigに埋め込む。

### NZXT（nzxt.com）

| 製品 | max_gpu_length_mm | max_cpu_cooler_height_mm |
|---|---|---|
| H510 | 369 ← 修正済 | 165 要確認 |
| H200i | 328 要確認 | 167 要確認 |
| H9 Flow | 385 要確認 | 185 要確認 |
| H3 Flow | 380 要確認 | 165 要確認 |
| H2 Flow | 340 要確認 | 167 要確認 |

### CoolerMaster（coolermaster.com）

| 製品 | max_gpu_length_mm | max_cpu_cooler_height_mm |
|---|---|---|
| MasterCase H500 | 410 要確認 | 167 要確認 |
| HAF 500 | 410 要確認 | 170 要確認 |
| MasterBox TD500 Mesh V2 | 410 要確認 | 165 要確認 |
| MasterBox Q300L | 360 要確認 | 157 要確認 |
| Silencio S600 | 410 要確認 | 160 要確認 |

### Fractal Design（fractal-design.com）

| 製品 | max_gpu_length_mm | max_cpu_cooler_height_mm |
|---|---|---|
| Define 7 | 491 要確認 | 185 要確認 |
| Define 7 XL | 503 要確認 | 185 要確認 |
| North | 355 要確認 | 170 要確認 |
| Torrent | 461 要確認 | 188 要確認 |
| Meshify 2 | 467 要確認 | 185 要確認 |

---

## フェーズ2: PSU スペック対照表

PSUの `wattage_w` は製品名から推定可能（RM850x → 850W）だが、公式ページで確認する。

### Corsair

| 製品 | wattage_w |
|---|---|
| RM850x (2021) | 850 要確認 |
| RM1000x (2021) | 1000 要確認 |
| RM750x (2021) | 750 要確認 |
| HX1200 | 1200 要確認 |
| RM1200x SHIFT | 1200 要確認 |

### Seasonic / SilverStone（同様）

---

## エラーハンドリング

- bot検知（ステータス403 or 極小レスポンス）→ non-headless で再試行
- スペック値が取得できない → `[SKIP]` として記録し手動確認リストへ
- 既存値と一致 → `[OK]` として記録（source_urlのみ更新）

---

## 完了定義

- [ ] フェーズ1: 15件全件 source_url が埋まり、スペック値が公式値と一致
- [ ] フェーズ2: 15件全件 source_url が埋まり、wattage_w が公式値と一致
- [ ] フェーズ3: 96件 card_length_mm が公式値と一致
- [ ] git commit & push 完了
