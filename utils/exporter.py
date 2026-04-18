import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def export_to_csv(data: List[Dict[str, Any]], filename: str = "trades.csv"):
    if not data:
        return
    
    file_path = Path(__file__).parent.parent / filename
    file_exists = file_path.exists()
    
    fieldnames = list(data[0].keys())
    
    try:
        with open(file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in data:
                row["timestamp"] = row.get("timestamp", datetime.now().isoformat())
            writer.writerows(data)
        logger.info(f"Exported {len(data)} trades to {filename}")
    except Exception as e:
        logger.error(f"CSV export failed: {e}")