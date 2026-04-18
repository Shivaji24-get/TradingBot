import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_file: str = "trading_bot.log", log_level: str = "INFO"):
    log_path = Path(__file__).parent.parent / log_file
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {datetime.now()}")
    return logger
