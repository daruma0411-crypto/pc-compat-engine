#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTO products.jsonl のアフィリエイトURL一括設定ツール

使い方:
  1. 下の AFFILIATE_CONFIG にA8.net/ValueCommerce等のプログラム情報を入力
  2. python scripts/set_bto_affiliate_urls.py を実行
  3. products.jsonl が更新される

A8.net URL形式:
  https://px.a8.net/svt/ejp?a8mat={A8MAT_ID}&a8ejpredirect={encoded_url}

ValueCommerce URL形式:
  https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={SID}&pid={PID}&vc_url={encoded_url}
"""
import json
import urllib.parse
from pathlib import Path

# ======= ここを編集 =======
AFFILIATE_CONFIG = {
    # A8.net プログラムID (a8mat値)
    # A8.net管理画面 > 参加中プログラム > プログラム詳細 で確認
    'dospara_a8mat': '',     # ドスパラのA8 a8mat値
    'koubou_a8mat': '',      # パソコン工房のA8 a8mat値
    'sycom_a8mat': '',       # サイコムのA8 a8mat値

    # ValueCommerce (sid は全プログラム共通、pid はプログラム別)
    'vc_sid': '3764551',     # ValueCommerce SID (既存データから取得済み)
    'hp_vc_pid': '',         # HPのValueCommerce PID

    # LinkShare (Dell)
    'dell_linkshare_id': '', # DellのLinkShare プログラムID
}
# ==========================

PRODUCTS_FILE = Path(__file__).parent.parent / 'workspace' / 'data' / 'bto' / 'products.jsonl'


def make_a8_url(a8mat: str, dest_url: str) -> str:
    """A8.netアフィリエイトURL生成"""
    if not a8mat:
        return ''
    encoded = urllib.parse.quote(dest_url, safe='')
    return f'https://px.a8.net/svt/ejp?a8mat={a8mat}&a8ejpredirect={encoded}'


def make_vc_url(sid: str, pid: str, dest_url: str) -> str:
    """ValueCommerceアフィリエイトURL生成"""
    if not sid or not pid:
        return ''
    encoded = urllib.parse.quote(dest_url, safe='')
    return f'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={sid}&pid={pid}&vc_url={encoded}'


def main():
    cfg = AFFILIATE_CONFIG
    products = []
    updated = 0

    with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))

    for p in products:
        aff = p.get('affiliate', {})
        # 既にURLが設定済みならスキップ
        if aff.get('url'):
            continue

        maker = p.get('maker', '')
        dest_url = p.get('url', '')
        new_url = ''

        if maker == 'ドスパラ' and cfg['dospara_a8mat']:
            new_url = make_a8_url(cfg['dospara_a8mat'], dest_url)
        elif maker == 'パソコン工房' and cfg['koubou_a8mat']:
            new_url = make_a8_url(cfg['koubou_a8mat'], dest_url)
        elif maker == 'サイコム' and cfg['sycom_a8mat']:
            new_url = make_a8_url(cfg['sycom_a8mat'], dest_url)
        elif maker == 'HP' and cfg['hp_vc_pid']:
            new_url = make_vc_url(cfg['vc_sid'], cfg['hp_vc_pid'], dest_url)

        if new_url:
            aff['url'] = new_url
            p['affiliate'] = aff
            updated += 1
            print(f'  ✅ {p["id"]}: {maker} → URL設定完了')

    if updated > 0:
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + '\n')
        print(f'\n✅ {updated}件のアフィリエイトURL更新完了')
    else:
        print('\n⚠️ 更新対象なし（AFFILIATE_CONFIG にプログラムIDを設定してください）')
        print('\n設定が必要な項目:')
        if not cfg['dospara_a8mat']:
            print('  - dospara_a8mat: A8.net管理画面 > ドスパラのプログラムID')
        if not cfg['koubou_a8mat']:
            print('  - koubou_a8mat: A8.net管理画面 > パソコン工房のプログラムID')
        if not cfg['sycom_a8mat']:
            print('  - sycom_a8mat: A8.net管理画面 > サイコムのプログラムID')
        if not cfg['hp_vc_pid']:
            print('  - hp_vc_pid: ValueCommerce管理画面 > HPのプログラムPID')


if __name__ == '__main__':
    main()
