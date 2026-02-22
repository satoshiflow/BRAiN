"""
Skills API Routes - PicoClaw-Style Skill System

PHASE 1: REST API for ControlDeck Integration
Provides CRUD operations for skills and execution endpoint

KI Documentation:
- Database: skills table (PostgreSQL, Migration 009)
- Pattern: Standard REST CRUD + Execute
- Security: Add auth middleware when integrating with auth system
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import asyncpg
import uuid
import os
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Database singleton
_db_pool: Optional[asyncpg.Pool] = None

# Categories matching the database enum
SKILL_CATEGORIES = ["api", "file", "communication", "analysis", "custom"]


# Pydantic Models
from typing import Any

class SkillParameter(BaseModel):
    name: str
    type: str  # string, number, boolean, object, array
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None


class SkillManifest(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "custom"  # api, file, communication, analysis, custom
    version: Optional[str] = "1.0.0"
    parameters: Optional[List[SkillParameter]] = []
    returns: Optional[dict] = None


class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "custom"
    manifest: SkillManifest
    handler_path: str
    enabled: bool = True


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    manifest: Optional[SkillManifest] = None
    handler_path: Optional[str] = None
    enabled: Optional[bool] = None


class SkillResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    manifest: dict
    handler_path: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class SkillExecutionRequest(BaseModel):
    parameters: dict


class SkillExecutionResult(BaseModel):
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int


async def get_db() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global _db_pool
    if _db_pool is None:
        database_url = os.getenv("DATABASE_URL")
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        _db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    return _db_pool


def row_to_skill(row) -> SkillResponse:
    """Convert database row to response model"""
    return SkillResponse(
        id=str(row['id']),
        name=row['name'],
        description=row['description'],
        category=row['category'],
        manifest=row['manifest'],
        handler_path=row['handler_path'],
        enabled=row['enabled'],
        created_at=row['created_at'],
        updated_at=row['updated_at']
    )


@router.get("", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = None,
    search: Optional[str] = None,
    enabled_only: bool = False
):
    """
    List all skills with optional filtering
    
    Query Parameters:
    - category: Filter by category (api, file, communication, analysis, custom)
    - search: Search in name and description
    - enabled_only: Show only enabled skills
    """
    db = await get_db()
    
    query = "SELECT * FROM skills WHERE 1=1"
    params = []
    
    if category:
        query += f" AND category = ${len(params)+1}"
        params.append(category)
    
    if enabled_only:
        query += " AND enabled = true"
    
    if search:
        query += f" AND (name ILIKE ${len(params)+1} OR description ILIKE ${len(params)+1})"
        params.append(f"%{search}%")
    
    query += " ORDER BY created_at DESC"
    
    async with db.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [row_to_skill(row) for row in rows]


@router.get("/categories")
async def get_categories():
    """Get all available skill categories"""
    return {"categories": SKILL_CATEGORIES}


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """Get a single skill by ID"""
    db = await get_db()
    
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM skills WHERE id = $1",
            uuid.UUID(skill_id)
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return row_to_skill(row)


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(skill_data: SkillCreate):
    """
    Create a new skill
    
    Example:
    {
        "name": "pdf_converter",
        "description": "Converts documents to PDF",
        "category": "file",
        "manifest": {
            "name": "PDF Converter",
            "description": "Converts documents to PDF format",
            "category": "file",
            "version": "1.0.0",
            "parameters": [
                {"name": "input_file", "type": "string", "required": true}
            ]
        },
        "handler_path": "skills/pdf_converter/handler.py",
        "enabled": true
    }
    """
    db = await get_db()
    
    # Validate category
    if skill_data.category not in SKILL_CATEGORIES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category. Must be one of: {', '.join(SKILL_CATEGORIES)}"
        )
    
    async with db.acquire() as conn:
        # Check if name already exists
        existing = await conn.fetchrow(
            "SELECT id FROM skills WHERE name = $1",
            skill_data.name
        )
        if existing:
            raise HTTPException(status_code=409, detail="Skill with this name already exists")
        
        # Create skill
        row = await conn.fetchrow(
            """
            INSERT INTO skills (name, description, category, manifest, handler_path, enabled)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            skill_data.name,
            skill_data.description,
            skill_data.category,
            skill_data.manifest.model_dump(),
            skill_data.handler_path,
            skill_data.enabled
        )
        
        return row_to_skill(row)


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: str, skill_data: SkillUpdate):
    """Update an existing skill"""
    db = await get_db()
    
    # Build dynamic update query
    updates = []
    params = []
    
    if skill_data.name is not None:
        updates.append(f"name = ${len(params)+1}")
        params.append(skill_data.name)
    
    if skill_data.description is not None:
        updates.append(f"description = ${len(params)+1}")
        params.append(skill_data.description)
    
    if skill_data.category is not None:
        if skill_data.category not in SKILL_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(SKILL_CATEGORIES)}"
            )
        updates.append(f"category = ${len(params)+1}")
        params.append(skill_data.category)
    
    if skill_data.manifest is not None:
        updates.append(f"manifest = ${len(params)+1}")
        params.append(skill_data.manifest.model_dump())
    
    if skill_data.handler_path is not None:
        updates.append(f"handler_path = ${len(params)+1}")
        params.append(skill_data.handler_path)
    
    if skill_data.enabled is not None:
        updates.append(f"enabled = ${len(params)+1}")
        params.append(skill_data.enabled)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(uuid.UUID(skill_id))
    
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE skills SET {', '.join(updates)} WHERE id = ${len(params)} RETURNING *",
            *params
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        return row_to_skill(row)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: str):
    """Delete a skill"""
    db = await get_db()
    
    async with db.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM skills WHERE id = $1",
            uuid.UUID(skill_id)
        )
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/{skill_id}/execute", response_model=SkillExecutionResult)
async def execute_skill(skill_id: str, request: SkillExecutionRequest):
    """
    Execute a skill with parameters
    
    TODO: Implement actual skill execution
    Currently returns mock result for testing
    """
    db = await get_db()
    import time
    
    start_time = time.time()
    
    async with db.acquire() as conn:
        skill = await conn.fetchrow(
            "SELECT * FROM skills WHERE id = $1 AND enabled = true",
            uuid.UUID(skill_id)
        )
        
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found or disabled")
        
        # TODO: Implement actual skill execution
        # For now, return mock successful result
        execution_time = int((time.time() - start_time) * 1000)
        
        return SkillExecutionResult(
            success=True,
            output={
                "message": f"Skill '{skill['name']}' executed successfully",
                "parameters_received": request.parameters,
                "handler": skill['handler_path']
            },
            execution_time_ms=execution_time
        )
