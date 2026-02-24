#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB制約抽出スクリプト (PageIndex Phase 1)

各マザーボードのマニュアルテキスト (manual.txt) を Claude Haiku API に渡し、
M.2/PCIe帯域共有・M.2/SATA無効化ルールを構造化 JSON として抽出する。
結果は products.jsonl の `constraints` フィールドに保存する。

使い方:
  python scripts/extract_mb_constraints.py           # 全 4 メーカー処理
  python scripts/extract_mb_constraints.py --dry-run # 実際には保存しない
  python scripts/extract_mb_constraints.py --maker gigabyte_mb  # 特定メーカーのみ
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_ROOT = pathlib.Path(__file__).parent.parent
_WORKSPACE = _ROOT / "workspace" / "data"

_MAKERS = ["asrock_mb", "gigabyte_mb", "asus_mb", "msi_mb"]

# 使用する Claude モデル
_MODEL = "claude-haiku-4-5-20251001"

# 抽出プロンプト
_EXTRACT_SYSTEM = """\
あなたはマザーボードマニュアルの技術情報を構造化するエキスパートです。
JSON のみで回答し、説明文・マークダウン・コードブロックは不要です。
"""

_EXTRACT_USER_TMPL = """\
以下はマザーボードマニュアルのテキストです。
このテキストから以下の制約情報を抽出して JSON で返してください。

## 抽出対象

1. **m2_pcie_sharing**: M.2スロットを使用すると PCIe スロットの帯域が低下するもの
   - 例: 「M2D_CPUにデバイスを取り付けると PCIEX16 が x8 モードになる」
2. **m2_sata_sharing**: M.2スロットを使用すると SATA ポートが無効になるもの
   - 例: 「M2M_SBを使用すると SATA3 0/1 が無効になる」

## 出力形式（JSONのみ）

{{
  "m2_pcie_sharing": [
    {{"m2_slot": "スロット名", "affects": "PCIeスロット名", "effect": "x8モードに制限"}}
  ],
  "m2_sata_sharing": [
    {{"m2_slot": "スロット名", "affects": "SATAポート番号/名称", "effect": "無効化"}}
  ]
}}

該当情報がない場合は空リスト [] を返してください。

## マニュアルテキスト（先頭 {chars} 文字）

{text}
"""

_MAX_CHARS = 8000
_WINDOW = 300  # キーワード周辺の前後文字数


# M.2/PCIe/SATA 共有に関連するキーワード
_KEYWORDS = [
    "共有", "帯域", "バンド幅", "無効", "disable",
    "x8モード", "x8 モード", "x8mode",
    "bandwidth", "share",
    "M.2", "PCIe", "SATA",
]


def _extract_relevant_sections(text: str) -> str:
    """マニュアルから M.2/PCIe/SATA 関連の重要セクションを抽出する。"""
    positions = []
    for kw in _KEYWORDS:
        pos = 0
        while True:
            idx = text.find(kw, pos)
            if idx < 0:
                break
            positions.append(idx)
            pos = idx + 1

    if not positions:
        # キーワードなし → 先頭を返す
        return text[:_MAX_CHARS]

    # 各位置の前後 _WINDOW 文字を収集（重複除去）
    segments = []
    positions.sort()
    merged_start = max(0, positions[0] - _WINDOW)
    merged_end = min(len(text), positions[0] + _WINDOW)

    for pos in positions[1:]:
        start = max(0, pos - _WINDOW)
        end = min(len(text), pos + _WINDOW)
        if start <= merged_end:
            merged_end = max(merged_end, end)
        else:
            segments.append(text[merged_start:merged_end])
            merged_start = start
            merged_end = end
    segments.append(text[merged_start:merged_end])

    result = "\n...\n".join(segments)
    return result[:_MAX_CHARS]


def _call_claude(api_key: str, text: str) -> dict:
    """Claude Haiku API を呼び出して制約 JSON を返す。"""
    user_msg = _EXTRACT_USER_TMPL.format(
        chars=len(text),
        text=text,
    )
    body = json.dumps({
        "model": _MODEL,
        "max_tokens": 512,
        "system": _EXTRACT_SYSTEM,
        "messages": [{"role": "user", "content": user_msg}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    content = data.get("content", [{}])[0].get("text", "{}")

    # コードブロック除去
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)

    try:
        result = json.loads(content.strip())
        # 必須キーの補完
        result.setdefault("m2_pcie_sharing", [])
        result.setdefault("m2_sata_sharing", [])
        return result
    except json.JSONDecodeError:
        print(f"  [WARN] JSON パース失敗: {content[:200]}", file=sys.stderr)
        return {"m2_pcie_sharing": [], "m2_sata_sharing": []}


def process_maker(maker: str, api_key: str, dry_run: bool, force: bool = False) -> tuple[int, int]:
    """1メーカーの products.jsonl を処理して constraints を更新。
    Returns: (updated, skipped)
    """
    jsonl_path = _WORKSPACE / maker / "products.jsonl"
    if not jsonl_path.exists():
        print(f"[{maker}] SKIP: products.jsonl が見つかりません", file=sys.stderr)
        return 0, 0

    products = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))

    updated = 0
    skipped = 0

    print(f"\n[{maker}] {len(products)} 件処理開始", file=sys.stderr)

    for i, prod in enumerate(products, 1):
        name = prod.get("name", prod.get("id", "unknown"))[:60]
        manual_path_rel = prod.get("manual_path", "")

        if not manual_path_rel:
            print(f"  [{i}] SKIP (manual_path なし): {name}", file=sys.stderr)
            skipped += 1
            continue

        # 既に constraints があればスキップ（--force で上書き）
        if "constraints" in prod and not force:
            print(f"  [{i}] SKIP (既存 constraints あり): {name}", file=sys.stderr)
            skipped += 1
            continue

        # manual.txt のパス解決
        manual_path = _ROOT / manual_path_rel.replace("\\", "/")
        if not manual_path.exists():
            print(f"  [{i}] SKIP (manual.txt 不存在): {name}", file=sys.stderr)
            skipped += 1
            continue

        # テキスト読み込み
        text = manual_path.read_text(encoding="utf-8", errors="replace")
        text_excerpt = _extract_relevant_sections(text)

        print(f"  [{i}] 処理中: {name} ({len(text)} 文字 → 抽出{len(text_excerpt)} 文字)", file=sys.stderr)

        if dry_run:
            print(f"       [DRY-RUN] Claude API 呼び出しをスキップ", file=sys.stderr)
            prod["constraints"] = {"m2_pcie_sharing": [], "m2_sata_sharing": []}
            updated += 1
            continue

        try:
            constraints = _call_claude(api_key, text_excerpt)
            prod["constraints"] = constraints

            pcie_count = len(constraints.get("m2_pcie_sharing", []))
            sata_count = len(constraints.get("m2_sata_sharing", []))
            print(
                f"       OK: PCIe共有={pcie_count}件, SATA共有={sata_count}件",
                file=sys.stderr,
            )
            updated += 1

        except Exception as e:
            print(f"       ERROR: {e}", file=sys.stderr)
            skipped += 1

        # レートリミット対策
        time.sleep(1.0)

    # products.jsonl を上書き保存
    if not dry_run:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in products:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{maker}] 保存完了: {jsonl_path}", file=sys.stderr)
    else:
        print(f"[{maker}] DRY-RUN: 保存スキップ", file=sys.stderr)

    print(
        f"[{maker}] 完了: 更新={updated} スキップ={skipped}",
        file=sys.stderr,
    )
    return updated, skipped


def main():
    parser = argparse.ArgumentParser(description="MB制約抽出スクリプト (PageIndex Phase 1)")
    parser.add_argument("--maker", choices=_MAKERS, help="特定メーカーのみ処理")
    parser.add_argument("--dry-run", action="store_true", help="API呼び出しをスキップして動作確認")
    parser.add_argument("--force", action="store_true", help="既存 constraints を上書き")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY が設定されていません", file=sys.stderr)
        sys.exit(1)

    makers = [args.maker] if args.maker else _MAKERS

    total_updated = 0
    total_skipped = 0

    for maker in makers:
        u, s = process_maker(maker, api_key, dry_run=args.dry_run, force=args.force)
        total_updated += u
        total_skipped += s

    print(
        f"\n=== 全体完了: 更新={total_updated} スキップ={total_skipped} ===",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
