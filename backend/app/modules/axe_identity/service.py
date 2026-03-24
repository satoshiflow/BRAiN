"""
AXE Identity Service Layer

Business logic for managing AXE identities.
"""

from typing import List, Optional
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AXEIdentityORM
from .schemas import AXEIdentityCreate, AXEIdentityUpdate, AXEIdentityResponse

logger = logging.getLogger(__name__)


class AXEIdentityService:
    """Service for AXE Identity management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._active_cache: Optional[AXEIdentityResponse] = None

    async def _rollback_optional_identity_error(self, exc: Exception) -> None:
        if not isinstance(exc, (ProgrammingError, DBAPIError, SQLAlchemyError)):
            raise exc

        logger.warning("AXE identity lookup unavailable, using fallback identity: %s", exc)
        try:
            await self.db.rollback()
        except Exception as rollback_exc:  # pragma: no cover
            logger.debug("AXE identity rollback skipped: %s", rollback_exc)

    async def get_all(self) -> List[AXEIdentityResponse]:
        """Get all identities ordered by creation date (newest first)"""
        result = await self.db.execute(
            select(AXEIdentityORM).order_by(AXEIdentityORM.created_at.desc())
        )
        identities = result.scalars().all()
        return [self._to_response(i) for i in identities]

    async def get_by_id(self, identity_id: str) -> Optional[AXEIdentityResponse]:
        """Get identity by ID"""
        result = await self.db.execute(
            select(AXEIdentityORM).where(AXEIdentityORM.id == identity_id)
        )
        identity = result.scalar_one_or_none()
        return self._to_response(identity) if identity else None

    def _to_response(self, identity: AXEIdentityORM) -> AXEIdentityResponse:
        created_at = identity.created_at or datetime.now(timezone.utc)
        updated_at = identity.updated_at or created_at
        return AXEIdentityResponse(
            id=identity.id,
            name=identity.name,
            description=identity.description,
            system_prompt=identity.system_prompt,
            personality=identity.personality or {},
            capabilities=identity.capabilities or [],
            is_active=bool(identity.is_active),
            version=identity.version or 1,
            created_at=created_at,
            updated_at=updated_at,
            created_by=identity.created_by,
        )

    async def get_active(self) -> Optional[AXEIdentityResponse]:
        """
        Get currently active identity with caching.

        Returns:
            Active identity or None if no identity is active
        """
        # Return cached if available
        if self._active_cache:
            return self._active_cache

        try:
            result = await self.db.execute(
                select(AXEIdentityORM).where(AXEIdentityORM.is_active == True)
            )
            identity = result.scalar_one_or_none()
        except Exception as exc:
            await self._rollback_optional_identity_error(exc)
            return None

        if identity:
            self._active_cache = self._to_response(identity)
            logger.debug(f"Active identity: {identity.name}")
        else:
            logger.warning("No active identity found")

        return self._active_cache

    async def get_default(self) -> AXEIdentityResponse:
        """
        Get default fallback identity when no identity is active.

        Returns:
            Default AXE identity with standard prompt
        """
        return AXEIdentityResponse(
            id="00000000-0000-0000-0000-000000000000",
            name="AXE Default",
            description="Default AXE identity",
            system_prompt=(
                "Du bist AXE (Auxiliary Execution Engine), der intelligente Assistent "
                "des BRAiN-Systems. Du hilfst Nutzern bei System-Administration, "
                "Monitoring und Troubleshooting. Antworte präzise, hilfsbereit und "
                "technisch versiert."
            ),
            personality={},
            capabilities=[],
            is_active=True,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by="system"
        )

    async def create(self, data: AXEIdentityCreate, created_by: str) -> AXEIdentityResponse:
        """
        Create new identity.

        Args:
            data: Identity creation data
            created_by: Username/ID of creator

        Returns:
            Created identity

        Raises:
            IntegrityError: If name already exists
        """
        identity = AXEIdentityORM(
            **data.dict(),
            created_by=created_by
        )

        try:
            self.db.add(identity)
            await self.db.commit()
            await self.db.refresh(identity)
            logger.info(f"Created AXE identity: {identity.name} (by {created_by})")
            return self._to_response(identity)
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create identity: {e}")
            raise

    async def update(
        self,
        identity_id: str,
        data: AXEIdentityUpdate
    ) -> Optional[AXEIdentityResponse]:
        """
        Update existing identity.

        Args:
            identity_id: Identity UUID
            data: Update data (only provided fields are updated)

        Returns:
            Updated identity or None if not found
        """
        result = await self.db.execute(
            select(AXEIdentityORM).where(AXEIdentityORM.id == identity_id)
        )
        identity = result.scalar_one_or_none()

        if not identity:
            logger.warning(f"Identity not found: {identity_id}")
            return None

        # Update only provided fields
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(identity, key, value)

        # Increment version and update timestamp
        identity.version += 1
        identity.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(identity)

        # Invalidate cache if this was active
        if identity.is_active:
            self._active_cache = None

        logger.info(f"Updated AXE identity: {identity.name} (v{identity.version})")
        return self._to_response(identity)

    async def activate(self, identity_id: str) -> Optional[AXEIdentityResponse]:
        """
        Activate identity (deactivates all others).

        Args:
            identity_id: Identity UUID to activate

        Returns:
            Activated identity or None if not found
        """
        # Deactivate all identities
        await self.db.execute(
            update(AXEIdentityORM).values(is_active=False)
        )

        # Activate target identity
        result = await self.db.execute(
            select(AXEIdentityORM).where(AXEIdentityORM.id == identity_id)
        )
        identity = result.scalar_one_or_none()

        if not identity:
            await self.db.rollback()
            logger.warning(f"Identity not found for activation: {identity_id}")
            return None

        identity.is_active = True
        identity.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(identity)

        # Invalidate cache
        self._active_cache = None

        logger.info(f"✅ Activated AXE identity: {identity.name}")
        return self._to_response(identity)

    async def delete(self, identity_id: str) -> bool:
        """
        Delete identity (only if not active).

        Args:
            identity_id: Identity UUID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete active identity
        """
        result = await self.db.execute(
            select(AXEIdentityORM).where(AXEIdentityORM.id == identity_id)
        )
        identity = result.scalar_one_or_none()

        if not identity:
            logger.warning(f"Identity not found for deletion: {identity_id}")
            return False

        if identity.is_active:
            logger.error(f"Cannot delete active identity: {identity.name}")
            raise ValueError("Cannot delete active identity")

        await self.db.delete(identity)
        await self.db.commit()

        logger.info(f"🗑️ Deleted AXE identity: {identity.name}")
        return True


# Singleton instance (optional, kann auch per Depends() injiziert werden)
_service_instance: Optional[AXEIdentityService] = None


def get_service_instance(db: AsyncSession) -> AXEIdentityService:
    """Get or create service singleton"""
    global _service_instance
    if _service_instance is None or _service_instance.db != db:
        _service_instance = AXEIdentityService(db)
    return _service_instance
