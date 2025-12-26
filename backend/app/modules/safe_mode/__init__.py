"""
Safe Mode Module (Sprint 7.4)

Global kill-switch for BRAiN operations.
"""

from backend.app.modules.safe_mode.service import (
    SafeModeService,
    get_safe_mode_service,
)

__all__ = [
    "SafeModeService",
    "get_safe_mode_service",
]
