import pytest
import json
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta

@pytest.fixture
def project_dirs(tmp_path):
    """Create isolated data/logs/reports directories."""
    data_dir = tmp_path / 'data'
    logs_dir = tmp_path / 'logs'
    reports_dir = tmp_path / 'reports'
    for d in [data_dir, logs_dir, reports_dir]:
        d.mkdir()
    return {'data': data_dir, 'logs': logs_dir, 'reports': reports_dir, 'root': tmp_path}

@pytest.fixture
def sample_legacy_records():
    """Generate 100 sample legacy records for testing."""
    records = []
    for i in range(100):
        records.append({
            'id': str(uuid.uuid4()),
            'amount': round(random.uniform(10.0, 9999.99), 2),
            'status': random.choice(['pending', 'completed', 'failed', 'processing']),
            'timestamp': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            'account_number': f'{random.randint(1000000000, 9999999999)}'
        })
    return records

@pytest.fixture
def legacy_data_file(project_dirs, sample_legacy_records):
    """Write sample legacy records to a file."""
    path = project_dirs['data'] / 'legacy.json'
    path.write_text(json.dumps(sample_legacy_records, indent=2), encoding='utf-8')
    return path

@pytest.fixture
def sample_log_file(project_dirs):
    """Create a sample log file with various log entries including errors."""
    log_path = project_dirs['logs'] / 'migration_20240101_120000.log'
    entries = [
        {"timestamp": "2024-01-01T12:00:01", "level": "INFO", "component": "migrator", "message": "Migration started", "details": None},
        {"timestamp": "2024-01-01T12:00:02", "level": "INFO", "component": "migrator", "message": "Migrated record", "details": {"record_id": "abc-1"}},
        {"timestamp": "2024-01-01T12:00:03", "level": "INFO", "component": "migrator", "message": "Migrated record", "details": {"record_id": "abc-2"}},
        {"timestamp": "2024-01-01T12:00:04", "level": "ERROR", "component": "migrator", "message": "Simulated failure: timeout on record abc-3", "details": {"record_id": "abc-3"}},
        {"timestamp": "2024-01-01T12:00:05", "level": "INFO", "component": "migrator", "message": "Migrated record", "details": {"record_id": "abc-4"}},
        {"timestamp": "2024-01-01T12:00:06", "level": "ERROR", "component": "migrator", "message": "permission denied for record abc-5", "details": {"record_id": "abc-5"}},
        {"timestamp": "2024-01-01T12:00:07", "level": "ERROR", "component": "migrator", "message": "connection refused while processing abc-6", "details": {"record_id": "abc-6"}},
        {"timestamp": "2024-01-01T12:00:10", "level": "INFO", "component": "migrator", "message": "Migration finished", "details": {"total_records": 6, "success_count": 4, "failure_count": 2, "total_time_seconds": 9.0}}
    ]
    lines = [json.dumps(e) for e in entries]
    log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return log_path

@pytest.fixture
def clean_log_file(project_dirs):
    """Create a log file with no errors."""
    log_path = project_dirs['logs'] / 'migration_20240102_120000.log'
    entries = [
        {"timestamp": "2024-01-02T12:00:01", "level": "INFO", "component": "migrator", "message": "Migration started", "details": None},
        {"timestamp": "2024-01-02T12:00:02", "level": "INFO", "component": "migrator", "message": "Migrated record", "details": {"record_id": "def-1"}},
        {"timestamp": "2024-01-02T12:00:03", "level": "INFO", "component": "migrator", "message": "Migrated record", "details": {"record_id": "def-2"}},
        {"timestamp": "2024-01-02T12:00:04", "level": "INFO", "component": "migrator", "message": "Migration finished", "details": {"total_records": 2, "success_count": 2, "failure_count": 0, "total_time_seconds": 3.0}}
    ]
    lines = [json.dumps(e) for e in entries]
    log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return log_path
