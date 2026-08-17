import json
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from faker import Faker

from migration_toolkit import config
from migration_toolkit.logger import get_logger

logger = get_logger("MigrationEngine")

class MigrationEngine:
    """Core migration engine."""
    
    def __init__(self, data_dir: Optional[Path] = None, logs_dir: Optional[Path] = None):
        self.data_dir = data_dir or config.DATA_DIR
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.state_file = self.data_dir / "state.json"
        self.legacy_file = self.data_dir / "legacy.json"
        self.migrated_file = self.data_dir / "migrated.json"
        
    def generate_legacy_data(self) -> Path:
        """Generate fake financial records into legacy.json."""
        if self.legacy_file.exists():
            return self.legacy_file
            
        faker = Faker()
        records = []
        statuses = ["pending", "completed", "failed", "processing"]
        
        for _ in range(config.RECORD_COUNT):
            record = {
                "id": str(uuid.uuid4()),
                "amount": round(random.uniform(10.00, 99999.99), 2),
                "status": random.choice(statuses),
                "timestamp": faker.date_time_between(start_date='-2y', end_date='now').isoformat(),
                "account_number": faker.numerify(text='##########')
            }
            records.append(record)
            
        try:
            with open(self.legacy_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except OSError as e:
            logger.error("Failed to write legacy data", extra={"details": {"error": str(e)}})
            raise
            
        return self.legacy_file

    def load_state(self) -> dict[str, Any]:
        """Load state.json or return default state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except OSError as e:
                logger.error("Failed to load state", extra={"details": {"error": str(e)}})
                
        return {
            "status": "not_started",
            "last_checkpoint": 0,
            "total_records": 0,
            "started_at": None,
            "updated_at": None,
            "batch_id": None,
            "failed_records": []
        }

    def save_state(self, state: dict[str, Any]) -> None:
        """Atomic write to state.json."""
        state["updated_at"] = datetime.now().isoformat()
        temp_file = self.state_file.with_suffix('.tmp')
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
        except OSError as e:
            logger.error("Failed to save state", extra={"details": {"error": str(e)}})
            raise

    def transform_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Transform legacy record to new format."""
        status_map = {
            "pending": "PENDING",
            "completed": "COMPLETED",
            "failed": "FAILED",
            "processing": "IN_PROGRESS"
        }
        return {
            "id": record["id"],
            "amount_cents": int(record["amount"] * 100),
            "schema_version": "2.0",
            "status": status_map.get(record["status"], "UNKNOWN"),
            "migrated_at": datetime.now().isoformat(),
            "original_timestamp": record["timestamp"],
            "account_ref": f"ACC-{record['account_number']}"
        }

    def run(self, fail_rate: float = 0.0) -> int:
        """Main migration logic."""
        start_time = time.time()
        config.ensure_dirs()
        
        try:
            self.generate_legacy_data()
        except Exception as e:
            logger.error("Error generating data", extra={"details": {"error": str(e)}})
            return 1
            
        try:
            with open(self.legacy_file, "r", encoding="utf-8") as f:
                legacy_records = json.load(f)
        except OSError as e:
            logger.error("Failed to load legacy data", extra={"details": {"error": str(e)}})
            return 1

        state = self.load_state()
        if state["status"] == "completed":
            logger.info("Migration already completed. Exiting.")
            return 0
            
        if not state.get("started_at"):
            state["started_at"] = datetime.now().isoformat()
            state["total_records"] = len(legacy_records)

        migrated_records = []
        if self.migrated_file.exists():
            try:
                with open(self.migrated_file, "r", encoding="utf-8") as f:
                    migrated_records = json.load(f)
            except OSError as e:
                logger.error("Failed to load migrated data", extra={"details": {"error": str(e)}})
                return 1

        migrated_ids = {r["id"] for r in migrated_records}
        checkpoint = state.get("last_checkpoint", 0)
        
        state["status"] = "in_progress"
        self.save_state(state)

        records_to_process = legacy_records[checkpoint:]
        success_count = 0

        if not records_to_process:
            try:
                with open(self.migrated_file, "w", encoding="utf-8") as f:
                    json.dump(migrated_records, f, indent=2)
            except OSError as e:
                logger.error("Failed to write migrated file", extra={"details": {"error": str(e)}})

        try:
            for i in range(0, len(records_to_process), config.BATCH_SIZE):
                batch = records_to_process[i:i + config.BATCH_SIZE]
                state["batch_id"] = str(uuid.uuid4())
                
                for record in batch:
                    if record["id"] in migrated_ids:
                        continue
                        
                    if fail_rate > 0 and random.random() < fail_rate:
                        raise RuntimeError(f"Simulated failure: timeout on record {record['id']}")
                        
                    transformed = self.transform_record(record)
                    migrated_records.append(transformed)
                    migrated_ids.add(record["id"])
                    success_count += 1
                    
                    logger.info("Migrated record", extra={"details": {"record_id": record["id"]}})
                    
                checkpoint += len(batch)
                
                try:
                    with open(self.migrated_file, "w", encoding="utf-8") as f:
                        json.dump(migrated_records, f, indent=2)
                except OSError as e:
                    logger.error("Failed to save migrated batch", extra={"details": {"error": str(e)}})
                    raise
                    
                state["last_checkpoint"] = checkpoint
                self.save_state(state)
                logger.info("Batch completed", extra={"details": {"batch_size": len(batch), "checkpoint": checkpoint}})
                
        except Exception as e:
            state["status"] = "failed"
            self.save_state(state)
            logger.error("Migration failed", extra={"details": {"error": str(e)}})
            return 1
            
        state["status"] = "completed"
        self.save_state(state)
        
        total_time = time.time() - start_time
        avg_time = total_time / success_count if success_count > 0 else 0
        logger.info("Migration finished", extra={"details": {
            "total_time_seconds": total_time,
            "avg_time_per_record": avg_time,
            "success_count": success_count
        }})
        
        return 0

if __name__ == '__main__':
    fail_rate = float(os.environ.get('MIGRATION_FAIL_RATE', '0.0'))
    engine = MigrationEngine()
    sys.exit(engine.run(fail_rate=fail_rate))
