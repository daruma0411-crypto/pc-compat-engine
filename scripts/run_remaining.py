"""ケース・PSU・クーラーを順番実行"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import kakaku_scraper_case  as case_mod
import kakaku_scraper_psu   as psu_mod
import kakaku_scraper_cooler as cooler_mod

for label, mod in [('ケース', case_mod), ('PSU', psu_mod), ('CPUクーラー', cooler_mod)]:
    print(f'\n{"="*55}')
    print(f'【{label}】スクレイプ開始')
    print(f'{"="*55}')
    mod.main()

print('\n全カテゴリ完了')
