#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_gpu.py
GPU 96件の source_url 補完 + MSI UUID ID 修正 + ASUS length_mm 補完
"""

import json, pathlib, sys, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

_ROOT = pathlib.Path(__file__).parent.parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# MSI クリーンアップ
# ─────────────────────────────────────────────────────────────────────────────

# 重複UUID（既存の msi_ レコードと同一製品）→ 削除
MSI_DUPLICATE_IDS = {
    'b7131668c8b1',  # RTX 5090 32G LIGHTNING Z
    '72dce161f6f0',  # RTX 3050 LP E 6G OC
    'ca8604eaa957',  # RTX 5070 Ti 16G VENTUS 3X PZ OC
    '4bcf36a440f3',  # RTX 5060 Ti 8G VENTUS 2X OC CLASSIC
    'c1f45884e35c',  # RTX 5050 8G VENTUS 2X OC
}

# 新規UUID（固有モデル）→ proper msi_ IDに改名
MSI_UUID_RENAME = {
    'caebfa788510': 'msi_geforce-rtx-5060-ti-16g-ventus-2x-oc-white-plus',
    'fb6daa15f435': 'msi_geforce-rtx-5060-8g-inspire-itx-oc',
    '4f754a85d890': 'msi_geforce-rtx-5060-8g-gaming-oc',
    'a248f5db4f17': 'msi_geforce-rtx-5060-ti-16g-gaming-trio-oc',
    '57f790741a0b': 'msi_geforce-rtx-5060-ti-16g-gaming-oc',
    '004371f20131': 'msi_geforce-rtx-5060-ti-16g-ventus-2x-oc-plus',
    '2fc1fbca6d24': 'msi_geforce-rtx-5060-ti-8g-gaming-trio-oc',
}

# ─────────────────────────────────────────────────────────────────────────────
# length_mm 補完（ASUS 2件のみ）
# ─────────────────────────────────────────────────────────────────────────────

LENGTH_FIX = {
    'asus_asus-tuf-gaming-geforce-rtx-5060-ti-8gb-gddr7-oc-edition': 216,
    'asus_rog-astral-geforce-rtx-5090-32gb-gddr7-oc-edition':        354,
}

# ─────────────────────────────────────────────────────────────────────────────
# source_url 補完マップ  id → (data_dir, url)
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_URL_MAP = {

    # ── ASRock (16件) ─────────────────────────────────────────────────────
    'asrock_asrock-radeon-rx-9060-xt-challenger-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209060%20XT%20Challenger%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9060-xt-steel-legend-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209060%20XT%20Steel%20Legend%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9060-xt-steel-legend-8gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209060%20XT%20Steel%20Legend%208GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9070-challenger-16g':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20Challenger%2016G/index.asp'),
    'asrock_asrock-radeon-rx-9070-steel-legend-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20Steel%20Legend%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9070-xt-challenger-16g':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20XT%20Challenger%2016G/index.asp'),
    'asrock_asrock-radeon-rx-9070-xt-steel-legend-16g':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20XT%20Steel%20Legend%2016G/index.asp'),
    'asrock_asrock-radeon-rx-9070-xt-steel-legend-dark-16g':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20XT%20Steel%20Legend%20Dark%2016G/index.asp'),
    'asrock_asrock-radeon-rx-9070-xt-taichi-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20XT%20Taichi%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9070-xt-taichi-white-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20XT%20Taichi%20White%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-ai-pro-r9700-creator-32gb':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20AI%20PRO%20R9700%20Creator%2032GB/index.asp'),
    'asrock_asrock-intel-arc-a770-phantom-gaming-d-8gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/Intel/Arc%20A770%20Phantom%20Gaming%20D%208GB%20OC/index.asp'),
    'asrock_asrock-intel-arc-a750-challenger-se-8gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/Intel/Arc%20A750%20Challenger%20SE%208GB%20OC/index.asp'),
    'asrock_asrock-intel-arc-a770-challenger-se-16gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/Intel/Arc%20A770%20Challenger%20SE%2016GB%20OC/index.asp'),
    'asrock_asrock-radeon-rx-9060-xt-challenger-16g':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209060%20XT%20Challenger%2016G/index.asp'),
    'asrock_asrock-radeon-rx-7600-challenger-8gb-oc':
        ('asrock', 'https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%207600%20Challenger%208GB%20OC/index.asp'),

    # ── ASUS (12件) ──────────────────────────────────────────────────────
    'asus_asus-tuf-gaming-radeon-rx-9060-xt-oc-edition-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/tuf-gaming/tuf-rx9060xt-o16g-gaming/'),
    'asus_asus-prime-radeon-rx-9060-xt-o16g-oc-edition-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/prime/prime-rx9060xt-o16g/'),
    'asus_asus-dual-radeon-rx-9060-xt-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/dual/dual-rx9060xt-16g/'),
    'asus_asus-dual-radeon-rx-9060-xt-16gb-gddr6-white':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/dual/dual-rx9060xt-16g-white/'),
    'asus_asus-tuf-gaming-radeon-rx-9070-oc-edition-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/tuf-gaming/tuf-rx9070-o16g-gaming/'),
    'asus_asus-prime-radeon-rx-9070-xt-o16g-oc-edition-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/prime/prime-rx9070xt-o16g/'),
    'asus_asus-tuf-gaming-radeon-rx-9070-xt-oc-edition-16gb-gddr6':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/tuf-gaming/tuf-rx9070xt-o16g-gaming/'),
    'asus_asus-prime-geforce-rtx-5070-ti-16gb-gddr7':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/prime/prime-rtx5070ti-16g/'),
    'asus_asus-prime-geforce-rtx-5080-o16g-16gb-gddr7':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/prime/prime-rtx5080-o16g/'),
    'asus_asus-geforce-rtx-5080-16gb-gddr7-noctua-oc-edition':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/asus/rtx5080-o16g-noctua/'),
    'asus_asus-geforce-gt-710-2gb-gddr5-silent':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/all-series/gt710-sl-2gd5-brk-evo/'),
    'asus_asus-geforce-gt-730-2gb-gddr5-4hdmi':
        ('asus', 'https://www.asus.com/jp/motherboards-components/graphics-cards/all-series/gt730-4h-sl-2gd5/'),

    # ── Gainward (1件) ────────────────────────────────────────────────────
    'gainward_gainward-geforce-rtx-5070-phoenix-12gb-gddr7':
        ('gainward', 'https://www.gainward.com/main/vgapro.php?id=NE75070019K9-GB2050X'),

    # ── GIGABYTE (14件) ───────────────────────────────────────────────────
    'gigabyte_gigabyte-radeon-rx-9060-xt-gaming-oc-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-R9060XTGAMING-OC-16GD'),
    'gigabyte_gigabyte-radeon-rx-9060-xt-gaming-oc-8g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-R9060XTGAMING-OC-8GD'),
    'gigabyte_gigabyte-radeon-rx-9070-gaming-oc-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-R9070GAMING-OC-16GD'),
    'gigabyte_gigabyte-geforce-rtx-5050-gaming-oc-8g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5050GAMING-OC-8GD'),
    'gigabyte_gigabyte-geforce-rtx-5050-oc-low-profile-8g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5050OC-8GL'),
    'gigabyte_gigabyte-geforce-rtx-5050-windforce-2x-oc-8g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5050WF2OC-8GD'),
    'gigabyte_gigabyte-geforce-rtx-5060-windforce-2x-max-oc-8g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5060WF2MAX-OC-8GD'),
    'gigabyte_gigabyte-geforce-rtx-5060-ti-windforce-2x-max-oc-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N506TWF2MAX-OC-16GD'),
    'gigabyte_gigabyte-geforce-rtx-5070-aero-oc-12g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5070AERO-OC-12GD'),
    'gigabyte_gigabyte-geforce-rtx-5070-gaming-oc-12g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5070GAMING-OC-12GD'),
    'gigabyte_gigabyte-geforce-rtx-5080-aero-oc-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5080AERO-OC-16GD'),
    'gigabyte_gigabyte-geforce-rtx-5080-aorus-master-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N5080AORUS-M-16GD'),
    'gigabyte_gigabyte-geforce-rtx-5070-ti-eagle-oc-sff-16g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N507TEAGLE-OC-16GD'),
    'gigabyte_gigabyte-geforce-rtx-3050-windforce-2x-oc-v2-6g':
        ('gigabyte', 'https://www.gigabyte.com/jp/Graphics-Card/GV-N3050WF2OCV2-6GD'),

    # ── Intel (1件) ───────────────────────────────────────────────────────
    'intel_intel-arc-a770-16gb':
        ('intel', 'https://www.intel.com/content/www/us/en/products/sku/229150/intel-arc-a770-graphics-16gb/specifications.html'),

    # ── 玄人志向 (6件) ───────────────────────────────────────────────────
    'kuroutoshikou_rd-rx9070xt-e16gb-tp-radeon-rx-9070-xt-16gb':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/rd-rx9070xt-e16gbt/'),
    'kuroutoshikou_gg-rtx5060ti-e16gb-lineage-ii-geforce-rtx-5060-ti-16gb':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/gg-rtx5060ti-e16gb-lineage-ii/'),
    'kuroutoshikou_gg-rtx5060ti-e8gb-oc-df-v2-geforce-rtx-5060-ti-8gb':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/gg-rtx5060ti-e8gb-oc-df-v2/'),
    'kuroutoshikou_gk-rtx5060ti-e8gb-white-df-v2-geforce-rtx-5060-ti-8gb-white':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/gk-rtx5060ti-e8gb-white-df-v2/'),
    'kuroutoshikou_rd-rx6400-e4gb-lp-radeon-rx-6400-4gb-lp':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/rd-rx6400-e4gb-lp/'),
    'kuroutoshikou_gf-gt710-e1gb-hs-geforce-gt-710-1gb':
        ('kuroutoshikou', 'https://www.kuroutoshikou.com/product/detail/gf-gt710-e1gb-hs/'),

    # ── MSI (5件 ※ msi_msi- 形式) ───────────────────────────────────────
    'msi_msi-geforce-rtx-5070-12g-ventus-2x-oc-white':
        ('msi', 'https://jp.msi.com/Graphics-Card/GeForce-RTX-5070-12G-VENTUS-2X-OC-WHITE'),
    'msi_msi-geforce-rtx-3050-ventus-2x-e-6g-oc':
        ('msi', 'https://jp.msi.com/Graphics-Card/GeForce-RTX-3050-VENTUS-2X-E-6G-OC'),
    'msi_msi-geforce-gt-710-2gd3h-4hdmi':
        ('msi', 'https://jp.msi.com/Graphics-Card/GeForce-GT-710-2GD3H-4HDMI'),
    'msi_msi-geforce-gt-710-2gd3h-lp':
        ('msi', 'https://jp.msi.com/Graphics-Card/GeForce-GT-710-2GD3H-LP'),
    'msi_msi-geforce-gt-1030-2gd4-lp-oc':
        ('msi', 'https://jp.msi.com/Graphics-Card/GeForce-GT-1030-2GD4-LP-OC'),

    # ── Palit (17件) ──────────────────────────────────────────────────────
    'palit_palit-geforce-rtx-5060-dual-8gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75060019P1-GB2063D'),
    'palit_palit-geforce-rtx-5060-white-oc-8gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75060U19P1-GB2063M'),
    'palit_palit-geforce-rtx-5060-ti-dual-8gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7506T019P1-GB2062D'),
    'palit_palit-geforce-rtx-5060-ti-infinity-3-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7506T019T1-GB2061S'),
    'palit_palit-geforce-rtx-5060-ti-infinity-3-oc-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7506TS19T1-GB2061S'),
    'palit_palit-geforce-rtx-5060-ti-white-oc-8gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7506TU19P1-GB2062M'),
    'palit_palit-geforce-rtx-5060-ti-white-oc-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7506TU19T1-GB2061M'),
    'palit_palit-geforce-rtx-5070-infinity-3-12gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75070019K9-GB2050S'),
    'palit_palit-geforce-rtx-5070-infinity-3-oc-12gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75070S19K9-GB2050S'),
    'palit_palit-geforce-rtx-5070-white-oc-12gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75070U19K9-GB2050W'),
    'palit_palit-geforce-rtx-5070-ti-gamingpro-s-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7507T019T2-GB2031U'),
    'palit_palit-geforce-rtx-5070-ti-gamingpro-s-oc-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE7507TS19T2-GB2031U'),
    'palit_palit-geforce-rtx-5080-gamingpro-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75080019T2-GB2031A'),
    'palit_palit-geforce-rtx-5080-gamingpro-oc-16gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75080S19T2-GB2031A'),
    'palit_palit-geforce-rtx-5090-gamerock-32gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75090019R5-GB2020G'),
    'palit_palit-geforce-rtx-5090-gamerock-oc-32gb-gddr7':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE75090S19R5-GB2020G'),
    'palit_palit-geforce-rtx-3050-stormx-6gb-gddr6':
        ('palit', 'https://www.palit.com/palit/vgapro.php?id=NE63050018JE-1072F'),

    # ── PNY (3件) ──────────────────────────────────────────────────────
    'pny_pny-geforce-rtx-5060-8gb-overclocked-dualfan':
        ('pny', 'https://www.pny.com/en-apac/GeForce-RTX-5060-8GB-Overclocked-Edition-Dual-Fan-Graphics-Card'),
    'pny_pny-geforce-rtx-5060-ti-16gb-overclocked-dualfan':
        ('pny', 'https://www.pny.com/en-apac/GeForce-RTX-5060-Ti-16GB-Overclocked-Edition-Dual-Fan-Graphics-Card'),
    'pny_pny-geforce-rtx-5070-12gb-overclocked-triplefan':
        ('pny', 'https://www.pny.com/en-apac/GeForce-RTX-5070-12GB-Overclocked-Edition-Triple-Fan-Graphics-Card'),

    # ── PowerColor (3件) ─────────────────────────────────────────────────
    'powercolor_powercolor-radeon-rx-9060-xt-hellhound-16gb-gddr6-oc':
        ('powercolor', 'https://www.powercolor.com/rdna4-rx9060xt-hellhound'),
    'powercolor_powercolor-radeon-rx-9060-xt-hellhound-spectral-white-16gb-oc':
        ('powercolor', 'https://www.powercolor.com/rdna4-rx9060xt-hellhound-spectral-white'),
    'powercolor_powercolor-red-devil-spectral-white-radeon-rx-9070-xt-16gb-gddr6':
        ('powercolor', 'https://www.powercolor.com/rdna4-rx9070xt-red-devil-spectral-white'),

    # ── SAPPHIRE (7件) ────────────────────────────────────────────────────
    'sapphire_sapphire-nitro-radeon-rx-9060-xt-gaming-oc-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/nitro-rx-9060-xt-gaming-oc-16g-gddr6'),
    'sapphire_sapphire-pulse-radeon-rx-9060-xt-gaming-oc-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pulse-rx-9060-xt-gaming-oc-16g-gddr6'),
    'sapphire_sapphire-pulse-radeon-rx-9060-xt-gaming-oc-8gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pulse-rx-9060-xt-gaming-oc-8g-gddr6'),
    'sapphire_sapphire-pure-radeon-rx-9060-xt-gaming-oc-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pure-rx-9060-xt-gaming-oc-16g-gddr6'),
    'sapphire_sapphire-pulse-radeon-rx-9070-gaming-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pulse-rx-9070-gaming-16g-gddr6'),
    'sapphire_sapphire-pulse-radeon-rx-9070-xt-gaming-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pulse-rx-9070-xt-gaming-16g-gddr6'),
    'sapphire_sapphire-pure-radeon-rx-9070-xt-gaming-oc-16gb-gddr6':
        ('sapphire', 'https://www.sapphiretech.com/en/consumer/pure-rx-9070-xt-gaming-oc-16g-gddr6'),

    # ── SPARKLE (10件) ────────────────────────────────────────────────────
    'sparkle_sparkle-intel-arc-b570-guardian-oc-10gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-B570-GUARDIAN-OC-10GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-b570-guardian-luna-oc-10gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-B570-GUARDIAN-Luna-OC-10GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-b580-roc-luna-oc-12gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-B580-ROC-Luna-OC-12GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-b580-titan-luna-oc-12gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-B580-TITAN-Luna-OC-12GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-b580-titan-oc-12gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-B580-TITAN-OC-12GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-pro-b60-24gb-gddr6-blower':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-Pro-B60-24GB-GDDR6-Blower/'),
    'sparkle_sparkle-intel-arc-a380-genie-6gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-A380-GENIE-6GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-a750-titan-oc-8gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-A750-TITAN-OC-8GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-a310-eco-4gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-A310-ECO-4GB-GDDR6/'),
    'sparkle_sparkle-intel-arc-a380-elf-6gb-gddr6':
        ('sparkle', 'https://www.sparkle.com.tw/Products/VGA/SPARKLE-Intel-Arc-A380-ELF-6GB-GDDR6/'),

    # ── ZOTAC (1件) ───────────────────────────────────────────────────────
    'zotac_zotac-gaming-geforce-rtx-5080-solid-core-oc-16gb-gddr7':
        ('zotac', 'https://www.zotac.com/jp/product/graphics_card/zotac-gaming-geforce-rtx-5080-solid-core-oc-16gb-gddr7'),
}

# ─────────────────────────────────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────────────────────────────────

def load_jsonl(data_dir):
    path = _ROOT / 'workspace' / 'data' / data_dir / 'products.jsonl'
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def save_jsonl(data_dir, records):
    path = _ROOT / 'workspace' / 'data' / data_dir / 'products.jsonl'
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

# ─────────────────────────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────────────────────────

def run(dry_run=True):
    print('=' * 70)
    print(f"GPU source_url補完 / MSIクリーンアップ  {'[DRY-RUN]' if dry_run else '[APPLY]'}")
    print('=' * 70)

    all_records = {}  # data_dir → list[dict]
    results = {'url_ok': 0, 'url_skip': 0, 'len_ok': 0,
               'msi_dup_removed': 0, 'msi_renamed': 0, 'not_found': 0}

    # ── A: MSI クリーンアップ ──────────────────────────────────────────────
    print('\n【A】MSI UUID形式ID クリーンアップ')
    if 'msi' not in all_records:
        all_records['msi'] = load_jsonl('msi')
    msi_records = all_records['msi']

    # 重複削除
    before = len(msi_records)
    if not dry_run:
        msi_records = [r for r in msi_records if r['id'] not in MSI_DUPLICATE_IDS]
    dup_count = len([r for r in msi_records if r['id'] in MSI_DUPLICATE_IDS]) if dry_run else 0
    removed = before - len(msi_records) if not dry_run else len(MSI_DUPLICATE_IDS)
    print(f'  重複削除: {removed}件 (Lightning Z, 3050 LP, 5070Ti VENTUS, 5060Ti VENTUS, 5050 VENTUS)')
    results['msi_dup_removed'] = removed

    # UUID → proper ID 改名
    renamed = 0
    for rec in msi_records:
        if rec['id'] in MSI_UUID_RENAME:
            new_id = MSI_UUID_RENAME[rec['id']]
            print(f'  改名: {rec["id"]} -> {new_id}')
            print(f'        {rec["name"]}')
            if not dry_run:
                rec['id'] = new_id
            renamed += 1
    print(f'  改名: {renamed}件')
    results['msi_renamed'] = renamed
    if not dry_run:
        all_records['msi'] = msi_records

    # ── B: length_mm 補完 (ASUS 2件) ──────────────────────────────────────
    print('\n【B】length_mm 補完 (ASUS 2件)')
    if 'asus' not in all_records:
        all_records['asus'] = load_jsonl('asus')
    for pid, mm in LENGTH_FIX.items():
        target = next((r for r in all_records['asus'] if r['id'] == pid), None)
        if not target:
            print(f'  {pid}: レコードなし')
            results['not_found'] += 1
            continue
        cur = target.get('specs', {}).get('length_mm')
        print(f'  {target["name"][:50]:50s}  {cur} -> {mm} mm')
        if not dry_run:
            target.setdefault('specs', {})['length_mm'] = mm
        results['len_ok'] += 1

    # ── C: source_url 補完 (96件) ─────────────────────────────────────────
    print('\n【C】source_url 補完')
    for pid, (data_dir, url) in SOURCE_URL_MAP.items():
        if data_dir not in all_records:
            all_records[data_dir] = load_jsonl(data_dir)
        target = next((r for r in all_records[data_dir] if r['id'] == pid), None)
        if not target:
            print(f'  NOT FOUND: {pid}')
            results['not_found'] += 1
            continue
        if target.get('source_url'):
            results['url_skip'] += 1
            continue
        print(f'  {target["name"][:55]:55s}  -> OK')
        if not dry_run:
            target['source_url'] = url
        results['url_ok'] += 1

    # ── 保存 ──────────────────────────────────────────────────────────────
    if not dry_run:
        for data_dir, records in all_records.items():
            save_jsonl(data_dir, records)
            print(f'\n  -> {data_dir}/products.jsonl 保存')

    # ── サマリー ──────────────────────────────────────────────────────────
    print('\n' + '=' * 70)
    print(f"【サマリー】{'DRY-RUN' if dry_run else 'APPLY完了'}")
    print(f"  MSI重複削除:  {results['msi_dup_removed']}件")
    print(f"  MSI ID改名:   {results['msi_renamed']}件")
    print(f"  length_mm補完: {results['len_ok']}件")
    print(f"  source_url設定: {results['url_ok']}件")
    print(f"  既設定(skip):  {results['url_skip']}件")
    print(f"  not_found:     {results['not_found']}件")
    if dry_run:
        print('\n  --apply を付けて再実行すると実際に更新されます')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    run(dry_run=not args.apply)
