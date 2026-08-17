import pytest
import json
from pathlib import Path
from migration_toolkit.triage import TriageScanner


def test_detects_timeout(project_dirs, sample_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=sample_log_file)

    timeouts = [c for c in result['categories'] if c['pattern'] == 'timeout']
    assert len(timeouts) > 0
    assert timeouts[0]['count'] >= 1


def test_detects_permission_denied(project_dirs, sample_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=sample_log_file)

    perm_denied = [c for c in result['categories'] if c['pattern'] == 'permission_denied']
    assert len(perm_denied) > 0
    assert perm_denied[0]['count'] >= 1


def test_detects_connection_refused(project_dirs, sample_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=sample_log_file)

    conn_refused = [c for c in result['categories'] if c['pattern'] == 'connection_refused']
    assert len(conn_refused) > 0
    assert conn_refused[0]['count'] >= 1


def test_correct_count(project_dirs):
    log_path = project_dirs['logs'] / 'timeout.log'
    entries = [
        {"timestamp": "2024-01-01T12:00:00", "level": "ERROR", "component": "migrator",
         "message": f"timeout error {i}", "details": None}
        for i in range(5)
    ]
    lines = [json.dumps(e) for e in entries]
    log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=log_path)

    timeouts = [c for c in result['categories'] if c['pattern'] == 'timeout']
    assert len(timeouts) > 0
    assert timeouts[0]['count'] == 5


def test_no_false_positives(project_dirs, clean_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=clean_log_file)

    assert result['total_issues'] == 0
    assert len(result['categories']) == 0


def test_severity_classification(project_dirs, sample_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    result = scanner.run(log_path=sample_log_file)

    timeouts = [c for c in result['categories'] if c['pattern'] == 'timeout']
    if timeouts:
        assert timeouts[0]['severity'] == 'warning'

    perm_denied = [c for c in result['categories'] if c['pattern'] == 'permission_denied']
    if perm_denied:
        assert perm_denied[0]['severity'] == 'critical'


def test_triage_report_output(project_dirs, sample_log_file):
    scanner = TriageScanner(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    scanner.run(log_path=sample_log_file)

    json_files = list(project_dirs['reports'].glob('triage*.json'))
    assert len(json_files) > 0

    with open(json_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert 'total_issues' in data
    assert 'categories' in data
