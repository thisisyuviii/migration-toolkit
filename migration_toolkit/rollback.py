import json
import sys
from pathlib import Path
from typing import Optional

from migration_toolkit import config
from migration_toolkit.logger import get_logger

logger = get_logger("RollbackManager")

class RollbackManager:
    """Manages rollback of failed migrations."""
    
    def __init__(self, data_dir: Optional[Path] = None, logs_dir: Optional[Path] = None):
        self.data_dir = data_dir or config.DATA_DIR
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.state_file = self.data_dir / "state.json"
        self.migrated_file = self.data_dir / "migrated.json"

    def run(self) -> int:
        """Execute rollback operation."""
        config.ensure_dirs()
        
        if not self.state_file.exists():
            logger.info("No state file found. Nothing to roll back.")
            return 0
            
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except OSError as e:
            logger.error("Failed to load state", extra={"details": {"error": str(e)}})
            return 1
            
        if state.get("status") not in ("failed", "in_progress"):
            logger.info("Nothing to roll back", extra={"details": {"current_status": state.get("status")}})
            return 0
            
        migrated_records = []
        if self.migrated_file.exists():
            try:
                with open(self.migrated_file, "r", encoding="utf-8") as f:
                    migrated_records = json.load(f)
            except OSError as e:
                logger.error("Failed to load migrated data", extra={"details": {"error": str(e)}})
                return 1
                
        last_checkpoint = state.get("last_checkpoint", 0)
        previous_batch_boundary = (last_checkpoint // config.BATCH_SIZE) * config.BATCH_SIZE
        
        if len(migrated_records) > previous_batch_boundary:
            trimmed_records = migrated_records[:previous_batch_boundary]
            try:
                with open(self.migrated_file, "w", encoding="utf-8") as f:
                    json.dump(trimmed_records, f, indent=2)
                logger.info("Trimmed migrated data", extra={"details": {
                    "original_count": len(migrated_records),
                    "new_count": len(trimmed_records)
                }})
            except OSError as e:
                logger.error("Failed to save trimmed migrated data", extra={"details": {"error": str(e)}})
                return 1
                
        state["status"] = "rolled_back"
        state["last_checkpoint"] = previous_batch_boundary
        
        temp_file = self.state_file.with_suffix('.tmp')
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
            logger.info("State updated after rollback", extra={"details": {"new_checkpoint": previous_batch_boundary}})
        except OSError as e:
            logger.error("Failed to save state", extra={"details": {"error": str(e)}})
            return 1
            
        return 0

if __name__ == '__main__':
    manager = RollbackManager()
    sys.exit(manager.run())
