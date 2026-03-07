"""Compatibility bridge for legacy supervisor router."""

from __future__ import annotations


def get_legacy_supervisor_router():
    from modules.supervisor.router import router as _router

    return _router
