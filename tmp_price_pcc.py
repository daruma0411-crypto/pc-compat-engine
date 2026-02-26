import sys, os, logging
sys.path.insert(0, r'C:\Users\iwashita.AKGNET\pc-compat-engine\scripts')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(
            r'C:\Users\iwashita.AKGNET\pc-compat-engine\logs\price_psu_case_cooler.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger()

from kakaku_scraper_base import update_prices_in_jsonl, DATA_ROOT
from datetime import datetime, timezone

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
log.info(f'[PSU+Case+Cooler] 開始 TODAY={TODAY}')

for cat in ['kakaku_psu', 'kakaku_case', 'kakaku_cooler']:
    path = os.path.join(DATA_ROOT, cat, 'products.jsonl')
    log.info(f'  -> {cat} 開始')
    n = update_prices_in_jsonl(path, TODAY)
    log.info(f'  -> {cat} 完了 {n}件更新')

log.info('[PSU+Case+Cooler] 全完了')
