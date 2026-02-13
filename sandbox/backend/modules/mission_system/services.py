"""
Mission System Services Layer.
Factory für den echten MissionOrchestrator aus orchestrator.py
"""

from typing import Optional
from .queue import MissionQueueManager
from .orchestrator import MissionOrchestrator as RealMissionOrchestrator


_orchestrator_instance: Optional[RealMissionOrchestrator] = None


def get_orchestrator() -> RealMissionOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        queue_manager = MissionQueueManager()
        _orchestrator_instance = RealMissionOrchestrator(queue_manager)
    return _orchestrator_instance
