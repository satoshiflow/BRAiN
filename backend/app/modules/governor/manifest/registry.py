"""
Governor Manifest Registry (Phase 2).

Manages versioned, immutable manifests with:
- CRUD operations
- Hash chain validation
- Version history tracking
- Active/Shadow manifest management
- Activation gate enforcement
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ActivationGateConfig,
    ShadowReport,
)
from backend.app.modules.neurorail.errors import (
    ManifestNotFoundError,
    ManifestInvalidSchemaError,
    ManifestHashMismatchError,
    NeuroRailErrorCode,
    ActivationGateBlockedError,
)


class ManifestRegistry:
    """
    Registry for governor manifests.

    Responsibilities:
    - Store manifests with version history
    - Validate hash chain integrity
    - Manage active/shadow manifests
    - Enforce activation gates
    - Track manifest lineage
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize registry with database session.

        Args:
            db: Async database session
        """
        self.db = db

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    async def create(
        self,
        manifest: GovernorManifest,
        validate_hash_chain: bool = True
    ) -> GovernorManifest:
        """
        Create new manifest version.

        Args:
            manifest: Manifest to create
            validate_hash_chain: Whether to validate hash chain

        Returns:
            Created manifest

        Raises:
            ManifestHashMismatchError: If hash chain invalid
            ManifestInvalidSchemaError: If schema validation fails
        """
        logger.info(f"Creating manifest: {manifest.version} ({manifest.name})")

        # Validate hash chain if prev hash exists
        if validate_hash_chain and manifest.hash_prev:
            await self._validate_hash_chain(manifest)

        # Compute self hash if not set
        if not manifest.hash_self:
            manifest.hash_self = manifest.compute_hash()

        # Insert into database
        query = text("""
            INSERT INTO governor_manifests
                (manifest_id, version, created_at, hash_prev, hash_self,
                 effective_at, shadow_mode, shadow_start,
                 name, description, rules, budget_defaults, risk_classes,
                 job_overrides, metadata)
            VALUES
                (:manifest_id, :version, :created_at, :hash_prev, :hash_self,
                 :effective_at, :shadow_mode, :shadow_start,
                 :name, :description, :rules, :budget_defaults, :risk_classes,
                 :job_overrides, :metadata)
        """)

        import json
        await self.db.execute(query, {
            "manifest_id": manifest.manifest_id,
            "version": manifest.version,
            "created_at": manifest.created_at,
            "hash_prev": manifest.hash_prev,
            "hash_self": manifest.hash_self,
            "effective_at": manifest.effective_at,
            "shadow_mode": manifest.shadow_mode,
            "shadow_start": manifest.shadow_start,
            "name": manifest.name,
            "description": manifest.description,
            "rules": json.dumps([r.model_dump() for r in manifest.rules]),
            "budget_defaults": json.dumps(manifest.budget_defaults.model_dump()),
            "risk_classes": json.dumps({k: v.model_dump() for k, v in manifest.risk_classes.items()}),
            "job_overrides": json.dumps({k: v.model_dump() for k, v in manifest.job_overrides.items()}) if manifest.job_overrides else None,
            "metadata": json.dumps(manifest.metadata) if manifest.metadata else None,
        })
        await self.db.commit()

        logger.info(
            f"Manifest created: {manifest.version} "
            f"(shadow={manifest.shadow_mode}, hash={manifest.hash_self[:8]}...)"
        )

        return manifest

    async def get(self, version: str) -> GovernorManifest:
        """
        Get manifest by version.

        Args:
            version: Manifest version

        Returns:
            Manifest

        Raises:
            ManifestNotFoundError: If version not found
        """
        query = text("""
            SELECT manifest_id, version, created_at, hash_prev, hash_self,
                   effective_at, shadow_mode, shadow_start,
                   name, description, rules, budget_defaults, risk_classes,
                   job_overrides, metadata
            FROM governor_manifests
            WHERE version = :version
        """)

        result = await self.db.execute(query, {"version": version})
        row = result.fetchone()

        if not row:
            raise ManifestNotFoundError(version=version)

        return self._row_to_manifest(row)

    async def get_active(self) -> Optional[GovernorManifest]:
        """
        Get currently active manifest.

        Returns:
            Active manifest, or None if no manifest is active
        """
        query = text("""
            SELECT manifest_id, version, created_at, hash_prev, hash_self,
                   effective_at, shadow_mode, shadow_start,
                   name, description, rules, budget_defaults, risk_classes,
                   job_overrides, metadata
            FROM governor_manifests
            WHERE shadow_mode = FALSE
              AND effective_at IS NOT NULL
            ORDER BY effective_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(query)
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_manifest(row)

    async def get_shadow(self) -> Optional[GovernorManifest]:
        """
        Get currently shadowed manifest.

        Returns:
            Shadow manifest, or None
        """
        query = text("""
            SELECT manifest_id, version, created_at, hash_prev, hash_self,
                   effective_at, shadow_mode, shadow_start,
                   name, description, rules, budget_defaults, risk_classes,
                   job_overrides, metadata
            FROM governor_manifests
            WHERE shadow_mode = TRUE
              AND shadow_start IS NOT NULL
            ORDER BY shadow_start DESC
            LIMIT 1
        """)

        result = await self.db.execute(query)
        row = result.fetchone()

        if not row:
            return None

        return self._row_to_manifest(row)

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[GovernorManifest]:
        """
        List all manifests.

        Args:
            limit: Maximum results
            offset: Result offset

        Returns:
            List of manifests
        """
        query = text("""
            SELECT manifest_id, version, created_at, hash_prev, hash_self,
                   effective_at, shadow_mode, shadow_start,
                   name, description, rules, budget_defaults, risk_classes,
                   job_overrides, metadata
            FROM governor_manifests
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await self.db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()

        return [self._row_to_manifest(row) for row in rows]

    async def delete(self, version: str) -> None:
        """
        Delete manifest by version.

        WARNING: Only use for cleanup. Manifests should be immutable.

        Args:
            version: Manifest version to delete
        """
        logger.warning(f"Deleting manifest: {version}")

        query = text("DELETE FROM governor_manifests WHERE version = :version")
        await self.db.execute(query, {"version": version})
        await self.db.commit()

    # ========================================================================
    # Activation & Shadowing
    # ========================================================================

    async def activate(
        self,
        version: str,
        gate_config: Optional[ActivationGateConfig] = None,
        shadow_report: Optional[ShadowReport] = None,
        force: bool = False
    ) -> GovernorManifest:
        """
        Activate a manifest version.

        Args:
            version: Manifest version to activate
            gate_config: Activation gate configuration
            shadow_report: Shadow evaluation report (required unless force=True)
            force: Force activation without gate check

        Returns:
            Activated manifest

        Raises:
            ManifestNotFoundError: If version not found
            ActivationGateBlockedError: If activation gate blocks
        """
        logger.info(f"Activating manifest: {version} (force={force})")

        # Get manifest
        manifest = await self.get(version)

        # Activation gate check (unless forced)
        if not force:
            if not shadow_report:
                raise ActivationGateBlockedError(
                    version=version,
                    reason="Shadow report required for activation (use force=True to override)"
                )

            gate_config = gate_config or ActivationGateConfig()
            if not shadow_report.safe_to_activate:
                raise ActivationGateBlockedError(
                    version=version,
                    reason=f"Activation gate blocked: {shadow_report.activation_gate_reason}"
                )

        # Deactivate current active manifest
        query_deactivate = text("""
            UPDATE governor_manifests
            SET shadow_mode = TRUE, effective_at = NULL
            WHERE shadow_mode = FALSE
        """)
        await self.db.execute(query_deactivate)

        # Activate new manifest
        query_activate = text("""
            UPDATE governor_manifests
            SET shadow_mode = FALSE,
                effective_at = :effective_at
            WHERE version = :version
        """)
        await self.db.execute(query_activate, {
            "version": version,
            "effective_at": datetime.utcnow()
        })
        await self.db.commit()

        logger.info(f"Manifest activated: {version}")

        # Reload and return
        return await self.get(version)

    async def set_shadow(self, version: str) -> GovernorManifest:
        """
        Set manifest to shadow mode.

        Args:
            version: Manifest version

        Returns:
            Updated manifest
        """
        logger.info(f"Setting manifest to shadow mode: {version}")

        query = text("""
            UPDATE governor_manifests
            SET shadow_mode = TRUE,
                shadow_start = :shadow_start,
                effective_at = NULL
            WHERE version = :version
        """)
        await self.db.execute(query, {
            "version": version,
            "shadow_start": datetime.utcnow()
        })
        await self.db.commit()

        return await self.get(version)

    # ========================================================================
    # Hash Chain Validation
    # ========================================================================

    async def _validate_hash_chain(self, manifest: GovernorManifest) -> None:
        """
        Validate manifest hash chain.

        Args:
            manifest: Manifest to validate

        Raises:
            ManifestHashMismatchError: If hash chain invalid
        """
        if not manifest.hash_prev:
            return  # First manifest in chain

        # Get previous manifest by hash
        query = text("""
            SELECT version, hash_self
            FROM governor_manifests
            WHERE hash_self = :hash_prev
        """)
        result = await self.db.execute(query, {"hash_prev": manifest.hash_prev})
        row = result.fetchone()

        if not row:
            raise ManifestHashMismatchError(
                expected_hash=manifest.hash_prev,
                actual_hash="<not found>",
                details={"error": "Previous manifest with hash not found"}
            )

        logger.debug(
            f"Hash chain validated: {manifest.version} → {row[0]} "
            f"({manifest.hash_prev[:8]}...)"
        )

    def _row_to_manifest(self, row: Any) -> GovernorManifest:
        """
        Convert database row to manifest.

        Args:
            row: Database row

        Returns:
            GovernorManifest
        """
        import json
        from backend.app.modules.governor.manifest.schemas import (
            ManifestRule,
            Budget,
            RiskClass,
        )

        rules_data = json.loads(row[10])  # rules column
        budget_defaults_data = json.loads(row[11])  # budget_defaults column
        risk_classes_data = json.loads(row[12])  # risk_classes column
        job_overrides_data = json.loads(row[13]) if row[13] else {}  # job_overrides column
        metadata_data = json.loads(row[14]) if row[14] else {}  # metadata column

        return GovernorManifest(
            manifest_id=row[0],
            version=row[1],
            created_at=row[2],
            hash_prev=row[3],
            hash_self=row[4],
            effective_at=row[5],
            shadow_mode=row[6],
            shadow_start=row[7],
            name=row[8],
            description=row[9],
            rules=[ManifestRule(**r) for r in rules_data],
            budget_defaults=Budget(**budget_defaults_data),
            risk_classes={k: RiskClass(**v) for k, v in risk_classes_data.items()},
            job_overrides={k: Budget(**v) for k, v in job_overrides_data.items()},
            metadata=metadata_data,
        )


# ============================================================================
# Singleton Helper
# ============================================================================

_registry: Optional[ManifestRegistry] = None


def get_manifest_registry(db: AsyncSession) -> ManifestRegistry:
    """Get manifest registry instance (scoped to DB session)."""
    return ManifestRegistry(db)
