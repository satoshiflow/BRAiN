"""
Skills Module - Service Layer

Business logic for skill management and execution.
"""

from __future__ import annotations

import asyncio
import importlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SkillModel, SkillCategory
from .schemas import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillValidationResult,
    SkillValidationError,
    SkillManifest,
    SkillParameter,
)


class SkillService:
    """
    Skill management and execution service.
    
    Provides:
    - CRUD operations for skills
    - Skill execution with parameter validation
    - In-memory skill registry for enabled skills
    """
    
    def __init__(self):
        """Initialize the skill service"""
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}
        logger.info("🔧 Skill Service initialized")
    
    async def load_skills(self, db: AsyncSession) -> None:
        """
        Load all enabled skills into the in-memory registry.
        
        Call this during application startup.
        """
        self._registry.clear()
        self._handlers.clear()
        
        result = await db.execute(
            select(SkillModel).where(SkillModel.enabled == True)
        )
        skills = result.scalars().all()
        
        for skill in skills:
            try:
                self._register_skill(skill)
                logger.debug(f"✅ Loaded skill: {skill.name}")
            except Exception as e:
                logger.error(f"❌ Failed to load skill {skill.name}: {e}")
        
        logger.info(f"🎯 Loaded {len(self._registry)} skills into registry")
    
    def _register_skill(self, skill: SkillModel) -> None:
        """Register a skill in the in-memory registry"""
        self._registry[skill.name] = {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "category": skill.category,
            "manifest": skill.manifest,
            "handler_path": skill.handler_path,
        }
    
    def _load_handler(self, handler_path: str) -> Callable:
        """Dynamically load a skill handler from module path"""
        if handler_path in self._handlers:
            return self._handlers[handler_path]
        
        try:
            module_path, function_name = handler_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            handler = getattr(module, function_name)
            self._handlers[handler_path] = handler
            return handler
        except (ImportError, AttributeError, ValueError) as e:
            raise ImportError(f"Failed to load handler {handler_path}: {e}")
    
    # ========================================================================
    # CRUD Operations
    # ========================================================================
    
    async def get_skills(
        self,
        db: AsyncSession,
        category: Optional[SkillCategory] = None,
        enabled_only: bool = False,
    ) -> List[SkillModel]:
        """Get all skills with optional filtering"""
        query = select(SkillModel)
        
        if category:
            query = query.where(SkillModel.category == category)
        
        if enabled_only:
            query = query.where(SkillModel.enabled == True)
        
        query = query.order_by(SkillModel.name)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_skill(self, db: AsyncSession, skill_id: UUID) -> Optional[SkillModel]:
        """Get a skill by ID"""
        result = await db.execute(
            select(SkillModel).where(SkillModel.id == skill_id)
        )
        return result.scalar_one_or_none()
    
    async def get_skill_by_name(self, db: AsyncSession, name: str) -> Optional[SkillModel]:
        """Get a skill by name"""
        result = await db.execute(
            select(SkillModel).where(SkillModel.name == name)
        )
        return result.scalar_one_or_none()
    
    async def create_skill(self, db: AsyncSession, skill_data: SkillCreate) -> SkillModel:
        """Create a new skill"""
        # Check for duplicate name
        existing = await self.get_skill_by_name(db, skill_data.name)
        if existing:
            raise ValueError(f"Skill with name '{skill_data.name}' already exists")
        
        skill = SkillModel(
            name=skill_data.name,
            description=skill_data.description,
            category=skill_data.category,
            manifest=skill_data.manifest.model_dump(),
            handler_path=skill_data.handler_path,
            enabled=skill_data.enabled,
        )
        
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        
        # Register in memory if enabled
        if skill.enabled:
            self._register_skill(skill)
        
        logger.info(f"➕ Created skill: {skill.name}")
        return skill
    
    async def update_skill(
        self, db: AsyncSession, skill_id: UUID, skill_data: SkillUpdate
    ) -> Optional[SkillModel]:
        """Update an existing skill"""
        skill = await self.get_skill(db, skill_id)
        if not skill:
            return None
        
        # Check for duplicate name if name is being changed
        if skill_data.name and skill_data.name != skill.name:
            existing = await self.get_skill_by_name(db, skill_data.name)
            if existing:
                raise ValueError(f"Skill with name '{skill_data.name}' already exists")
        
        # Update fields
        if skill_data.name is not None:
            # Remove old name from registry
            if skill.name in self._registry:
                del self._registry[skill.name]
            skill.name = skill_data.name
        
        if skill_data.description is not None:
            skill.description = skill_data.description
        
        if skill_data.category is not None:
            skill.category = skill_data.category
        
        if skill_data.manifest is not None:
            skill.manifest = skill_data.manifest.model_dump()
        
        if skill_data.handler_path is not None:
            skill.handler_path = skill_data.handler_path
        
        if skill_data.enabled is not None:
            skill.enabled = skill_data.enabled
        
        skill.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(skill)
        
        # Update registry
        if skill.enabled:
            self._register_skill(skill)
        elif skill.name in self._registry:
            del self._registry[skill.name]
        
        logger.info(f"🔄 Updated skill: {skill.name}")
        return skill
    
    async def delete_skill(self, db: AsyncSession, skill_id: UUID) -> bool:
        """Delete a skill"""
        skill = await self.get_skill(db, skill_id)
        if not skill:
            return False
        
        # Remove from registry
        if skill.name in self._registry:
            del self._registry[skill.name]
        
        await db.delete(skill)
        await db.commit()
        
        logger.info(f"🗑️ Deleted skill: {skill.name}")
        return True
    
    # ========================================================================
    # Execution
    # ========================================================================
    
    async def execute_skill(
        self,
        db: AsyncSession,
        skill_id: UUID,
        params: Dict[str, Any],
    ) -> SkillExecutionResult:
        """
        Execute a skill with the given parameters.
        
        Args:
            db: Database session
            skill_id: UUID of the skill to execute
            params: Parameters to pass to the skill
        
        Returns:
            SkillExecutionResult with success status and output
        """
        start_time = time.time()
        
        # Get skill
        skill = await self.get_skill(db, skill_id)
        if not skill:
            return SkillExecutionResult(
                success=False,
                error=f"Skill with ID {skill_id} not found",
                skill_id=skill_id,
                skill_name="unknown",
            )
        
        if not skill.enabled:
            return SkillExecutionResult(
                success=False,
                error=f"Skill '{skill.name}' is disabled",
                skill_id=skill_id,
                skill_name=skill.name,
            )
        
        # Validate parameters
        manifest = SkillManifest(**skill.manifest)
        validation = self._validate_params(manifest, params)
        if not validation.valid:
            errors = "; ".join([f"{e.field}: {e.message}" for e in validation.errors])
            return SkillExecutionResult(
                success=False,
                error=f"Parameter validation failed: {errors}",
                skill_id=skill_id,
                skill_name=skill.name,
            )
        
        # Load and execute handler
        try:
            handler = self._load_handler(skill.handler_path)
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                output = await handler(params)
            else:
                output = handler(params)
            
            execution_time = (time.time() - start_time) * 1000
            
            return SkillExecutionResult(
                success=True,
                output=output,
                execution_time_ms=round(execution_time, 2),
                skill_id=skill_id,
                skill_name=skill.name,
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"❌ Skill execution failed for {skill.name}: {e}")
            
            return SkillExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=round(execution_time, 2),
                skill_id=skill_id,
                skill_name=skill.name,
            )
    
    def _validate_params(
        self, manifest: SkillManifest, params: Dict[str, Any]
    ) -> SkillValidationResult:
        """
        Validate parameters against the skill manifest.
        
        Args:
            manifest: Skill manifest with parameter definitions
            params: Parameters to validate
        
        Returns:
            SkillValidationResult with validation status and errors
        """
        errors: List[SkillValidationError] = []
        
        # Build parameter map
        param_map = {p.name: p for p in manifest.parameters}
        
        # Check for required parameters
        for param_def in manifest.parameters:
            if param_def.required and param_def.name not in params:
                errors.append(SkillValidationError(
                    field=param_def.name,
                    message=f"Required parameter '{param_def.name}' is missing"
                ))
        
        # Validate provided parameters
        for param_name, param_value in params.items():
            if param_name not in param_map:
                errors.append(SkillValidationError(
                    field=param_name,
                    message=f"Unknown parameter '{param_name}'"
                ))
                continue
            
            param_def = param_map[param_name]
            
            # Type validation
            if not self._validate_type(param_value, param_def.type):
                errors.append(SkillValidationError(
                    field=param_name,
                    message=f"Parameter '{param_name}' should be of type '{param_def.type}'"
                ))
        
        return SkillValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate a value against an expected type"""
        type_map = {
            "string": str,
            "str": str,
            "integer": int,
            "int": int,
            "number": (int, float),
            "float": float,
            "boolean": bool,
            "bool": bool,
            "array": list,
            "list": list,
            "object": dict,
            "dict": dict,
        }
        
        expected = type_map.get(expected_type.lower())
        if expected is None:
            return True  # Unknown types pass validation
        
        return isinstance(value, expected)
    
    # ========================================================================
    # Registry Access
    # ========================================================================
    
    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the in-memory skill registry"""
        return self._registry.copy()
    
    def get_registry_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a skill from the registry by name"""
        return self._registry.get(name)


# Singleton instance
_skill_service: Optional[SkillService] = None


def get_skill_service() -> SkillService:
    """Get or create the skill service singleton"""
    global _skill_service
    if _skill_service is None:
        _skill_service = SkillService()
    return _skill_service
