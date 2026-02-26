# ゲームスペックDB恒久対策 設計書

## 背景

モンハンワイルズのテストで以下の構造的問題が発覚：
1. 推奨スペックが2段階（minimum/recommended）のみで、高設定・ウルトラ設定がない
2. 同一appidで重複エントリが存在（手動追加+スクレイプ）
3. 手動追加分に不正確なデータが含まれる
4. 予算→スペック段階のマッピングが粗い（20万で2択のみ）

## 実装方針：最速ルート（A案：新スキーマ移行）

### Step 1: 移行スクリプト（重複排除 + 新スキーマ）
- games.jsonl の全エントリを読み込み
- 同一appidは scraped_at が最新のものを優先
- `minimum`/`recommended` を `specs` オブジェクト配下に移動
- `source` フィールド追加（steam_official / manual）
- `label` / `target` を各段階に自動付与

### Step 2: MHW 4段階データ手動投入
- カプコン公式の4段階スペックを投入
- minimum / recommended / high / ultra

### Step 3: app.py 参照パス更新
- `data['recommended']` → `data['specs']['recommended']`
- 予算→段階マッピングロジック追加

### Step 4: スクレイパーにupsertロジック追加
- 同一appid存在時は上書き更新（append廃止）

### Step 5: テスト検証

## 新スキーマ

```json
{
  "appid": 2246340,
  "name": "モンスターハンターワイルズ",
  "source": "steam_official",
  "scraped_at": "2026-02-25T04:47:25",
  "short_description": "...",
  "genres": ["アクション", "RPG"],
  "release_date": "2025年2月27日",
  "metacritic_score": null,
  "screenshot": "https://...",
  "specs": {
    "minimum": {
      "label": "最低",
      "target": "FHD/30fps 最低設定",
      "gpu": ["GTX 1660", "RX 5500 XT"],
      "gpu_vram_gb": 6,
      "cpu": ["Core i5-10400", "Ryzen 5 3600"],
      "ram_gb": 16,
      "storage_gb": 75,
      "storage_type": "SSD",
      "notes": "..."
    },
    "recommended": { "label": "推奨", "target": "FHD中設定/60fps", ... },
    "high": { "label": "高", "target": "1440p高設定/60fps", ... },
    "ultra": { "label": "ウルトラ", "target": "4K/60fps", ... }
  }
}
```

## 予算→段階マッピング

| 予算 | 選択段階 |
|------|---------|
| ~10万 | minimum |
| 10~15万 | recommended |
| 15~25万 | high |
| 25万~ | ultra |

段階が存在しない場合は、存在する最上位段階にフォールバック。

## テストケース

- テストC: Tarkov 15万 → 推奨スペック基準、RAM 64GBにならないこと
- MHW-1: 20万 → RTX 4070 Ti SUPER相当以上（RTX 5060はNG）
- MHW-2: 10万 → 推奨（中設定FHD/60fps）段階基準
- MHW-3: 4K最高画質 → ウルトラ段階、RTX 4080 SUPER以上
