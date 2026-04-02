from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.knowledge_engine.service import get_knowledge_engine_service

from .schemas import (
    ExperienceCachePolicy,
    ExperiencePayload,
    ExperienceRenderRequest,
    ExperienceSection,
    ExperienceSourceRef,
    ExperienceSafety,
    ExperienceType,
    OutputEnvelope,
    OutputTarget,
    OutputType,
)


class ExperienceComposerService:
    def __init__(self, knowledge_service: Any | None = None) -> None:
        self.knowledge_service = knowledge_service or get_knowledge_engine_service()

    async def render(
        self,
        db: AsyncSession,
        principal: Principal,
        payload: ExperienceRenderRequest,
    ) -> OutputEnvelope:
        items = await self._resolve_knowledge_items(db, principal, payload)
        sources = self._build_sources(items)
        summary = self._build_summary(payload, items)
        warnings = self._build_warnings(payload)

        if payload.experience_type == ExperienceType.CHAT_ANSWER:
            return OutputEnvelope(
                type=OutputType.ANSWER,
                target=OutputTarget.CHAT,
                payload={
                    "text": self._build_chat_text(payload, summary, sources),
                    "sources": [source.model_dump(mode="json") for source in sources],
                },
                metadata=self._build_metadata(principal, payload, items),
            )

        experience_payload = ExperiencePayload(
            experience_type=payload.experience_type,
            variant=payload.experience_type.value,
            context={
                "intent": payload.intent.value,
                "audience": payload.audience.type.value,
                "audience_id": payload.audience.id,
                "device": payload.context.device,
                "locale": payload.context.locale,
                "customer_id": payload.context.customer_id,
                "region": payload.context.region,
                "season": payload.context.season,
                "user_skill": payload.context.user_skill,
            },
            data={
                "summary": summary,
                "subject": payload.subject.model_dump(mode="json"),
                "audience": payload.audience.model_dump(mode="json"),
                "knowledge_items": items,
                "next_step": self._build_next_step(payload),
            },
            sources=sources,
            sections=self._build_sections(payload.experience_type),
            safety=ExperienceSafety(mode="strict", warnings=warnings),
            cache=self._build_cache_policy(payload.experience_type),
        )

        output_type = OutputType.PRESENTATION if payload.experience_type == ExperienceType.PRESENTATION else OutputType.UI
        output_target = self._target_for_experience(payload.experience_type)
        return OutputEnvelope(
            type=output_type,
            target=output_target,
            payload=experience_payload.model_dump(mode="json"),
            metadata=self._build_metadata(principal, payload, items),
        )

    async def _resolve_knowledge_items(
        self,
        db: AsyncSession,
        principal: Principal,
        payload: ExperienceRenderRequest,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        subject_id = payload.subject.id
        if subject_id:
            try:
                item = await self.knowledge_service.get_item(db, principal, UUID(subject_id))
            except (ValueError, TypeError):
                item = None
            if item is not None:
                item_id = str(item.get("id"))
                seen_ids.add(item_id)
                items.append(item)

        query = payload.subject.query or self._extract_query_from_input(payload)
        if query:
            results = await self.knowledge_service.semantic_search(db, principal, query, limit=4)
            for item in results:
                item_id = str(item.get("id"))
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                items.append(item)

        return items[:4]

    @staticmethod
    def _extract_query_from_input(payload: ExperienceRenderRequest) -> str | None:
        if payload.input is None:
            return None
        content = payload.input.content or {}
        for key in ("text", "query", "prompt", "caption"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _build_sources(items: list[dict[str, Any]]) -> list[ExperienceSourceRef]:
        sources: list[ExperienceSourceRef] = []
        for item in items:
            sources.append(
                ExperienceSourceRef(
                    id=str(item.get("id")),
                    title=str(item.get("title") or "Untitled knowledge item"),
                    type=str(item.get("type") or "note"),
                    tags=[str(tag) for tag in (item.get("tags") or [])],
                )
            )
        return sources

    def _build_summary(self, payload: ExperienceRenderRequest, items: list[dict[str, Any]]) -> dict[str, Any]:
        if items:
            first = items[0]
            title = str(first.get("title") or payload.subject.query or payload.subject.type)
            body = self._trim_text(str(first.get("content") or ""), 420)
            return {
                "title": title,
                "body": body,
                "source_count": len(items),
            }

        fallback_query = payload.subject.query or self._extract_query_from_input(payload) or payload.subject.type
        return {
            "title": fallback_query,
            "body": "Noch keine verknuepften Wissenseintraege gefunden. Die Experience basiert vorerst auf Anfrage und Kontext.",
            "source_count": 0,
        }

    @staticmethod
    def _trim_text(text: str, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    @staticmethod
    def _build_warnings(payload: ExperienceRenderRequest) -> list[str]:
        warnings: list[str] = []
        if payload.context.user_skill and payload.context.user_skill.lower() in {"beginner", "starter", "novice"}:
            warnings.append("Darstellung auf einfache, risikoarme Schritte reduziert.")
        if payload.audience.type.value == "public":
            warnings.append("Oeffentliche Ausgabe: sensible Details und interne Annahmen ausblenden.")
        return warnings

    @staticmethod
    def _build_next_step(payload: ExperienceRenderRequest) -> dict[str, Any]:
        if payload.experience_type == ExperienceType.PRESENTATION:
            label = "Praesentationsgespraech vorbereiten"
        elif payload.experience_type == ExperienceType.CHAT_ANSWER:
            label = "Rueckfrage anbieten"
        elif payload.experience_type == ExperienceType.MOBILE_VIEW:
            label = "Mobile Kurzansicht weiter verdichten"
        else:
            label = "Konkrete Anschlussaktion definieren"
        return {"label": label, "intent": payload.intent.value}

    @staticmethod
    def _build_sections(experience_type: ExperienceType) -> list[ExperienceSection]:
        if experience_type == ExperienceType.PRESENTATION:
            return [
                ExperienceSection(component="title_slide", data_ref="summary"),
                ExperienceSection(component="key_points", data_ref="knowledge_items"),
                ExperienceSection(component="source_slide", data_ref="sources"),
                ExperienceSection(component="next_steps", data_ref="next_step"),
            ]
        if experience_type == ExperienceType.MOBILE_VIEW:
            return [
                ExperienceSection(component="compact_header", data_ref="summary"),
                ExperienceSection(component="step_list", data_ref="knowledge_items"),
                ExperienceSection(component="warning_box", data_ref="safety"),
                ExperienceSection(component="source_list", data_ref="sources"),
            ]
        if experience_type == ExperienceType.CUSTOMER_EXPLAINER:
            return [
                ExperienceSection(component="hero_card", data_ref="summary"),
                ExperienceSection(component="audience_context", data_ref="audience"),
                ExperienceSection(component="summary_block", data_ref="summary"),
                ExperienceSection(component="source_list", data_ref="sources"),
                ExperienceSection(component="cta_block", data_ref="next_step"),
            ]
        return [
            ExperienceSection(component="hero_card", data_ref="summary"),
            ExperienceSection(component="summary_block", data_ref="summary"),
            ExperienceSection(component="source_list", data_ref="sources"),
            ExperienceSection(component="cta_block", data_ref="next_step"),
        ]

    @staticmethod
    def _build_cache_policy(experience_type: ExperienceType) -> ExperienceCachePolicy:
        if experience_type == ExperienceType.CHAT_ANSWER:
            return ExperienceCachePolicy(ttl_seconds=300, persist=False)
        if experience_type == ExperienceType.MOBILE_VIEW:
            return ExperienceCachePolicy(ttl_seconds=900, persist=False)
        if experience_type == ExperienceType.PRESENTATION:
            return ExperienceCachePolicy(ttl_seconds=3600, persist=False)
        return ExperienceCachePolicy(ttl_seconds=1800, persist=False)

    @staticmethod
    def _target_for_experience(experience_type: ExperienceType) -> OutputTarget:
        if experience_type == ExperienceType.MOBILE_VIEW:
            return OutputTarget.MOBILE
        return OutputTarget.WEB

    @staticmethod
    def _build_chat_text(
        payload: ExperienceRenderRequest,
        summary: dict[str, Any],
        sources: list[ExperienceSourceRef],
    ) -> str:
        text = summary.get("body") or "Keine passenden Wissenselemente gefunden."
        title = str(summary.get("title") or payload.subject.query or payload.subject.type)
        if sources:
            source_names = ", ".join(source.title for source in sources[:2])
            return f"{title}: {text} Quellenbasis: {source_names}."
        return f"{title}: {text} Kontext: {payload.intent.value}."

    @staticmethod
    def _build_metadata(
        principal: Principal,
        payload: ExperienceRenderRequest,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "principal_id": principal.principal_id,
            "tenant_id": principal.tenant_id,
            "experience_type": payload.experience_type.value,
            "intent": payload.intent.value,
            "knowledge_item_ids": [str(item.get("id")) for item in items],
            "knowledge_item_count": len(items),
        }


_experience_composer_service: ExperienceComposerService | None = None


def get_experience_composer_service() -> ExperienceComposerService:
    global _experience_composer_service
    if _experience_composer_service is None:
        _experience_composer_service = ExperienceComposerService()
    return _experience_composer_service
