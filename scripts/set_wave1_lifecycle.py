#!/usr/bin/env python3
"""
Set Wave-1 modules to deprecated status in module_lifecycle.
Part of: Execution Consolidation Plan (Block A3)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError

from app.modules.module_lifecycle.models import ModuleLifecycleModel
from app.modules.module_lifecycle.schemas import ModuleLifecycleStatus


# Wave-1 modules to deprecate
WAVE1_MODULES = [
    {
        "module_id": "factory_executor",
        "classification": "REPLACE",
        "canonical_path": "backend/app/modules/factory_executor",
        "active_routes": [],
        "data_owner": "skillrun",
        "auth_surface": "operator",
        "event_contract_status": "partial",
        "audit_policy": "audit_required",
        "replacement_target": "opencode_repair + opencode worker job contracts",
        "sunset_phase": "wave1-factory-executor",
        "notes": "Generic execution orchestrator replaced by OpenCode worker"
    },
    {
        "module_id": "webgenesis",
        "classification": "CONSOLIDATE",
        "canonical_path": "backend/app/modules/webgenesis",
        "active_routes": [
            "/api/webgenesis/{site_id}/generate",
            "/api/webgenesis/{site_id}/build",
            "/api/webgenesis/{site_id}/deploy",
            "/api/webgenesis/{site_id}/rollback",
        ],
        "data_owner": "skillrun",
        "auth_surface": "operator+dmz",
        "event_contract_status": "partial",
        "audit_policy": "audit_required",
        "replacement_target": "opencode worker (build/deploy/rollback)",
        "sunset_phase": "wave1-webgenesis-exec",
        "notes": "Execution layer only; domain orchestrator (specs/QA) remains"
    },
    {
        "module_id": "course_factory",
        "classification": "CONSOLIDATE",
        "canonical_path": "backend/app/modules/course_factory",
        "active_routes": [
            "/api/course-factory/generate",
            "/api/course-factory/enhance",
        ],
        "data_owner": "skillrun",
        "auth_surface": "operator",
        "event_contract_status": "partial",
        "audit_policy": "audit_required",
        "replacement_target": "course_factory -> runtime job contract -> opencode",
        "sunset_phase": "wave1-course-bridge",
        "notes": "Bridge to deprecated executor; direct job contracts needed"
    },
]


async def set_lifecycle_status(db: AsyncSession):
    """Set Wave-1 modules to deprecated status."""
    
    print("🔧 Setting Wave-1 module lifecycle status...")
    print()

    for config in WAVE1_MODULES:
        module_id = config["module_id"]

        result = await db.execute(
            select(ModuleLifecycleModel).where(ModuleLifecycleModel.module_id == module_id).limit(1)
        )
        item = result.scalar_one_or_none()

        if item is None:
            item = ModuleLifecycleModel(
                module_id=module_id,
                owner_scope="system",
                classification=config["classification"],
                lifecycle_status=ModuleLifecycleStatus.DEPRECATED.value,
                canonical_path=config["canonical_path"],
                active_routes=config["active_routes"],
                data_owner=config["data_owner"],
                auth_surface=config["auth_surface"],
                event_contract_status=config["event_contract_status"],
                audit_policy=config["audit_policy"],
                migration_adapter=None,
                kill_switch=None,
                replacement_target=config["replacement_target"],
                sunset_phase=config["sunset_phase"],
                notes=config["notes"],
            )
            db.add(item)
            print(f"  ✓ Created: {module_id} -> deprecated")
        else:
            item.lifecycle_status = ModuleLifecycleStatus.DEPRECATED.value
            item.replacement_target = config["replacement_target"]
            item.sunset_phase = config["sunset_phase"]
            item.notes = config["notes"]
            print(f"  ✓ Updated: {module_id} -> deprecated")
    
    await db.commit()
    print()
    print("✅ Wave-1 lifecycle status set")


async def main():
    """Main entry point."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://brain:brain_dev_pass@localhost:5432/brain_dev",
    )
    
    try:
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            await set_lifecycle_status(session)
    
    except ProgrammingError as e:
        print(f"❌ Error: {e}")
        print()
        print("Note: module_lifecycle table not available.")
        print("Run migrations first, then retry this script.")
        print("Example local bootstrap: ./scripts/start_local_dev.sh")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Note: This script requires local PostgreSQL running.")
        print("Start with: ./scripts/start_local_dev.sh")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
