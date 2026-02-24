#!/usr/bin/env python3
"""
expand_data_v2.py — 110件 → 150件 データ拡充
追加:
  CPUクーラー ×15: Corsair iCUE ×5 / DeepCool ×5 / be quiet! ×5
  マザーボード ×15: ASUS ROG ×5 / MSI MAG ×5 / GIGABYTE AORUS ×5
  Intel CPU    ×10: Core Ultra 200S 非K系 (LGA1851)
"""
import json, os, re

BASE = os.path.join(os.path.dirname(__file__), '..', 'workspace', 'data')
NOW  = "2026-02-24T00:00:00+00:00"

SOCKETS_COMMON = ["AM5", "AM4", "LGA1851", "LGA1700", "LGA1200"]


# ────────────────────────────────────────────────
# ヘルパー
# ────────────────────────────────────────────────
def make_id(maker, name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return f"{maker}_{slug}"

def load_ids(path):
    ids = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.add(json.loads(line)['id'])
    return ids

def append_records(dirpath, records):
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, 'products.jsonl')
    existing = load_ids(path)
    added = 0
    with open(path, 'a', encoding='utf-8') as f:
        for r in records:
            if r['id'] not in existing:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
                added += 1
                existing.add(r['id'])
    label = os.path.relpath(dirpath, BASE)
    print(f"  {label}: +{added} 件")
    return added


# ────────────────────────────────────────────────
# レコード生成ヘルパー
# ────────────────────────────────────────────────
def cooler_record(maker, name, source_url,
                  height_mm, side_clearance_mm, sockets,
                  fan_size_mm, tdp_rating_w=None,
                  cooler_type="air", radiator_size_mm=None):
    specs = {
        "type": cooler_type,
        "height_mm": height_mm,
        "socket_support": sockets,
        "fan_size_mm": fan_size_mm,
        "tdp_rating_w": tdp_rating_w,
    }
    if side_clearance_mm is not None:
        specs["side_clearance_mm"] = side_clearance_mm
    if radiator_size_mm is not None:
        specs["radiator_size_mm"] = radiator_size_mm
    return {
        "id": make_id(maker, name),
        "name": name, "maker": maker, "category": "cpu_cooler",
        "source_url": source_url,
        "manual_url": None, "manual_path": None, "manual_scraped_at": None,
        "created_at": NOW,
        "specs": specs,
    }


def mb_record(maker, name, source_url,
              socket, chipset, form_factor, m2_slots, max_memory_gb,
              memory_type="DDR5", memory_slots=4,
              sata_ports=4, power_connector="1 x 8 pin"):
    return {
        "id": make_id(maker, name),
        "name": name, "maker": maker, "category": "motherboard",
        "source_url": source_url,
        "manual_url": None, "manual_path": None, "manual_scraped_at": None,
        "created_at": NOW,
        "specs": {
            "socket": socket,
            "chipset": chipset,
            "form_factor": form_factor,
            "m2_slots": m2_slots,
            "max_memory_gb": max_memory_gb,
            "memory_type": memory_type,
            "memory_slots": memory_slots,
            "sata_ports": sata_ports,
            "power_connector": power_connector,
        },
    }


def cpu_record(maker, name, source_url,
               socket, cores, p_cores, e_cores, threads,
               base_clock_ghz, boost_clock_ghz, tdp_w, max_turbo_power_w,
               memory_type, max_memory_speed_mhz, max_memory_gb,
               integrated_gpu, igpu_model, pcie_version, l3_cache_mb):
    return {
        "id": make_id(maker, name),
        "name": name, "maker": maker, "category": "cpu",
        "source_url": source_url,
        "manual_url": None, "manual_path": None, "manual_scraped_at": None,
        "created_at": NOW,
        "specs": {
            "socket": socket,
            "cores": cores, "p_cores": p_cores, "e_cores": e_cores, "threads": threads,
            "base_clock_ghz": base_clock_ghz,
            "boost_clock_ghz": boost_clock_ghz,
            "tdp_w": tdp_w,
            "max_turbo_power_w": max_turbo_power_w,
            "memory_type": memory_type,
            "max_memory_speed_mhz": max_memory_speed_mhz,
            "max_memory_gb": max_memory_gb,
            "integrated_gpu": integrated_gpu,
            "igpu_model": igpu_model,
            "pcie_version": pcie_version,
            "l3_cache_mb": l3_cache_mb,
        },
    }


# ════════════════════════════════════════════════
# データ定義
# ════════════════════════════════════════════════

# ── Corsair iCUE CPUクーラー ×5 ──────────────────────────
CORSAIR_COOLERS = [
    cooler_record(
        "corsair", "iCUE H150i Elite LCD XT",
        "https://www.corsair.com/jp/ja/p/cooling/cw-9060065-ww/icue-h150i-elite-lcd-xt-liquid-cpu-cooler-cw-9060065-ww",
        height_mm=42, side_clearance_mm=None, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=350, cooler_type="aio", radiator_size_mm=360,
    ),
    cooler_record(
        "corsair", "iCUE H100i Elite LCD XT",
        "https://www.corsair.com/jp/ja/p/cooling/cw-9060064-ww/icue-h100i-elite-lcd-xt-liquid-cpu-cooler-cw-9060064-ww",
        height_mm=42, side_clearance_mm=None, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=300, cooler_type="aio", radiator_size_mm=240,
    ),
    cooler_record(
        "corsair", "iCUE H115i Elite LCD XT",
        "https://www.corsair.com/jp/ja/p/cooling/cw-9060066-ww/icue-h115i-elite-lcd-xt-liquid-cpu-cooler-cw-9060066-ww",
        height_mm=42, side_clearance_mm=None, sockets=SOCKETS_COMMON,
        fan_size_mm=140, tdp_rating_w=320, cooler_type="aio", radiator_size_mm=280,
    ),
    cooler_record(
        "corsair", "iCUE H170i Elite LCD XT",
        "https://www.corsair.com/jp/ja/p/cooling/cw-9060067-ww/icue-h170i-elite-lcd-xt-liquid-cpu-cooler-cw-9060067-ww",
        height_mm=42, side_clearance_mm=None, sockets=SOCKETS_COMMON,
        fan_size_mm=140, tdp_rating_w=400, cooler_type="aio", radiator_size_mm=420,
    ),
    cooler_record(
        "corsair", "A115",
        "https://www.corsair.com/jp/ja/p/cooling/ct-9010004-ww/a115-low-noise-high-performance-dual-140mm-fan-cpu-cooler-ct-9010004-ww",
        height_mm=163, side_clearance_mm=56, sockets=SOCKETS_COMMON,
        fan_size_mm=140, tdp_rating_w=300, cooler_type="air",
    ),
]

# ── DeepCool CPUクーラー ×5 ──────────────────────────────
DEEPCOOL_COOLERS = [
    cooler_record(
        "deepcool", "AK620",
        "https://www.deepcool.com/products/Cooling/cpuaircooler/AK620-High-Performance-CPU-Cooler/2021/12932.shtml",
        height_mm=160, side_clearance_mm=60, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=260, cooler_type="air",
    ),
    cooler_record(
        "deepcool", "AK620 Digital",
        "https://www.deepcool.com/products/Cooling/cpuaircooler/AK620-Digital/2022/14199.shtml",
        height_mm=160, side_clearance_mm=60, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=260, cooler_type="air",
    ),
    cooler_record(
        "deepcool", "AK400",
        "https://www.deepcool.com/products/Cooling/cpuaircooler/AK400/2022/13673.shtml",
        height_mm=155, side_clearance_mm=45, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=220, cooler_type="air",
    ),
    cooler_record(
        "deepcool", "ASSASSIN IV",
        "https://www.deepcool.com/products/Cooling/cpuaircooler/ASSASSIN-IV/2023/16013.shtml",
        height_mm=168, side_clearance_mm=66, sockets=SOCKETS_COMMON,
        fan_size_mm=140, tdp_rating_w=280, cooler_type="air",
    ),
    cooler_record(
        "deepcool", "MYSTIQUE 360",
        "https://www.deepcool.com/products/Cooling/liquidcooler/MYSTIQUE-360/2023/16231.shtml",
        height_mm=40, side_clearance_mm=None, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=350, cooler_type="aio", radiator_size_mm=360,
    ),
]

# ── be quiet! CPUクーラー ×5 ─────────────────────────────
BEQUIET_COOLERS = [
    cooler_record(
        "bequiet", "Pure Rock 2",
        "https://www.bequiet.com/en/cpucooler/2916",
        height_mm=155, side_clearance_mm=27, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=150, cooler_type="air",
    ),
    cooler_record(
        "bequiet", "Pure Rock 2 FX",
        "https://www.bequiet.com/en/cpucooler/4041",
        height_mm=155, side_clearance_mm=27, sockets=SOCKETS_COMMON,
        fan_size_mm=120, tdp_rating_w=150, cooler_type="air",
    ),
    cooler_record(
        "bequiet", "Dark Rock 4",
        "https://www.bequiet.com/en/cpucooler/1376",
        height_mm=159, side_clearance_mm=40, sockets=SOCKETS_COMMON,
        fan_size_mm=135, tdp_rating_w=200, cooler_type="air",
    ),
    cooler_record(
        "bequiet", "Dark Rock Pro 4",
        "https://www.bequiet.com/en/cpucooler/1375",
        height_mm=163, side_clearance_mm=40, sockets=SOCKETS_COMMON,
        fan_size_mm=135, tdp_rating_w=250, cooler_type="air",
    ),
    cooler_record(
        "bequiet", "Dark Rock Elite",
        "https://www.bequiet.com/en/cpucooler/3786",
        height_mm=168, side_clearance_mm=59, sockets=SOCKETS_COMMON,
        fan_size_mm=135, tdp_rating_w=280, cooler_type="air",
    ),
]

# ── ASUS ROG マザーボード ×5 ─────────────────────────────
ASUS_MBS = [
    mb_record(
        "asus", "ROG MAXIMUS Z890 APEX",
        "https://rog.asus.com/motherboards/rog-maximus/rog-maximus-z890-apex/",
        socket="LGA1851", chipset="Z890", form_factor="EATX",
        m2_slots=5, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "asus", "ROG STRIX Z890-F GAMING WIFI",
        "https://rog.asus.com/motherboards/rog-strix/rog-strix-z890-f-gaming-wifi/",
        socket="LGA1851", chipset="Z890", form_factor="ATX",
        m2_slots=5, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "asus", "ROG STRIX B860-F GAMING WIFI",
        "https://rog.asus.com/motherboards/rog-strix/rog-strix-b860-f-gaming-wifi/",
        socket="LGA1851", chipset="B860", form_factor="ATX",
        m2_slots=4, max_memory_gb=192, memory_slots=4,
        sata_ports=4, power_connector="1 x 8 pin",
    ),
    mb_record(
        "asus", "ROG CROSSHAIR X870E HERO",
        "https://rog.asus.com/motherboards/rog-crosshair/rog-crosshair-x870e-hero/",
        socket="AM5", chipset="X870E", form_factor="ATX",
        m2_slots=5, max_memory_gb=256, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "asus", "ROG STRIX X870-F GAMING WIFI",
        "https://rog.asus.com/motherboards/rog-strix/rog-strix-x870-f-gaming-wifi/",
        socket="AM5", chipset="X870", form_factor="ATX",
        m2_slots=4, max_memory_gb=256, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
]

# ── MSI MAG マザーボード ×5 ──────────────────────────────
MSI_MBS = [
    mb_record(
        "msi", "MAG Z890 TOMAHAWK WIFI",
        "https://www.msi.com/Motherboard/MAG-Z890-TOMAHAWK-WIFI",
        socket="LGA1851", chipset="Z890", form_factor="ATX",
        m2_slots=5, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "msi", "MAG Z890 CARBON WIFI",
        "https://www.msi.com/Motherboard/MAG-Z890-CARBON-WIFI",
        socket="LGA1851", chipset="Z890", form_factor="ATX",
        m2_slots=5, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "msi", "MAG B860 TOMAHAWK WIFI",
        "https://www.msi.com/Motherboard/MAG-B860-TOMAHAWK-WIFI",
        socket="LGA1851", chipset="B860", form_factor="ATX",
        m2_slots=4, max_memory_gb=192, memory_slots=4,
        sata_ports=4, power_connector="1 x 8 pin",
    ),
    mb_record(
        "msi", "MAG X870 TOMAHAWK WIFI",
        "https://www.msi.com/Motherboard/MAG-X870-TOMAHAWK-WIFI",
        socket="AM5", chipset="X870", form_factor="ATX",
        m2_slots=4, max_memory_gb=256, memory_slots=4,
        sata_ports=4, power_connector="2 x 8 pin",
    ),
    mb_record(
        "msi", "MAG B850 TOMAHAWK WIFI",
        "https://www.msi.com/Motherboard/MAG-B850-TOMAHAWK-WIFI",
        socket="AM5", chipset="B850", form_factor="ATX",
        m2_slots=4, max_memory_gb=256, memory_slots=4,
        sata_ports=4, power_connector="1 x 8 pin",
    ),
]

# ── GIGABYTE AORUS マザーボード ×5 ───────────────────────
GIGABYTE_MBS = [
    mb_record(
        "gigabyte", "Z890 AORUS MASTER",
        "https://www.gigabyte.com/Motherboard/Z890-AORUS-MASTER",
        socket="LGA1851", chipset="Z890", form_factor="EATX",
        m2_slots=6, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "gigabyte", "Z890 AORUS ELITE WIFI7",
        "https://www.gigabyte.com/Motherboard/Z890-AORUS-ELITE-WIFI7",
        socket="LGA1851", chipset="Z890", form_factor="ATX",
        m2_slots=5, max_memory_gb=192, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "gigabyte", "B860 AORUS ELITE WIFI7",
        "https://www.gigabyte.com/Motherboard/B860-AORUS-ELITE-WIFI7",
        socket="LGA1851", chipset="B860", form_factor="ATX",
        m2_slots=4, max_memory_gb=192, memory_slots=4,
        sata_ports=4, power_connector="1 x 8 pin",
    ),
    mb_record(
        "gigabyte", "X870E AORUS MASTER",
        "https://www.gigabyte.com/Motherboard/X870E-AORUS-MASTER",
        socket="AM5", chipset="X870E", form_factor="ATX",
        m2_slots=6, max_memory_gb=256, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
    mb_record(
        "gigabyte", "X870 AORUS ELITE WIFI7",
        "https://www.gigabyte.com/Motherboard/X870-AORUS-ELITE-WIFI7",
        socket="AM5", chipset="X870", form_factor="ATX",
        m2_slots=4, max_memory_gb=256, memory_slots=4,
        sata_ports=6, power_connector="2 x 8 pin",
    ),
]

# ── Intel Core Ultra 200S 非K (LGA1851) ×10 ─────────────
# 65W TDP (通常版) / 35W TDP (T 省電力版)
INTEL_CPUS_EXTRA = [
    # ── 65W 通常版 ────────────────────────────
    cpu_record(
        "intel", "Intel Core Ultra 9 285",
        "https://ark.intel.com/content/www/us/en/ark/products/240484/intel-core-ultra-9-processor-285-36m-cache-up-to-5-60-ghz.html",
        socket="LGA1851", cores=24, p_cores=8, e_cores=16, threads=24,
        base_clock_ghz=3.7, boost_clock_ghz=5.6, tdp_w=65, max_turbo_power_w=250,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 800",
        pcie_version="5.0", l3_cache_mb=36,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 7 265",
        "https://ark.intel.com/content/www/us/en/ark/products/240483/intel-core-ultra-7-processor-265-30m-cache-up-to-5-40-ghz.html",
        socket="LGA1851", cores=20, p_cores=8, e_cores=12, threads=20,
        base_clock_ghz=3.9, boost_clock_ghz=5.4, tdp_w=65, max_turbo_power_w=250,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 770",
        pcie_version="5.0", l3_cache_mb=30,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 7 265F",
        "https://ark.intel.com/content/www/us/en/ark/products/240480/intel-core-ultra-7-processor-265f-30m-cache-up-to-5-40-ghz.html",
        socket="LGA1851", cores=20, p_cores=8, e_cores=12, threads=20,
        base_clock_ghz=3.9, boost_clock_ghz=5.4, tdp_w=65, max_turbo_power_w=250,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=False, igpu_model=None,
        pcie_version="5.0", l3_cache_mb=30,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 5 245",
        "https://ark.intel.com/content/www/us/en/ark/products/240477/intel-core-ultra-5-processor-245-24m-cache-up-to-5-00-ghz.html",
        socket="LGA1851", cores=14, p_cores=6, e_cores=8, threads=14,
        base_clock_ghz=4.2, boost_clock_ghz=5.0, tdp_w=65, max_turbo_power_w=159,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 770",
        pcie_version="5.0", l3_cache_mb=24,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 5 245F",
        "https://ark.intel.com/content/www/us/en/ark/products/240474/intel-core-ultra-5-processor-245f-24m-cache-up-to-5-00-ghz.html",
        socket="LGA1851", cores=14, p_cores=6, e_cores=8, threads=14,
        base_clock_ghz=4.2, boost_clock_ghz=5.0, tdp_w=65, max_turbo_power_w=159,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=False, igpu_model=None,
        pcie_version="5.0", l3_cache_mb=24,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 5 235",
        "https://ark.intel.com/content/www/us/en/ark/products/240472/intel-core-ultra-5-processor-235-24m-cache-up-to-4-80-ghz.html",
        socket="LGA1851", cores=14, p_cores=6, e_cores=8, threads=14,
        base_clock_ghz=3.8, boost_clock_ghz=4.8, tdp_w=65, max_turbo_power_w=115,
        memory_type=["DDR5"], max_memory_speed_mhz=6000, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 770",
        pcie_version="5.0", l3_cache_mb=24,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 3 215",
        "https://ark.intel.com/content/www/us/en/ark/products/240470/intel-core-ultra-3-processor-215-12m-cache-up-to-4-60-ghz.html",
        socket="LGA1851", cores=12, p_cores=4, e_cores=8, threads=12,
        base_clock_ghz=3.4, boost_clock_ghz=4.6, tdp_w=58, max_turbo_power_w=115,
        memory_type=["DDR5"], max_memory_speed_mhz=5600, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 710",
        pcie_version="5.0", l3_cache_mb=12,
    ),
    # ── 35W 省電力版 (T suffix) ────────────────
    cpu_record(
        "intel", "Intel Core Ultra 9 285T",
        "https://ark.intel.com/content/www/us/en/ark/products/240486/intel-core-ultra-9-processor-285t-36m-cache-up-to-5-50-ghz.html",
        socket="LGA1851", cores=24, p_cores=8, e_cores=16, threads=24,
        base_clock_ghz=3.0, boost_clock_ghz=5.5, tdp_w=35, max_turbo_power_w=250,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 800",
        pcie_version="5.0", l3_cache_mb=36,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 7 265T",
        "https://ark.intel.com/content/www/us/en/ark/products/240485/intel-core-ultra-7-processor-265t-30m-cache-up-to-5-30-ghz.html",
        socket="LGA1851", cores=20, p_cores=8, e_cores=12, threads=20,
        base_clock_ghz=2.9, boost_clock_ghz=5.3, tdp_w=35, max_turbo_power_w=115,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 770",
        pcie_version="5.0", l3_cache_mb=30,
    ),
    cpu_record(
        "intel", "Intel Core Ultra 5 245T",
        "https://ark.intel.com/content/www/us/en/ark/products/240478/intel-core-ultra-5-processor-245t-24m-cache-up-to-4-90-ghz.html",
        socket="LGA1851", cores=14, p_cores=6, e_cores=8, threads=14,
        base_clock_ghz=3.2, boost_clock_ghz=4.9, tdp_w=35, max_turbo_power_w=115,
        memory_type=["DDR5"], max_memory_speed_mhz=6400, max_memory_gb=192,
        integrated_gpu=True, igpu_model="Intel Graphics 770",
        pcie_version="5.0", l3_cache_mb=24,
    ),
]


# ════════════════════════════════════════════════
# メイン
# ════════════════════════════════════════════════
def main():
    total = 0
    print("=== CPUクーラー ===")
    total += append_records(os.path.join(BASE, 'corsair_cooler'), CORSAIR_COOLERS)
    total += append_records(os.path.join(BASE, 'deepcool_cooler'), DEEPCOOL_COOLERS)
    total += append_records(os.path.join(BASE, 'bequiet_cooler'), BEQUIET_COOLERS)

    print("=== マザーボード ===")
    total += append_records(os.path.join(BASE, 'asus_mb'), ASUS_MBS)
    total += append_records(os.path.join(BASE, 'msi_mb'), MSI_MBS)
    total += append_records(os.path.join(BASE, 'gigabyte_mb'), GIGABYTE_MBS)

    print("=== Intel CPU (LGA1851 非K) ===")
    total += append_records(os.path.join(BASE, 'intel_cpu'), INTEL_CPUS_EXTRA)

    print(f"\n合計 +{total} 件追加")

    # 全件カウント
    total_all = 0
    for root, dirs, files in os.walk(BASE):
        for fn in files:
            if fn == 'products.jsonl':
                with open(os.path.join(root, fn), encoding='utf-8') as f:
                    total_all += sum(1 for l in f if l.strip())
    print(f"全件数: {total_all} 件")


if __name__ == '__main__':
    main()
