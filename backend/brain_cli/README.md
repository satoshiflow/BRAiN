# BRAiN CLI Tool

Command-line interface for BRAiN system management and monitoring.

## Installation

```bash
cd backend
pip install -e .
```

This installs the `brain-cli` command globally.

## Commands

### Status Command

Check BRAiN system status and health.

```bash
# Show detailed status (default)
brain-cli status

# Show JSON output
brain-cli status --format=json

# Show one-line summary
brain-cli status --format=summary

# Watch mode (updates every 5s)
brain-cli status --watch

# Custom API URL
brain-cli status --api-url=http://localhost:8001
```

**Output includes:**
- Overall system health status
- Immune system metrics (active/critical issues, event rates)
- Mission system statistics (queue depth, running/pending missions)
- Agent system information (total/active/idle agents)
- Performance metrics (latency, memory, CPU, edge-of-chaos score)
- Bottleneck detection (if any)
- Optimization recommendations (if any)

**Output Formats:**
- `text` - Rich terminal output with colors and formatting (default)
- `json` - Machine-readable JSON for scripting
- `summary` - One-line summary for quick checks

### Module Management

```bash
# Create new module skeleton
brain-cli module-create <module-name>

# Check module structure
brain-cli module-check
```

### Development

```bash
# Start docker-compose
brain-cli dev-up

# Run tests
brain-cli dev-test [path]
```

## Examples

### Check system health

```bash
$ brain-cli status

╭─────────────────────────────────────────────────────────╮
│       BRAiN System Status Report                        │
│  Timestamp: 2026-01-13 10:30:45 UTC                    │
╰─────────────────────────────────────────────────────────╯

Overall Status: ✅ HEALTHY
Uptime: 2h 34m 12s

🛡️  Immune System
────────────────────────────────────────────────────────────
  Status: ✅ HEALTHY
  Active Issues: 0
  Critical Issues: 0
  Event Rate: 42.5 events/min

📋 Mission System
────────────────────────────────────────────────────────────
  Queue Depth: 5
  Running: 2
  Pending: 3
  Completion Rate: 95.2%

🤖 Agent System
────────────────────────────────────────────────────────────
  Total Agents: 4
  Active: 0
  Idle: 0
  Utilization: 0.0%

📊 Performance Metrics
────────────────────────────────────────────────────────────
  Avg Latency: 45.2ms
  P95 Latency: 123.4ms
  Memory Usage: 512.3 MB
  CPU Usage: 35.2%
  Edge-of-Chaos Score: 0.65
```

### Quick status check

```bash
$ brain-cli status --format=summary

✅ HEALTHY | Uptime: 2h 34m | Missions: 5 queued, 2 running | Agents: 4 total, 0 active
```

### JSON output for scripting

```bash
$ brain-cli status --format=json | jq '.overall_status'

"healthy"
```

### Watch mode for monitoring

```bash
$ brain-cli status --watch

# Updates every 5 seconds
# Press Ctrl+C to stop
```

## Dependencies

Required Python packages (already in requirements.txt):
- `typer==0.9.0` - CLI framework
- `rich==13.7.0` - Terminal formatting
- `httpx>=0.24` - Async HTTP client

## Architecture

```
brain_cli/
├── main.py                    # CLI entry point
├── commands/                  # Command implementations
│   ├── __init__.py
│   └── status.py             # Status command
├── formatters/                # Output formatters
│   ├── __init__.py
│   └── status_formatter.py   # Rich terminal formatting
└── README.md                  # This file
```

## Contributing

When adding new commands:

1. Create command implementation in `commands/`
2. Add formatter if needed in `formatters/`
3. Register command in `main.py`
4. Update this README
5. Add tests in `tests/`

## Troubleshooting

### Command not found

```bash
# Reinstall CLI
cd backend
pip install -e .
```

### Connection refused

```bash
# Ensure backend is running
docker compose ps backend

# Or check API URL
brain-cli status --api-url=http://your-backend:8000
```

### Import errors

```bash
# Ensure you're in the backend directory
cd backend

# Check Python path
python -c "import brain_cli; print(brain_cli.__file__)"
```
