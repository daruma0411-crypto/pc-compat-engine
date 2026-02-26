import sys, os, logging
sys.path.insert(0, r'C:\Users\iwashita.AKGNET\pc-compat-engine\scripts')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(
            r'C:\Users\iwashita.AKGNET\pc-compat-engine\logs\price_cpu.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger()

from kakaku_scraper_base import update_prices_in_jsonl, DATA_ROOT
from datetime import datetime, timezone

TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
log.info(f'[CPU] 開始 TODAY={TODAY}')

path = os.path.join(DATA_ROOT, 'kakaku_cpu', 'products.jsonl')
n = update_prices_in_jsonl(path, TODAY)
log.info(f'[CPU] 完了 {n}件更新')
