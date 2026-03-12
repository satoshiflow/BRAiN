"""
Factory Executor Module

Executes business plans with preflight checks and rollback capabilities.

Version: 1.0.0
Sprint: 5
"""

# ============================================================================
# DEPRECATION NOTICE (Execution Consolidation Wave 1)
# Module role will be reduced/replaced by OpenCode execution plane.
#
# Status: PLANNED_FOR_DEPRECATION
# Owner: BRAiN Runtime / OpenCode Integration
# Replacement Target: opencode worker job contracts
# Sunset Phase: wave1-factory-executor
# Rule: Do not add new features here. Only critical fixes allowed.
# See: docs/specs/opencode_execution_consolidation_plan.md
# ============================================================================



from app.modules.factory_executor.preflight import PreflightChecker
from app.modules.factory_executor.executor import FactoryExecutor
from app.modules.factory_executor.rollback_manager import RollbackManager

__all__ = [
    "PreflightChecker",
    "FactoryExecutor",
    "RollbackManager",
]
