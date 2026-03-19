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
            "え、5万円も安くなってるんだけど\n\n"
            "RTX 4070の価格推移\n"
            "1月: ¥218,800\n"
            "3月: ¥164,974\n\n"
            "RTX 5070出てから旧世代が暴落してる\n"
            f"今が底かもしれない\n\n{SITE_URL}",
            'shock_data'
        ),
        (
            "メモリ買おうとしてる人、急いだ方がいい\n\n"
            "今週のDDR5\n"
            "値上がり: 449件\n"
            "値下がり: 217件\n\n"
            "来週さらに上がる可能性あり\n"
            f"価格チェック→ {SITE_URL}",
            'shock_data'
        ),
        (
            "GPU予算、年々エグくなってない？\n\n"
            "2024年: 4.2万円\n"
            "2025年: 5.8万円\n"
            "2026年: 7.1万円\n\n"
            "でもRTX 4060は4.5万で買える\n"
            f"コスパ最強はまだこいつ\n\n{SITE_URL}",
            'shock_data'
        ),
    ])
    
    # === 2. 間違い指摘型 ===
    all_tweets.extend([
        (
            "これ全部やってた人、正直に手挙げて\n\n"
            "❌ メモリ1枚挿し→性能半減してる\n"
            "❌ 電源ケチった→パーツ巻き込んで死亡\n"
            "❌ CPUに10万かけてGPU3万→逆だろ\n\n"
            f"自分のPC大丈夫？→ {SITE_URL}",
            'mistake'
        ),
        (
            "PC初心者、これだけは覚えて帰って\n\n"
            "❌「推奨スペック」は快適じゃない\n"
            "❌ HDDだけは令和では人権ない\n"
            "❌ エアフロー無視すると夏に死ぬ\n\n"
            "全部やらかした民はRT",
            'mistake'
        ),
        (
            "GPU選びで騙されるな\n\n"
            "❌ VRAM多い=速い ←嘘\n"
            "❌ 最新=最強 ←嘘\n"
            "❌ ベンチ=実ゲーム ←嘘\n\n"
            "実際のゲームで比べないと意味ない\n\n"
            f"ゲーム別に診断できる→ {SITE_URL}",
            'mistake'
        ),
    ])
    
    # === 3. ランキング型 ===
    all_tweets.extend([
        (
            "今買うべきGPU、これで決まり\n\n"
            "🥇 RTX 4060 ¥44,800←王者\n"
            "🥈 RX 7600 ¥35,800←最安\n"
            "🥉 RTX 4060 Ti ¥58,800\n"
            "4️⃣ RX 7700 XT ¥62,800\n"
            "5️⃣ RTX 4070 ¥82,800←値崩れ中\n\n"
            f"異論ある人、引用RTで語って\n\n{SITE_URL}",
            'ranking'
        ),
        (
            "PCスペック要求がエグいゲームTOP5\n\n"
            "🥇 サイバーパンク2077（化け物）\n"
            "🥈 スターフィールド（重すぎ）\n"
            "🥉 モンハンワイルズ\n"
            "4️⃣ エルデンリング\n"
            "5️⃣ バルダーズゲート3\n\n"
            f"全部動かすには15万円必要\n\n{SITE_URL}",
            'ranking'
        ),
        (
            "このGPUでそのゲーム動くの？一覧\n\n"
            "🎮 フォートナイト: GTX 1060〜\n"
            "🎮 Apex: RTX 2060〜\n"
            "🎮 エルデン: RTX 3060〜\n"
            "🎮 モンハン: RTX 4060〜\n"
            "🎮 サイパン: RTX 4070〜\n\n"
            f"保存しとくと便利\n\n{SITE_URL}",
            'ranking'
        ),
    ])
    
    # === 4. 予算別提案型 ===
    all_tweets.extend([
        (
            "ゲーミングPCって結局いくら必要なの？\n\n"
            "💰 5万: Apex 60fps（中古なら余裕）\n"
            "💰 10万: モンハン快適\n"
            "💰 15万: エルデン 144fps\n"
            "💰 20万: サイパン 4K\n"
            "💰 30万: もう何も怖くない\n\n"
            f"あなたはどのライン？\n\n{SITE_URL}",
            'budget'
        ),
        (
            "学生でもゲーミングPC買えるぞ\n\n"
            "🎓 3万: マイクラ・Among Us\n"
            "🎓 5万: Apex・フォトナ余裕\n"
            "🎓 8万: モンハン・エルデンいける\n"
            "🎓 10万: 大体のゲーム快適\n\n"
            f"中古パーツなら半額でいける\n\n{SITE_URL}",
            'budget'
        ),
    ])
    
    # === 5. VS型 ===
    all_tweets.extend([
        (
            "この論争、終わらせたい\n\n"
            "RTX 4070 vs RX 7800 XT\n\n"
            "4070: DLSS神 / レイトレ◎ / VRAM 12GB\n"
            "7800XT: VRAM 16GB / 1万安い / 1440p最強\n\n"
            "どっち派？引用RTで決着つけよう",
            'vs'
        ),
        (
            "ゲーム用CPUどっち買う？\n\n"
            "Intel i7-14700K\n"
            "→シングル最強だけど爆熱\n\n"
            "AMD Ryzen 7 7800X3D\n"
            "→ゲーム最強で省電力\n\n"
            "正直7800X3D一択じゃね？\n反論ある人こい",
            'vs'
        ),
        (
            "自作とBTO、初心者はどっちにすべき？\n\n"
            "自作: 2万安い / 好きなパーツ選べる / 壊したら自己責任\n"
            "BTO: 保証あり / 届いて即使える / パーツ選べない\n\n"
            "俺は自作派だけど\nぶっちゃけ初心者はBTOでよくない？",
            'vs'
        ),
    ])
    
    # === 6. ビフォーアフター型 ===
    all_tweets.extend([
        (
            "グラボ変えただけでこの差はズルい\n\n"
            "GTX 1060 → Apex 30fps カクカク😵\n"
            "RTX 4060 → Apex 144fps ヌルヌル😎\n\n"
            "交換費用たった3万円\n"
            "電源足りてればポン付け\n\n"
            f"あなたのPCで何fps出る？→ {SITE_URL}",
            'before_after'
        ),
        (
            "1万円でPC生まれ変わった\n\n"
            "HDD → SSD換装しただけ\n\n"
            "起動: 2分 → 8秒\n"
            "ゲームロード: 45秒 → 5秒\n\n"
            "まだHDDの人、マジで今すぐ変えて\n世界変わるから",
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
            f"{game}、あなたのPCで動く？\n\n"
            f"最低: {min_gpu}（カクカク覚悟）\n"
            f"推奨: {rec_gpu}（まあまあ）\n"
            f"快適: {best_gpu}（ヌルヌル）\n\n"
            f"「推奨」でもカクつく場面あるから\n"
            f"正直{best_gpu}欲しい\n\n"
            f"診断→ {SITE_URL}",
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
