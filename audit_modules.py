#!/usr/bin/env python3
"""Audit all modules for EventStream compliance"""

import os
import subprocess
from pathlib import Path

def audit_module(module_path: Path) -> dict:
    """Audit a single module"""
    module_name = module_path.name

    # Check for EventStream usage
    result = subprocess.run(
        ['grep', '-rl', 'from.*event_stream import\\|EventStream', str(module_path)],
        capture_output=True, text=True
    )
    has_event_stream = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

    # Check for router files
    routers = list(module_path.glob('*router*.py'))
    has_router = len(routers)

    # Check for service files
    services = list(module_path.glob('*service*.py'))
    has_service = len(services)

    return {
        'name': module_name,
        'event_stream': has_event_stream,
        'router': has_router,
        'service': has_service
    }

# Scan backend/app/modules
app_modules_dir = Path('backend/app/modules')
results = []

for module_path in sorted(app_modules_dir.iterdir()):
    if module_path.is_dir() and not module_path.name.startswith('_'):
        result = audit_module(module_path)
        results.append(result)

# Print results as table
print("Module|EventStream Files|Router Files|Service Files")
print("------|-----------------|------------|-------------")
for r in results:
    print(f"{r['name']}|{r['event_stream']}|{r['router']}|{r['service']}")
