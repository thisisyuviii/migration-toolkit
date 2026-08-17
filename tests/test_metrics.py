import pytest
import json
import csv
from pathlib import Path
from migration_toolkit.metrics import MetricsGenerator


def test_correct_metrics_calculation(project_dirs, sample_log_file):
    generator = MetricsGenerator(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    metrics = generator.run(log_path=sample_log_file)

    assert metrics['total_records'] == 6
    assert metrics['success_count'] == 3
    assert metrics['failure_count'] == 3
    assert metrics['success_rate'] == pytest.approx(50.0, abs=0.1)
    assert metrics['total_time_seconds'] == 9.0


def test_csv_output(project_dirs, sample_log_file):
    generator = MetricsGenerator(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    generator.run(log_path=sample_log_file)

    csv_files = list(project_dirs['reports'].glob('*.csv'))
    assert len(csv_files) > 0

    with open(csv_files[0], 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]['total_records'] == '6'
    assert rows[0]['success_count'] == '3'


def test_json_output(project_dirs, sample_log_file):
    generator = MetricsGenerator(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    generator.run(log_path=sample_log_file)

    json_files = list(project_dirs['reports'].glob('*.json'))
    assert len(json_files) > 0

    with open(json_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert 'total_records' in data


def test_empty_log(project_dirs):
    empty_log = project_dirs['logs'] / 'empty.log'
    empty_log.touch()

    generator = MetricsGenerator(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    metrics = generator.run(log_path=empty_log)

    assert metrics['total_records'] == 0
    assert metrics['success_count'] == 0
    assert metrics['failure_count'] == 0
    assert metrics['total_time_seconds'] == 0.0
    assert metrics['success_rate'] == 0


def test_avg_time_calculation(project_dirs, sample_log_file):
    generator = MetricsGenerator(logs_dir=project_dirs['logs'], reports_dir=project_dirs['reports'])
    metrics = generator.run(log_path=sample_log_file)

    assert metrics['avg_time_per_record'] == pytest.approx(9.0 / 6, abs=0.01)
