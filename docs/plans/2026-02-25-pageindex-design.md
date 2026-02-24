# PageIndex実装 設計ドキュメント

作成日: 2026-02-25

## 目的

MBマニュアルPDF（39件）から M.2/PCIe帯域共有・M.2/SATA無効化ルールを抽出し、
`/api/diagnose` の診断精度を向上させる。

## 背景

MB マニュアルには製品スペック表に載らない重要な制約情報が記載されている:

- M.2スロット使用時の PCIe スロット帯域低下（x16 → x8）
- M.2スロット使用時の SATA ポート無効化
- PCIe スロット間の帯域共有条件

これらを診断フローに組み込むことで、ハルシネーションや見落としを減らす。

## アーキテクチャ概要

```
【オフライン前処理】
manual.txt (39件) → extract_mb_constraints.py → Claude Haiku API
  → constraints JSON → products.jsonl に保存

【診断時】
/api/diagnose → _compute_prechecks() → constraints 参照
  → precheck lines に MB制約情報追加 → Claude が最終判断
```

## コンポーネント1: オフライン抽出スクリプト

**ファイル:** `scripts/extract_mb_constraints.py`

### 処理フロー

1. `asrock_mb / gigabyte_mb / asus_mb / msi_mb` の `products.jsonl` を読み込み
2. `manual_path` があるレコード（最大39件）を対象
3. `manual.txt` の先頭 5,000文字を Claude Haiku API に送付
4. 抽出プロンプトで M.2/PCIe・M.2/SATA 制約を構造化 JSON として取得
5. `products.jsonl` の `constraints` フィールドに保存（上書き）
6. `git commit` で変更を保存

### 抽出プロンプト（要点）

```
このマザーボードマニュアルから以下の制約情報をJSONで返してください:
1. M.2スロット使用時にPCIeスロットの帯域が低下するもの
2. M.2スロット使用時にSATAポートが無効化されるもの

出力形式:
{
  "m2_pcie_sharing": [{"m2_slot": "...", "affects": "...", "effect": "..."}],
  "m2_sata_sharing": [{"m2_slot": "...", "affects": "...", "effect": "..."}]
}
該当情報がない場合は空リスト []
```

### コスト見積もり

- 対象: 39件 × 5,000文字 ≈ 650K トークン入力
- Claude Haiku 料金: 約 $0.04（$0.00025/1K input tokens）
- 実行時間: 約 5〜10 分（rate limit 対策 sleep 込み）

## コンポーネント2: データ構造

`products.jsonl` の各 MB レコードに `constraints` フィールドを追加:

```json
{
  "constraints": {
    "m2_pcie_sharing": [
      {
        "m2_slot": "M2D_CPU",
        "affects": "PCIEX16",
        "effect": "x8モードに制限"
      }
    ],
    "m2_sata_sharing": [
      {
        "m2_slot": "M2M_SB",
        "affects": "SATA3 0/1",
        "effect": "無効化"
      }
    ]
  }
}
```

制約がないMBは `"constraints": {"m2_pcie_sharing": [], "m2_sata_sharing": []}` を保存。

## コンポーネント3: app.py 診断統合

### `_compute_prechecks()` への追加

`app.py` の `_compute_prechecks()` 末尾（return の直前）に追加:

```python
# MB マニュアル制約情報（M.2/PCIe共有 / M.2/SATA無効化）
for mb_part, mb_data in mb_entries:
    constraints = mb_data.get('constraints', {})
    for rule in constraints.get('m2_pcie_sharing', []):
        lines.append(
            f"- MB制約情報: {mb_part}: {rule['m2_slot']}使用時は"
            f"{rule['affects']}が{rule['effect']} = WARNING（M.2使用時は要確認）"
        )
    for rule in constraints.get('m2_sata_sharing', []):
        lines.append(
            f"- MB制約情報: {mb_part}: {rule['m2_slot']}使用時は"
            f"SATA {rule['affects']}が{rule['effect']} = WARNING（M.2使用時はSATA本数減少）"
        )
```

### システムプロンプトへの追加

`_PC_DIAGNOSIS_SYSTEM_PROMPT` に1行追加:

```
- MB制約情報はM.2 SSDを使用しない構成ならWARRINGではなくOKまたは参考情報として扱うこと
```

## 対象ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `scripts/extract_mb_constraints.py` | 新規作成 |
| `workspace/data/asrock_mb/products.jsonl` | constraints フィールド追加 |
| `workspace/data/gigabyte_mb/products.jsonl` | constraints フィールド追加 |
| `workspace/data/asus_mb/products.jsonl` | constraints フィールド追加 |
| `workspace/data/msi_mb/products.jsonl` | constraints フィールド追加 |
| `app.py` | _compute_prechecks() + system prompt 修正 |

## 成功基準

- 39件中 30件以上（77%以上）で `constraints` が抽出できる
- RTX 4090 + ASUS ROG Z890-F + M.2 SSD の診断で M.2/PCIe 共有 WARNING が出る
- M.2 SSD なしの構成では余分な WARNING が増えない
