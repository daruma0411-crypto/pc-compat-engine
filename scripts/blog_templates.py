#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブログ記事テンプレート（11種類）
変数: {game}（日本語名）, {game_en}（英語名）, {gpu_model}, {budget}, {today}, {today_short}, {month}, {week},
      {season_context}, {data_context}, {source_note}
"""

BLOG_TEMPLATES = [
    {
        "id": "troubleshooting",
        "title": "「{game}」が動かない時の対処法7選",
        "keywords": ["{game} 動かない", "{game} 起動しない", "{game} トラブル"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のデータです（{source_note}）:\n{data_context}\n\n"
            "「{game}」が動かない時の対処法を7つ、1,500文字程度で解説してください。\n"
            "1. スペック不足の確認\n2. グラフィックドライバの更新\n3. DirectX/Visual C++の再インストール\n"
            "4. ウイルス対策ソフトの例外設定\n5. 管理者権限で実行\n6. ファイルの整合性チェック\n7. セーブデータの移動\n"
            "各対処法は具体的な手順を含め、初心者向けに。上記の実データを参考にスペック情報は正確に記載。\n"
            "最後に「それでも解決しない場合はAI診断チャットで相談」と誘導。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグ（h2, p, ol, li）で構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "gpu_list",
        "title": "RTX {gpu_model}で遊べる最新ゲーム50選【{month}月版】",
        "keywords": ["RTX {gpu_model} ゲーム", "RTX {gpu_model} おすすめ"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際の市場データです（{source_note}）:\n{data_context}\n\n"
            "RTX {gpu_model}で快適に遊べるゲーム50本を1,800文字程度で紹介してください。\n"
            "1080p高設定で60fps以上出るゲームを中心に、ジャンル別に分類。\n"
            "各ゲームに期待FPS（目安）を記載。直近発売の新作を優先的に含めてください。\n"
            "上記の実データ（価格・性能スコア）を正確に反映してください。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグ（h2, h3, p, ul, li）で構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "budget_build",
        "title": "予算{budget}万円で組む最強ゲーミングPC構成【{today_short}版】",
        "keywords": ["予算{budget}万円 ゲーミングPC", "{budget}万円 PC構成"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際の市場価格です（{source_note}）:\n{data_context}\n\n"
            "予算{budget}万円で組めるゲーミングPC構成を1,500文字程度で提案してください。\n"
            "上記の実際の市場価格データを使って、具体的なパーツ名と価格を記載してください。\n"
            "合計金額が予算内に収まるよう計算すること。\n"
            "初心者向けの説明。最後にBTOショップでの購入も選択肢として紹介。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "benchmark",
        "title": "「{game}」の推奨スペックとGPU別FPS目安【{today_short}更新】",
        "keywords": ["{game} 推奨スペック", "{game} FPS", "{game} 動作環境"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のデータです（{source_note}）:\n{data_context}\n\n"
            "「{game}」の推奨スペックとGPU別FPS目安を1,200文字程度で解説してください。\n"
            "上記のSteam公式スペックと性能スコアを正確に引用してください。\n"
            "GPU別FPS表（主要GPU 6〜8機種の1080p/WQHD/4K目安）を含めること。\n"
            "※FPS値は性能スコアからの推定目安であり実測値ではない旨を明記。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "laptop",
        "title": "ノートPCで「{game}」は快適に遊べる？おすすめ3選",
        "keywords": ["{game} ノートPC", "{game} ゲーミングノート"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のデータです（{source_note}）:\n{data_context}\n\n"
            "ノートPCで「{game}」をプレイする際のポイントを1,400文字程度で解説。\n"
            "上記の公式スペックを正確に引用しつつ、推奨ゲーミングノートスペックを提案。\n"
            "おすすめ製品3つ（RTX 4060/4070搭載機）、デスクトップとの性能差。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "high_res",
        "title": "「{game}」をWQHD/4Kで遊ぶために必要なGPU",
        "keywords": ["{game} WQHD", "{game} 4K GPU"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際の市場データです（{source_note}）:\n{data_context}\n\n"
            "「{game}」を高解像度（WQHD/4K）で遊ぶためのGPU選びを1,300文字程度で解説。\n"
            "上記の実際のGPU価格と性能スコアを使い、解像度ごとの推奨GPUを提案。\n"
            "フレームレート目標別の提案、コストパフォーマンス分析。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "performance",
        "title": "「{game}」が重い・カクつく原因と解決策5選",
        "keywords": ["{game} 重い", "{game} カクつく", "{game} FPS出ない"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のデータです（{source_note}）:\n{data_context}\n\n"
            "「{game}」が重い・カクつく時の解決策を5つ、1,400文字程度で解説。\n"
            "上記の公式スペックと性能スコアを参考に、原因の診断方法と具体的な解決策を記載。\n"
            "初心者向け。最後にAI診断チャットへ誘導。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "used_parts",
        "title": "中古パーツで組む「{game}」向け格安ゲーミングPC",
        "keywords": ["{game} 中古パーツ", "{game} 格安PC"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際の市場データです（{source_note}）:\n{data_context}\n\n"
            "中古パーツで「{game}」を遊べるPCを組む方法を1,500文字程度で解説。\n"
            "上記の旧世代GPU新品価格を参考に、中古市場での狙い目を提案。\n"
            "予算5〜8万円の構成例。リスク・注意点を明記。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "mod",
        "title": "「{game}」のMODを入れるために必要なスペック",
        "keywords": ["{game} MOD スペック", "{game} MOD 重い"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のデータです（{source_note}）:\n{data_context}\n\n"
            "「{game}」にMODを導入する際の推奨スペックを1,200文字程度で解説。\n"
            "上記の公式スペックとVRAM別GPU価格を参考に、MODの種類別にスペック提案。\n"
            "VRAM容量の重要性を実際のGPU価格と合わせて説明。\n"
            "価格データを引用する際は必ず「価格.com調べ」と記載してください。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "ranking",
        "title": "{month}月版 最新ゲーム推奨スペックランキングTOP20",
        "keywords": ["ゲーム 推奨スペック ランキング", "2026年 ゲーム 重い"],
        "prompt": (
            "今日は{today}です。{season_context}\n"
            "以下は実際のゲームスペックデータです（{source_note}）:\n{data_context}\n\n"
            "最新ゲームの推奨スペックをランキング形式（重い順TOP20）で紹介。2,000文字程度。\n"
            "上記のデータベースにあるゲームを中心に、推奨GPUが重い順にランキング。\n"
            "各ゲームの推奨GPU/CPU、ジャンル別推奨スペック。\n"
            "SEOキーワード: {keywords}\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
    {
        "id": "weekly_report",
        "title": "【週刊】PCパーツ価格ウォッチ {today_short}第{week}週",
        "keywords": ["PCパーツ 価格", "GPU 値下げ", "自作PC 相場"],
        "prompt": (
            "今日は{today}です。以下は今週のPCパーツ価格変動データです（{source_note}）:\n"
            "{data_context}\n\n"
            "上記の実データを元に、今週のPCパーツ価格動向レポートを1,800文字程度で作成してください。\n"
            "以下の構成で記事にしてください:\n"
            "1. 今週の注目トピック（値下げ・新登場・トレンド）\n"
            "2. GPU価格動向（チップ別最安値をテーブルで）\n"
            "3. CPU価格動向\n"
            "4. メモリ・ストレージ動向\n"
            "5. 今週の買い時パーツBEST3（理由付き）\n"
            "6. 来週の注目ポイント\n"
            "価格は上記データの数値を正確に使うこと。「価格.com調べ」と明記してください。\n"
            "出力はHTMLタグで構造化してください。コードフェンス（```）は絶対に使わないでください。"
        ),
    },
]
