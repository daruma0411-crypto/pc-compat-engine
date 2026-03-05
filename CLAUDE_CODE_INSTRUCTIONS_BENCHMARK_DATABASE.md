# Claude Code 実装指示書: ベンチマークデータベース構築プロジェクト

## 📋 プロジェクト概要

**目的**: 「14,000件の互換性データ」を実態のあるベンチマークデータベースに変換し、業界最高精度のPC診断サービスを実現する

**現在の問題**:
- ❌ 予算別構成の性能は「推測値」（根拠なし）
- ❌ スペック診断は「推奨スペック以上か？」の二択のみ
- ❌ ユーザーが本当に知りたい「実FPS」がわからない
- ❌ 「14,000件のデータ」と謳っているが実態がない

**実装後**:
- ✅ GPU × ゲーム × 解像度 × 設定 → 実FPS データベース
- ✅ 「RTX 4060 + Elden Ring + 1080p高設定 = 平均72fps」
- ✅ 予算別構成の性能が実測値ベースに
- ✅ 「あと3万円で144fps届く」など具体的提案
- ✅ 競合にない圧倒的価値

**実装時間**: 10時間（3フェーズ）

---

## 🗄️ データベース設計

### スキーマ: `workspace/data/benchmark_fps.jsonl`

```json
{
  "gpu": "GeForce RTX 4060",
  "game": "Elden Ring",
  "resolution": "1080p",
  "settings": "high",
  "avg_fps": 72,
  "min_fps": 58,
  "1_percent_low": 54,
  "cpu": "AMD Ryzen 5 7600",
  "ram_gb": 16,
  "source": "TechPowerUp",
  "source_url": "https://www.techpowerup.com/review/...",
  "date": "2024-11-15",
  "verified": true
}
```

### フィールド定義

| フィールド | 型 | 説明 | 必須 |
|-----------|-----|------|------|
| `gpu` | string | GPU名（performance_scores.jsonlと統一） | ✅ |
| `game` | string | ゲーム名（games.jsonlと統一） | ✅ |
| `resolution` | enum | `1080p` / `1440p` / `4k` | ✅ |
| `settings` | enum | `low` / `medium` / `high` / `ultra` | ✅ |
| `avg_fps` | number | 平均FPS | ✅ |
| `min_fps` | number | 最小FPS | ⭕ |
| `1_percent_low` | number | 1%ローFPS | ⭕ |
| `cpu` | string | テスト時のCPU | ⭕ |
| `ram_gb` | number | テスト時のRAM容量 | ⭕ |
| `source` | string | データソース名 | ✅ |
| `source_url` | string | 元記事URL | ✅ |
| `date` | string | データ取得日（YYYY-MM-DD） | ✅ |
| `verified` | boolean | 信頼性検証済みか | ✅ |

---

## 🚀 Phase 1: 最小データセット構築（3時間）

### 目標

- 人気GPU 20種 × 人気ゲーム 50本 × 3解像度 × 2設定
- = **6,000レコード** の初期データセット

### 対象GPU（20種）

```python
TARGET_GPUS = [
    # NVIDIA RTX 40シリーズ
    "GeForce RTX 4060",
    "GeForce RTX 4060 Ti",
    "GeForce RTX 4070",
    "GeForce RTX 4070 Super",
    "GeForce RTX 4070 Ti",
    "GeForce RTX 4080",
    "GeForce RTX 4080 Super",
    "GeForce RTX 4090",
    
    # NVIDIA RTX 30シリーズ
    "GeForce RTX 3060",
    "GeForce RTX 3060 Ti",
    "GeForce RTX 3070",
    "GeForce RTX 3070 Ti",
    "GeForce RTX 3080",
    
    # AMD RX 7000シリーズ
    "Radeon RX 7600",
    "Radeon RX 7700 XT",
    "Radeon RX 7800 XT",
    "Radeon RX 7900 XT",
    "Radeon RX 7900 XTX",
    
    # エントリー
    "GeForce GTX 1660 SUPER",
    "Radeon RX 6600",
]
```

### 対象ゲーム（50本・優先度順）

```python
TARGET_GAMES = [
    # 超人気（必須）
    "Elden Ring",
    "Cyberpunk 2077",
    "Baldur's Gate 3",
    "Starfield",
    "Hogwarts Legacy",
    "Call of Duty: Modern Warfare III",
    "Fortnite",
    "Apex Legends",
    "Valorant",
    "Counter-Strike 2",
    
    # 重量級（ベンチマーク定番）
    "Red Dead Redemption 2",
    "Microsoft Flight Simulator",
    "Assassin's Creed Valhalla",
    "Watch Dogs: Legion",
    "Control",
    
    # 最新人気
    "Palworld",
    "Helldivers 2",
    "Final Fantasy VII Rebirth",
    "Dragon's Dogma 2",
    "Monster Hunter Wilds",
    
    # eスポーツ
    "League of Legends",
    "Dota 2",
    "Overwatch 2",
    "Rainbow Six Siege",
    
    # RPG
    "The Witcher 3: Wild Hunt",
    "Skyrim",
    "Fallout 4",
    "Dark Souls III",
    
    # その他人気
    "Grand Theft Auto V",
    "Minecraft",
    "Stray",
    "Resident Evil 4",
    "Street Fighter 6",
    "Armored Core VI",
    "Lies of P",
    "Alan Wake 2",
    "Atomic Heart",
    "Hitman 3",
    "Death Stranding",
    "Horizon Zero Dawn",
    "God of War",
    "Spider-Man Remastered",
    "The Last of Us Part I",
    "Returnal",
    "Ratchet & Clank: Rift Apart",
    "Uncharted: Legacy of Thieves Collection",
    "Nioh 2",
    "Sekiro: Shadows Die Twice",
    "Persona 5 Royal",
]
```

### データ収集テンプレート

**CSVフォーマット**: `workspace/data/benchmark_raw.csv`

```csv
gpu,game,resolution,settings,avg_fps,min_fps,1_percent_low,cpu,ram_gb,source,source_url,date,verified
GeForce RTX 4060,Elden Ring,1080p,high,72,58,54,Ryzen 5 7600,16,TechPowerUp,https://...,2024-11-15,true
GeForce RTX 4060,Elden Ring,1440p,high,52,42,38,Ryzen 5 7600,16,TechPowerUp,https://...,2024-11-15,true
GeForce RTX 4060,Elden Ring,4k,high,28,22,20,Ryzen 5 7600,16,TechPowerUp,https://...,2024-11-15,true
```

### 変換スクリプト: `scripts/convert_benchmark_csv_to_jsonl.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVベンチマークデータをJSONLに変換
"""

import csv
import json
from pathlib import Path

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
CSV_FILE = WORKSPACE_DIR / "workspace" / "data" / "benchmark_raw.csv"
JSONL_FILE = WORKSPACE_DIR / "workspace" / "data" / "benchmark_fps.jsonl"

def convert_csv_to_jsonl():
    """CSVをJSONLに変換"""
    if not CSV_FILE.exists():
        print(f"❌ {CSV_FILE} が見つかりません")
        return
    
    records = []
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                'gpu': row['gpu'].strip(),
                'game': row['game'].strip(),
                'resolution': row['resolution'].strip().lower(),
                'settings': row['settings'].strip().lower(),
                'avg_fps': int(row['avg_fps']) if row['avg_fps'] else None,
                'min_fps': int(row['min_fps']) if row['min_fps'] else None,
                '1_percent_low': int(row['1_percent_low']) if row['1_percent_low'] else None,
                'cpu': row['cpu'].strip() if row['cpu'] else None,
                'ram_gb': int(row['ram_gb']) if row['ram_gb'] else None,
                'source': row['source'].strip(),
                'source_url': row['source_url'].strip(),
                'date': row['date'].strip(),
                'verified': row['verified'].strip().lower() == 'true',
            }
            records.append(record)
    
    # JSONL書き込み
    with open(JSONL_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ {len(records)} レコードを {JSONL_FILE} に変換しました")

if __name__ == '__main__':
    convert_csv_to_jsonl()
```

### データ収集手順（手動）

1. **TechPowerUp GPU Review検索**
   ```
   site:techpowerup.com "RTX 4060" review
   site:techpowerup.com "RX 7800 XT" review
   ```

2. **記事からFPSデータ抽出**
   - ベンチマークセクションを探す
   - 1080p / 1440p / 4K のFPS表を確認
   - CSV形式で記録

3. **最低限のデータ目標**
   - GPU 20種 × ゲーム 10本 × 解像度 2種 × 設定 1種
   - = **400レコード**（Phase 1の最小目標）

---

## 🤖 Phase 2: 自動収集システム構築（5時間）

### YouTube API連携

**新規ファイル**: `scripts/benchmark_youtube_scraper.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTubeベンチマーク動画からFPSデータ自動収集
"""

import re
import json
from pathlib import Path
import yt_dlp

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = WORKSPACE_DIR / "workspace" / "data" / "benchmark_youtube.jsonl"

# YouTube検索クエリテンプレート
SEARCH_TEMPLATE = "{gpu} {game} benchmark fps"

# FPS抽出正規表現パターン
FPS_PATTERNS = [
    # "1080p High: 72 FPS"
    r'(\d{3,4}p)\s+(low|medium|high|ultra):\s*(\d+)\s*fps',
    
    # "1080p: 72fps"
    r'(\d{3,4}p):\s*(\d+)\s*fps',
    
    # "72 FPS @ 1080p High"
    r'(\d+)\s*fps\s*@\s*(\d{3,4}p)\s+(low|medium|high|ultra)',
    
    # "Average: 72"
    r'average:\s*(\d+)',
]

def extract_fps_from_youtube(gpu, game, max_results=5):
    """
    YouTubeからベンチマーク動画を検索してFPS抽出
    
    Args:
        gpu: GPU名（例: "RTX 4060"）
        game: ゲーム名（例: "Elden Ring"）
        max_results: 検索結果数
    
    Returns:
        List[dict]: 抽出されたベンチマークデータ
    """
    search_query = SEARCH_TEMPLATE.format(gpu=gpu, game=game)
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': max_results,
        'no_warnings': True,
    }
    
    results = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)
            
            if not search_results or 'entries' not in search_results:
                return results
            
            for entry in search_results['entries']:
                video_id = entry.get('id')
                title = entry.get('title', '')
                description = entry.get('description', '')
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                # タイトル + 説明文からFPS抽出
                text = f"{title}\n{description}"
                
                # パターンマッチング
                for pattern in FPS_PATTERNS:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        fps_data = parse_fps_match(match, gpu, game, url)
                        if fps_data:
                            results.append(fps_data)
    
    except Exception as e:
        print(f"❌ YouTube検索エラー ({gpu} + {game}): {e}")
    
    return results

def parse_fps_match(match, gpu, game, url):
    """
    正規表現マッチからベンチマークデータ構築
    """
    # パターンによって構造が異なる
    if len(match) == 3 and match[0].endswith('p'):
        # "1080p High: 72 FPS"
        resolution = match[0].lower()
        settings = match[1].lower()
        avg_fps = int(match[2])
    elif len(match) == 2 and match[0].endswith('p'):
        # "1080p: 72fps"
        resolution = match[0].lower()
        settings = 'unknown'
        avg_fps = int(match[1])
    elif len(match) == 3 and match[1].endswith('p'):
        # "72 FPS @ 1080p High"
        avg_fps = int(match[0])
        resolution = match[1].lower()
        settings = match[2].lower()
    elif len(match) == 1:
        # "Average: 72"
        avg_fps = int(match[0])
        resolution = 'unknown'
        settings = 'unknown'
    else:
        return None
    
    return {
        'gpu': gpu,
        'game': game,
        'resolution': resolution,
        'settings': settings,
        'avg_fps': avg_fps,
        'min_fps': None,
        '1_percent_low': None,
        'cpu': None,
        'ram_gb': None,
        'source': 'YouTube',
        'source_url': url,
        'date': None,  # 取得日時を追加する場合
        'verified': False,  # YouTube データは未検証扱い
    }

def scrape_multiple(gpu_list, game_list):
    """
    複数のGPU × ゲーム組み合わせをスクレイピング
    """
    all_results = []
    
    total = len(gpu_list) * len(game_list)
    count = 0
    
    for gpu in gpu_list:
        for game in game_list:
            count += 1
            print(f"[{count}/{total}] 検索中: {gpu} + {game}")
            
            results = extract_fps_from_youtube(gpu, game)
            all_results.extend(results)
            
            print(f"  → {len(results)} 件のデータ取得")
    
    # JSONL保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for record in all_results:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 合計 {len(all_results)} レコードを {OUTPUT_FILE} に保存")

# 実行例
if __name__ == '__main__':
    # テスト実行
    gpus = ["RTX 4060", "RTX 4070"]
    games = ["Elden Ring", "Cyberpunk 2077"]
    
    scrape_multiple(gpus, games)
```

### 依存関係追加

**ファイル**: `requirements.txt`

```txt
# 既存の依存関係
flask
python-dotenv
anthropic
tweepy
Pillow

# 新規追加（Phase 2用）
yt-dlp
beautifulsoup4
lxml
requests
```

---

## 🧠 Phase 3: 診断エンジン実装（2時間）

### ベンチマークデータ読み込みモジュール

**新規ファイル**: `scripts/benchmark_db.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ベンチマークデータベース アクセスモジュール
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# パス設定
WORKSPACE_DIR = Path(__file__).parent.parent
BENCHMARK_FILE = WORKSPACE_DIR / "workspace" / "data" / "benchmark_fps.jsonl"
PERFORMANCE_SCORES_FILE = WORKSPACE_DIR / "workspace" / "data" / "performance_scores.jsonl"

# キャッシュ
_benchmark_cache = []
_performance_scores = {}

def load_benchmark_database():
    """ベンチマークデータベース読み込み"""
    global _benchmark_cache
    
    if _benchmark_cache:
        return _benchmark_cache
    
    if not BENCHMARK_FILE.exists():
        print(f"⚠️ {BENCHMARK_FILE} が見つかりません")
        return []
    
    with open(BENCHMARK_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                _benchmark_cache.append(json.loads(line))
    
    print(f"✅ {len(_benchmark_cache)} 件のベンチマークデータ読み込み完了")
    return _benchmark_cache

def load_performance_scores():
    """GPUパフォーマンススコア読み込み"""
    global _performance_scores
    
    if _performance_scores:
        return _performance_scores
    
    if not PERFORMANCE_SCORES_FILE.exists():
        print(f"⚠️ {PERFORMANCE_SCORES_FILE} が見つかりません")
        return {}
    
    with open(PERFORMANCE_SCORES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry['type'] == 'gpu':
                    _performance_scores[entry['name']] = entry['score']
    
    return _performance_scores

def find_benchmark(gpu: str, game: str, resolution: str = None, settings: str = None) -> Optional[Dict]:
    """
    ベンチマークデータ検索
    
    Args:
        gpu: GPU名
        game: ゲーム名
        resolution: 解像度（省略可）
        settings: グラフィック設定（省略可）
    
    Returns:
        マッチしたベンチマークデータ or None
    """
    db = load_benchmark_database()
    
    # GPUの正規化（GeForce/Radeon除去）
    gpu_normalized = gpu.replace('GeForce ', '').replace('Radeon ', '').strip()
    
    for record in db:
        record_gpu = record['gpu'].replace('GeForce ', '').replace('Radeon ', '').strip()
        
        # GPU + ゲーム名が一致
        if record_gpu.lower() != gpu_normalized.lower():
            continue
        if record['game'].lower() != game.lower():
            continue
        
        # 解像度指定があれば一致確認
        if resolution and record['resolution'].lower() != resolution.lower():
            continue
        
        # 設定指定があれば一致確認
        if settings and record['settings'].lower() != settings.lower():
            continue
        
        # verified=true を優先
        if record.get('verified', False):
            return record
    
    # verified=false でも返す
    for record in db:
        record_gpu = record['gpu'].replace('GeForce ', '').replace('Radeon ', '').strip()
        
        if record_gpu.lower() == gpu_normalized.lower() and record['game'].lower() == game.lower():
            if resolution and record['resolution'].lower() != resolution.lower():
                continue
            if settings and record['settings'].lower() != settings.lower():
                continue
            return record
    
    return None

def estimate_fps(user_gpu: str, game: str, resolution: str, settings: str = 'high') -> Dict:
    """
    ベンチマークデータがない場合、スコアから推定
    
    Args:
        user_gpu: ユーザーのGPU
        game: ゲーム名
        resolution: 解像度
        settings: グラフィック設定
    
    Returns:
        推定FPS情報
    """
    scores = load_performance_scores()
    
    # ユーザーGPUのスコア
    user_score = scores.get(user_gpu)
    if not user_score:
        return {
            'estimated': False,
            'avg_fps': None,
            'message': 'GPUスコアが見つかりません',
        }
    
    # ゲームの推奨GPUを検索
    # （games.jsonl から推奨スペック取得は別途実装）
    
    # 仮実装: RTX 3060 を基準（スコア40）として計算
    base_score = 40
    base_fps = 60  # RTX 3060で1080p高設定60fps想定
    
    # 解像度補正
    resolution_factor = {
        '1080p': 1.0,
        '1440p': 0.7,
        '4k': 0.4,
    }.get(resolution.lower(), 1.0)
    
    # 設定補正
    settings_factor = {
        'low': 1.5,
        'medium': 1.2,
        'high': 1.0,
        'ultra': 0.8,
    }.get(settings.lower(), 1.0)
    
    # 推定FPS計算
    estimated_fps = int(base_fps * (user_score / base_score) * resolution_factor * settings_factor)
    
    return {
        'estimated': True,
        'avg_fps': estimated_fps,
        'confidence': 'low',
        'message': f'スコアベースの推定値です（実測データなし）',
    }

def suggest_upgrade(current_gpu: str, target_fps: int, current_fps: int, game: str) -> Optional[Dict]:
    """
    目標FPSに到達するためのアップグレード提案
    
    Args:
        current_gpu: 現在のGPU
        target_fps: 目標FPS
        current_fps: 現在のFPS
        game: ゲーム名
    
    Returns:
        アップグレード提案
    """
    if current_fps >= target_fps:
        return None
    
    gap = target_fps - current_fps
    required_boost = target_fps / current_fps  # 必要な性能倍率
    
    scores = load_performance_scores()
    current_score = scores.get(current_gpu, 50)
    required_score = int(current_score * required_boost)
    
    # 推奨GPU候補
    candidates = []
    for gpu_name, score in scores.items():
        if score >= required_score:
            candidates.append({
                'gpu': gpu_name,
                'score': score,
                'boost': score / current_score,
            })
    
    # スコア順にソート
    candidates.sort(key=lambda x: x['score'])
    
    if not candidates:
        return None
    
    # 最もコスパの良い選択肢（最小スコアで条件満たす）
    best = candidates[0]
    
    return {
        'recommended_gpu': best['gpu'],
        'expected_boost': f"{best['boost']:.1f}倍",
        'expected_fps': int(current_fps * best['boost']),
        'message': f"{best['gpu']} にアップグレードで目標達成可能",
    }
```

### 高度な診断API実装

**ファイル**: `app.py` に追加

```python
# 既存のimportに追加
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

from benchmark_db import find_benchmark, estimate_fps, suggest_upgrade

@app.route('/api/diagnose_advanced', methods=['POST'])
def diagnose_advanced():
    """
    高度なスペック診断API
    
    入力:
    {
      "gpu": "RTX 4060",
      "game": "Elden Ring",
      "resolution": "1080p",
      "target_fps": 144,
      "settings": "high"
    }
    
    出力:
    {
      "verdict": "OK" | "UPGRADE_RECOMMENDED" | "UNKNOWN",
      "expected_fps": 72,
      "target_fps": 144,
      "gap": 72,
      "upgrade_suggestion": {...},
      "benchmark_source": "実測データ" | "推定値"
    }
    """
    data = request.json
    
    gpu = data.get('gpu', '').strip()
    game = data.get('game', '').strip()
    resolution = data.get('resolution', '1080p').strip()
    target_fps = data.get('target_fps', 60)
    settings = data.get('settings', 'high').strip()
    
    if not gpu or not game:
        return jsonify({'error': 'GPU と game は必須です'}), 400
    
    # ベンチマークデータ検索
    benchmark = find_benchmark(gpu, game, resolution, settings)
    
    if benchmark:
        # 実測データあり
        avg_fps = benchmark['avg_fps']
        min_fps = benchmark.get('min_fps')
        
        verdict = 'OK' if avg_fps >= target_fps else 'UPGRADE_RECOMMENDED'
        gap = target_fps - avg_fps if avg_fps < target_fps else 0
        
        result = {
            'verdict': verdict,
            'expected_fps': avg_fps,
            'min_fps': min_fps,
            'target_fps': target_fps,
            'gap': gap,
            'benchmark_source': '実測データ',
            'source': benchmark.get('source'),
            'source_url': benchmark.get('source_url'),
        }
        
        # アップグレード提案
        if verdict == 'UPGRADE_RECOMMENDED':
            upgrade = suggest_upgrade(gpu, target_fps, avg_fps, game)
            if upgrade:
                result['upgrade_suggestion'] = upgrade
    else:
        # 推定値
        estimation = estimate_fps(gpu, game, resolution, settings)
        
        if not estimation['avg_fps']:
            return jsonify({
                'verdict': 'UNKNOWN',
                'message': estimation['message'],
            })
        
        avg_fps = estimation['avg_fps']
        verdict = 'OK' if avg_fps >= target_fps else 'UPGRADE_RECOMMENDED'
        gap = target_fps - avg_fps if avg_fps < target_fps else 0
        
        result = {
            'verdict': verdict,
            'expected_fps': avg_fps,
            'target_fps': target_fps,
            'gap': gap,
            'benchmark_source': '推定値（実測データなし）',
            'confidence': estimation.get('confidence', 'low'),
        }
        
        # アップグレード提案
        if verdict == 'UPGRADE_RECOMMENDED':
            upgrade = suggest_upgrade(gpu, target_fps, avg_fps, game)
            if upgrade:
                result['upgrade_suggestion'] = upgrade
    
    return jsonify(result)
```

---

## 🎨 フロントエンド改善

### ゲームページの予算別構成を実データベースに

**ファイル**: `scripts/generate_game_pages.py`

**修正箇所**: `BUDGET_BUILDS` を動的に計算

```python
from benchmark_db import find_benchmark

def calculate_budget_performance(game_name, gpu_name, resolution='1080p', settings='high'):
    """
    予算別構成の期待性能を実データから計算
    """
    benchmark = find_benchmark(gpu_name, game_name, resolution, settings)
    
    if benchmark:
        avg_fps = benchmark['avg_fps']
        
        # 解像度別の性能表示
        if avg_fps >= 100:
            return f"{resolution} {settings}設定 {avg_fps}fps（高リフレッシュ対応）"
        elif avg_fps >= 60:
            return f"{resolution} {settings}設定 {avg_fps}fps（快適）"
        elif avg_fps >= 30:
            return f"{resolution} {settings}設定 {avg_fps}fps"
        else:
            return f"{resolution} {settings}設定 約{avg_fps}fps（動作可能）"
    else:
        # データなし → 従来の推測表示
        return f"{resolution} {settings}設定（推定）"

# BUDGET_BUILDSの performance を動的計算に変更
for key, build in BUDGET_BUILDS.items():
    build['performance'] = calculate_budget_performance(
        game_name=game_title,
        gpu_name=build['gpu'],
        resolution='1080p',
        settings='high'
    )
```

### スペック診断ツール強化

**ファイル**: `static/app.js`

**新しい診断結果表示**:

```javascript
// /api/diagnose_advanced を呼び出し
async function diagnoseAdvanced(gpu, game, resolution, targetFps, settings) {
  const response = await fetch('/api/diagnose_advanced', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      gpu,
      game,
      resolution,
      target_fps: targetFps,
      settings,
    }),
  });
  
  const result = await response.json();
  
  // 結果表示
  displayAdvancedResult(result);
}

function displayAdvancedResult(result) {
  const html = `
    <div class="diagnosis-result ${result.verdict}">
      <h3>${VERDICT_MAP[result.verdict].icon} ${VERDICT_MAP[result.verdict].label}</h3>
      
      <div class="fps-info">
        <p><strong>期待FPS:</strong> ${result.expected_fps} fps</p>
        ${result.min_fps ? `<p><strong>最小FPS:</strong> ${result.min_fps} fps</p>` : ''}
        <p><strong>目標FPS:</strong> ${result.target_fps} fps</p>
        ${result.gap > 0 ? `<p class="warning"><strong>不足:</strong> ${result.gap} fps</p>` : ''}
      </div>
      
      <div class="benchmark-source">
        <small>${result.benchmark_source}</small>
        ${result.source_url ? `<a href="${result.source_url}" target="_blank">データソース</a>` : ''}
      </div>
      
      ${result.upgrade_suggestion ? `
        <div class="upgrade-suggestion">
          <h4>🔧 アップグレード提案</h4>
          <p>${result.upgrade_suggestion.message}</p>
          <p><strong>推奨GPU:</strong> ${result.upgrade_suggestion.recommended_gpu}</p>
          <p><strong>期待FPS:</strong> ${result.upgrade_suggestion.expected_fps} fps（${result.upgrade_suggestion.expected_boost}）</p>
        </div>
      ` : ''}
    </div>
  `;
  
  document.getElementById('diagnosis-result').innerHTML = html;
}
```

---

## 🧪 テスト・検証

### ユニットテスト: `tests/test_benchmark_db.py`

```python
import unittest
from scripts.benchmark_db import find_benchmark, estimate_fps, suggest_upgrade

class TestBenchmarkDB(unittest.TestCase):
    
    def test_find_benchmark_exact_match(self):
        """完全一致のベンチマーク検索"""
        result = find_benchmark(
            gpu='RTX 4060',
            game='Elden Ring',
            resolution='1080p',
            settings='high'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['gpu'], 'GeForce RTX 4060')
        self.assertEqual(result['resolution'], '1080p')
        self.assertGreater(result['avg_fps'], 0)
    
    def test_estimate_fps(self):
        """FPS推定機能"""
        result = estimate_fps(
            user_gpu='RTX 4070',
            game='Cyberpunk 2077',
            resolution='1440p',
            settings='high'
        )
        
        self.assertTrue(result['estimated'])
        self.assertIsNotNone(result['avg_fps'])
        self.assertGreater(result['avg_fps'], 0)
    
    def test_suggest_upgrade(self):
        """アップグレード提案"""
        suggestion = suggest_upgrade(
            current_gpu='RTX 3060',
            target_fps=144,
            current_fps=70,
            game='Valorant'
        )
        
        self.assertIsNotNone(suggestion)
        self.assertIn('recommended_gpu', suggestion)
        self.assertGreaterEqual(suggestion['expected_fps'], 144)

if __name__ == '__main__':
    unittest.main()
```

---

## 📋 実装手順（10時間）

### Day 1: Phase 1（3時間）

1. **データ収集準備**（30分）
   - `workspace/data/benchmark_raw.csv` 作成
   - CSVテンプレート準備

2. **手動データ収集**（2時間）
   - TechPowerUp検索
   - 最低400レコード収集（GPU 20種 × ゲーム 10本 × 解像度 2種）

3. **変換スクリプト実行**（30分）
   - `convert_benchmark_csv_to_jsonl.py` 実装・実行
   - `benchmark_fps.jsonl` 生成確認

---

### Day 2: Phase 2（5時間）

1. **YouTube API実装**（2時間）
   - `benchmark_youtube_scraper.py` 実装
   - `yt-dlp` インストール
   - テスト実行（GPU 5種 × ゲーム 5本）

2. **自動収集実行**（2時間）
   - GPU 20種 × ゲーム 50本 の組み合わせ実行
   - `benchmark_youtube.jsonl` 生成
   - データ品質チェック

3. **データマージ**（1時間）
   - 手動データ + YouTube データ統合
   - 重複削除
   - `benchmark_fps.jsonl` 最終版生成

---

### Day 3: Phase 3（2時間）

1. **診断エンジン実装**（1時間）
   - `benchmark_db.py` 実装
   - `app.py` に `/api/diagnose_advanced` 追加

2. **フロントエンド改善**（30分）
   - `app.js` に高度診断UI追加
   - CSS調整

3. **テスト・検証**（30分）
   - ローカルサーバー起動
   - 診断機能テスト
   - バグ修正

---

### 完了後: Git commit & push

```bash
cd C:\Users\iwashita.AKGNET\pc-compat-engine

git add workspace/data/benchmark_fps.jsonl
git add scripts/benchmark_db.py
git add scripts/benchmark_youtube_scraper.py
git add scripts/convert_benchmark_csv_to_jsonl.py
git add app.py
git add static/app.js
git add requirements.txt

git commit -m "feat: ベンチマークデータベース構築 - 実FPS診断機能実装

- Phase 1: 手動データ収集（400+ レコード）
- Phase 2: YouTube自動収集システム
- Phase 3: 高度診断API (/api/diagnose_advanced)
- 予算別構成の性能を実データベースに基づいて計算
- GPU × ゲーム × 解像度 × 設定 → 実FPS データ完備
- アップグレード提案機能実装
"

git push
```

---

## 📊 期待効果

### Before（現在）

```
ユーザー: 「RTX 4060でエルデンリング動く？」
サイト: 「推奨スペック満たしてます ✅」
ユーザー: 「で、何fps出るの？」
サイト: 「...」
```

### After（実装後）

```
ユーザー: 「RTX 4060でエルデンリング動く？」
サイト:
  「✅ 動作OK！

  期待性能（実測データ）:
  - 1080p 高設定: 平均72fps（快適）
  - 1440p 高設定: 平均52fps
  - 4K 高設定: 平均28fps

  144fps目標の場合:
  → RTX 4070 以上を推奨（1.8倍の性能）
  → 予算20万円で実現可能 → BTO商品を見る」

データソース: TechPowerUp
```

---

## 🎯 競合優位性

| サイト | データ内容 | 精度 | 日本語 |
|--------|-----------|------|--------|
| Game-Debate | 推奨スペックのみ | 低 | ❌ |
| Can You RUN It | GPU判定のみ | 低 | ❌ |
| PC Builds | 構成例のみ | 中 | ❌ |
| UserBenchmark | ユーザー投稿 | 中 | ❌ |
| **PC互換チェッカー（本実装後）** | **実FPS × 解像度 × 設定** | **高** | **✅** |

**唯一無二の価値**:
- ✅ 日本語完全対応
- ✅ 実測FPSデータベース（6,000+ レコード）
- ✅ 予算別提案と連携
- ✅ BTO直結アフィリエイト
- ✅ アップグレード提案機能

---

## ⚠️ 注意事項

### データ収集の法的留意点

1. **TechPowerUp**: データ引用は適切な出典表示が必要
2. **YouTube**: 動画説明文からの抽出は利用規約遵守
3. **スクレイピング**: robots.txt 確認、アクセス頻度制限

### データ品質管理

- ✅ `verified: true` フラグで信頼性管理
- ✅ 複数ソースでクロスチェック
- ✅ 異常値（FPS < 10 or > 500）はフィルタリング
- ✅ 定期的な更新（月1回）

---

## 📈 今後の拡張

### 短期（1-3ヶ月）
- ✅ データ自動更新システム（週次）
- ✅ ユーザー投稿ベンチマーク機能
- ✅ グラフ表示（FPS推移、GPU比較チャート）

### 中期（3-6ヶ月）
- ✅ 10,000+ レコード達成
- ✅ CPU × ゲーム のベンチマークも追加
- ✅ VR対応ゲームのデータ

### 長期（6-12ヶ月）
- ✅ AI予測モデル（機械学習でFPS推定精度向上）
- ✅ API公開（外部サイトへのデータ提供）

---

**実装時間目安**: 10時間（3フェーズ）

**Co-Authored-By**: Claude Opus 4.6 <noreply@anthropic.com>
