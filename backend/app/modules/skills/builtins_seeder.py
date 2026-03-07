"""
Built-in Skills Seeder

Automatically seeds built-in skills to database on startup.
Builtins cannot be deleted, only enabled/disabled.
"""

from typing import List, Dict, Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .builtins import BUILTIN_SKILLS, http_request, file_read, file_write, shell_command, web_search
from .models import SkillModel, SkillCategory


# Map builtin names to their handler paths and modules
BUILTIN_HANDLERS = {
    "http_request": "app.modules.skills.builtins.http_request.execute",
    "file_read": "app.modules.skills.builtins.file_read.execute",
    "file_write": "app.modules.skills.builtins.file_write.execute",
    "shell_command": "app.modules.skills.builtins.shell_command.execute",
    "web_search": "app.modules.skills.builtins.web_search.execute",
}

# Category mapping for builtins
BUILTIN_CATEGORIES = {
    "http_request": SkillCategory.API,
    "file_read": SkillCategory.FILE,
    "file_write": SkillCategory.FILE,
    "shell_command": SkillCategory.CUSTOM,
    "web_search": SkillCategory.ANALYSIS,
}


async def seed_builtin_skills(db: AsyncSession) -> None:
    """
    Seed built-in skills to database if they don't exist.
    
    This runs on application startup. Existing builtins are not modified,
    only new ones are added (disabled by default for security).
    """
    logger.info("🌱 Seeding built-in skills...")
    
    seeded_count = 0
    
    for skill_name, manifest in BUILTIN_SKILLS.items():
        # Check if skill already exists
        result = await db.execute(
            select(SkillModel).where(SkillModel.name == skill_name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.debug(f"  ✓ Built-in skill '{skill_name}' already exists")
            continue
        
        # Create new builtin skill (disabled by default for security)
        handler_path = BUILTIN_HANDLERS.get(skill_name)
        category = BUILTIN_CATEGORIES.get(skill_name, SkillCategory.CUSTOM)
        
        if not handler_path:
            logger.warning(f"  ⚠️ No handler path for builtin '{skill_name}', skipping")
            continue
        
        skill = SkillModel(
            name=skill_name,
            description=manifest.get("description", f"Built-in skill: {skill_name}"),
            category=category,
            manifest=manifest,
            handler_path=handler_path,
            enabled=False,  # Disabled by default - admin must explicitly enable
            is_builtin=True,  # Mark as builtin
        )
        
        db.add(skill)
        seeded_count += 1
        logger.info(f"  ➕ Seeded builtin skill: {skill_name} (disabled)")
    
    if seeded_count > 0:
        await db.commit()
        logger.info(f"🌱 Seeded {seeded_count} new built-in skills")
    else:
        logger.info("🌱 All built-in skills already present")


async def get_builtin_status(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get status of all built-in skills.
    
    Returns:
        List of dicts with name, enabled status, and description
    """
    result = await db.execute(
        select(SkillModel).where(SkillModel.is_builtin == True)
    )
    builtins = result.scalars().all()
    
    return [
        {
            "id": str(b.id),
            "name": b.name,
            "enabled": b.enabled,
            "description": b.description,
            "category": b.category,
        }
        for b in builtins
    ]


async def toggle_builtin(db: AsyncSession, skill_id: str, enabled: bool) -> bool:
    """
    Enable or disable a built-in skill.
    
    Args:
        db: Database session
        skill_id: UUID of the builtin skill
        enabled: True to enable, False to disable
        
    Returns:
        True if successful, False if skill not found or not a builtin
    """
    from uuid import UUID
    
    result = await db.execute(
        select(SkillModel).where(
            SkillModel.id == UUID(skill_id),
            SkillModel.is_builtin == True
        )
    )
    skill = result.scalar_one_or_none()
    
    if not skill:
        return False
    
    skill.enabled = enabled
    await db.commit()
    
    action = "enabled" if enabled else "disabled"
    logger.info(f"🔧 Built-in skill '{skill.name}' {action}")
    
    return True
