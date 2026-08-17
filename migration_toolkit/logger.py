import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from migration_toolkit.config import LOGS_DIR

CURRENT_LOG_FILE: Optional[Path] = None

class JSONLinesFormatter(logging.Formatter):
    """Custom JSON formatter that outputs JSON lines."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "details": getattr(record, "details", None)
        }
        return json.dumps(log_entry)

def get_logger(component: str, log_dir: Optional[Path] = None) -> logging.Logger:
    """Get a logger instance for the given component."""
    global CURRENT_LOG_FILE
    
    logger = logging.getLogger(component)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        return logger
        
    log_dir_path = log_dir or LOGS_DIR
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    if CURRENT_LOG_FILE is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        CURRENT_LOG_FILE = log_dir_path / f"migration_{timestamp}.log"
        
    formatter = JSONLinesFormatter()
    
    file_handler = logging.FileHandler(CURRENT_LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    return logger

def get_latest_log_file() -> Optional[Path]:
    """Return the most recent log file in the logs directory."""
    files = get_all_log_files()
    return files[0] if files else None

def get_all_log_files() -> list[Path]:
    """Return all log files sorted by modification time, newest first."""
    if not LOGS_DIR.exists():
        return []
    files = list(LOGS_DIR.glob("*.log"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files
