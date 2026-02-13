"""
Skills Module - PicoClaw-style Skill System

A lightweight, extensible skill system for BRAiN that allows:
- Dynamic skill registration and execution
- Parameter validation via manifests
- Built-in and custom skill support
"""

from .models import SkillModel, SkillCategory
from .schemas import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillManifest,
    SkillParameter,
)
from .service import SkillService, get_skill_service
from .router import router

__all__ = [
    "SkillModel",
    "SkillCategory",
    "SkillCreate",
    "SkillUpdate",
    "SkillResponse",
    "SkillExecutionRequest",
    "SkillExecutionResult",
    "SkillManifest",
    "SkillParameter",
    "SkillService",
    "get_skill_service",
    "router",
]
