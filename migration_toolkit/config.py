import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

STATE_FILE = DATA_DIR / "state.json"
LEGACY_FILE = DATA_DIR / "legacy.json"
MIGRATED_FILE = DATA_DIR / "migrated.json"

BATCH_SIZE = 50
RECORD_COUNT = 750

ERROR_PATTERNS = {
    "timeout": {"pattern": r"timeout", "severity": "warning"},
    "permission_denied": {"pattern": r"permission denied", "severity": "critical"},
    "invalid_format": {"pattern": r"invalid format", "severity": "warning"},
    "connection_refused": {"pattern": r"connection refused", "severity": "critical"},
    "disk_full": {"pattern": r"disk full|no space left", "severity": "critical"}
}

def ensure_dirs() -> None:
    """Create data, logs, and reports directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
