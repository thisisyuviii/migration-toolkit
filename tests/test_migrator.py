import pytest
import json
from pathlib import Path
from migration_toolkit.migrator import MigrationEngine
from migration_toolkit.config import RECORD_COUNT

def test_generate_legacy_data(project_dirs):
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    engine.generate_legacy_data()
    legacy_file = project_dirs['data'] / 'legacy.json'
    assert legacy_file.exists()
    
    with open(legacy_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    assert len(data) == RECORD_COUNT
    assert all(k in data[0] for k in ['id', 'amount', 'status', 'timestamp', 'account_number'])

def test_transform_record(project_dirs):
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    record = {
        'id': 'test-1',
        'amount': 123.45,
        'status': 'pending',
        'timestamp': '2024-01-01T00:00:00',
        'account_number': '1234567890'
    }
    result = engine.transform_record(record)
    assert result['amount_cents'] == 12345
    assert result['status'] == 'PENDING'
    assert result['schema_version'] == '2.0'
    assert result['account_ref'] == 'ACC-1234567890'
    assert result['id'] == 'test-1'

def test_full_migration(project_dirs, legacy_data_file):
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    ret = engine.run()
    assert ret == 0
    
    migrated_file = project_dirs['data'] / 'migrated.json'
    assert migrated_file.exists()
    
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 100
    
    state_file = project_dirs['data'] / 'state.json'
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    assert state['status'] == 'completed'

def test_idempotency(project_dirs, legacy_data_file):
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    assert engine.run() == 0
    assert engine.run() == 0
    
    migrated_file = project_dirs['data'] / 'migrated.json'
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 100

def test_resume_after_interruption(project_dirs, legacy_data_file):
    state_file = project_dirs['data'] / 'state.json'
    migrated_file = project_dirs['data'] / 'migrated.json'
    
    with open(legacy_data_file, 'r', encoding='utf-8') as f:
        legacy_records = json.load(f)
        
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    
    partial_migrated = [engine.transform_record(r) for r in legacy_records[:50]]
    with open(migrated_file, 'w', encoding='utf-8') as f:
        json.dump(partial_migrated, f)
        
    state = {
        'status': 'in_progress',
        'last_checkpoint': 50,
        'total_records': 100,
        'started_at': None,
        'updated_at': None,
        'batch_id': None,
        'failed_records': []
    }
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f)
        
    assert engine.run() == 0
    
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 100
    
    with open(state_file, 'r', encoding='utf-8') as f:
        new_state = json.load(f)
    assert new_state['status'] == 'completed'

def test_handles_empty_dataset(project_dirs):
    legacy_file = project_dirs['data'] / 'legacy.json'
    with open(legacy_file, 'w', encoding='utf-8') as f:
        json.dump([], f)
        
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    assert engine.run() == 0
    
    migrated_file = project_dirs['data'] / 'migrated.json'
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) == 0
    
    state_file = project_dirs['data'] / 'state.json'
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    assert state['status'] == 'completed'

def test_migration_with_failures(project_dirs, legacy_data_file):
    engine = MigrationEngine(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    ret = engine.run(fail_rate=1.0)
    assert ret == 1
    
    state_file = project_dirs['data'] / 'state.json'
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    assert state['status'] == 'failed'
