# Migration Toolkit

A CLI-based automation tool that simulates infrastructure migration, metric generation, and issue triage — the kind of tooling SysDEs build at scale.

[![CI](https://github.com/user/migration-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/user/migration-toolkit/actions/workflows/ci.yml)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI Layer                                                      │
│  migrate.sh → migrator.py ──(on failure)──→ rollback.py         │
└──────────┬──────────────────────────────────────────────────────┘
           │                                                       
┌──────────▼──────────────────────────────────────────────────────┐
│  Data Layer                                                      │
│  legacy.json → [transform] → migrated.json                      │
│  state.json (tracks progress for resumability)                   │
└──────────┬──────────────────────────────────────────────────────┘
           │                                                       
┌──────────▼──────────────────────────────────────────────────────┐
│  Analysis Layer                                                  │
│  logger.py → logs/   ←── metrics.py (CSV/JSON reports)           │
│                      ←── triage.py  (error pattern scanning)     │
└──────────┬──────────────────────────────────────────────────────┘
           │                                                       
┌──────────▼──────────────────────────────────────────────────────┐
│  Presentation Layer                                              │
│  dashboard/app.py → Flask web UI (status, metrics, triage)       │
└──────────┬──────────────────────────────────────────────────────┘
           │                                                       
┌──────────▼──────────────────────────────────────────────────────┐
│  Ops Layer                                                       │
│  systemd service │ cron nightly reports │ GitHub Actions CI       │
└─────────────────────────────────────────────────────────────────┘
```

## Why Idempotency and Resumability Matter

Production migrations handle millions of records across distributed systems where failures are inevitable — network timeouts, disk issues, process kills. An idempotent migration can be safely re-run without duplicating or corrupting data (each record has a deterministic migration ID checked before write). A resumable migration tracks progress in a state file with batch checkpoints, so an interrupted run picks up exactly where it left off instead of restarting from scratch.

## Setup

```bash
# Clone and install
git clone https://github.com/user/migration-toolkit.git
cd migration-toolkit
pip install -r requirements.txt
pip install -e .
```

## Usage

### Run Migration

```bash
# Via Bash wrapper (recommended — includes pre-checks)
bash scripts/migrate.sh

# Or directly via Python
python -m migration_toolkit.migrator
```

The migrator will:
1. Generate 750 fake financial records in `data/legacy.json` (first run only)
2. Transform each record to the new schema (amount→cents, status mapping, ISO timestamps)
3. Write results to `data/migrated.json` with progress tracked in `data/state.json`

### Simulate Failures

```bash
# Inject a 30% random failure rate
MIGRATION_FAIL_RATE=0.3 python -m migration_toolkit.migrator
```

### Rollback

```bash
# Roll back a failed migration to the last good checkpoint
python -m migration_toolkit.rollback
```

### Generate Reports

```bash
# Metrics report (CSV + JSON)
python -m migration_toolkit.metrics

# Triage scan (error pattern detection)
python -m migration_toolkit.triage
```

Reports are written to `reports/`.

### Dashboard

```bash
python dashboard/app.py
# Visit http://localhost:5050
```

The dashboard shows:
- **Migration Status**: Current state, checkpoint progress, timestamps
- **Metrics Summary**: Success rate, record counts, timing data
- **Triage Summary**: Detected error patterns with severity and counts
- **Historical Runs**: Past report listing

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=migration_toolkit --cov-report=term-missing
```

## systemd Setup

Install the migration as a systemd service:

```bash
# Copy the service file
sudo cp systemd/migration-toolkit.service /etc/systemd/system/

# Create the service user
sudo useradd -r -s /usr/sbin/nologin migration

# Deploy the toolkit
sudo mkdir -p /opt/migration-toolkit
sudo cp -r . /opt/migration-toolkit/
sudo chown -R migration:migration /opt/migration-toolkit

# Enable and run
sudo systemctl daemon-reload
sudo systemctl enable migration-toolkit.service
sudo systemctl start migration-toolkit.service

# Check status
sudo systemctl status migration-toolkit.service
sudo journalctl -u migration-toolkit.service
```

## Cron Setup

Set up nightly metrics generation at 2:00 AM:

```bash
# Create log directory
sudo mkdir -p /var/log/migration-toolkit
sudo chown migration:migration /var/log/migration-toolkit

# Install the cron job
crontab -l 2>/dev/null | cat - cron/nightly_report.cron | crontab -

# Verify
crontab -l

# Remove the cron job
crontab -l | grep -v migration_toolkit | crontab -
```

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR to `main`:

1. **Lint**: Runs `shellcheck` on all `.sh` files
2. **Test**: Runs `pytest` across Python 3.10, 3.11, and 3.12

The build fails if either step fails.

## Project Structure

```
migration-toolkit/
├── scripts/
│   └── migrate.sh              # Bash entrypoint with pre-checks
├── migration_toolkit/
│   ├── __init__.py
│   ├── config.py               # Centralized paths and constants
│   ├── logger.py               # Structured JSON-line logging
│   ├── migrator.py             # Core migration engine
│   ├── rollback.py             # Rollback to last checkpoint
│   ├── metrics.py              # Log parsing → CSV/JSON reports
│   └── triage.py               # Error pattern scanning
├── dashboard/
│   ├── app.py                  # Flask web UI
│   └── templates/
│       └── index.html
├── systemd/
│   └── migration-toolkit.service
├── cron/
│   └── nightly_report.cron
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_migrator.py        # 7 tests: idempotency, resume, edge cases
│   ├── test_rollback.py        # 4 tests: rollback safety
│   ├── test_metrics.py         # 5 tests: calculation accuracy
│   └── test_triage.py          # 7 tests: pattern detection
├── .github/workflows/ci.yml
├── requirements.txt
├── setup.py
└── README.md
```

## License

MIT
