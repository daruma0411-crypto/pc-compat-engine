"""
MB・RAM データ拡充スクリプト
- ASUS/MSI/GIGABYTE MB: 各5件追加（Z790/B760 LGA1700） → 各10件
- RAM: Kingston DDR5×3 + Crucial DDR4×2 + Crucial DDR5×3 + TeamGroup DDR5×2 追加
"""
import json, os, hashlib
from datetime import datetime

NOW = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workspace", "data")


def make_id(maker: str, name: str) -> str:
    return hashlib.md5(f"{maker}:{name}".encode()).hexdigest()[:12]


def mb_record(maker, name, source_url, socket, chipset, form_factor,
              m2_slots, max_memory_gb, memory_type="DDR5", memory_slots=4,
              sata_ports=4, power_connector="1 x 8 pin"):
    return {
        "id": make_id(maker, name),
        "name": name,
        "maker": maker,
        "category": "motherboard",
        "source_url": source_url,
        "manual_url": "",
        "manual_path": "",
        "manual_scraped_at": "",
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


def ram_record(maker, name, source_url, memory_type, speed_mhz,
               capacity_gb, kit_count, cl_latency):
    return {
        "id": make_id(maker, name),
        "name": name,
        "maker": maker,
        "category": "ram",
        "source_url": source_url,
        "manual_url": "",
        "manual_path": "",
        "manual_scraped_at": "",
        "created_at": NOW,
        "specs": {
            "memory_type": memory_type,
            "speed_mhz": speed_mhz,
            "capacity_gb": capacity_gb,
            "kit_count": kit_count,
            "cl_latency": cl_latency,
        },
    }


def append_jsonl(dirpath: str, records: list):
    os.makedirs(dirpath, exist_ok=True)
    fpath = os.path.join(dirpath, "products.jsonl")
    # 既存IDを読んで重複スキップ
    existing_ids = set()
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_ids.add(json.loads(line)["id"])
    added = 0
    with open(fpath, "a", encoding="utf-8") as f:
        for r in records:
            if r["id"] not in existing_ids:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                added += 1
    return added


# ==============================================================
# ASUS MBs 追加（Z790/B760 LGA1700 × 5件）
# ==============================================================
ASUS_MBS_NEW = [
    mb_record("asus", "ROG MAXIMUS Z790 APEX",
              "https://www.asus.com/jp/motherboards-components/motherboards/rog/rog-maximus-z790-apex/",
              "LGA1700", "Z790", "ATX", 5, 128, "DDR5", 4, 6, "1 x 8 pin + 1 x 4 pin"),
    mb_record("asus", "ROG STRIX Z790-F GAMING WIFI",
              "https://www.asus.com/jp/motherboards-components/motherboards/rog/rog-strix-z790-f-gaming-wifi/",
              "LGA1700", "Z790", "ATX", 4, 128, "DDR5", 4, 4, "1 x 8 pin"),
    mb_record("asus", "TUF GAMING Z790-PLUS WIFI D4",
              "https://www.asus.com/jp/motherboards-components/motherboards/tuf-gaming/tuf-gaming-z790-plus-wifi-d4/",
              "LGA1700", "Z790", "ATX", 4, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("asus", "TUF GAMING B760-PLUS WIFI D4",
              "https://www.asus.com/jp/motherboards-components/motherboards/tuf-gaming/tuf-gaming-b760-plus-wifi-d4/",
              "LGA1700", "B760", "ATX", 3, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("asus", "PRIME B760M-A D4",
              "https://www.asus.com/jp/motherboards-components/motherboards/prime/prime-b760m-a-d4/",
              "LGA1700", "B760", "Micro-ATX", 2, 64, "DDR4", 4, 4, "1 x 8 pin"),
]

# ==============================================================
# MSI MBs 追加（Z790/B760 LGA1700 × 5件）
# ==============================================================
MSI_MBS_NEW = [
    mb_record("msi", "MEG Z790 GODLIKE",
              "https://www.msi.com/Motherboard/MEG-Z790-GODLIKE",
              "LGA1700", "Z790", "E-ATX", 6, 192, "DDR5", 4, 6, "2 x 8 pin"),
    mb_record("msi", "MAG Z790 TOMAHAWK WIFI DDR4",
              "https://www.msi.com/Motherboard/MAG-Z790-TOMAHAWK-WIFI-DDR4",
              "LGA1700", "Z790", "ATX", 4, 128, "DDR4", 4, 6, "1 x 8 pin"),
    mb_record("msi", "PRO Z790-P WIFI DDR4",
              "https://www.msi.com/Motherboard/PRO-Z790-P-WIFI-DDR4",
              "LGA1700", "Z790", "ATX", 3, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("msi", "MAG B760M MORTAR WIFI DDR4",
              "https://www.msi.com/Motherboard/MAG-B760M-MORTAR-WIFI-DDR4",
              "LGA1700", "B760", "Micro-ATX", 2, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("msi", "PRO B760M-E DDR4",
              "https://www.msi.com/Motherboard/PRO-B760M-E-DDR4",
              "LGA1700", "B760", "Micro-ATX", 2, 128, "DDR4", 4, 4, "1 x 8 pin"),
]

# ==============================================================
# GIGABYTE MBs 追加（Z790/B760 LGA1700 × 5件）
# ==============================================================
GIGABYTE_MBS_NEW = [
    mb_record("gigabyte", "Z790 AORUS MASTER",
              "https://www.gigabyte.com/jp/Motherboard/Z790-AORUS-MASTER-rev-10",
              "LGA1700", "Z790", "ATX", 5, 192, "DDR5", 4, 6, "2 x 8 pin"),
    mb_record("gigabyte", "Z790 AORUS ELITE AX DDR4",
              "https://www.gigabyte.com/jp/Motherboard/Z790-AORUS-ELITE-AX-DDR4-rev-10",
              "LGA1700", "Z790", "ATX", 4, 128, "DDR4", 4, 6, "1 x 8 pin"),
    mb_record("gigabyte", "Z790 UD DDR4",
              "https://www.gigabyte.com/jp/Motherboard/Z790-UD-DDR4-rev-10",
              "LGA1700", "Z790", "ATX", 3, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("gigabyte", "B760M AORUS ELITE DDR4",
              "https://www.gigabyte.com/jp/Motherboard/B760M-AORUS-ELITE-DDR4-rev-10",
              "LGA1700", "B760", "Micro-ATX", 2, 128, "DDR4", 4, 4, "1 x 8 pin"),
    mb_record("gigabyte", "B760 DS3H DDR4",
              "https://www.gigabyte.com/jp/Motherboard/B760-DS3H-DDR4-rev-10",
              "LGA1700", "B760", "ATX", 2, 128, "DDR4", 4, 4, "1 x 8 pin"),
]

# ==============================================================
# RAM 追加（Kingston DDR4×2 + DDR5×3 / Crucial DDR4×2 + DDR5×3）
# ==============================================================
KINGSTON_RAMS = [
    ram_record("kingston", "Kingston FURY Beast DDR4-3200 32GB Kit (2x16GB)",
               "https://www.kingston.com/jp/memory/gaming/kingston-fury-beast-ddr4-rgb-memory",
               "DDR4", 3200, 32, 2, 16),
    ram_record("kingston", "Kingston FURY Beast DDR4-3600 32GB Kit (2x16GB)",
               "https://www.kingston.com/jp/memory/gaming/kingston-fury-beast-ddr4-rgb-memory",
               "DDR4", 3600, 32, 2, 18),
    ram_record("kingston", "Kingston FURY Beast DDR5-5600 32GB Kit (2x16GB)",
               "https://www.kingston.com/jp/memory/gaming/kingston-fury-beast-ddr5-memory",
               "DDR5", 5600, 32, 2, 40),
    ram_record("kingston", "Kingston FURY Beast DDR5-6000 32GB Kit (2x16GB)",
               "https://www.kingston.com/jp/memory/gaming/kingston-fury-beast-ddr5-memory",
               "DDR5", 6000, 32, 2, 36),
    ram_record("kingston", "Kingston FURY Renegade DDR5-7200 32GB Kit (2x16GB)",
               "https://www.kingston.com/jp/memory/gaming/kingston-fury-renegade-ddr5-memory",
               "DDR5", 7200, 32, 2, 38),
]

CRUCIAL_RAMS = [
    ram_record("crucial", "Crucial Ballistix DDR4-3200 32GB Kit (2x16GB)",
               "https://www.crucial.com/memory/ddr4/bl2k16g32c16u4",
               "DDR4", 3200, 32, 2, 16),
    ram_record("crucial", "Crucial Ballistix DDR4-3600 32GB Kit (2x16GB)",
               "https://www.crucial.com/memory/ddr4",
               "DDR4", 3600, 32, 2, 16),
    ram_record("crucial", "Crucial Pro DDR5-5600 32GB Kit (2x16GB)",
               "https://www.crucial.com/memory/ddr5/cp2k16g56c46u5",
               "DDR5", 5600, 32, 2, 46),
    ram_record("crucial", "Crucial Pro DDR5-6000 32GB Kit (2x16GB)",
               "https://www.crucial.com/memory/ddr5",
               "DDR5", 6000, 32, 2, 46),
    ram_record("crucial", "Crucial Pro DDR5-6000 64GB Kit (2x32GB)",
               "https://www.crucial.com/memory/ddr5",
               "DDR5", 6000, 64, 2, 46),
]

# ==============================================================
# 書き込み実行
# ==============================================================
if __name__ == "__main__":
    results = {
        "asus_mb":     append_jsonl(os.path.join(BASE, "asus_mb"),     ASUS_MBS_NEW),
        "msi_mb":      append_jsonl(os.path.join(BASE, "msi_mb"),      MSI_MBS_NEW),
        "gigabyte_mb": append_jsonl(os.path.join(BASE, "gigabyte_mb"), GIGABYTE_MBS_NEW),
        "kingston_ram": append_jsonl(os.path.join(BASE, "kingston_ram"), KINGSTON_RAMS),
        "crucial_ram":  append_jsonl(os.path.join(BASE, "crucial_ram"),  CRUCIAL_RAMS),
    }
    for k, v in results.items():
        print(f"{k}: +{v}件追加")

    # 最終件数確認
    import glob
    cat_count = {}
    for path in glob.glob(os.path.join(BASE, "*/products.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    c = json.loads(line).get("category", "?")
                    cat_count[c] = cat_count.get(c, 0) + 1
    print("\n=== 最終カテゴリ別件数 ===")
    total = 0
    for c, n in sorted(cat_count.items()):
        print(f"  {c}: {n}件")
        total += n
    print(f"  合計: {total}件")
