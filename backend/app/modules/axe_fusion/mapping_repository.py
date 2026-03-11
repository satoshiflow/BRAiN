"""Persistence helpers for AXE sanitizer mapping telemetry."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _result_rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


@dataclass(frozen=True)
class MappingEntryRecord:
    placeholder: str
    entity_type: str
    original_hash: str
    hash_key_version: int
    preview_redacted: str
    ordinal: int


class AXEMappingRepository:
    """Stores privacy-safe mapping metadata and deanonymization outcomes."""

    _ENTITY_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
    _ENTITY_TYPE_ALLOWLIST = {
        "email",
        "phone",
        "ip",
        "card",
        "path",
        "secret",
    }

    def __init__(self) -> None:
        self._hash_key = os.getenv("AXE_MAPPING_HASH_KEY", "dev-axe-mapping-key")
        self._hash_key_version = int(os.getenv("AXE_MAPPING_HASH_KEY_VERSION", "1"))
        self._hash_keys_by_version = self._load_hash_key_registry()

    def _load_hash_key_registry(self) -> Dict[int, str]:
        registry: Dict[int, str] = {}
        csv_map = os.getenv("AXE_MAPPING_HASH_KEYS", "").strip()
        if csv_map:
            for item in csv_map.split(","):
                if ":" not in item:
                    continue
                version_raw, key = item.split(":", 1)
                try:
                    version = int(version_raw.strip())
                except ValueError:
                    continue
                cleaned_key = key.strip()
                if cleaned_key:
                    registry[version] = cleaned_key

        current_key = self._hash_key.strip()
        if current_key:
            registry.setdefault(self._hash_key_version, current_key)
        return registry

    def _hash_key_for_version(self, key_version: int) -> str:
        key = self._hash_keys_by_version.get(key_version)
        if key:
            return key
        return self._hash_key

    def fingerprint_messages(self, messages: List[Dict[str, Any]]) -> str:
        payload = _json_dumps(messages).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def fingerprint_text(self, value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()

    def hash_value(self, value: str, *, key_version: Optional[int] = None) -> str:
        normalized = (value or "").strip()
        resolved_key_version = key_version if key_version is not None else self._hash_key_version
        hash_key = self._hash_key_for_version(resolved_key_version)
        digest = hmac.new(
            hash_key.encode("utf-8"),
            normalized.encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()

    def _sanitize_entity_type(self, entity_type: str) -> str:
        normalized = (entity_type or "").strip().lower()
        if normalized in self._ENTITY_TYPE_ALLOWLIST:
            return normalized
        if self._ENTITY_TYPE_PATTERN.match(normalized):
            return normalized
        return "unknown"

    def redact_preview(self, value: str, cap: int = 24) -> str:
        if not value:
            return ""
        shortened = value[:cap]
        if len(shortened) <= 6:
            return "*" * len(shortened)
        return f"{shortened[:3]}***{shortened[-3:]}"

    def mapping_entries_from_replacements(self, replacements: Dict[str, str]) -> List[MappingEntryRecord]:
        entries: List[MappingEntryRecord] = []
        for ordinal, placeholder in enumerate(sorted(replacements.keys())):
            original = replacements[placeholder]
            entity_type = self._sanitize_entity_type(placeholder.strip("[]").split("_", 1)[0].lower())
            entries.append(
                MappingEntryRecord(
                    placeholder=placeholder,
                    entity_type=entity_type,
                    original_hash=self.hash_value(original, key_version=self._hash_key_version),
                    hash_key_version=self._hash_key_version,
                    preview_redacted=self.redact_preview(original),
                    ordinal=ordinal,
                )
            )
        return entries

    async def record_mapping_set(
        self,
        db: AsyncSession,
        *,
        request_id: str,
        provider: str,
        provider_model: str,
        sanitization_level: str,
        message_fingerprint: str,
        mapping_count: int,
        principal_id: Optional[str] = None,
    ) -> str:
        mapping_set_id = str(uuid4())
        principal_hash = self.hash_value(principal_id) if principal_id else None
        created_at = _utc_now()
        expires_at = created_at + timedelta(days=90)
        inserted = await db.execute(
            text(
                """
                INSERT INTO axe_mapping_sets (
                    id, request_id, provider, provider_model, sanitization_level,
                    principal_hash, message_fingerprint, mapping_count, created_at, expires_at
                ) VALUES (
                    :id, :request_id, :provider, :provider_model, :sanitization_level,
                    :principal_hash, :message_fingerprint, :mapping_count, :created_at, :expires_at
                )
                ON CONFLICT (request_id, provider, message_fingerprint)
                DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": mapping_set_id,
                "request_id": request_id,
                "provider": provider,
                "provider_model": provider_model,
                "sanitization_level": sanitization_level,
                "principal_hash": principal_hash,
                "message_fingerprint": message_fingerprint,
                "mapping_count": mapping_count,
                "created_at": created_at,
                "expires_at": expires_at,
            },
        )
        inserted_row = inserted.first()
        if inserted_row:
            inserted_mapping = dict(inserted_row._mapping)
            return str(inserted_mapping.get("id", mapping_set_id))
        row = (await db.execute(
            text(
                """
                SELECT id FROM axe_mapping_sets
                WHERE request_id = :request_id
                  AND provider = :provider
                  AND message_fingerprint = :message_fingerprint
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "request_id": request_id,
                "provider": provider,
                "message_fingerprint": message_fingerprint,
            },
        )).first()
        if row is None:
            return mapping_set_id
        row_mapping = dict(row._mapping)
        return str(row_mapping.get("id", mapping_set_id))

    async def record_mapping_entries(
        self,
        db: AsyncSession,
        *,
        mapping_set_id: str,
        entries: Iterable[MappingEntryRecord],
    ) -> None:
        for entry in entries:
            await db.execute(
                text(
                    """
                    INSERT INTO axe_mapping_entries (
                        id, mapping_set_id, placeholder, entity_type,
                        original_hash, hash_key_version, preview_redacted,
                        ordinal, created_at
                    ) VALUES (
                        :id, :mapping_set_id, :placeholder, :entity_type,
                        :original_hash, :hash_key_version, :preview_redacted,
                        :ordinal, :created_at
                    )
                    ON CONFLICT (mapping_set_id, placeholder) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid4()),
                    "mapping_set_id": mapping_set_id,
                    "placeholder": entry.placeholder,
                    "entity_type": entry.entity_type,
                    "original_hash": entry.original_hash,
                    "hash_key_version": entry.hash_key_version,
                    "preview_redacted": entry.preview_redacted,
                    "ordinal": entry.ordinal,
                    "created_at": _utc_now(),
                },
            )

    async def record_deanonymization_attempt(
        self,
        db: AsyncSession,
        *,
        request_id: str,
        mapping_set_id: str,
        attempt_no: int,
        status: str,
        reason_code: Optional[str],
        placeholder_count: int,
        restored_count: int,
        unresolved_placeholders: List[str],
        response_fingerprint: str,
    ) -> None:
        idem_material = f"{request_id}:{mapping_set_id}:{attempt_no}:{response_fingerprint}"
        idempotency_key = hashlib.sha256(idem_material.encode("utf-8")).hexdigest()
        await db.execute(
            text(
                """
                INSERT INTO axe_deanonymization_attempts (
                    id, request_id, mapping_set_id, attempt_no, status, reason_code,
                    placeholder_count, restored_count, unresolved_placeholders,
                    response_fingerprint, idempotency_key, created_at
                ) VALUES (
                    :id, :request_id, :mapping_set_id, :attempt_no, :status, :reason_code,
                    :placeholder_count, :restored_count, CAST(:unresolved_placeholders AS jsonb),
                    :response_fingerprint, :idempotency_key, :created_at
                )
                ON CONFLICT (idempotency_key) DO NOTHING
                """
            ),
            {
                "id": str(uuid4()),
                "request_id": request_id,
                "mapping_set_id": mapping_set_id,
                "attempt_no": attempt_no,
                "status": status,
                "reason_code": reason_code,
                "placeholder_count": placeholder_count,
                "restored_count": restored_count,
                "unresolved_placeholders": _json_dumps(unresolved_placeholders),
                "response_fingerprint": response_fingerprint,
                "idempotency_key": idempotency_key,
                "created_at": _utc_now(),
            },
        )

    async def get_next_attempt_no(
        self,
        db: AsyncSession,
        *,
        request_id: str,
        mapping_set_id: str,
    ) -> int:
        row = (
            await db.execute(
                text(
                    """
                    SELECT COALESCE(MAX(attempt_no), 0) + 1 AS next_attempt
                    FROM axe_deanonymization_attempts
                    WHERE request_id = :request_id
                      AND mapping_set_id = CAST(:mapping_set_id AS uuid)
                    """
                ),
                {
                    "request_id": request_id,
                    "mapping_set_id": mapping_set_id,
                },
            )
        ).first()
        if row is None:
            return 1
        data = dict(row._mapping)
        return int(data.get("next_attempt", 1))

    async def list_deanonymization_outcomes(
        self,
        db: AsyncSession,
        *,
        request_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        rows = await db.execute(
            text(
                """
                SELECT
                    a.request_id,
                    s.provider,
                    s.provider_model,
                    a.status,
                    a.reason_code,
                    a.placeholder_count,
                    a.restored_count,
                    a.unresolved_placeholders,
                    a.created_at
                FROM axe_deanonymization_attempts a
                JOIN axe_mapping_sets s ON s.id = a.mapping_set_id
                WHERE (:request_id IS NULL OR a.request_id = :request_id)
                  AND (:status IS NULL OR a.status = :status)
                ORDER BY a.created_at DESC
                LIMIT :limit
                """
            ),
            {
                "request_id": request_id,
                "status": status,
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in rows]

    async def list_learning_candidates(
        self,
        db: AsyncSession,
        *,
        provider: Optional[str] = None,
        gate_state: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        rows = await db.execute(
            text(
                """
                SELECT
                    id,
                    window_start,
                    window_end,
                    provider,
                    pattern_name,
                    sample_size,
                    failure_rate,
                    confidence_score,
                    risk_score,
                    proposed_change,
                    gate_state,
                    approved_by,
                    approved_at,
                    created_at
                FROM axe_learning_candidates
                WHERE (:provider IS NULL OR provider = :provider)
                  AND (:gate_state IS NULL OR gate_state = :gate_state)
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {
                "provider": provider,
                "gate_state": gate_state,
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in rows]

    async def set_learning_candidate_state(
        self,
        db: AsyncSession,
        *,
        candidate_id: str,
        new_state: str,
        approved_by: Optional[str],
    ) -> bool:
        result = await db.execute(
            text(
                """
                UPDATE axe_learning_candidates
                SET gate_state = :new_state,
                    approved_by = :approved_by,
                    approved_at = CASE WHEN :new_state = 'approved' THEN NOW() ELSE approved_at END
                WHERE id = CAST(:candidate_id AS uuid)
                """
            ),
            {
                "candidate_id": candidate_id,
                "new_state": new_state,
                "approved_by": approved_by,
            },
        )
        return _result_rowcount(result) > 0

    async def run_retention_cleanup(self, db: AsyncSession) -> Dict[str, int]:
        retention_run_id = str(uuid4())
        started = _utc_now()
        await db.execute(
            text(
                """
                INSERT INTO axe_data_retention_runs (id, run_started_at, status)
                VALUES (CAST(:id AS uuid), :run_started_at, 'running')
                """
            ),
            {"id": retention_run_id, "run_started_at": started},
        )

        deleted_attempts = 0
        deleted_mapping_sets = 0
        deleted_candidates = 0
        try:
            attempts_result = await db.execute(
                text(
                    """
                    DELETE FROM axe_deanonymization_attempts a
                    USING axe_mapping_sets s
                    WHERE a.mapping_set_id = s.id
                      AND s.expires_at < NOW()
                    """
                )
            )
            deleted_attempts = _result_rowcount(attempts_result)

            mapping_result = await db.execute(
                text(
                    """
                    DELETE FROM axe_mapping_sets
                    WHERE expires_at < NOW()
                    """
                )
            )
            deleted_mapping_sets = _result_rowcount(mapping_result)

            candidates_result = await db.execute(
                text(
                    """
                    DELETE FROM axe_learning_candidates
                    WHERE created_at < NOW() - INTERVAL '180 days'
                    """
                )
            )
            deleted_candidates = _result_rowcount(candidates_result)

            await db.execute(
                text(
                    """
                    UPDATE axe_data_retention_runs
                    SET run_finished_at = NOW(),
                        deleted_mapping_sets = :deleted_mapping_sets,
                        deleted_attempts = :deleted_attempts,
                        deleted_candidates = :deleted_candidates,
                        status = 'succeeded',
                        error_summary = NULL
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {
                    "id": retention_run_id,
                    "deleted_mapping_sets": deleted_mapping_sets,
                    "deleted_attempts": deleted_attempts,
                    "deleted_candidates": deleted_candidates,
                },
            )
        except Exception as exc:
            await db.execute(
                text(
                    """
                    UPDATE axe_data_retention_runs
                    SET run_finished_at = NOW(),
                        status = 'failed',
                        error_summary = :error_summary
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {
                    "id": retention_run_id,
                    "error_summary": str(exc)[:500],
                },
            )
            raise

        return {
            "deleted_mapping_sets": deleted_mapping_sets,
            "deleted_attempts": deleted_attempts,
            "deleted_candidates": deleted_candidates,
        }

    async def generate_learning_candidates(
        self,
        db: AsyncSession,
        *,
        window_days: int = 7,
        min_sample_size: int = 50,
    ) -> int:
        result = await db.execute(
            text(
                """
                WITH aggregate_source AS (
                    SELECT
                        s.provider AS provider,
                        e.entity_type AS pattern_name,
                        COUNT(*)::int AS sample_size,
                        SUM(CASE WHEN a.status IN ('partial', 'failed') THEN 1 ELSE 0 END)::int AS failure_count
                    FROM axe_deanonymization_attempts a
                    JOIN axe_mapping_sets s ON s.id = a.mapping_set_id
                    JOIN axe_mapping_entries e ON e.mapping_set_id = s.id
                    WHERE a.created_at >= NOW() - make_interval(days => :window_days)
                    GROUP BY s.provider, e.entity_type
                )
                INSERT INTO axe_learning_candidates (
                    id,
                    window_start,
                    window_end,
                    provider,
                    pattern_name,
                    sample_size,
                    failure_rate,
                    confidence_score,
                    risk_score,
                    proposed_change,
                    gate_state,
                    created_at
                )
                SELECT
                    gen_random_uuid(),
                    NOW() - make_interval(days => :window_days),
                    NOW(),
                    src.provider,
                    src.pattern_name,
                    src.sample_size,
                    CASE WHEN src.sample_size = 0 THEN 0::numeric ELSE (src.failure_count::numeric / src.sample_size::numeric) END,
                    LEAST(1.0, src.sample_size::numeric / 1000.0),
                    CASE WHEN src.sample_size = 0 THEN 0::numeric ELSE (src.failure_count::numeric / src.sample_size::numeric) END,
                    jsonb_build_object(
                        'action', 'review_pattern',
                        'entity_type', src.pattern_name,
                        'window_days', :window_days,
                        'sample_size', src.sample_size
                    ),
                    CASE
                        WHEN src.sample_size < 200 THEN 'needs_human_review'
                        WHEN (src.failure_count::numeric / NULLIF(src.sample_size::numeric, 0)) > 0.30 THEN 'needs_human_review'
                        ELSE 'pending_auto_gate'
                    END,
                    NOW()
                FROM aggregate_source src
                WHERE src.sample_size >= :min_sample_size
                ON CONFLICT (window_start, window_end, provider, pattern_name) DO NOTHING
                """
            ),
            {
                "window_days": window_days,
                "min_sample_size": min_sample_size,
            },
        )
        return _result_rowcount(result)
