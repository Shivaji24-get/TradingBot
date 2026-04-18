import logging
from datetime import datetime, time
from dateutil import tz

logger = logging.getLogger(__name__)

IST = tz.gettz("Asia/Kolkata")

def is_market_open(open_time: str = "09:15", close_time: str = "15:30") -> bool:
    now = datetime.now(IST)
    market_open = time(int(open_time.split(":")[0]), int(open_time.split(":")[1]))
    market_close = time(int(close_time.split(":")[0]), int(close_time.split(":")[1]))
    
    current_time = now.time()
    
    if now.weekday() >= 5:
        return False
    
    return market_open <= current_time <= market_close

def wait_for_market_open(open_time: str = "09:15"):
    import time
    while not is_market_open(open_time):
        logger.info("Waiting for market open...")
        time.sleep(60)

def get_time_until_open(open_time: str = "09:15") -> int:
    now = datetime.now(IST)
    market_open = time(int(open_time.split(":")[0]), int(open_time.split(":")[1]))
    
    next_open = now.replace(hour=market_open.hour, minute=market_open.minute, second=0)
    if now.time() > market_open:
        from datetime import timedelta
        next_open += timedelta(days=1)
    
    return int((next_open - now).total_seconds())