"""
Skills API Routes - Simplified Version
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
import asyncpg
import os
import uuid

router = APIRouter(prefix="/api/skills", tags=["skills"])

_db_pool = None
SKILL_CATEGORIES = ["api", "file", "communication", "analysis", "custom"]

async def get_db():
    global _db_pool
    if _db_pool is None:
        database_url = os.getenv("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")
        _db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
        
        # Create table if not exists
        async with _db_pool.acquire() as conn:
            try:
                await conn.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'skillcategory') THEN
                            CREATE TYPE skillcategory AS ENUM ('api', 'file', 'communication', 'analysis', 'custom');
                        END IF;
                    END
                    $$;
                """)
            except:
                pass
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    category VARCHAR(20) NOT NULL DEFAULT 'custom',
                    manifest JSONB NOT NULL DEFAULT '{}',
                    handler_path VARCHAR(255) NOT NULL DEFAULT '',
                    enabled BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills (name);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills (category);")
    
    return _db_pool


@router.get("")
async def list_skills(category: Optional[str] = None, search: Optional[str] = None):
    """List all skills"""
    try:
        db = await get_db()
        
        async with db.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM skills ORDER BY created_at DESC")
            
            return {
                "skills": [
                    {
                        "id": str(row['id']),
                        "name": row['name'],
                        "description": row['description'],
                        "category": row['category'],
                        "manifest": row['manifest'],
                        "handler_path": row['handler_path'],
                        "enabled": row['enabled'],
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                    for row in rows
                ]
            }
    except Exception as e:
        print(f"[Skills Error] {e}")
        return {"skills": [], "error": str(e)}


@router.get("/categories")
async def get_categories():
    """Get all categories"""
    return {"categories": SKILL_CATEGORIES}


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get single skill"""
    try:
        db = await get_db()
        
        async with db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM skills WHERE id = $1", uuid.UUID(skill_id))
            
            if not row:
                raise HTTPException(status_code=404, detail="Skill not found")
            
            return {
                "id": str(row['id']),
                "name": row['name'],
                "description": row['description'],
                "category": row['category'],
                "manifest": row['manifest'],
                "handler_path": row['handler_path'],
                "enabled": row['enabled'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_skill(skill: dict):
    """Create new skill"""
    try:
        db = await get_db()
        
        async with db.acquire() as conn:
            # Check name exists
            existing = await conn.fetchrow("SELECT id FROM skills WHERE name = $1", skill.get('name'))
            if existing:
                raise HTTPException(status_code=409, detail="Skill name already exists")
            
            import json
            row = await conn.fetchrow(
                """
                INSERT INTO skills (name, description, category, manifest, handler_path, enabled)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6)
                RETURNING *
                """,
                skill.get('name'),
                skill.get('description'),
                skill.get('category', 'custom'),
                json.dumps(skill.get('manifest', {})),
                skill.get('handler_path', ''),
                skill.get('enabled', True)
            )
            
            return {
                "id": str(row['id']),
                "name": row['name'],
                "description": row['description'],
                "category": row['category'],
                "manifest": row['manifest'],
                "handler_path": row['handler_path'],
                "enabled": row['enabled'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: str):
    """Delete skill"""
    try:
        db = await get_db()
        
        async with db.acquire() as conn:
            result = await conn.execute("DELETE FROM skills WHERE id = $1", uuid.UUID(skill_id))
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Skill not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
