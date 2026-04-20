#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
価格変動アラートツイート生成（実データ）
diff_logs から過去14日間の値下げTOP5を抽出
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SITE_URL = 'https://pc-jisaku.com'
DIFF_LOGS_DIR = Path(__file__).parent.parent / 'workspace' / 'data' / 'diff_logs'

CATEGORY_LABEL = {
    'gpu': 'GPU',
    'cpu': 'CPU',
    'mb': 'マザーボード',
    'ram': 'メモリ',
    'psu': '電源',
    'case': 'ケース',
    'cooler': 'クーラー',
}

CATEGORY_EMOJI = {
    'gpu': '🎮',
    'cpu': '💻',
    'mb': '🔌',
    'ram': '🧠',
    'psu': '⚡',
    'case': '📦',
    'cooler': '❄️',
}


def shorten_product_name(name, max_len=40):
    """製品名を読みやすく短縮"""
    name = re.sub(r'\[.*?\]', '', name).strip()
    name = re.sub(r'\s+', ' ', name)
    if len(name) > max_len:
        name = name[:max_len - 1] + '…'
    return name


def load_recent_drops(days=14):
    """直近N日のdiff_logsから値下げ情報を集計"""
    if not DIFF_LOGS_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})-(gpu|cpu|mb|ram|psu|case|cooler)\.jsonl$')

    best_per_product = {}

    for f in sorted(DIFF_LOGS_DIR.glob('*.jsonl')):
        m = pattern.match(f.name)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), '%Y-%m-%d')
        except ValueError:
            continue
        if file_date < cutoff:
            continue

        with open(f, 'r', encoding='utf-8') as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get('type') != 'price_changed':
                    continue
                old_p = entry.get('old_price')
                new_p = entry.get('new_price')
                if not (isinstance(old_p, (int, float)) and isinstance(new_p, (int, float))):
                    continue
                if old_p <= 0 or new_p <= 0:
                    continue
                drop = old_p - new_p
                if drop <= 0:
                    continue

                pid = entry.get('id')
                if not pid:
                    continue

                current = best_per_product.get(pid)
                if current is None or drop > current['drop']:
                    best_per_product[pid] = {
                        'id': pid,
                        'name': entry.get('name', ''),
                        'category': entry.get('category', ''),
                        'old_price': old_p,
                        'new_price': new_p,
                        'drop': drop,
                        'drop_pct': drop / old_p * 100,
                        'date': file_date,
                    }

    return list(best_per_product.values())


EXCLUDE_KEYWORDS = [
    'Threadripper', 'EPYC', 'Xeon',
    'RTX 5000 Ada', 'RTX 6000', 'RTX A',
    'Quadro', 'Tesla',
    'RTX PRO', 'RTXPRO',
    'SUPERMICRO', 'Supermicro',
    'GT 1030', 'GT 710',
    'GTX 10', 'GTX 9', 'GTX 16',
    'RTX 20', 'RTX 30',
    'RX 5', 'RX 6',
    'i3-', 'i5-10', 'i5-11', 'i5-12',
    'Ryzen 3 ', 'Ryzen 5 3', 'Ryzen 5 5',
]


def _is_excluded(name):
    normalized = re.sub(r'\s+', '', name.lower())
    for kw in EXCLUDE_KEYWORDS:
        kw_norm = re.sub(r'\s+', '', kw.lower())
        if kw_norm in normalized:
            return True
    return False


def pick_top_drops(drops, top_n=5, min_drop_pct=5.0, max_drop_pct=50.0,
                   min_price=5000, max_price=200000):
    """上位の値下げ抽出。異常値・業務向け・旧世代を除外"""
    candidates = [
        d for d in drops
        if min_drop_pct <= d['drop_pct'] <= max_drop_pct
        and min_price <= d['old_price'] <= max_price
        and not _is_excluded(d.get('name', ''))
    ]
    candidates.sort(key=lambda d: d['drop'], reverse=True)

    picked = []
    seen_categories = {}
    for d in candidates:
        cat_count = seen_categories.get(d['category'], 0)
        if cat_count >= 2:
            continue
        picked.append(d)
        seen_categories[d['category']] = cat_count + 1
        if len(picked) >= top_n:
            break

    if len(picked) < top_n:
        remaining = [d for d in candidates if d not in picked]
        for d in remaining:
            picked.append(d)
            if len(picked) >= top_n:
                break

    return picked


def format_price(n):
    return f"¥{int(n):,}"


def generate_price_alert_tweet():
    """値下げアラート型ツイートを生成。データ不足ならNoneを返す。
    戻り値: (tweet_text, pattern_type, top_items) または (None, None, None)
    """
    drops = load_recent_drops(days=14)
    top = pick_top_drops(drops, top_n=5)

    if len(top) < 3:
        return None, None, None

    total_savings = sum(d['drop'] for d in top)
    today = datetime.now().strftime('%m/%d')

    lines = []
    lines.append(f"【⚡値下げ速報】{today}朝の狙い目パーツ")
    lines.append("")
    lines.append("過去2週間の価格変動から")
    lines.append('"今が買い時"を厳選しました。')
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 大幅値下げTOP{len(top)}")
    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append("")

    for i, d in enumerate(top, 1):
        emoji = CATEGORY_EMOJI.get(d['category'], '📌')
        cat_label = CATEGORY_LABEL.get(d['category'], d['category'])
        name = shorten_product_name(d['name'], max_len=36)
        lines.append(f"{i}. {emoji} {name}")
        lines.append(f"   {format_price(d['old_price'])} → {format_price(d['new_price'])} (▼{format_price(d['drop'])})")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"合計で{format_price(total_savings)}お得。")
    lines.append("互換性チェックは下から↓")
    lines.append(SITE_URL)
    lines.append("")
    lines.append("#自作PC #PCパーツ")

    tweet_text = '\n'.join(lines)
    return tweet_text, 'price_alert', top


if __name__ == '__main__':
    text, pattern, items = generate_price_alert_tweet()
    if text is None:
        print("[NG] 値下げデータ不足")
        sys.exit(1)
    print(f"[型: {pattern}]")
    print(text)
    print(f"\n文字数: {len(text)}")
    print(f"アイテム数: {len(items)}")
