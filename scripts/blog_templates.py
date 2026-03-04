#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事テンプレート（10種類）
変数: {game}, {gpu_model}, {budget}
"""

BLOG_TEMPLATES = [
    {
        "id": "troubleshooting",
        "title": "「{game}」が動かない時の対処法7選",
        "keywords": ["{game} 動かない", "{game} 起動しない", "{game} トラブル"],
        "prompt": (
            "「{game}」が動かない時の対処法を7つ、1,500文字程度で解説してください。\n"
            "1. スペック不足の確認\n2. グラフィックドライバの更新\n3. DirectX/Visual C++の再インストール\n"
            "4. ウイルス対策ソフトの例外設定\n5. 管理者権限で実行\n6. ファイルの整合性チェック\n7. セーブデータの移動\n"
            "各対処法は具体的な手順を含め、初心者向けに。最後に「それでも解決しない場合はAI診断チャットで相談」と誘導。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグ（h2, p, ol, li）で構造化してください。"
        ),
    },
    {
        "id": "gpu_list",
        "title": "RTX {gpu_model}で遊べる最新ゲーム50選",
        "keywords": ["RTX {gpu_model} ゲーム", "RTX {gpu_model} おすすめ"],
        "prompt": (
            "RTX {gpu_model}で快適に遊べるゲーム50本を1,800文字程度で紹介してください。\n"
            "1080p高設定で60fps以上出るゲームを中心に、ジャンル別に分類。\n"
            "各ゲームに期待FPS（目安）を記載。最新ゲームと定番をバランス良く。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグ（h2, h3, p, ul, li）で構造化してください。"
        ),
    },
    {
        "id": "budget_build",
        "title": "予算{budget}万円で組む最強ゲーミングPC構成【2026年版】",
        "keywords": ["予算{budget}万円 ゲーミングPC", "{budget}万円 PC構成"],
        "prompt": (
            "予算{budget}万円で組めるゲーミングPC構成を1,500文字程度で提案してください。\n"
            "2026年3月時点の最新パーツでコスパ重視。GPU/CPU/RAM/SSD/マザボ/電源の選び方。\n"
            "初心者向けの説明。最後にBTOショップでの購入も選択肢として紹介。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "benchmark",
        "title": "「{game}」の推奨スペックとGPU別FPS目安",
        "keywords": ["{game} 推奨スペック", "{game} FPS", "{game} 動作環境"],
        "prompt": (
            "「{game}」の推奨スペックとGPU別FPS目安を1,200文字程度で解説してください。\n"
            "公式推奨スペック、GPU別FPS表（RTX 3060/4060/4070/5070の1080p/WQHD/4K目安）。\n"
            "※FPS値は一般的な目安であり実測値ではない旨を明記。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "laptop",
        "title": "ノートPCで「{game}」は快適に遊べる？おすすめ3選",
        "keywords": ["{game} ノートPC", "{game} ゲーミングノート"],
        "prompt": (
            "ノートPCで「{game}」をプレイする際のポイントを1,400文字程度で解説。\n"
            "推奨ゲーミングノートスペック、おすすめ製品3つ（RTX 4060/4070搭載機）、デスクトップとの性能差。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "high_res",
        "title": "「{game}」をWQHD/4Kで遊ぶために必要なGPU",
        "keywords": ["{game} WQHD", "{game} 4K GPU"],
        "prompt": (
            "「{game}」を高解像度（WQHD/4K）で遊ぶためのGPU選びを1,300文字程度で解説。\n"
            "解像度ごとの推奨GPU、フレームレート目標別の提案、コストパフォーマンス分析。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "performance",
        "title": "「{game}」が重い・カクつく原因と解決策5選",
        "keywords": ["{game} 重い", "{game} カクつく", "{game} FPS出ない"],
        "prompt": (
            "「{game}」が重い・カクつく時の解決策を5つ、1,400文字程度で解説。\n"
            "原因の診断方法、グラフィック設定の最適化手順、ドライバ更新、RAM/SSD不足の確認。\n"
            "初心者向け。最後にAI診断チャットへ誘導。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "used_parts",
        "title": "中古パーツで組む「{game}」向け格安ゲーミングPC",
        "keywords": ["{game} 中古パーツ", "{game} 格安PC"],
        "prompt": (
            "中古パーツで「{game}」を遊べるPCを組む方法を1,500文字程度で解説。\n"
            "狙い目のGPU/CPU、避けるべきパーツ、予算5〜8万円の構成例。\n"
            "リスク・注意点を明記。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "mod",
        "title": "「{game}」のMODを入れるために必要なスペック",
        "keywords": ["{game} MOD スペック", "{game} MOD 重い"],
        "prompt": (
            "「{game}」にMODを導入する際の推奨スペックを1,200文字程度で解説。\n"
            "MODの種類別（軽量/グラフィック/大型）にスペック提案。VRAM容量の重要性。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
    {
        "id": "ranking",
        "title": "2026年版 最新ゲーム推奨スペックランキングTOP20",
        "keywords": ["ゲーム 推奨スペック ランキング", "2026年 ゲーム 重い"],
        "prompt": (
            "2026年最新ゲームの推奨スペックをランキング形式（重い順TOP20）で紹介。2,000文字程度。\n"
            "各ゲームの推奨GPU/CPU、ジャンル別推奨スペック。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。"
        ),
    },
]
