"""Config Management - Service"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import ConfigEntryModel
from .schemas import ConfigCreate, ConfigUpdate, ConfigResponse

class ConfigManagementService:
    def __init__(self, event_stream=None):
        self.event_stream = event_stream
        self._cache = {}
        logger.info("⚙️ Config Management Service initialized")
    
    async def _publish_event(self, event_type: str, key: str, data: Dict[str, Any] = None):
        if self.event_stream is None:
            return
        try:
            await self.event_stream.publish({
                "type": event_type,
                "key": key,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {}
            })
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")
    
    async def get_config(self, db: AsyncSession, key: str, environment: str = "default") -> Optional[ConfigEntryModel]:
        result = await db.execute(
            select(ConfigEntryModel)
            .where(ConfigEntryModel.key == key)
            .where(ConfigEntryModel.environment == environment)
        )
        return result.scalar_one_or_none()
    
    async def get_configs(
        self,
        db: AsyncSession,
        environment: Optional[str] = None,
        include_secrets: bool = False
    ) -> List[ConfigEntryModel]:
        query = select(ConfigEntryModel)
        if environment:
            query = query.where(ConfigEntryModel.environment == environment)
        query = query.order_by(ConfigEntryModel.key)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def set_config(
        self,
        db: AsyncSession,
        config_data: ConfigCreate,
        user_id: Optional[str] = None
    ) -> ConfigEntryModel:
        # Check if exists
        result = await db.execute(
            select(ConfigEntryModel)
            .where(ConfigEntryModel.key == config_data.key)
            .where(ConfigEntryModel.environment == config_data.environment)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update
            existing.value = config_data.value
            existing.type = config_data.type
            existing.is_secret = config_data.is_secret
            existing.description = config_data.description
            existing.version += 1
            existing.updated_by = user_id
            existing.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(existing)
            
            logger.info(f"🔄 Config updated: {config_data.key}")
            await self._publish_event("config.changed", config_data.key, {
                "version": existing.version,
                "environment": config_data.environment
            })
            return existing
        
        # Create new
        config = ConfigEntryModel(
            key=config_data.key,
            value=config_data.value,
            type=config_data.type,
            environment=config_data.environment,
            is_secret=config_data.is_secret,
            description=config_data.description,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"➕ Config created: {config_data.key}")
        await self._publish_event("config.deployed", config_data.key, {
            "environment": config_data.environment
        })
        return config
    
    async def delete_config(self, db: AsyncSession, key: str, environment: str = "default") -> bool:
        result = await db.execute(
            select(ConfigEntryModel)
            .where(ConfigEntryModel.key == key)
            .where(ConfigEntryModel.environment == environment)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return False
        
        await db.delete(config)
        await db.commit()
        
        logger.info(f"🗑️ Config deleted: {key}")
        return True
    
    async def bulk_update(
        self,
        db: AsyncSession,
        configs: Dict[str, Any],
        environment: str,
        user_id: Optional[str] = None
    ) -> List[ConfigEntryModel]:
        updated = []
        for key, value in configs.items():
            config_data = ConfigCreate(
                key=key,
                value=value,
                environment=environment
            )
            config = await self.set_config(db, config_data, user_id)
            updated.append(config)
        
        logger.info(f"📦 Bulk updated {len(updated)} configs")
        return updated

_service = None

def get_config_service(event_stream=None):
    global _service
    if _service is None:
        _service = ConfigManagementService(event_stream=event_stream)
    return _service
