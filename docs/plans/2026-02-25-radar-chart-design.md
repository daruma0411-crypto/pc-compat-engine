# レーダーチャート設計書

作成: 2026-02-25

## 概要

ゲームモードの推奨構成（build-card）と横並びに、5軸レーダーチャートを表示する。
CPU・GPU・VRAM・RAM・コスパのバランスをビジュアルで伝える。

## レイアウト

```
[📋 推奨構成カード ~320px] [📊 レーダーチャート ~300px]
```

- ラッパー `.build-row` を `display: flex; gap: 12px; align-items: flex-start`
- モバイル (480px以下) は `flex-direction: column`
- build-card は `flex: 1; min-width: 280px`
- radar-wrap は `flex: 0 0 280px`

## チャート仕様

| 項目 | 値 |
|---|---|
| ライブラリ | Chart.js 4.x（CDN: jsdelivr） |
| チャート種別 | `type: 'radar'` |
| 軸 | CPU・GPU・VRAM・RAM・コスパ（5軸） |
| スコア範囲 | 1〜10 |
| 塗り色 | `rgba(158,207,255,0.2)` |
| 線色 | `#9ECFFF`（`--c-primary`） |
| ラベル色 | `#BBC2CA`（`--c-muted`） |
| グリッド色 | `rgba(96,105,117,0.4)` |
| canvas サイズ | 260×260px |

## スコア計算ロジック（app.py）

関数名: `_compute_radar_scores(build: list, specs: dict) -> dict`

### CPU スコア

モデル名のキーワードマッチで Tier 判定:

| キーワード | スコア |
|---|---|
| i9 / Ryzen 9 / Core Ultra 9 / Threadripper | 10 |
| i7 / Ryzen 7 / Core Ultra 7 | 8 |
| i5 / Ryzen 5 / Core Ultra 5 | 6 |
| i3 / Ryzen 3 | 4 |
| Celeron / Pentium / Athlon | 2 |
| 不明 | 5 |

### GPU スコア

`tdp_w` ベースで正規化:

| TDP (W) | スコア |
|---|---|
| 350+ | 10 |
| 280〜349 | 9 |
| 200〜279 | 7 |
| 150〜199 | 6 |
| 75〜149 | 4 |
| ～74 | 3 |
| 不明 | 5 |

### VRAM スコア

`vram_gb` の直接マッピング:

| VRAM (GB) | スコア |
|---|---|
| 24 | 10 |
| 16 | 9 |
| 12 | 8 |
| 8 | 6 |
| 6 | 5 |
| 4 | 3 |
| 不明 | 5 |

### RAM スコア

推奨構成の build アイテム内の `name` から容量を抽出、または specs から:

| 容量 (GB) | スコア |
|---|---|
| 64+ | 10 |
| 32 | 8 |
| 16 | 6 |
| 8 | 4 |
| 不明 | 5 |

### コスパ スコア

`total_estimate` の金額（万円）と GPU+CPU スコアの合計から算出:

```python
perf = (gpu_score + cpu_score) / 2  # 平均性能
budget = total_yen / 10000           # 万円単位

value = min(10, round(perf / (budget / 15) * 5))
# 15万円で平均スコアなら value=5、安ければ上がる
```

金額が取得できない場合は 5 をデフォルト。

## データフロー

```
POST /api/recommend
  → Claude が構成生成 (recommended_build, total_estimate)
  → _lookup_pc_specs(parts) でスペック取得
  → _compute_radar_scores(build, specs) でスコア計算
  → レスポンスに radar_scores: {cpu, gpu, vram, ram, value} 追加

フロント
  → appendRecommendationMessage(data) で受信
  → build-row ラッパーに build-card + radar-wrap を横並び
  → renderRadarChart(canvasId, data.radar_scores) で Chart.js 描画
```

## 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `app.py` | `_compute_radar_scores()` 追加、`/api/recommend` レスポンスに `radar_scores` 追加 |
| `static/index.html` | Chart.js CDN追加、CSS（.build-row）追加、`renderRadarChart()` 追加、`appendRecommendationMessage()` 修正 |

## エラーハンドリング

- スペック取得失敗の軸は 5（中央値）でフォールバック
- `radar_scores` がレスポンスに含まれない場合はチャートを非表示（後方互換）
- Chart.js CDN ロード失敗時はチャートエリアを非表示
