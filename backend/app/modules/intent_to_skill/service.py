from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.skill_engine.schemas import SkillRunCreate
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.skills_registry.schemas import SkillSortBy, VersionSelector
from app.modules.skills_registry.service import get_skill_registry_service

from .schemas import (
    IntentCandidateSkill,
    IntentDraftSuggestion,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentResolutionType,
)


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) >= 3
    }


def _slugify(text: str) -> str:
    chunks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return "-".join(chunks[:5]) if chunks else "new-skill"


class IntentToSkillService:
    def _normalize_intent(self, payload: IntentExecuteRequest) -> str:
        parts = [
            payload.intent_text or "",
            payload.problem_statement or "",
            payload.source_url or "",
        ]
        normalized = "\n".join(part.strip() for part in parts if part and part.strip())
        if not normalized:
            raise ValueError("At least one of intent_text, problem_statement, source_url is required")
        return normalized

    def _definition_corpus(self, definition: Any) -> str:
        required_caps = [
            str(cap.get("capability_key", ""))
            for cap in (getattr(definition, "required_capabilities", []) or [])
            if isinstance(cap, dict)
        ]
        optional_caps = [
            str(cap.get("capability_key", ""))
            for cap in (getattr(definition, "optional_capabilities", []) or [])
            if isinstance(cap, dict)
        ]
        return " ".join(
            [
                str(getattr(definition, "skill_key", "")),
                str(getattr(definition, "purpose", "")),
                " ".join(required_caps),
                " ".join(optional_caps),
            ]
        )

    def _score_definition(self, *, intent_tokens: set[str], definition: Any) -> float:
        corpus_tokens = _tokenize(self._definition_corpus(definition))
        if not intent_tokens or not corpus_tokens:
            return 0.0

        overlap = len(intent_tokens.intersection(corpus_tokens))
        base = overlap / max(1, len(intent_tokens))

        skill_key = str(getattr(definition, "skill_key", "")).lower()
        if any(token in skill_key for token in intent_tokens):
            base += 0.12

        value_boost = min(0.1, float(getattr(definition, "value_score", 0.0) or 0.0) * 0.1)
        return round(max(0.0, min(1.0, base + value_boost)), 3)

    def _draft_suggestion(self, normalized_intent: str) -> IntentDraftSuggestion:
        intent_tokens = _tokenize(normalized_intent)
        capabilities: list[str] = []
        if any(token in intent_tokens for token in {"search", "knowledge", "find", "query"}):
            capabilities.append("knowledge.query")
        if any(token in intent_tokens for token in {"write", "generate", "draft", "create"}):
            capabilities.append("text.generate")
        if any(token in intent_tokens for token in {"execute", "run", "workflow", "automation"}):
            capabilities.append("workflow.execute")
        if not capabilities:
            capabilities = ["text.generate", "workflow.execute"]

        return IntentDraftSuggestion(
            suggested_skill_key=f"draft.{_slugify(normalized_intent)}",
            rationale="No active skill reached confidence threshold; generated a draft skill suggestion.",
            recommended_capabilities=capabilities,
        )

    async def execute_intent(
        self,
        db: AsyncSession,
        payload: IntentExecuteRequest,
        principal: Principal,
    ) -> IntentExecuteResponse:
        normalized_intent = self._normalize_intent(payload)
        intent_tokens = _tokenize(normalized_intent)

        registry_service = get_skill_registry_service()
        skill_engine_service = get_skill_engine_service()

        definitions = await registry_service.list_definitions(
            db,
            tenant_id=principal.tenant_id,
            include_system=True,
            status="active",
            sort_by=SkillSortBy.VALUE_SCORE,
        )

        latest_by_key: dict[str, Any] = {}
        for item in definitions:
            existing = latest_by_key.get(item.skill_key)
            if existing is None:
                latest_by_key[item.skill_key] = item
                continue
            if item.version > existing.version:
                latest_by_key[item.skill_key] = item
                continue
            if (
                item.version == existing.version
                and principal.tenant_id
                and item.tenant_id == principal.tenant_id
                and existing.tenant_id != principal.tenant_id
            ):
                latest_by_key[item.skill_key] = item

        candidates: list[IntentCandidateSkill] = []
        for item in latest_by_key.values():
            score = self._score_definition(intent_tokens=intent_tokens, definition=item)
            if score <= 0:
                continue
            candidates.append(
                IntentCandidateSkill(
                    skill_key=item.skill_key,
                    version=item.version,
                    score=score,
                    reason=f"Matched against purpose/capability corpus (risk={item.risk_tier})",
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0] if candidates else None

        if best is None or best.score < payload.min_confidence:
            return IntentExecuteResponse(
                resolution_type=IntentResolutionType.DRAFT_REQUIRED,
                normalized_intent=normalized_intent,
                confidence=round(float(best.score if best else 0.0), 3),
                reason="No matching active skill exceeded minimum confidence",
                candidates=candidates[:5],
                draft_suggestion=self._draft_suggestion(normalized_intent),
            )

        response = IntentExecuteResponse(
            resolution_type=IntentResolutionType.MATCHED_SKILL,
            normalized_intent=normalized_intent,
            confidence=best.score,
            reason="Matched to active skill with sufficient confidence",
            matched_skill_key=best.skill_key,
            matched_skill_version=best.version,
            candidates=candidates[:5],
        )

        if not payload.auto_execute:
            return response

        run_payload = SkillRunCreate(
            skill_key=best.skill_key,
            version=best.version,
            input_payload={
                **payload.input_payload,
                "intent_text": payload.intent_text,
                "problem_statement": payload.problem_statement,
                "source_url": payload.source_url,
                "normalized_intent": normalized_intent,
                "intent_context": payload.context,
            },
            idempotency_key=f"intent-{uuid.uuid4().hex}",
            trigger_type=payload.trigger_type,
            mission_id=payload.mission_id,
            governance_snapshot={
                "origin": "intent_to_skill",
                "resolution_confidence": best.score,
                "selector": VersionSelector.ACTIVE.value,
            },
        )

        run = await skill_engine_service.create_run(db, run_payload, principal)
        report = await skill_engine_service.execute_run(db, run.id, principal)

        response.skill_run = report.skill_run
        response.execution_report = report
        return response


_intent_to_skill_service: IntentToSkillService | None = None


def get_intent_to_skill_service() -> IntentToSkillService:
    global _intent_to_skill_service
    if _intent_to_skill_service is None:
        _intent_to_skill_service = IntentToSkillService()
    return _intent_to_skill_service
