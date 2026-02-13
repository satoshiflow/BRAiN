"""
Mission Templates Schemas

Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime


# ============================================================================
# Step and Variable Schemas
# ============================================================================

class TemplateStep(BaseModel):
    """A single step in a mission template"""
    order: int = Field(..., ge=1, description="Execution order of the step")
    action: str = Field(..., min_length=1, description="Action type/name")
    config: Dict[str, Any] = Field(default_factory=dict, description="Step configuration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order": 1,
                "action": "validate_source",
                "config": {"timeout": 30}
            }
        }


class TemplateVariable(BaseModel):
    """Variable definition for a template"""
    type: str = Field(default="string", description="Variable type (string, number, boolean, object, array)")
    required: bool = Field(default=True, description="Whether the variable is required")
    default: Optional[Any] = Field(default=None, description="Default value")
    description: Optional[str] = Field(default=None, description="Variable description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "string",
                "required": True,
                "description": "Source URL for data sync"
            }
        }


# ============================================================================
# Template Schemas
# ============================================================================

class MissionTemplateBase(BaseModel):
    """Base template schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    category: str = Field(default="general", max_length=100, description="Template category")
    steps: List[TemplateStep] = Field(default_factory=list, description="Template steps")
    variables: Dict[str, TemplateVariable] = Field(default_factory=dict, description="Variable definitions")


class MissionTemplateCreate(MissionTemplateBase):
    """Schema for creating a new template"""
    pass


class MissionTemplateUpdate(BaseModel):
    """Schema for updating an existing template"""
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, max_length=100)
    steps: Optional[List[TemplateStep]] = Field(default=None)
    variables: Optional[Dict[str, TemplateVariable]] = Field(default=None)


class MissionTemplateResponse(MissionTemplateBase):
    """Schema for template responses"""
    id: str = Field(..., description="Template ID")
    owner_id: Optional[str] = Field(default=None, description="ID of the template owner")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    
    class Config:
        from_attributes = True


class MissionTemplateListResponse(BaseModel):
    """Schema for listing templates"""
    items: List[MissionTemplateResponse]
    total: int


# ============================================================================
# Instantiation Schema
# ============================================================================

class InstantiateTemplateRequest(BaseModel):
    """Request to instantiate a template into a mission"""
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variable values for instantiation")
    mission_name: Optional[str] = Field(default=None, description="Override the generated mission name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "variables": {
                    "source_url": "https://api.example.com/data",
                    "target_url": "https://target.example.com/api"
                },
                "mission_name": "Custom Data Sync Mission"
            }
        }


class InstantiateTemplateResponse(BaseModel):
    """Response after template instantiation"""
    mission_id: str = Field(..., description="Created mission ID")
    mission_name: str = Field(..., description="Mission name")
    status: str = Field(default="created", description="Mission status")
    template_id: str = Field(..., description="Source template ID")
    variables_applied: Dict[str, Any] = Field(default_factory=dict, description="Variables that were applied")


# ============================================================================
# Filter/Query Schemas
# ============================================================================

class TemplateFilter(BaseModel):
    """Filter parameters for listing templates"""
    category: Optional[str] = Field(default=None, description="Filter by category")
    search: Optional[str] = Field(default=None, description="Search in name/description")


class TemplateCategoriesResponse(BaseModel):
    """Response with available categories"""
    categories: List[str]
