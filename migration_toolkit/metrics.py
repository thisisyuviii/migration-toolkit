import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from migration_toolkit import config
from migration_toolkit.logger import get_logger, get_latest_log_file

logger = get_logger("MetricsGenerator")

class MetricsGenerator:
    """Generates metrics reports from logs."""
    
    def __init__(self, logs_dir: Optional[Path] = None, reports_dir: Optional[Path] = None):
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.reports_dir = reports_dir or config.REPORTS_DIR

    def parse_log(self, log_path: Path) -> dict[str, Any]:
        """Parse JSON-lines log file to extract raw metrics."""
        parsed = {
            "total_records": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_time": 0.0
        }
        
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        msg = entry.get("message", "")
                        details = entry.get("details") or {}
                        
                        if msg == "Migrated record":
                            parsed["success_count"] += 1
                            parsed["total_records"] += 1
                        elif entry.get("level") == "ERROR":
                            parsed["failure_count"] += 1
                            parsed["total_records"] += 1
                        elif msg == "Migration finished":
                            parsed["total_time"] = details.get("total_time_seconds", 0.0)
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.error("Failed to parse log", extra={"details": {"error": str(e), "file": str(log_path)}})
            
        return parsed

    def compute_metrics(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Compute final metrics from raw data."""
        total = parsed["total_records"]
        metrics = {
            "total_records": total,
            "success_count": parsed["success_count"],
            "failure_count": parsed["failure_count"],
            "success_rate": round((parsed["success_count"] / total * 100), 2) if total > 0 else 0,
            "avg_time_per_record": round((parsed["total_time"] / total), 4) if total > 0 else 0,
            "total_time_seconds": parsed["total_time"],
            "generated_at": datetime.now().isoformat()
        }
        return metrics

    def write_csv(self, metrics: dict[str, Any], output_path: Path) -> None:
        """Write metrics to CSV."""
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
                writer.writeheader()
                writer.writerow(metrics)
        except OSError as e:
            logger.error("Failed to write CSV", extra={"details": {"error": str(e)}})

    def write_json(self, metrics: dict[str, Any], output_path: Path) -> None:
        """Write metrics to JSON."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
        except OSError as e:
            logger.error("Failed to write JSON", extra={"details": {"error": str(e)}})

    def run(self, log_path: Optional[Path] = None) -> dict[str, Any]:
        """Generate metrics report."""
        config.ensure_dirs()
        target_log = log_path or get_latest_log_file()
        
        if not target_log:
            logger.error("No log file found")
            return {}
            
        parsed = self.parse_log(target_log)
        metrics = self.compute_metrics(parsed)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.reports_dir / f"metrics_{timestamp}.csv"
        json_path = self.reports_dir / f"metrics_{timestamp}.json"
        
        self.write_csv(metrics, csv_path)
        self.write_json(metrics, json_path)
        
        logger.info("Metrics generated", extra={"details": {"json_report": str(json_path)}})
        return metrics

    def get_latest_report(self) -> Optional[dict[str, Any]]:
        """Find the most recent metrics JSON report."""
        reports = self.get_all_reports()
        return reports[0] if reports else None

    def get_all_reports(self) -> list[dict[str, Any]]:
        """Return all metrics reports, newest first."""
        if not self.reports_dir.exists():
            return []
        files = list(self.reports_dir.glob("metrics_*.json"))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        reports = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    reports.append(json.load(f))
            except OSError:
                continue
        return reports

if __name__ == '__main__':
    gen = MetricsGenerator()
    result = gen.run()
