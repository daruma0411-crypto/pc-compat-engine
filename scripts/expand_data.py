"""
データ拡充スクリプト — 150件 → 200件
使い方: python scripts/expand_data.py [--apply]
"""
import json
import os
import sys

WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'workspace', 'data')
APPLY = '--apply' in sys.argv
TS = '2026-02-24T00:00:00+00:00'

def _rec(id_, name, maker, category, specs, source_url=None):
    return {
        'id': id_, 'name': name, 'maker': maker, 'category': category,
        'source_url': source_url, 'manual_url': None, 'manual_path': None,
        'manual_scraped_at': None, 'created_at': TS, 'specs': specs,
    }

# ──────────────────────────────────────────────────────────────────
# 1. AMD Ryzen 7000 シリーズ (AM5 / DDR5) × 5
# ──────────────────────────────────────────────────────────────────
AMD_7000 = [
    _rec('amd_amd-ryzen-9-7950x', 'AMD Ryzen 9 7950X', 'amd', 'cpu',
         {'model':'Ryzen 9 7950X','socket':'AM5','cores':16,'p_cores':16,'e_cores':0,
          'threads':32,'base_clock_ghz':4.5,'boost_clock_ghz':5.7,'tdp_w':170,
          'max_turbo_power_w':230,'memory_type':['DDR5'],'max_memory_speed_mhz':5200,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':64},
         'https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7950x.html'),
    _rec('amd_amd-ryzen-9-7900x', 'AMD Ryzen 9 7900X', 'amd', 'cpu',
         {'model':'Ryzen 9 7900X','socket':'AM5','cores':12,'p_cores':12,'e_cores':0,
          'threads':24,'base_clock_ghz':4.7,'boost_clock_ghz':5.6,'tdp_w':170,
          'max_turbo_power_w':230,'memory_type':['DDR5'],'max_memory_speed_mhz':5200,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':64},
         'https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7900x.html'),
    _rec('amd_amd-ryzen-7-7700x', 'AMD Ryzen 7 7700X', 'amd', 'cpu',
         {'model':'Ryzen 7 7700X','socket':'AM5','cores':8,'p_cores':8,'e_cores':0,
          'threads':16,'base_clock_ghz':4.5,'boost_clock_ghz':5.4,'tdp_w':105,
          'max_turbo_power_w':142,'memory_type':['DDR5'],'max_memory_speed_mhz':5200,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':32},
         'https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700x.html'),
    _rec('amd_amd-ryzen-5-7600x', 'AMD Ryzen 5 7600X', 'amd', 'cpu',
         {'model':'Ryzen 5 7600X','socket':'AM5','cores':6,'p_cores':6,'e_cores':0,
          'threads':12,'base_clock_ghz':4.7,'boost_clock_ghz':5.3,'tdp_w':105,
          'max_turbo_power_w':142,'memory_type':['DDR5'],'max_memory_speed_mhz':5200,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':32},
         'https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600x.html'),
    _rec('amd_amd-ryzen-5-7600', 'AMD Ryzen 5 7600', 'amd', 'cpu',
         {'model':'Ryzen 5 7600','socket':'AM5','cores':6,'p_cores':6,'e_cores':0,
          'threads':12,'base_clock_ghz':3.8,'boost_clock_ghz':5.1,'tdp_w':65,
          'max_turbo_power_w':88,'memory_type':['DDR5'],'max_memory_speed_mhz':5200,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':32},
         'https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600.html'),
]

# ──────────────────────────────────────────────────────────────────
# 2. Intel Core 第14世代 (LGA1700 / DDR4 or DDR5) × 5
# ──────────────────────────────────────────────────────────────────
INTEL_14GEN = [
    _rec('intel_intel-core-i9-14900k', 'Intel Core i9-14900K', 'intel', 'cpu',
         {'model':'Core i9-14900K','socket':'LGA1700','cores':24,'p_cores':8,'e_cores':16,
          'threads':32,'base_clock_ghz':3.2,'boost_clock_ghz':6.0,'tdp_w':125,
          'max_turbo_power_w':253,'memory_type':['DDR4','DDR5'],'max_memory_speed_mhz':5600,
          'max_memory_gb':128,'integrated_gpu':True,'igpu_model':'Intel UHD 770',
          'pcie_version':'5.0','l3_cache_mb':36},
         'https://ark.intel.com/content/www/us/en/ark/products/236773/intel-core-i9-processor-14900k-36m-cache-up-to-6-00-ghz.html'),
    _rec('intel_intel-core-i9-14900kf', 'Intel Core i9-14900KF', 'intel', 'cpu',
         {'model':'Core i9-14900KF','socket':'LGA1700','cores':24,'p_cores':8,'e_cores':16,
          'threads':32,'base_clock_ghz':3.2,'boost_clock_ghz':6.0,'tdp_w':125,
          'max_turbo_power_w':253,'memory_type':['DDR4','DDR5'],'max_memory_speed_mhz':5600,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':36},
         'https://ark.intel.com/content/www/us/en/ark/products/236774/intel-core-i9-processor-14900kf-36m-cache-up-to-6-00-ghz.html'),
    _rec('intel_intel-core-i7-14700k', 'Intel Core i7-14700K', 'intel', 'cpu',
         {'model':'Core i7-14700K','socket':'LGA1700','cores':20,'p_cores':8,'e_cores':12,
          'threads':28,'base_clock_ghz':3.4,'boost_clock_ghz':5.6,'tdp_w':125,
          'max_turbo_power_w':253,'memory_type':['DDR4','DDR5'],'max_memory_speed_mhz':5600,
          'max_memory_gb':128,'integrated_gpu':True,'igpu_model':'Intel UHD 770',
          'pcie_version':'5.0','l3_cache_mb':33},
         'https://ark.intel.com/content/www/us/en/ark/products/236782/intel-core-i7-processor-14700k-33m-cache-up-to-5-60-ghz.html'),
    _rec('intel_intel-core-i5-14600k', 'Intel Core i5-14600K', 'intel', 'cpu',
         {'model':'Core i5-14600K','socket':'LGA1700','cores':14,'p_cores':6,'e_cores':8,
          'threads':20,'base_clock_ghz':3.5,'boost_clock_ghz':5.3,'tdp_w':125,
          'max_turbo_power_w':181,'memory_type':['DDR4','DDR5'],'max_memory_speed_mhz':5600,
          'max_memory_gb':128,'integrated_gpu':True,'igpu_model':'Intel UHD 770',
          'pcie_version':'5.0','l3_cache_mb':24},
         'https://ark.intel.com/content/www/us/en/ark/products/236796/intel-core-i5-processor-14600k-24m-cache-up-to-5-30-ghz.html'),
    _rec('intel_intel-core-i5-14600kf', 'Intel Core i5-14600KF', 'intel', 'cpu',
         {'model':'Core i5-14600KF','socket':'LGA1700','cores':14,'p_cores':6,'e_cores':8,
          'threads':20,'base_clock_ghz':3.5,'boost_clock_ghz':5.3,'tdp_w':125,
          'max_turbo_power_w':181,'memory_type':['DDR4','DDR5'],'max_memory_speed_mhz':5600,
          'max_memory_gb':128,'integrated_gpu':False,'igpu_model':None,
          'pcie_version':'5.0','l3_cache_mb':24},
         'https://ark.intel.com/content/www/us/en/ark/products/236797/intel-core-i5-processor-14600kf-24m-cache-up-to-5-30-ghz.html'),
]

# ──────────────────────────────────────────────────────────────────
# 3. Corsair DDR4 × 5
# ──────────────────────────────────────────────────────────────────
CORSAIR_DDR4 = [
    _rec('corsair_corsair-vengeance-lpx-ddr4-3200-32gb', 'Corsair Vengeance LPX DDR4-3200 32GB Kit (2x16GB)',
         'corsair', 'ram',
         {'model':'CMK32GX4M2E3200C16','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-36',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':31}),
    _rec('corsair_corsair-vengeance-lpx-ddr4-3600-32gb', 'Corsair Vengeance LPX DDR4-3600 32GB Kit (2x16GB)',
         'corsair', 'ram',
         {'model':'CMK32GX4M2D3600C18','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':31}),
    _rec('corsair_corsair-vengeance-lpx-ddr4-3200-16gb', 'Corsair Vengeance LPX DDR4-3200 16GB Kit (2x8GB)',
         'corsair', 'ram',
         {'model':'CMK16GX4M2E3200C16','memory_type':'DDR4','capacity_gb':16,'kit_count':2,
          'per_stick_gb':8,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-36',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':31}),
    _rec('corsair_corsair-vengeance-rgb-pro-ddr4-3600-32gb', 'Corsair Vengeance RGB Pro DDR4-3600 32GB Kit (2x16GB)',
         'corsair', 'ram',
         {'model':'CMW32GX4M2D3600C18','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':44}),
    _rec('corsair_corsair-vengeance-lpx-ddr4-3200-64gb', 'Corsair Vengeance LPX DDR4-3200 64GB Kit (2x32GB)',
         'corsair', 'ram',
         {'model':'CMK64GX4M2E3200C16','memory_type':'DDR4','capacity_gb':64,'kit_count':2,
          'per_stick_gb':32,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-36',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':31}),
]

# ──────────────────────────────────────────────────────────────────
# 4. G.Skill DDR4 × 5
# ──────────────────────────────────────────────────────────────────
GSKILL_DDR4 = [
    _rec('gskill_gskill-ripjaws-v-ddr4-3200-32gb', 'G.Skill Ripjaws V DDR4-3200 32GB Kit (2x16GB)',
         'gskill', 'ram',
         {'model':'F4-3200C16D-32GVK','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-38',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Red','height_mm':42}),
    _rec('gskill_gskill-ripjaws-v-ddr4-3600-32gb', 'G.Skill Ripjaws V DDR4-3600 32GB Kit (2x16GB)',
         'gskill', 'ram',
         {'model':'F4-3600C18D-32GVK','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Red','height_mm':42}),
    _rec('gskill_gskill-trident-z-rgb-ddr4-3600-32gb', 'G.Skill Trident Z RGB DDR4-3600 32GB Kit (2x16GB)',
         'gskill', 'ram',
         {'model':'F4-3600C18D-32GTZR','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black/Silver','height_mm':44}),
    _rec('gskill_gskill-ripjaws-v-ddr4-3200-16gb', 'G.Skill Ripjaws V DDR4-3200 16GB Kit (2x8GB)',
         'gskill', 'ram',
         {'model':'F4-3200C16D-16GVK','memory_type':'DDR4','capacity_gb':16,'kit_count':2,
          'per_stick_gb':8,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-38',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Red','height_mm':42}),
    _rec('gskill_gskill-trident-z-royal-ddr4-3600-32gb', 'G.Skill Trident Z Royal DDR4-3600 32GB Kit (2x16GB)',
         'gskill', 'ram',
         {'model':'F4-3600C18D-32GTRS','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Silver','height_mm':44}),
]

# ──────────────────────────────────────────────────────────────────
# 5. TeamGroup DDR4 × 5
# ──────────────────────────────────────────────────────────────────
TEAMGROUP_DDR4 = [
    _rec('teamgroup_teamgroup-t-force-vulcan-z-ddr4-3200-32gb',
         'TeamGroup T-Force Vulcan Z DDR4-3200 32GB Kit (2x16GB)', 'teamgroup', 'ram',
         {'model':'TLZGD432G3200HC16FDC01','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-38',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Gray','height_mm':31}),
    _rec('teamgroup_teamgroup-t-force-vulcan-z-ddr4-3600-32gb',
         'TeamGroup T-Force Vulcan Z DDR4-3600 32GB Kit (2x16GB)', 'teamgroup', 'ram',
         {'model':'TLZGD432G3600HC18JDC01','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-20-20-44',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Gray','height_mm':31}),
    _rec('teamgroup_teamgroup-t-force-delta-rgb-ddr4-3600-32gb',
         'TeamGroup T-Force Delta RGB DDR4-3600 32GB Kit (2x16GB)', 'teamgroup', 'ram',
         {'model':'TF3D432G3600HC18JDC01','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':18,'timings':'18-22-22-42',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Black','height_mm':44}),
    _rec('teamgroup_teamgroup-t-force-vulcan-z-ddr4-3200-16gb',
         'TeamGroup T-Force Vulcan Z DDR4-3200 16GB Kit (2x8GB)', 'teamgroup', 'ram',
         {'model':'TLZGD416G3200HC16FDC01','memory_type':'DDR4','capacity_gb':16,'kit_count':2,
          'per_stick_gb':8,'speed_mhz':3200,'cas_latency':16,'timings':'16-18-18-38',
          'voltage_v':1.35,'form_factor':'DIMM','xmp':True,'expo':False,'color':'Gray','height_mm':31}),
    _rec('teamgroup_teamgroup-t-force-xtreem-argb-ddr4-3600-32gb',
         'TeamGroup T-Force Xtreem ARGB DDR4-3600 32GB Kit (2x16GB)', 'teamgroup', 'ram',
         {'model':'TF10D432G3600HC14CDC01','memory_type':'DDR4','capacity_gb':32,'kit_count':2,
          'per_stick_gb':16,'speed_mhz':3600,'cas_latency':14,'timings':'14-15-15-35',
          'voltage_v':1.45,'form_factor':'DIMM','xmp':True,'expo':False,'color':'White','height_mm':44}),
]

# ──────────────────────────────────────────────────────────────────
# 6. Seasonic PSU × 5
# ──────────────────────────────────────────────────────────────────
SEASONIC_PSU = [
    _rec('seasonic_seasonic-focus-gx-850', 'Seasonic Focus GX-850', 'seasonic', 'psu',
         {'model':'FOCUS GX-850','wattage_w':850,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':150,'connector_12vhpwr':0,'connector_8pin_pcie':4}),
    _rec('seasonic_seasonic-focus-gx-750', 'Seasonic Focus GX-750', 'seasonic', 'psu',
         {'model':'FOCUS GX-750','wattage_w':750,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':140,'connector_12vhpwr':0,'connector_8pin_pcie':4}),
    _rec('seasonic_seasonic-focus-gx-650', 'Seasonic Focus GX-650', 'seasonic', 'psu',
         {'model':'FOCUS GX-650','wattage_w':650,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':140,'connector_12vhpwr':0,'connector_8pin_pcie':2}),
    _rec('seasonic_seasonic-focus-gx-1000', 'Seasonic Focus GX-1000', 'seasonic', 'psu',
         {'model':'FOCUS GX-1000','wattage_w':1000,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':160,'connector_12vhpwr':1,'connector_8pin_pcie':4}),
    _rec('seasonic_seasonic-prime-tx-850', 'Seasonic Prime TX-850', 'seasonic', 'psu',
         {'model':'PRIME TX-850','wattage_w':850,'form_factor':'ATX','efficiency_rating':'Titanium',
          'modular':True,'depth_mm':170,'connector_12vhpwr':0,'connector_8pin_pcie':6}),
]

# ──────────────────────────────────────────────────────────────────
# 7. SilverStone PSU × 5
# ──────────────────────────────────────────────────────────────────
SILVERSTONE_PSU = [
    _rec('silverstone_silverstone-sx700-pt', 'SilverStone SX700-PT', 'silverstone', 'psu',
         {'model':'SST-SX700-PT','wattage_w':700,'form_factor':'SFX-L','efficiency_rating':'Platinum',
          'modular':True,'depth_mm':130,'connector_12vhpwr':0,'connector_8pin_pcie':4}),
    _rec('silverstone_silverstone-sx600-g', 'SilverStone SX600-G', 'silverstone', 'psu',
         {'model':'SST-SX600-G','wattage_w':600,'form_factor':'SFX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':100,'connector_12vhpwr':0,'connector_8pin_pcie':2}),
    _rec('silverstone_silverstone-et750-g', 'SilverStone ET750-G', 'silverstone', 'psu',
         {'model':'SST-ET750-G','wattage_w':750,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':False,'depth_mm':140,'connector_12vhpwr':0,'connector_8pin_pcie':4}),
    _rec('silverstone_silverstone-da850-g', 'SilverStone DA850 Gold', 'silverstone', 'psu',
         {'model':'SST-DA850-G','wattage_w':850,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':160,'connector_12vhpwr':1,'connector_8pin_pcie':4}),
    _rec('silverstone_silverstone-st1100-ti', 'SilverStone Strider Titanium 1100W', 'silverstone', 'psu',
         {'model':'SST-ST1100-TI','wattage_w':1100,'form_factor':'ATX','efficiency_rating':'Titanium',
          'modular':True,'depth_mm':180,'connector_12vhpwr':0,'connector_8pin_pcie':6}),
]

# ──────────────────────────────────────────────────────────────────
# 8. Corsair PSU × 5
# ──────────────────────────────────────────────────────────────────
CORSAIR_PSU = [
    _rec('corsair_corsair-rm850x', 'Corsair RM850x (2021)', 'corsair', 'psu',
         {'model':'CP-9020201-JP','wattage_w':850,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':160,'connector_12vhpwr':0,'connector_8pin_pcie':6}),
    _rec('corsair_corsair-rm1000x', 'Corsair RM1000x (2021)', 'corsair', 'psu',
         {'model':'CP-9020210-JP','wattage_w':1000,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':160,'connector_12vhpwr':1,'connector_8pin_pcie':6}),
    _rec('corsair_corsair-rm750x', 'Corsair RM750x (2021)', 'corsair', 'psu',
         {'model':'CP-9020199-JP','wattage_w':750,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':160,'connector_12vhpwr':0,'connector_8pin_pcie':4}),
    _rec('corsair_corsair-hx1200', 'Corsair HX1200', 'corsair', 'psu',
         {'model':'CP-9020140-JP','wattage_w':1200,'form_factor':'ATX','efficiency_rating':'Platinum',
          'modular':True,'depth_mm':160,'connector_12vhpwr':0,'connector_8pin_pcie':8}),
    _rec('corsair_corsair-rm1200x-shift', 'Corsair RM1200x SHIFT', 'corsair', 'psu',
         {'model':'CP-9020254-JP','wattage_w':1200,'form_factor':'ATX','efficiency_rating':'Gold',
          'modular':True,'depth_mm':200,'connector_12vhpwr':2,'connector_8pin_pcie':8}),
]

# ──────────────────────────────────────────────────────────────────
# 9. Fractal Design ケース × 5
# ──────────────────────────────────────────────────────────────────
FRACTAL_CASES = [
    _rec('fractal_fractal-design-define-7', 'Fractal Design Define 7', 'fractal', 'case',
         {'model':'Define 7','max_gpu_length_mm':491,'max_cpu_cooler_height_mm':185,
          'form_factor':'ATX','max_psu_length_mm':250}),
    _rec('fractal_fractal-design-define-7-xl', 'Fractal Design Define 7 XL', 'fractal', 'case',
         {'model':'Define 7 XL','max_gpu_length_mm':503,'max_cpu_cooler_height_mm':185,
          'form_factor':'E-ATX','max_psu_length_mm':250}),
    _rec('fractal_fractal-design-north', 'Fractal Design North', 'fractal', 'case',
         {'model':'North','max_gpu_length_mm':355,'max_cpu_cooler_height_mm':170,
          'form_factor':'ATX','max_psu_length_mm':200}),
    _rec('fractal_fractal-design-torrent', 'Fractal Design Torrent', 'fractal', 'case',
         {'model':'Torrent','max_gpu_length_mm':461,'max_cpu_cooler_height_mm':188,
          'form_factor':'ATX','max_psu_length_mm':250}),
    _rec('fractal_fractal-design-meshify-2', 'Fractal Design Meshify 2', 'fractal', 'case',
         {'model':'Meshify 2','max_gpu_length_mm':467,'max_cpu_cooler_height_mm':185,
          'form_factor':'ATX','max_psu_length_mm':250}),
]

# ──────────────────────────────────────────────────────────────────
# 10. Cooler Master ケース × 5
# ──────────────────────────────────────────────────────────────────
COOLERMASTER_CASES = [
    _rec('coolermaster_coolermaster-mastercase-h500', 'Cooler Master MasterCase H500',
         'coolermaster', 'case',
         {'model':'MCM-H500-IGNN-S00','max_gpu_length_mm':410,'max_cpu_cooler_height_mm':167,
          'form_factor':'ATX','max_psu_length_mm':180}),
    _rec('coolermaster_coolermaster-haf-500', 'Cooler Master HAF 500',
         'coolermaster', 'case',
         {'model':'H500-IGNN-S00','max_gpu_length_mm':410,'max_cpu_cooler_height_mm':170,
          'form_factor':'ATX','max_psu_length_mm':180}),
    _rec('coolermaster_coolermaster-td500-mesh-v2', 'Cooler Master MasterBox TD500 Mesh V2',
         'coolermaster', 'case',
         {'model':'MCB-D500D-WGNN-S01','max_gpu_length_mm':410,'max_cpu_cooler_height_mm':165,
          'form_factor':'ATX','max_psu_length_mm':180}),
    _rec('coolermaster_coolermaster-masterbox-q300l', 'Cooler Master MasterBox Q300L',
         'coolermaster', 'case',
         {'model':'MCB-Q300L-KANN-S00','max_gpu_length_mm':360,'max_cpu_cooler_height_mm':157,
          'form_factor':'mATX','max_psu_length_mm':180}),
    _rec('coolermaster_coolermaster-silencio-s600', 'Cooler Master Silencio S600',
         'coolermaster', 'case',
         {'model':'MCS-S600-KN5N-S00','max_gpu_length_mm':410,'max_cpu_cooler_height_mm':160,
          'form_factor':'ATX','max_psu_length_mm':180}),
]

# ──────────────────────────────────────────────────────────────────
# 書き込み処理
# ──────────────────────────────────────────────────────────────────
APPEND_MAP = {
    'amd_cpu':   AMD_7000,
    'intel_cpu': INTEL_14GEN,
}
NEW_MAP = {
    'corsair_ddr4':       CORSAIR_DDR4,
    'gskill_ddr4':        GSKILL_DDR4,
    'teamgroup_ddr4':     TEAMGROUP_DDR4,
    'seasonic_psu':       SEASONIC_PSU,
    'silverstone_psu':    SILVERSTONE_PSU,
    'corsair_psu':        CORSAIR_PSU,
    'fractal_cases':      FRACTAL_CASES,
    'coolermaster_cases': COOLERMASTER_CASES,
}

total_new = 0
print('=== ドライラン ===' if not APPLY else '=== 適用モード ===')

for dirname, records in APPEND_MAP.items():
    path = os.path.join(WORKSPACE, dirname, 'products.jsonl')
    print(f'\n[追記] {dirname}/products.jsonl  +{len(records)}件')
    for r in records:
        print(f'  + {r["name"]}')
    if APPLY:
        with open(path, 'a', encoding='utf-8') as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    total_new += len(records)

for dirname, records in NEW_MAP.items():
    path = os.path.join(WORKSPACE, dirname, 'products.jsonl')
    print(f'\n[新規] {dirname}/products.jsonl  {len(records)}件')
    for r in records:
        print(f'  + {r["name"]}')
    if APPLY:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    total_new += len(records)

print(f'\n合計追加: {total_new}件')
if not APPLY:
    print('※ 実際に書き込むには --apply を指定してください')
