#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec_verifier/config.py
製品ごとの公式URL・スペック抽出パターン定義

フェーズ1: ケース（15件）
フェーズ2: PSU（15件）
フェーズ3: GPU card_length_mm（96件）
"""

# ─────────────────────────────────────────────────────────────────────────────
# フェーズ1: ケース
# ─────────────────────────────────────────────────────────────────────────────

CASE_PRODUCTS = {

    # ── NZXT ──
    "nzxt_nzxt-h510": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h510",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィックス.*?(\d{3})\s*mm", r"(?:Max\.?|最大).*?GPU.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm", r"クーラー.*?高さ.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "nzxt_nzxt-h200i": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h200i",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィックス.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "nzxt_nzxt-h9-flow": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h9-flow",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィックス.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "nzxt_nzxt-h3-flow": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h3-flow",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィックス.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "nzxt_nzxt-h2-flow": {
        "data_dir": "cases",
        "source_url": "https://nzxt.com/ja-JP/product/h2-flow",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィックス.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },

    # ── Cooler Master ──
    "coolermaster_mastercase-h500": {
        "data_dir": "coolermaster_cases",
        "source_url": "https://www.coolermaster.com/jp/products/mastercase-h500/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィック.*?(\d{3})\s*mm", r"VGA.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPUクーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "coolermaster_haf-500": {
        "data_dir": "coolermaster_cases",
        "source_url": "https://www.coolermaster.com/jp/products/haf-500/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"VGA.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPUクーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "coolermaster_masterbox-td500-mesh-v2": {
        "data_dir": "coolermaster_cases",
        "source_url": "https://www.coolermaster.com/jp/products/masterbox-td500-mesh-v2/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"VGA.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPUクーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "coolermaster_masterbox-q300l": {
        "data_dir": "coolermaster_cases",
        "source_url": "https://www.coolermaster.com/jp/products/masterbox-q300l/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"VGA.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPUクーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "coolermaster_silencio-s600": {
        "data_dir": "coolermaster_cases",
        "source_url": "https://www.coolermaster.com/jp/products/silencio-s600/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"VGA.*?(\d{3})\s*mm"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPUクーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },

    # ── Fractal Design ──
    "fractal_define-7": {
        "data_dir": "fractal_cases",
        "source_url": "https://www.fractal-design.com/products/cases/define/define-7/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"グラフィック.*?(\d{3})\s*mm", r"Maximum GPU length.*?(\d{3})"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm", r"Cooler height.*?(\d{2,3})"], "range": (50, 250)},
        },
    },
    "fractal_define-7-xl": {
        "data_dir": "fractal_cases",
        "source_url": "https://www.fractal-design.com/products/cases/define/define-7-xl/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"Maximum GPU length.*?(\d{3})"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "fractal_north": {
        "data_dir": "fractal_cases",
        "source_url": "https://www.fractal-design.com/products/cases/north/north/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"Maximum GPU length.*?(\d{3})"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "fractal_torrent": {
        "data_dir": "fractal_cases",
        "source_url": "https://www.fractal-design.com/products/cases/torrent/torrent/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"Maximum GPU length.*?(\d{3})"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
    "fractal_meshify-2": {
        "data_dir": "fractal_cases",
        "source_url": "https://www.fractal-design.com/products/cases/meshify/meshify-2/",
        "spec_fields": {
            "max_gpu_length_mm":        {"patterns": [r"GPU.*?(\d{3})\s*mm", r"Maximum GPU length.*?(\d{3})"], "range": (100, 600)},
            "max_cpu_cooler_height_mm": {"patterns": [r"CPU.*?クーラー.*?(\d{2,3})\s*mm", r"CPU\s*Cooler.*?(\d{2,3})\s*mm"], "range": (50, 250)},
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# フェーズ2: PSU
# ─────────────────────────────────────────────────────────────────────────────

PSU_PRODUCTS = {

    # ── Corsair ──
    "corsair_rm850x-2021": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/psu/cp-9020200-jp/rm850x-shift-fully-modular-atx-power-supply-cp-9020200-jp",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W", r"定格出力.*?(\d{3,4})\s*W", r"Wattage.*?(\d{3,4})"], "range": (300, 2000)},
        },
    },
    "corsair_rm1000x-2021": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/psu/cp-9020201-jp/rm1000x-shift-fully-modular-atx-power-supply-cp-9020201-jp",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W", r"定格出力.*?(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "corsair_rm750x-2021": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/psu/cp-9020199-jp/rm750x-shift-fully-modular-atx-power-supply-cp-9020199-jp",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "corsair_hx1200": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/psu/cp-9020140-jp/hx1200-high-performance-atx-power-supply-cp-9020140-jp",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "corsair_rm1200x-shift": {
        "data_dir": "corsair_psu",
        "source_url": "https://www.corsair.com/jp/ja/p/psu/cp-9020254-jp/rm1200x-shift-fully-modular-atx-power-supply-cp-9020254-jp",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },

    # ── Seasonic ──
    "seasonic_focus-gx-850": {
        "data_dir": "seasonic_psu",
        "source_url": "https://www.seasonic.com/focus-gx-850",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W", r"Output Power.*?(\d{3,4})"], "range": (300, 2000)},
        },
    },
    "seasonic_focus-gx-750": {
        "data_dir": "seasonic_psu",
        "source_url": "https://www.seasonic.com/focus-gx-750",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "seasonic_focus-gx-650": {
        "data_dir": "seasonic_psu",
        "source_url": "https://www.seasonic.com/focus-gx-650",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "seasonic_focus-gx-1000": {
        "data_dir": "seasonic_psu",
        "source_url": "https://www.seasonic.com/focus-gx-1000",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "seasonic_prime-tx-850": {
        "data_dir": "seasonic_psu",
        "source_url": "https://www.seasonic.com/prime-tx-850",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },

    # ── SilverStone ──
    "silverstone_sx700-pt": {
        "data_dir": "silverstone_psu",
        "source_url": "https://www.silverstonetek.com/jp/product/info/power-supplies/SX700-PT/",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W", r"Output.*?(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "silverstone_sx600-g": {
        "data_dir": "silverstone_psu",
        "source_url": "https://www.silverstonetek.com/jp/product/info/power-supplies/SX600-G/",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "silverstone_et750-g": {
        "data_dir": "silverstone_psu",
        "source_url": "https://www.silverstonetek.com/jp/product/info/power-supplies/ET750-G/",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "silverstone_da850-gold": {
        "data_dir": "silverstone_psu",
        "source_url": "https://www.silverstonetek.com/jp/product/info/power-supplies/DA850-Gold/",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
    "silverstone_strider-titanium-1100w": {
        "data_dir": "silverstone_psu",
        "source_url": "https://www.silverstonetek.com/jp/product/info/power-supplies/ST1100-TI/",
        "spec_fields": {
            "wattage_w": {"patterns": [r"(\d{3,4})\s*W"], "range": (300, 2000)},
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 統合マップ（フェーズ指定で参照）
# ─────────────────────────────────────────────────────────────────────────────

PHASE_CONFIG = {
    1: CASE_PRODUCTS,
    2: PSU_PRODUCTS,
}
