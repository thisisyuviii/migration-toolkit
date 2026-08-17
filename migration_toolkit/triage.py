import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from migration_toolkit import config
from migration_toolkit.logger import get_logger, get_latest_log_file

logger = get_logger("TriageScanner")

class TriageScanner:
    """Scans logs for predefined error patterns."""
    
    def __init__(self, logs_dir: Optional[Path] = None, reports_dir: Optional[Path] = None):
        self.logs_dir = logs_dir or config.LOGS_DIR
        self.reports_dir = reports_dir or config.REPORTS_DIR

    def scan_log(self, log_path: Path) -> list[dict[str, Any]]:
        """Scan log file for errors."""
        matches = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    for pattern_name, info in config.ERROR_PATTERNS.items():
                        if re.search(info["pattern"], line, re.IGNORECASE):
                            try:
                                entry = json.loads(line)
                                timestamp = entry.get("timestamp", datetime.now().isoformat())
                            except json.JSONDecodeError:
                                timestamp = datetime.now().isoformat()
                                
                            matches.append({
                                "pattern_name": pattern_name,
                                "matched_text": info["pattern"],
                                "timestamp": timestamp,
                                "log_line": line.strip()
                            })
        except OSError as e:
            logger.error("Failed to scan log", extra={"details": {"error": str(e)}})
            
        return matches

    def categorize(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        """Categorize matched errors."""
        categories = {}
        for match in matches:
            name = match["pattern_name"]
            if name not in categories:
                categories[name] = {
                    "pattern": name,
                    "severity": config.ERROR_PATTERNS[name]["severity"],
                    "count": 0,
                    "first_seen": match["timestamp"],
                    "last_seen": match["timestamp"],
                    "samples": []
                }
            cat = categories[name]
            cat["count"] += 1
            cat["last_seen"] = max(cat["last_seen"], match["timestamp"])
            cat["first_seen"] = min(cat["first_seen"], match["timestamp"])
            if len(cat["samples"]) < 3:
                cat["samples"].append(match["log_line"])
                
        return {
            "categories": list(categories.values()),
            "total_issues": sum(c["count"] for c in categories.values()),
            "generated_at": datetime.now().isoformat()
        }

    def run(self, log_path: Optional[Path] = None) -> dict[str, Any]:
        """Run triage analysis."""
        config.ensure_dirs()
        target_log = log_path or get_latest_log_file()
        
        if not target_log:
            logger.error("No log file found for triage")
            return {}
            
        matches = self.scan_log(target_log)
        summary = self.categorize(matches)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"triage_{timestamp}.json"
        
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info("Triage report generated", extra={"details": {"report": str(report_path)}})
        except OSError as e:
            logger.error("Failed to write triage report", extra={"details": {"error": str(e)}})
            
        return summary

    def get_latest_report(self) -> Optional[dict[str, Any]]:
        """Get most recent triage report."""
        if not self.reports_dir.exists():
            return None
        files = list(self.reports_dir.glob("triage_*.json"))
        if not files:
            return None
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        try:
            with open(files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except OSError:
            return None

if __name__ == '__main__':
    scanner = TriageScanner()
    result = scanner.run()
