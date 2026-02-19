"""
AXE Identity Pydantic Schemas

Request/Response models for AXE Identity API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID


class AXEIdentityBase(BaseModel):
    """Base schema with common fields"""
    name: str = Field(..., max_length=255, description="Unique identity name")
    description: Optional[str] = Field(None, description="Optional description")
    system_prompt: str = Field(..., min_length=10, description="System prompt that defines AXE's behavior")
    personality: Dict = Field(default_factory=dict, description="Flexible personality traits")
    capabilities: List[str] = Field(default_factory=list, description="List of capability tags")


class AXEIdentityCreate(AXEIdentityBase):
    """Schema for creating new identity"""
    pass


class AXEIdentityUpdate(BaseModel):
    """Schema for updating existing identity (all fields optional)"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=10)
    personality: Optional[Dict] = None
    capabilities: Optional[List[str]] = None


class AXEIdentityResponse(AXEIdentityBase):
    """Schema for API responses"""
    id: UUID
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class AXEIdentityListResponse(BaseModel):
    """Schema for list responses"""
    identities: List[AXEIdentityResponse]
    total: int
