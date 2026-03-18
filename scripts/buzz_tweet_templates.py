#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バズ投稿テンプレート7型
PCゲーマーに刺さる投稿パターン集
"""
import random

SITE_URL = 'https://pc-jisaku.com'


def generate_buzz_tweets():
    """7つの型からランダムに1つ選んでツイートを生成"""
    all_tweets = []
    
    # === 1. 衝撃データ型 ===
    all_tweets.extend([
        (
            "知らないと損する事実\n\n"
            "RTX 4070、3ヶ月で24%値下げしてる\n\n"
            "2026年1月: ¥218,800\n"
            "2026年3月: ¥164,974\n\n"
            "5070出てから旧世代暴落中\n"
            f"今が買い時かもしれない\n\n📊 {SITE_URL}",
            'shock_data'
        ),
        (
            "マジで言ってる？\n\n"
            "DDR5メモリ、今週449件値上がり\n"
            "値下がりは217件だけ\n\n"
            "買うなら今週中がいいかも\n"
            f"価格チェック→ {SITE_URL}",
            'shock_data'
        ),
        (
            "これ知ってた？\n\n"
            "PCゲーマーの平均GPU予算\n"
            "2024年: 4.2万円\n"
            "2025年: 5.8万円\n"
            "2026年: 7.1万円\n\n"
            "年々上がってるけど\n"
            "コスパ最強はRTX 4060（4.5万）\n\n"
            f"📊 {SITE_URL}",
            'shock_data'
        ),
    ])
    
    # === 2. 間違い指摘型 ===
    all_tweets.extend([
        (
            "自作PCでよくある間違いTOP3\n\n"
            "❌ メモリ1枚挿し→性能半減\n"
            "❌ 電源ケチる→パーツ巻き込み故障\n"
            "❌ CPUに金かけすぎ→GPUが本体\n\n"
            "1つでもやってたら今すぐ見直して\n\n"
            f"診断→ {SITE_URL}",
            'mistake'
        ),
        (
            "PC初心者がやりがちな失敗\n\n"
            "❌ 推奨スペック=快適ではない\n"
            "❌ SSDなしでHDDだけ→地獄\n"
            "❌ ケースのエアフロー無視→熱暴走\n\n"
            "全部経験済みの人RT",
            'mistake'
        ),
        (
            "GPU選びの落とし穴\n\n"
            "❌ VRAM多い=速いではない\n"
            "❌ 最新=最強ではない\n"
            "❌ ベンチマーク=実ゲーム性能ではない\n\n"
            "実際のゲームで比較するのが大事\n\n"
            f"ゲーム別GPU診断→ {SITE_URL}",
            'mistake'
        ),
    ])
    
    # === 3. ランキング型 ===
    all_tweets.extend([
        (
            "【2026年3月】コスパ最強GPU TOP5\n\n"
            "🥇 RTX 4060 ¥44,800\n"
            "🥈 RX 7600 ¥35,800\n"
            "🥉 RTX 4060 Ti ¥58,800\n"
            "4️⃣ RX 7700 XT ¥62,800\n"
            "5️⃣ RTX 4070 ¥82,800\n\n"
            "異論は認める\n"
            f"あなたの推しGPUは？\n\n📊 {SITE_URL}",
            'ranking'
        ),
        (
            "【保存推奨】重いゲームランキング\n\n"
            "🥇 サイバーパンク2077（最も重い）\n"
            "🥈 スターフィールド\n"
            "🥉 モンハンワイルズ\n"
            "4️⃣ エルデンリング\n"
            "5️⃣ バルダーズゲート3\n\n"
            "全部動くPCの予算は約15万円\n\n"
            f"📊 {SITE_URL}",
            'ranking'
        ),
        (
            "Steam人気ゲーム 推奨GPU一覧\n\n"
            "🎮 フォートナイト: GTX 1060〜\n"
            "🎮 Apex: RTX 2060〜\n"
            "🎮 エルデンリング: RTX 3060〜\n"
            "🎮 モンハンワイルズ: RTX 4060〜\n"
            "🎮 サイバーパンク: RTX 4070〜\n\n"
            f"あなたのPCで動く？→ {SITE_URL}",
            'ranking'
        ),
    ])
    
    # === 4. 予算別提案型 ===
    all_tweets.extend([
        (
            "予算別「ゲーミングPC何買える？」\n\n"
            "💰 5万: Apex 60fps（中古パーツ）\n"
            "💰 10万: モンハン 60fps\n"
            "💰 15万: エルデン 144fps\n"
            "💰 20万: サイバーパンク 4K\n"
            "💰 30万: 全部最高設定\n\n"
            f"あなたはどこ？\n\n診断→ {SITE_URL}",
            'budget'
        ),
        (
            "学生向けゲーミングPC予算ガイド\n\n"
            "🎓 3万円: マイクラ・Among Us\n"
            "🎓 5万円: Apex・フォトナ\n"
            "🎓 8万円: モンハン・エルデン\n"
            "🎓 10万円: 大体のゲーム快適\n\n"
            "中古パーツ使えば半額いける\n\n"
            f"📊 {SITE_URL}",
            'budget'
        ),
    ])
    
    # === 5. VS型 ===
    all_tweets.extend([
        (
            "これ決着つけようぜ\n\n"
            "RTX 4070 vs RX 7800 XT\n\n"
            "RTX 4070\n"
            "✅ DLSS 3（神）\n"
            "✅ Ray Tracing強い\n"
            "❌ VRAM 12GB\n\n"
            "RX 7800 XT\n"
            "✅ VRAM 16GB\n"
            "✅ 1万円安い\n"
            "❌ ドライバ不安定\n\n"
            "どっち派？引用RTで教えて",
            'vs'
        ),
        (
            "Intel vs AMD 2026年版\n\n"
            "Intel Core i7-14700K\n"
            "✅ シングル性能最強\n"
            "❌ 爆熱・電力バカ食い\n\n"
            "AMD Ryzen 7 7800X3D\n"
            "✅ ゲーム最強\n"
            "✅ 省電力\n"
            "❌ マルチ弱い\n\n"
            "ゲーム用ならどっち？",
            'vs'
        ),
        (
            "自作PC vs BTO\n\n"
            "自作\n"
            "✅ 安い（同スペック-2万）\n"
            "✅ パーツ選べる\n"
            "❌ 自己責任\n\n"
            "BTO\n"
            "✅ 保証あり\n"
            "✅ 組立不要\n"
            "❌ パーツ選べない\n\n"
            "初心者はどっちがいい？",
            'vs'
        ),
    ])
    
    # === 6. ビフォーアフター型 ===
    all_tweets.extend([
        (
            "3万円でPCがここまで変わる\n\n"
            "Before: GTX 1060\n"
            "→ Apex 30fps カクカク😵\n\n"
            "After: RTX 4060\n"
            "→ Apex 144fps ヌルヌル😎\n\n"
            "交換したのはグラボだけ\n"
            "電源足りてればポン付けOK\n\n"
            f"あなたのPCも診断↓\n{SITE_URL}",
            'before_after'
        ),
        (
            "SSD換装の威力がヤバい\n\n"
            "Before: HDD\n"
            "→ Windows起動 2分\n"
            "→ ゲームロード 45秒\n\n"
            "After: NVMe SSD\n"
            "→ Windows起動 8秒\n"
            "→ ゲームロード 5秒\n\n"
            "たった1万円の投資で世界変わる",
            'before_after'
        ),
    ])
    
    # === 7. ゲーム名フック型 ===
    popular_games = [
        ("モンハンワイルズ", "GTX 1060", "i5-10600", "RTX 4060", "i7-12700", "RTX 4070", "i7-13700"),
        ("エルデンリング", "GTX 1060", "i5-8400", "RTX 3060", "i7-10700", "RTX 4070", "i7-12700"),
        ("サイバーパンク2077", "GTX 1060", "i5-8600", "RTX 3070", "i7-12700", "RTX 4070 Ti", "i9-13900"),
    ]
    
    for game, min_gpu, min_cpu, rec_gpu, rec_cpu, best_gpu, best_cpu in popular_games:
        all_tweets.append((
            f"{game}が動くPCスペック\n\n"
            f"最低: {min_gpu} / {min_cpu}\n"
            f"推奨: {rec_gpu} / {rec_cpu}\n"
            f"快適: {best_gpu} / {best_cpu}\n\n"
            f"推奨でもカクつく場面あるから\n"
            f"{best_gpu}以上が安心\n\n"
            f"あなたのPCで動く？↓\n{SITE_URL}",
            'game_hook'
        ))
    
    return all_tweets


def get_random_buzz_tweet():
    """ランダムに1つバズ型ツイートを返す"""
    all_tweets = generate_buzz_tweets()
    return random.choice(all_tweets)


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    text, pattern = get_random_buzz_tweet()
    print(f"[型: {pattern}]")
    print(text)
    print(f"\n文字数: {len(text)}")
