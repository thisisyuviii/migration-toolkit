import pytest
import json
from pathlib import Path
from migration_toolkit.rollback import RollbackManager

def test_rollback_after_failure(project_dirs, sample_legacy_records):
    legacy_file = project_dirs['data'] / 'legacy.json'
    with open(legacy_file, 'w', encoding='utf-8') as f:
        json.dump(sample_legacy_records, f)
        
    migrated_file = project_dirs['data'] / 'migrated.json'
    migrated_records = [{'id': r['id']} for r in sample_legacy_records[:75]]
    with open(migrated_file, 'w', encoding='utf-8') as f:
        json.dump(migrated_records, f)
        
    state_file = project_dirs['data'] / 'state.json'
    state = {
        'status': 'failed',
        'last_checkpoint': 50,
        'total_records': 100,
        'started_at': None,
        'updated_at': None,
        'batch_id': None,
        'failed_records': []
    }
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f)
        
    manager = RollbackManager(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    manager.run()
    
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert len(data) <= 50
    
    with open(state_file, 'r', encoding='utf-8') as f:
        new_state = json.load(f)
    assert new_state['status'] == 'rolled_back'

def test_rollback_idempotent(project_dirs, sample_legacy_records):
    legacy_file = project_dirs['data'] / 'legacy.json'
    with open(legacy_file, 'w', encoding='utf-8') as f:
        json.dump(sample_legacy_records, f)
        
    migrated_file = project_dirs['data'] / 'migrated.json'
    migrated_records = [{'id': r['id']} for r in sample_legacy_records[:75]]
    with open(migrated_file, 'w', encoding='utf-8') as f:
        json.dump(migrated_records, f)
        
    state_file = project_dirs['data'] / 'state.json'
    state = {
        'status': 'failed',
        'last_checkpoint': 50,
        'total_records': 100,
        'started_at': None,
        'updated_at': None,
        'batch_id': None,
        'failed_records': []
    }
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f)
        
    manager = RollbackManager(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    manager.run()
    
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data_first = json.load(f)
        
    manager.run()
    
    with open(migrated_file, 'r', encoding='utf-8') as f:
        data_second = json.load(f)
        
    assert data_first == data_second

def test_rollback_clean_state(project_dirs):
    state_file = project_dirs['data'] / 'state.json'
    state = {
        'status': 'completed',
        'last_checkpoint': 100,
        'total_records': 100,
        'started_at': None,
        'updated_at': None,
        'batch_id': None,
        'failed_records': []
    }
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f)
        
    manager = RollbackManager(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    ret = manager.run()
    
    assert ret == 0
    with open(state_file, 'r', encoding='utf-8') as f:
        new_state = json.load(f)
    assert new_state['status'] == 'completed'

def test_rollback_no_state_file(project_dirs):
    manager = RollbackManager(data_dir=project_dirs['data'], logs_dir=project_dirs['logs'])
    ret = manager.run()
    assert ret == 0
