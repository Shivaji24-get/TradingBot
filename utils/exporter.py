import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def export_to_csv(data: List[Dict[str, Any]], filename: str = "trades.csv"):
    if not data:
        return
    file_path = Path(filename)
    file_exists = file_path.exists()
    fieldnames = list(data[0].keys())
    try:
        with open(file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in data:
                row.setdefault("timestamp", datetime.now().isoformat())
            writer.writerows(data)
    except Exception as e:
        logger.error("CSV export failed: %s", e)
