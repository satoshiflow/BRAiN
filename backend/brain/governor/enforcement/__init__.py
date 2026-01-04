"""
Governor Enforcement Module

This module contains enforcement mechanisms for governance policies,
including locked field validation and constraint enforcement.

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-04
"""

from backend.brain.governor.enforcement.locks import (
    LockedFieldEnforcer,
    LockedFieldViolation,
    PolicyViolationError,
)

__all__ = [
    "LockedFieldEnforcer",
    "LockedFieldViolation",
    "PolicyViolationError",
]
