"""ゲーム別ページ416件のtitle/descriptionをSEO最適化するスクリプト

変更内容:
1. title: 「{ゲーム名} 推奨スペック・必要動作環境【2026年版】| pc-jisaku.com」
2. description: ゲームごとにユニークな文言（推奨GPU情報を含む）
3. og:title/og:description も同様に更新
"""
import os
import re
import glob

GAME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'game')

def extract_game_name(html):
    """HTMLからゲーム名を抽出"""
    m = re.search(r'<title>\s*(.+?)\s*推奨スペック', html)
    if m:
        return m.group(1).strip()
    return None

def extract_recommended_gpu(html):
    """HTMLから推奨GPUを抽出"""
    m = re.search(r'推奨スペックは.*?GPU:\s*([^,、]+)', html)
    if m:
        gpu = m.group(1).strip()
        # HTMLタグ除去
        gpu = re.sub(r'<[^>]+>', '', gpu)
        return gpu
    return None

def extract_recommended_cpu(html):
    """HTMLから推奨CPUを抽出"""
    m = re.search(r'CPU:\s*([^,、]+)', html)
    if m:
        cpu = m.group(1).strip()
        cpu = re.sub(r'<[^>]+>', '', cpu)
        return cpu
    return None

def extract_recommended_ram(html):
    """HTMLからRAMを抽出"""
    m = re.search(r'RAM:\s*(\d+\s*GB)', html)
    if m:
        return m.group(1).strip()
    return None

def optimize_page(filepath):
    """1ページを最適化"""
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    game_name = extract_game_name(html)
    if not game_name:
        return False, "ゲーム名抽出失敗"

    gpu = extract_recommended_gpu(html) or ""
    cpu = extract_recommended_cpu(html) or ""
    ram = extract_recommended_ram(html) or ""

    # --- title最適化 ---
    old_title_pattern = r'<title>.*?</title>'
    new_title = f'<title>{game_name} 推奨スペック・必要動作環境【2026年最新】| pc-jisaku.com</title>'
    html = re.sub(old_title_pattern, new_title, html, count=1)

    # --- description最適化 ---
    # GPUが取れたらユニークなdescription生成
    if gpu:
        short_gpu = gpu.split('/')[0].strip()[:40]  # 最初のGPUのみ、40文字以内
        new_desc = (
            f'{game_name}の推奨スペックと必要動作環境を徹底解説【2026年最新】。'
            f'推奨GPU: {short_gpu}。'
            f'予算別おすすめPC構成やfps目安、パーツの互換性もAIが無料で即診断。'
        )
    else:
        new_desc = (
            f'{game_name}の推奨スペックと必要動作環境【2026年最新】。'
            f'予算別おすすめPC構成やfps目安、パーツの互換性もAIが無料で即診断。'
        )

    # description置換
    old_desc_pattern = r'<meta name="description" content="[^"]*">'
    new_desc_tag = f'<meta name="description" content="{new_desc}">'
    html = re.sub(old_desc_pattern, new_desc_tag, html, count=1)

    # --- og:title最適化 ---
    old_og_title = r'<meta property="og:title" content="[^"]*">'
    new_og_title = f'<meta property="og:title" content="{game_name} 推奨スペック【2026年最新】| pc-jisaku.com">'
    html = re.sub(old_og_title, new_og_title, html, count=1)

    # --- og:description最適化 ---
    old_og_desc = r'<meta property="og:description" content="[^"]*">'
    new_og_desc = f'<meta property="og:description" content="{new_desc[:120]}">'
    html = re.sub(old_og_desc, new_og_desc, html, count=1)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return True, game_name

def main():
    files = sorted(glob.glob(os.path.join(GAME_DIR, '*.html')))
    print(f"対象ファイル: {len(files)}件")

    ok = 0
    fail = 0
    for fp in files:
        success, info = optimize_page(fp)
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL: {os.path.basename(fp)} - {info}")

    print(f"\n完了: {ok}件成功, {fail}件失敗")

if __name__ == '__main__':
    main()
