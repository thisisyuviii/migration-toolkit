"""Flask web dashboard for monitoring migration-toolkit status, metrics, and triage reports."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Config - paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
REPORTS_DIR = PROJECT_ROOT / 'reports'
STATE_FILE = DATA_DIR / 'state.json'

DEFAULT_STATE: Dict[str, Any] = {
    "status": "not_started",
    "last_checkpoint": 0,
    "total_records": 0,
    "started_at": None,
    "updated_at": None,
    "batch_id": None,
    "failed_records": [],
}


def _read_json(path: Path) -> Optional[Any]:
    """Safely read and parse a JSON file.

    Args:
        path: Path to the target JSON file.

    Returns:
        Parsed JSON object (dict or list), or None on error or if file does not exist.
    """
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        app.logger.warning("Failed to read JSON file %s: %s", path, exc)
        return None


def _get_latest_report(prefix: str) -> Optional[Dict[str, Any]]:
    """Find and return the latest report matching reports/{prefix}_*.json by modification time.

    Args:
        prefix: Report filename prefix (e.g. 'metrics' or 'triage').

    Returns:
        The latest report content as a dictionary with filename included, or None if not found.
    """
    if not REPORTS_DIR.is_dir():
        return None

    try:
        report_files = sorted(
            REPORTS_DIR.glob(f"{prefix}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        app.logger.warning("Failed to list reports directory: %s", exc)
        return None

    for file_path in report_files:
        data = _read_json(file_path)
        if isinstance(data, dict):
            data["filename"] = file_path.name
            return data
    return None


def _get_all_reports(prefix: str) -> List[Dict[str, Any]]:
    """Return all reports matching reports/{prefix}_*.json, newest first, with filename included.

    Args:
        prefix: Report filename prefix (e.g. 'metrics' or 'triage').

    Returns:
        List of report dictionaries sorted from newest to oldest.
    """
    if not REPORTS_DIR.is_dir():
        return []

    try:
        report_files = sorted(
            REPORTS_DIR.glob(f"{prefix}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        app.logger.warning("Failed to list reports directory: %s", exc)
        return []

    reports: List[Dict[str, Any]] = []
    for file_path in report_files:
        data = _read_json(file_path)
        if isinstance(data, dict):
            data["filename"] = file_path.name
            reports.append(data)
    return reports


@app.route("/")
def index() -> str:
    """Render the dashboard overview page with state, metrics, triage, and history."""
    state = _read_json(STATE_FILE) or DEFAULT_STATE
    metrics = _get_latest_report("metrics")
    triage = _get_latest_report("triage")
    history = _get_all_reports("metrics")
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return render_template(
        "index.html",
        state=state,
        metrics=metrics,
        triage=triage,
        history=history,
        current_time=current_time,
    )


@app.route("/api/status")
def api_status() -> Any:
    """Return current migration state, latest metrics, and triage reports as JSON."""
    state = _read_json(STATE_FILE) or DEFAULT_STATE
    metrics = _get_latest_report("metrics")
    triage = _get_latest_report("triage")

    return jsonify({
        "state": state,
        "metrics": metrics,
        "triage": triage,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
