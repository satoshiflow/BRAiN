"""
Mission Templates Service

Business logic for mission template CRUD and instantiation.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import uuid
from datetime import datetime

from .models import MissionTemplate
from .schemas import (
    MissionTemplateCreate,
    MissionTemplateUpdate,
    InstantiateTemplateRequest,
    InstantiateTemplateResponse,
)


class MissionTemplateService:
    """Service for managing mission templates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============================================================================
    # CRUD Operations
    # ============================================================================
    
    async def list_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MissionTemplate]:
        """List all templates with optional filtering"""
        query = select(MissionTemplate)
        
        if category:
            query = query.where(MissionTemplate.category == category)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    MissionTemplate.name.ilike(search_term),
                    MissionTemplate.description.ilike(search_term),
                )
            )
        
        query = query.order_by(MissionTemplate.name)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_template(self, template_id: str) -> Optional[MissionTemplate]:
        """Get a single template by ID"""
        result = await self.db.execute(
            select(MissionTemplate).where(MissionTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def create_template(
        self, 
        data: MissionTemplateCreate, 
        owner_id: Optional[str] = None
    ) -> MissionTemplate:
        """Create a new mission template"""
        template = MissionTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            category=data.category,
            steps=[step.model_dump() for step in data.steps],
            variables={
                name: var.model_dump(exclude_none=True) 
                for name, var in data.variables.items()
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Set owner if provided
        if owner_id:
            template.owner_id = owner_id
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def update_template(
        self, 
        template_id: str, 
        data: MissionTemplateUpdate
    ) -> Optional[MissionTemplate]:
        """Update an existing template"""
        template = await self.get_template(template_id)
        if not template:
            return None
        
        # Update fields if provided
        if data.name is not None:
            template.name = data.name
        if data.description is not None:
            template.description = data.description
        if data.category is not None:
            template.category = data.category
        if data.steps is not None:
            template.steps = [step.model_dump() for step in data.steps]
        if data.variables is not None:
            template.variables = {
                name: var.model_dump(exclude_none=True)
                for name, var in data.variables.items()
            }
        
        template.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a template by ID"""
        template = await self.get_template(template_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        return True
    
    # ============================================================================
    # Categories
    # ============================================================================
    
    async def get_categories(self) -> List[str]:
        """Get all unique template categories"""
        result = await self.db.execute(
            select(MissionTemplate.category).distinct()
        )
        return sorted([row[0] for row in result.all()])
    
    # ============================================================================
    # Template Instantiation
    # ============================================================================
    
    async def instantiate_template(
        self,
        template_id: str,
        request: InstantiateTemplateRequest,
    ) -> InstantiateTemplateResponse:
        """
        Instantiate a template into a new mission.
        
        This creates a mission from the template with the provided variable values.
        """
        # Get template
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Validate required variables
        provided_vars = request.variables or {}
        template_vars = template.variables or {}
        
        missing_required = []
        final_variables = {}
        
        for var_name, var_def in template_vars.items():
            var_def_dict = var_def if isinstance(var_def, dict) else var_def
            is_required = var_def_dict.get("required", True)
            
            if var_name in provided_vars:
                final_variables[var_name] = provided_vars[var_name]
            elif "default" in var_def_dict:
                final_variables[var_name] = var_def_dict["default"]
            elif is_required:
                missing_required.append(var_name)
        
        if missing_required:
            raise ValueError(
                f"Missing required variables: {', '.join(missing_required)}"
            )
        
        # Generate mission name
        mission_name = request.mission_name or f"{template.name} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')})"
        
        # Create mission ID
        mission_id = str(uuid.uuid4())
        
        # Prepare steps with variable substitution
        instantiated_steps = self._substitute_variables_in_steps(
            template.steps, final_variables
        )
        
        # Build mission payload
        mission_payload = {
            "id": mission_id,
            "name": mission_name,
            "description": template.description,
            "template_id": template_id,
            "steps": instantiated_steps,
            "variables": final_variables,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }
        
        # Note: In a full implementation, this would enqueue the mission
        # For now, we return the mission payload
        
        return InstantiateTemplateResponse(
            mission_id=mission_id,
            mission_name=mission_name,
            status="created",
            template_id=template_id,
            variables_applied=final_variables,
        )
    
    def _substitute_variables_in_steps(
        self, 
        steps: List[Dict[str, Any]], 
        variables: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Substitute variable placeholders in step configurations.
        
        Replaces {{variable_name}} with the actual value.
        """
        import json
        
        # Convert steps to JSON string for easy substitution
        steps_json = json.dumps(steps)
        
        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            if isinstance(var_value, (dict, list)):
                # For complex types, we need to JSON encode
                steps_json = steps_json.replace(
                    f'"{placeholder}"', json.dumps(var_value)
                )
            else:
                steps_json = steps_json.replace(placeholder, str(var_value))
        
        # Parse back to list
        return json.loads(steps_json)


# Factory function for dependency injection
def get_template_service(db: AsyncSession) -> MissionTemplateService:
    return MissionTemplateService(db)
