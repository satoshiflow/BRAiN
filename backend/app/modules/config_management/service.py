"""Config Management - Service"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit

from .models import ConfigEntryModel
from .schemas import (
    ConfigCreate,
    ConfigValueType,
    VaultDefinitionResponse,
    VaultGenerateResponse,
    VaultRotationRequestResponse,
    VaultValueResponse,
)


@dataclass(frozen=True)
class ManagedConfigDefinition:
    key: str
    label: str
    description: str
    classification: str
    value_type: ConfigValueType
    editable: bool = True
    generator_supported: bool = False
    rotation_supported: bool = False
    validation: dict[str, Any] | None = None


class ConfigManagementService:
    ROTATION_KEY_PREFIX = "__vault_pending__"
    SECRET_HINTS = (
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "PRIVATE_KEY",
        "API_KEY",
        "JWT_KEY",
    )
    SENSITIVE_HINTS = ("URL", "HOST", "ISSUER", "AUDIENCE", "MODE", "EXPIRE")

    def __init__(self, event_stream=None):
        self.event_stream = event_stream
        self._cache = {}
        self._managed_defs = self._build_static_definitions()
        logger.info("⚙️ Config Management Service initialized")

    @staticmethod
    def _utc_now_naive() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _build_static_definitions() -> dict[str, ManagedConfigDefinition]:
        items = [
            ManagedConfigDefinition("BRAIN_JWT_PRIVATE_KEY", "JWT Private Key", "RSA private key for JWT signing", "secret", "pem", generator_supported=True, rotation_supported=True),
            ManagedConfigDefinition("JWT_SECRET_KEY", "Legacy JWT Secret", "Legacy symmetric JWT secret", "secret", "string", generator_supported=True, rotation_supported=True),
            ManagedConfigDefinition("BRAIN_ADMIN_PASSWORD", "Admin Password", "Local admin bootstrap password", "secret", "string", generator_supported=True, rotation_supported=True),
            ManagedConfigDefinition("BRAIN_OPERATOR_PASSWORD", "Operator Password", "Local operator bootstrap password", "secret", "string", generator_supported=True, rotation_supported=True),
            ManagedConfigDefinition("BRAIN_VIEWER_PASSWORD", "Viewer Password", "Local viewer bootstrap password", "secret", "string", generator_supported=True, rotation_supported=True),
            ManagedConfigDefinition("OPENAI_API_KEY", "OpenAI API Key", "Provider API key", "secret", "string", rotation_supported=True),
            ManagedConfigDefinition("OPENROUTER_API_KEY", "OpenRouter API Key", "Provider API key", "secret", "string", rotation_supported=True),
            ManagedConfigDefinition("ANTHROPIC_API_KEY", "Anthropic API Key", "Provider API key", "secret", "string", rotation_supported=True),
            ManagedConfigDefinition("OPENWEBUI_API_KEY", "OpenWebUI API Key", "Provider API key", "secret", "string", rotation_supported=True),
            ManagedConfigDefinition("DATABASE_URL", "Database URL", "Primary database DSN", "secret", "url", rotation_supported=True),
            ManagedConfigDefinition("REDIS_URL", "Redis URL", "Primary redis endpoint", "sensitive", "url", rotation_supported=True),
            ManagedConfigDefinition("QDRANT_URL", "Qdrant URL", "Vector database endpoint", "sensitive", "url"),
            ManagedConfigDefinition("JWT_ISSUER", "JWT Issuer", "Token issuer claim", "sensitive", "string"),
            ManagedConfigDefinition("JWT_AUDIENCE", "JWT Audience", "Token audience claim", "sensitive", "string"),
            ManagedConfigDefinition("JWT_JWKS_URL", "JWKS URL", "JWKS endpoint", "sensitive", "url"),
            ManagedConfigDefinition("ACCESS_TOKEN_EXPIRE_MINUTES", "Access Token TTL", "Access token validity in minutes", "sensitive", "integer", validation={"min": 1, "max": 1440}),
            ManagedConfigDefinition("REFRESH_TOKEN_EXPIRE_DAYS", "Refresh Token TTL", "Refresh token validity in days", "sensitive", "integer", validation={"min": 1, "max": 365}),
            ManagedConfigDefinition("AGENT_TOKEN_EXPIRE_HOURS", "Agent Token TTL", "Agent token validity in hours", "sensitive", "integer", validation={"min": 1, "max": 720}),
            ManagedConfigDefinition("LOCAL_LLM_MODE", "Local LLM Mode", "Default provider routing mode", "sensitive", "string"),
            ManagedConfigDefinition("AXE_MINIWORKER_ENABLED", "AXE Miniworker Enabled", "Enable Pi-backed AXE miniworker executor", "sensitive", "boolean"),
            ManagedConfigDefinition("AXE_MINIWORKER_COMMAND", "AXE Miniworker Command", "Command used to launch the Pi miniworker runtime", "sensitive", "string"),
            ManagedConfigDefinition("AXE_MINIWORKER_PROVIDER", "AXE Miniworker Provider", "Provider override passed to Pi", "sensitive", "string"),
            ManagedConfigDefinition("AXE_MINIWORKER_MODEL", "AXE Miniworker Model", "Model override passed to Pi", "sensitive", "string"),
            ManagedConfigDefinition("AXE_MINIWORKER_WORKDIR", "AXE Miniworker Workdir", "Repository workdir used by Pi miniworker", "sensitive", "string"),
            ManagedConfigDefinition("AXE_MINIWORKER_TIMEOUT_SECONDS", "AXE Miniworker Timeout", "Hard timeout for Pi miniworker execution", "sensitive", "integer", validation={"min": 5, "max": 900}),
            ManagedConfigDefinition("AXE_MINIWORKER_MAX_FILES", "AXE Miniworker Max Files", "Maximum files included in one miniworker run", "sensitive", "integer", validation={"min": 1, "max": 20}),
            ManagedConfigDefinition("AXE_MINIWORKER_MAX_LLM_TOKENS", "AXE Miniworker Max Tokens", "Approximate token ceiling for one miniworker run", "sensitive", "integer", validation={"min": 128, "max": 200000}),
            ManagedConfigDefinition("AXE_MINIWORKER_MAX_COST_CREDITS", "AXE Miniworker Max Cost Credits", "Approximate credit ceiling for one miniworker run", "sensitive", "integer", validation={"min": 1, "max": 100000}),
            ManagedConfigDefinition("AXE_MINIWORKER_ALLOW_BOUNDED_APPLY", "AXE Miniworker Allow Bounded Apply", "Allow bounded apply mode for miniworker", "sensitive", "boolean"),
            ManagedConfigDefinition("BRAIN_CAPABILITY_ALLOW_INMEMORY_FALLBACK", "In-memory Capability Fallback", "Allow fallback when DB capability records missing", "sensitive", "boolean"),
            ManagedConfigDefinition("SKILL_MARKETPLACE_EXTERNAL_ENABLED", "External Marketplace Enabled", "Allow publishing to external marketplace", "sensitive", "boolean"),
            ManagedConfigDefinition("BRAIN_AUTO_LEARN_ON_SKILLRUN", "Auto Learn on SkillRun", "Enable automatic learning artifact ingestion", "sensitive", "boolean"),
        ]
        return {item.key: item for item in items}

    @staticmethod
    def _infer_value_type(raw_value: str) -> ConfigValueType:
        lowered = raw_value.strip().lower()
        if lowered in {"true", "false", "1", "0", "yes", "no"}:
            return "boolean"
        if lowered.isdigit():
            return "integer"
        if lowered.startswith("-----begin"):
            return "pem"
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return "url"
        return "string"

    @classmethod
    def _classify_key(cls, key: str) -> str:
        upper = key.upper()
        if any(hint in upper for hint in cls.SECRET_HINTS):
            return "secret"
        if any(hint in upper for hint in cls.SENSITIVE_HINTS) or upper.endswith("_URL"):
            return "sensitive"
        return "public_config"

    @staticmethod
    def _is_relevant_env_key(key: str) -> bool:
        if key.startswith("NEXT_PUBLIC_"):
            return True
        if key.startswith(("BRAIN_", "AXE_", "OPEN", "JWT_", "DATABASE_", "REDIS_", "QDRANT_")):
            return True
        return any(token in key for token in ("PASSWORD", "TOKEN", "SECRET", "API_KEY", "URL"))

    def _build_env_definition(self, key: str, value: str) -> ManagedConfigDefinition:
        return ManagedConfigDefinition(
            key=key,
            label=key.replace("_", " ").title(),
            description="Environment-provided configuration",
            classification=self._classify_key(key),
            value_type=self._infer_value_type(value),
            editable=True,
            generator_supported=key.upper().endswith("_PASSWORD") or key.upper().endswith("_SECRET_KEY"),
            rotation_supported=self._classify_key(key) in {"secret", "sensitive"},
            validation={},
        )

    def list_vault_definitions(self) -> list[VaultDefinitionResponse]:
        merged: dict[str, ManagedConfigDefinition] = dict(self._managed_defs)
        for key, raw_value in os.environ.items():
            if key in merged:
                continue
            if not self._is_relevant_env_key(key):
                continue
            merged[key] = self._build_env_definition(key, raw_value)

        items = [
            VaultDefinitionResponse(
                key=item.key,
                label=item.label,
                description=item.description,
                classification=item.classification,  # type: ignore[arg-type]
                value_type=item.value_type,
                editable=item.editable,
                generator_supported=item.generator_supported,
                rotation_supported=item.rotation_supported,
                validation=item.validation or {},
            )
            for item in sorted(merged.values(), key=lambda x: x.key)
        ]
        return items

    def _definition_for_key(self, key: str) -> ManagedConfigDefinition:
        if key in self._managed_defs:
            return self._managed_defs[key]
        raw = os.getenv(key, "")
        return self._build_env_definition(key, raw)

    @classmethod
    def _rotation_storage_key(cls, key: str) -> str:
        return f"{cls.ROTATION_KEY_PREFIX}:{key}"

    @classmethod
    def _rotation_target_key(cls, storage_key: str) -> str:
        return storage_key.replace(f"{cls.ROTATION_KEY_PREFIX}:", "", 1)

    @staticmethod
    def _fernet_from_env() -> Fernet | None:
        raw = os.getenv("CONFIG_VAULT_ENCRYPTION_KEY") or os.getenv("BRAIN_CONFIG_ENCRYPTION_KEY")
        if not raw:
            return None
        try:
            return Fernet(raw.encode("utf-8"))
        except Exception:
            digest = hashlib.sha256(raw.encode("utf-8")).digest()
            derived = base64.urlsafe_b64encode(digest)
            return Fernet(derived)

    def _encrypt_secret_payload(self, plain_text: str) -> dict[str, Any]:
        fernet = self._fernet_from_env()
        if fernet is None:
            raise ValueError("CONFIG_VAULT_ENCRYPTION_KEY must be configured for secret writes")
        token = fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
        return {"ciphertext": token, "alg": "fernet", "v": 1}

    def _decrypt_secret_payload(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict) and value.get("alg") == "fernet" and value.get("ciphertext"):
            fernet = self._fernet_from_env()
            if fernet is None:
                return None
            decrypted = fernet.decrypt(str(value["ciphertext"]).encode("utf-8"))
            return decrypted.decode("utf-8")
        if isinstance(value, str):
            return value
        return str(value)

    async def _publish_event(self, event_type: str, key: str, data: Dict[str, Any] | None = None):
        if self.event_stream is None:
            return
        try:
            await self.event_stream.publish({
                "type": event_type,
                "key": key,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {},
            })
        except Exception as exc:
            logger.warning(f"Failed to publish event: {exc}")

    def _generate_candidate_value(self, key: str, length: int | None = None) -> str:
        if key == "BRAIN_JWT_PRIVATE_KEY":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            return private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")
        token_length = length or 40
        return secrets.token_urlsafe(max(16, token_length))

    def _candidate_from_rotation_payload(self, payload: dict[str, Any]) -> Any:
        if payload.get("candidate_encrypted"):
            return self._decrypt_secret_payload(payload.get("candidate"))
        return payload.get("candidate")

    @staticmethod
    def _mask_value(definition: ManagedConfigDefinition, value: Any) -> Any:
        if value is None:
            return None
        if definition.classification == "secret":
            return "********"
        return value

    @staticmethod
    def _normalize_value(definition: ManagedConfigDefinition, value: Any) -> Any:
        if definition.value_type == "integer":
            return int(value)
        if definition.value_type == "boolean":
            if isinstance(value, bool):
                return value
            lowered = str(value).strip().lower()
            return lowered in {"1", "true", "yes", "on"}
        if definition.value_type in {"url", "string", "pem"}:
            return str(value)
        return value

    def validate_vault_candidate(self, key: str, value: Any) -> list[str]:
        definition = self._definition_for_key(key)
        errors: list[str] = []
        if value is None:
            errors.append("Value must not be null")
            return errors

        if definition.value_type == "url":
            as_text = str(value)
            if not (as_text.startswith("http://") or as_text.startswith("https://")):
                errors.append("URL must start with http:// or https://")

        if definition.value_type == "integer":
            try:
                int(value)
            except Exception:
                errors.append("Value must be an integer")

        if definition.value_type == "pem":
            text = str(value)
            if "-----BEGIN" not in text or "-----END" not in text:
                errors.append("PEM value is not valid")

        if definition.classification == "secret" and len(str(value).strip()) < 16:
            errors.append("Secret values must be at least 16 characters")

        validation = definition.validation or {}
        if "min" in validation:
            try:
                if int(value) < int(validation["min"]):
                    errors.append(f"Value must be >= {validation['min']}")
            except Exception:
                pass
        if "max" in validation:
            try:
                if int(value) > int(validation["max"]):
                    errors.append(f"Value must be <= {validation['max']}")
            except Exception:
                pass
        return errors

    async def get_config(self, db: AsyncSession, key: str, environment: str = "default") -> Optional[ConfigEntryModel]:
        result = await db.execute(
            select(ConfigEntryModel)
            .where(ConfigEntryModel.key == key)
            .where(ConfigEntryModel.environment == environment)
        )
        return result.scalar_one_or_none()

    async def resolve_effective_value(
        self,
        db: AsyncSession,
        key: str,
        *,
        environment: str = "default",
        default: Any = None,
    ) -> Any:
        row = await self.get_config(db, key, environment)
        if row is not None:
            if row.is_secret:
                decrypted = self._decrypt_secret_payload(row.value)
                return decrypted if decrypted is not None else default
            return row.value

        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        return default

    async def get_configs(
        self,
        db: AsyncSession,
        environment: Optional[str] = None,
        include_secrets: bool = False,
    ) -> List[ConfigEntryModel]:
        query = select(ConfigEntryModel)
        if environment:
            query = query.where(ConfigEntryModel.environment == environment)
        query = query.order_by(ConfigEntryModel.key)
        result = await db.execute(query)
        items = list(result.scalars().all())
        if include_secrets:
            return items
        for item in items:
            if item.is_secret:
                item.value = "***REDACTED***"
        return items

    async def set_config(
        self,
        db: AsyncSession,
        config_data: ConfigCreate,
        user_id: Optional[str] = None,
    ) -> ConfigEntryModel:
        result = await db.execute(
            select(ConfigEntryModel)
            .where(ConfigEntryModel.key == config_data.key)
            .where(ConfigEntryModel.environment == config_data.environment)
        )
        existing = result.scalar_one_or_none()

        persisted_value = config_data.value
        if config_data.is_secret:
            persisted_value = self._encrypt_secret_payload(str(config_data.value))

        if existing:
            existing.value = persisted_value
            existing.type = config_data.type
            existing.is_secret = config_data.is_secret
            existing.is_encrypted = config_data.is_secret
            existing.description = config_data.description
            existing.version += 1
            existing.updated_by = user_id
            existing.updated_at = self._utc_now_naive()
            await db.commit()
            await db.refresh(existing)
            await self._publish_event("config.changed", config_data.key, {"version": existing.version})
            return existing

        config = ConfigEntryModel(
            key=config_data.key,
            value=persisted_value,
            type=config_data.type,
            environment=config_data.environment,
            is_secret=config_data.is_secret,
            is_encrypted=config_data.is_secret,
            description=config_data.description,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        await self._publish_event("config.deployed", config_data.key, {"environment": config_data.environment})
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
        return True

    async def bulk_update(
        self,
        db: AsyncSession,
        configs: Dict[str, Any],
        environment: str,
        user_id: Optional[str] = None,
    ) -> List[ConfigEntryModel]:
        updated = []
        for key, value in configs.items():
            definition = self._definition_for_key(key)
            payload = ConfigCreate(
                key=key,
                value=self._normalize_value(definition, value),
                type="number" if definition.value_type == "integer" else ("boolean" if definition.value_type == "boolean" else "string"),
                environment=environment,
                is_secret=definition.classification == "secret",
                description=definition.description,
            )
            config = await self.set_config(db, payload, user_id)
            updated.append(config)
        return updated

    async def list_vault_values(
        self,
        db: AsyncSession,
        classification: str | None = None,
    ) -> list[VaultValueResponse]:
        definitions = self.list_vault_definitions()
        db_rows: dict[str, ConfigEntryModel] = {}
        try:
            rows = await self.get_configs(db, environment="default", include_secrets=True)
            db_rows = {row.key: row for row in rows}
        except Exception as exc:
            logger.warning("Config table unavailable, continuing with environment values only: {}", exc)

        items: list[VaultValueResponse] = []
        for item in definitions:
            if classification and item.classification != classification:
                continue
            source = "default"
            is_set = False
            value: Any = None
            updated_at = None
            updated_by = None

            row = db_rows.get(item.key)
            if row is not None:
                source = "db_override"
                is_set = row.value is not None
                value = self._decrypt_secret_payload(row.value) if row.is_secret else row.value
                updated_at = row.updated_at
                updated_by = row.updated_by
            elif item.key in os.environ:
                source = "environment"
                is_set = True
                value = os.getenv(item.key)

            definition = self._definition_for_key(item.key)
            items.append(
                VaultValueResponse(
                    key=item.key,
                    classification=item.classification,
                    value_type=item.value_type,
                    effective_source=source,  # type: ignore[arg-type]
                    is_set=is_set,
                    masked_value=self._mask_value(definition, value),
                    updated_at=updated_at,
                    updated_by=updated_by,
                )
            )

        return items

    async def upsert_vault_value(
        self,
        db: AsyncSession,
        *,
        key: str,
        value: Any,
        actor_id: str,
        actor_type: str,
        reason: str | None,
    ) -> VaultValueResponse:
        definition = self._definition_for_key(key)
        errors = self.validate_vault_candidate(key, value)
        if errors:
            raise ValueError("; ".join(errors))

        normalized = self._normalize_value(definition, value)
        payload = ConfigCreate(
            key=key,
            value=normalized,
            type="number" if definition.value_type == "integer" else ("boolean" if definition.value_type == "boolean" else "string"),
            environment="default",
            is_secret=definition.classification == "secret",
            description=definition.description,
        )
        model = await self.set_config(db, payload, actor_id)

        await write_unified_audit(
            event_type="config.vault.updated.v1",
            action="config_vault_update",
            actor=actor_id,
            actor_type=actor_type,
            resource_type="config_key",
            resource_id=key,
            severity="info",
            message="Config vault value updated",
            correlation_id=None,
            details={
                "classification": definition.classification,
                "value_type": definition.value_type,
                "reason": reason,
                "source": "db_override",
            },
        )

        return VaultValueResponse(
            key=key,
            classification=definition.classification,  # type: ignore[arg-type]
            value_type=definition.value_type,
            effective_source="db_override",
            is_set=True,
            masked_value=self._mask_value(definition, normalized),
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )

    async def generate_vault_value(
        self,
        db: AsyncSession,
        *,
        key: str,
        actor_id: str,
        actor_type: str,
        reason: str | None,
        length: int | None = None,
    ) -> VaultGenerateResponse:
        definition = self._definition_for_key(key)
        if not definition.generator_supported:
            raise ValueError(f"Generator not supported for key '{key}'")

        generated = self._generate_candidate_value(key, length)

        await self.upsert_vault_value(
            db,
            key=key,
            value=generated,
            actor_id=actor_id,
            actor_type=actor_type,
            reason=reason or "generated",
        )

        return VaultGenerateResponse(
            key=key,
            generated=True,
            masked_value=self._mask_value(definition, generated),
            revealed_value=generated,
        )

    async def create_rotation_request(
        self,
        db: AsyncSession,
        *,
        key: str,
        value: Any,
        generate: bool,
        length: int | None,
        actor_id: str,
        actor_type: str,
        reason: str | None,
    ) -> VaultRotationRequestResponse:
        definition = self._definition_for_key(key)
        if generate:
            if not definition.generator_supported:
                raise ValueError(f"Generator not supported for key '{key}'")
            candidate = self._generate_candidate_value(key, length)
        else:
            candidate = value

        errors = self.validate_vault_candidate(key, candidate)
        if errors:
            raise ValueError("; ".join(errors))

        normalized = self._normalize_value(definition, candidate)
        candidate_payload = normalized
        candidate_encrypted = False
        if definition.classification == "secret":
            candidate_payload = self._encrypt_secret_payload(str(normalized))
            candidate_encrypted = True

        pending_payload = {
            "status": "pending",
            "target_key": key,
            "classification": definition.classification,
            "candidate": candidate_payload,
            "candidate_encrypted": candidate_encrypted,
            "requested_by": actor_id,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "requested_reason": reason,
        }

        pending_entry = ConfigCreate(
            key=self._rotation_storage_key(key),
            value=pending_payload,
            type="json",
            environment="default",
            is_secret=False,
            description=f"Pending rotation request for {key}",
        )
        await self.set_config(db, pending_entry, actor_id)

        await write_unified_audit(
            event_type="config.vault.rotation.requested.v1",
            action="config_vault_rotation_request",
            actor=actor_id,
            actor_type=actor_type,
            resource_type="config_key",
            resource_id=key,
            severity="info",
            message="Config vault rotation requested",
            correlation_id=None,
            details={
                "classification": definition.classification,
                "reason": reason,
            },
        )

        return VaultRotationRequestResponse(
            key=key,
            status="pending",
            classification=definition.classification,  # type: ignore[arg-type]
            requested_by=actor_id,
            requested_at=datetime.now(timezone.utc),
            requested_reason=reason,
            masked_candidate=self._mask_value(definition, normalized),
        )

    async def list_rotation_requests(self, db: AsyncSession) -> list[VaultRotationRequestResponse]:
        result = await db.execute(
            select(ConfigEntryModel).where(ConfigEntryModel.key.like(f"{self.ROTATION_KEY_PREFIX}:%"))
        )
        rows = list(result.scalars().all())
        items: list[VaultRotationRequestResponse] = []
        for row in rows:
            payload = row.value if isinstance(row.value, dict) else {}
            target_key = payload.get("target_key") or self._rotation_target_key(row.key)
            definition = self._definition_for_key(target_key)
            requested_at_raw = payload.get("requested_at")
            try:
                requested_at = datetime.fromisoformat(str(requested_at_raw)) if requested_at_raw else datetime.now(timezone.utc)
            except Exception:
                requested_at = datetime.now(timezone.utc)
            candidate = self._candidate_from_rotation_payload(payload)
            items.append(
                VaultRotationRequestResponse(
                    key=target_key,
                    status="pending",
                    classification=definition.classification,  # type: ignore[arg-type]
                    requested_by=str(payload.get("requested_by") or row.updated_by or "unknown"),
                    requested_at=requested_at,
                    requested_reason=payload.get("requested_reason"),
                    masked_candidate=self._mask_value(definition, candidate),
                )
            )
        return sorted(items, key=lambda x: x.requested_at, reverse=True)

    async def approve_rotation_request(
        self,
        db: AsyncSession,
        *,
        key: str,
        actor_id: str,
        actor_type: str,
        reason: str | None,
    ) -> VaultValueResponse:
        pending = await self.get_config(db, self._rotation_storage_key(key), "default")
        if pending is None or not isinstance(pending.value, dict):
            raise ValueError(f"No pending rotation request found for '{key}'")

        payload = pending.value
        candidate = self._candidate_from_rotation_payload(payload)
        if candidate is None:
            raise ValueError("Pending rotation payload is invalid")

        response = await self.upsert_vault_value(
            db,
            key=key,
            value=candidate,
            actor_id=actor_id,
            actor_type=actor_type,
            reason=reason or "rotation-approved",
        )
        await self.delete_config(db, self._rotation_storage_key(key), "default")

        await write_unified_audit(
            event_type="config.vault.rotation.approved.v1",
            action="config_vault_rotation_approve",
            actor=actor_id,
            actor_type=actor_type,
            resource_type="config_key",
            resource_id=key,
            severity="info",
            message="Config vault rotation approved",
            correlation_id=None,
            details={"reason": reason},
        )
        return response

    async def reject_rotation_request(
        self,
        db: AsyncSession,
        *,
        key: str,
        actor_id: str,
        actor_type: str,
        reason: str | None,
    ) -> VaultRotationRequestResponse:
        pending = await self.get_config(db, self._rotation_storage_key(key), "default")
        if pending is None or not isinstance(pending.value, dict):
            raise ValueError(f"No pending rotation request found for '{key}'")

        payload = pending.value
        definition = self._definition_for_key(key)
        candidate = self._candidate_from_rotation_payload(payload)
        await self.delete_config(db, self._rotation_storage_key(key), "default")

        await write_unified_audit(
            event_type="config.vault.rotation.rejected.v1",
            action="config_vault_rotation_reject",
            actor=actor_id,
            actor_type=actor_type,
            resource_type="config_key",
            resource_id=key,
            severity="warning",
            message="Config vault rotation rejected",
            correlation_id=None,
            details={"reason": reason},
        )

        requested_at_raw = payload.get("requested_at")
        requested_at = datetime.now(timezone.utc)
        if requested_at_raw:
            try:
                requested_at = datetime.fromisoformat(str(requested_at_raw))
            except Exception:
                pass

        return VaultRotationRequestResponse(
            key=key,
            status="rejected",
            classification=definition.classification,  # type: ignore[arg-type]
            requested_by=str(payload.get("requested_by") or "unknown"),
            requested_at=requested_at,
            requested_reason=payload.get("requested_reason") or reason,
            masked_candidate=self._mask_value(definition, candidate),
        )


_service = None


def get_config_service(event_stream=None):
    global _service
    if _service is None:
        _service = ConfigManagementService(event_stream=event_stream)
    return _service
