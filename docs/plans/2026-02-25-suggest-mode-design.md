# 互換チェックモード 提案型フロー設計書

**日付**: 2026-02-25
**対象**: `app.py` / `static/index.html`

---

## 課題

現在の `/api/chat` は「全型番が揃うまで何度も聞き返す」フローのため：
- ユーザーが「提案ください」と言っても `parts < 2` 判定で質問に戻ってしまう
- DBはサーバー側にあるのに、ユーザーに全部品を入力させている非効率
- 購入リンクが診断完了まで表示されない

---

## 設計方針

**型番が揃っていたら即診断。不足していたら1回だけ聞いて全構成提案+購入リンク出力。**

---

## 変更概要

### 1. `_EXTRACT_SYSTEM_PROMPT` 修正

出力フォーマットに `intent` フィールドを追加：

```json
{
  "parts": ["型番1", "型番2"],
  "missing": ["cpu", "psu"],
  "intent": "diagnose" | "suggest",
  "reply": "ユーザーへの返答"
}
```

**intent 判定ルール：**
- `diagnose`: parts 2件以上 かつ「提案/おすすめ/選んで/決めて」等のキーワードなし
- `suggest`: 上記以外（型番不足 or 提案系キーワードあり）

### 2. `_suggest_build_with_claude()` 新規関数

**入力**: 確定済みパーツ（GPUやケース等）+ ユーザーメッセージ（予算・好み含む）

**処理**:
1. DBから互換性を考慮したパーツ候補を取得
   - GPU確定 → 対応ケース候補 / ケース確定 → 収まるGPU候補
   - CPU確定 → 対応ソケットのMB候補
2. Claudeに全構成（CPU/MB/RAM/PSU/クーラー）を提案させる
3. 提案後に互換チェック（GPU長×ケース、PSU容量、MB-CPUソケット等）を実施

**出力**: `type: "recommendation"` 形式（フロントがそのまま流用可能）

```json
{
  "type": "recommendation",
  "game": {"name": "◯◯に合う推奨構成"},
  "recommended_build": [...],
  "total_estimate": "¥XX万〜¥XX万",
  "reply": "構成提案コメント",
  "radar_scores": {...},
  "compat_check": {...}
}
```

### 3. `/api/chat` 分岐ロジック変更

```
extracted = _extract_parts_with_claude(message, history)
intent = extracted.get('intent', 'diagnose')

if intent == 'suggest':
    ai_turns = historyのassistantターン数
    if ai_turns >= 1:
        → _suggest_build_with_claude(parts, message, history) を返す
    else:
        → clarify（予算・用途を1回だけ質問）
else:  # diagnose
    if len(parts) < 2:
        → clarify
    else:
        → 即診断（現状と同じ）
```

### 4. フロントエンド対応

- `data.type === 'suggestion'` を追加して `appendRecommendationMessage(data)` を呼ぶ
- レスポンスの `game.name` に「◯◯に合う推奨構成」を入れて流用

---

## 期待するフロー例

### パターン1: 型番揃い → 即診断

```
User: RTX 4090 + NZXT H510 + i9-13900K + ROG STRIX Z790-F + 850W
Bot:  [即診断結果カード + 購入リンク]
```

### パターン2: 部分情報 → 1回質問 → 全構成提案

```
User: RTX 4070をLancool 216に入れたい
Bot:  GPU長互換OK。残りのパーツを提案するため、予算とお好みを教えてください。
User: 予算20万円、静音重視
Bot:  [全構成提案カード（CPU/MB/RAM/PSU/クーラー）+ 購入リンク]
```

### パターン3: 提案要求 → 即提案

```
User: RTX 4070に合うケースと電源を選んでください
Bot:  [提案カード（ケース/PSU）+ 購入リンク]
```

---

## 変更ファイル

- `app.py`: `_EXTRACT_SYSTEM_PROMPT` / `_suggest_build_with_claude()` / `/api/chat`
- `static/index.html`: `type === 'suggestion'` レスポンス処理追加
