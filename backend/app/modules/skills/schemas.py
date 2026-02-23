"""
Skills Module - Pydantic Schemas

Validation schemas for the Skill System.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class SkillCategory(str, Enum):
    """Categories for organizing skills"""
    API = "api"
    FILE = "file"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


# ============================================================================
# Skill Manifest Schemas
# ============================================================================

class SkillParameter(BaseModel):
    """
    Parameter definition for a skill.
    
    Defines the schema for a single parameter that the skill accepts.
    """
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, integer, boolean, array, object)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether the parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "url",
                "type": "string",
                "description": "The URL to fetch",
                "required": True,
                "default": None
            }
        }


class SkillManifest(BaseModel):
    """
    Skill manifest defining the skill's interface.
    
    This is the PicoClaw-style skill definition that describes:
    - What the skill does
    - What parameters it accepts
    - What it returns
    """
    name: str = Field(..., description="Skill name")
    description: str = Field(..., description="Skill description")
    version: str = Field(default="1.0.0", description="Skill version")
    author: Optional[str] = Field(default=None, description="Skill author")
    parameters: List[SkillParameter] = Field(default_factory=list, description="Input parameters")
    returns: Dict[str, Any] = Field(default_factory=dict, description="Return value schema")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "http_request",
                "description": "Make HTTP requests",
                "version": "1.0.0",
                "author": "BRAiN Team",
                "parameters": [
                    {
                        "name": "url",
                        "type": "string",
                        "description": "URL to request",
                        "required": True
                    },
                    {
                        "name": "method",
                        "type": "string",
                        "description": "HTTP method",
                        "required": False,
                        "default": "GET"
                    }
                ],
                "returns": {
                    "type": "object",
                    "description": "Response data"
                }
            }
        }


# ============================================================================
# CRUD Schemas
# ============================================================================

class SkillCreate(BaseModel):
    """Schema for creating a new skill"""
    name: str = Field(..., min_length=1, max_length=100, description="Unique skill name")
    description: Optional[str] = Field(default=None, description="Skill description")
    category: SkillCategory = Field(default=SkillCategory.CUSTOM, description="Skill category")
    manifest: SkillManifest = Field(..., description="Skill manifest definition")
    handler_path: str = Field(..., min_length=1, max_length=255, description="Python module path to handler")
    enabled: bool = Field(default=True, description="Whether the skill is enabled")


class SkillUpdate(BaseModel):
    """Schema for updating an existing skill"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None)
    category: Optional[SkillCategory] = Field(default=None)
    manifest: Optional[SkillManifest] = Field(default=None)
    handler_path: Optional[str] = Field(default=None, min_length=1, max_length=255)
    enabled: Optional[bool] = Field(default=None)


class SkillResponse(BaseModel):
    """Schema for skill response"""
    id: UUID = Field(..., description="Skill UUID")
    name: str = Field(..., description="Skill name")
    description: Optional[str] = Field(default=None)
    category: SkillCategory = Field(...)
    manifest: SkillManifest = Field(...)
    handler_path: str = Field(...)
    enabled: bool = Field(...)
    is_builtin: bool = Field(default=False, description="Whether this is a built-in skill")
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Schema for listing skills"""
    items: List[SkillResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of skills")


# ============================================================================
# Execution Schemas
# ============================================================================

class SkillExecutionRequest(BaseModel):
    """
    Request to execute a skill.
    
    Contains the skill ID and parameters to pass to the skill.
    """
    skill_id: UUID = Field(..., description="ID of the skill to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the skill")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_id": "123e4567-e89b-12d3-a456-426614174000",
                "params": {
                    "url": "https://api.example.com/data",
                    "method": "GET"
                }
            }
        }


class SkillExecutionResult(BaseModel):
    """
    Result of skill execution.
    
    Contains success status, output data, and any error information.
    """
    success: bool = Field(..., description="Whether execution was successful")
    output: Optional[Any] = Field(default=None, description="Skill output data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    skill_id: UUID = Field(..., description="ID of the executed skill")
    skill_name: str = Field(..., description="Name of the executed skill")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "output": {"status": 200, "data": "..."},
                "error": None,
                "execution_time_ms": 150.5,
                "skill_id": "123e4567-e89b-12d3-a456-426614174000",
                "skill_name": "http_request"
            }
        }


class SkillValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")


class SkillValidationResult(BaseModel):
    """Result of parameter validation"""
    valid: bool = Field(..., description="Whether parameters are valid")
    errors: List[SkillValidationError] = Field(default_factory=list, description="Validation errors")


# ============================================================================
# Category Schema
# ============================================================================

class SkillCategoriesResponse(BaseModel):
    """Response containing all available skill categories"""
    categories: List[Dict[str, str]] = Field(..., description="List of categories with id and name")
