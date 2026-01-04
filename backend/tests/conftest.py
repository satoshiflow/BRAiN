"""
Pytest Configuration for BRAiN Backend Tests

This file adds the backend directory to sys.path so that:
1. Tests can import `from backend.main import app` (from repo root)
2. Backend code can import `from app.core import X` (as it normally does)

This allows tests to run from either:
- Repository root: pytest backend/tests/
- Backend directory: cd backend && pytest tests/
"""

import sys
from pathlib import Path

# Get the backend directory (parent of tests/)
backend_dir = Path(__file__).parent.parent

# Add backend to sys.path so that imports like 'from app.core import X' work
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Print debug info (helpful for troubleshooting)
import os
if os.getenv("DEBUG_IMPORTS"):
    print(f"[conftest.py] Added to sys.path: {backend_dir}")
    print(f"[conftest.py] Current sys.path: {sys.path[:3]}...")
