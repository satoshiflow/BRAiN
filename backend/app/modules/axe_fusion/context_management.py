from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


CONTEXT_MODE_FULL = "full"
CONTEXT_MODE_COMPACTED = "compacted"
CONTEXT_MODE_RETRIEVAL_AUGMENTED = "retrieval_augmented"


@dataclass
class ContextTelemetry:
    estimated_prompt_tokens: int
    max_allowed_prompt_tokens: int
    context_mode: str
    trim_applied: bool
    trim_reason: str | None
    token_class: str
    compression_applied: bool
    retrieval_applied: bool
    selected_segment_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "max_allowed_prompt_tokens": self.max_allowed_prompt_tokens,
            "context_mode": self.context_mode,
            "trim_applied": self.trim_applied,
            "trim_reason": self.trim_reason,
            "token_class": self.token_class,
            "compression_applied": self.compression_applied,
            "retrieval_applied": self.retrieval_applied,
            "selected_segment_counts": self.selected_segment_counts,
        }


def _tokenize(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {part for part in cleaned.split() if len(part) >= 3}


def estimate_prompt_tokens(messages: list[dict[str, Any]]) -> int:
    total_chars = 0
    for message in messages:
        content = str(message.get("content") or "")
        total_chars += len(content)
    return max(1, int(math.ceil(total_chars / 4.0)))


def _token_class(estimated_tokens: int, max_tokens: int) -> str:
    ratio = estimated_tokens / max(max_tokens, 1)
    if ratio < 0.35:
        return "small"
    if ratio < 0.75:
        return "medium"
    return "large"


def build_context_envelope(
    messages: list[dict[str, Any]],
    *,
    max_prompt_tokens: int,
    short_term_turns: int = 10,
    summary_trigger_messages: int = 24,
    retrieval_top_k: int = 4,
) -> tuple[list[dict[str, Any]], ContextTelemetry]:
    if not messages:
        telemetry = ContextTelemetry(
            estimated_prompt_tokens=0,
            max_allowed_prompt_tokens=max_prompt_tokens,
            context_mode=CONTEXT_MODE_FULL,
            trim_applied=False,
            trim_reason=None,
            token_class="small",
            compression_applied=False,
            retrieval_applied=False,
            selected_segment_counts={
                "governance": 0,
                "active_turn": 0,
                "short_term": 0,
                "retrieval": 0,
                "summary": 0,
            },
        )
        return [], telemetry

    governance_segment = [msg for msg in messages if msg.get("role") == "system"]
    conversational_messages = [msg for msg in messages if msg.get("role") != "system"]
    if not conversational_messages:
        conversational_messages = list(messages)

    active_turn = conversational_messages[-1:]
    short_term = conversational_messages[-(short_term_turns + 1):-1] if len(conversational_messages) > 1 else []
    historical = conversational_messages[: max(0, len(conversational_messages) - len(short_term) - len(active_turn))]

    retrieval: list[dict[str, Any]] = []
    retrieval_applied = False
    if historical and active_turn:
        active_text = str(active_turn[0].get("content") or "")
        active_tokens = _tokenize(active_text)
        scored: list[tuple[int, dict[str, Any]]] = []
        for candidate in historical:
            candidate_text = str(candidate.get("content") or "")
            overlap = len(active_tokens.intersection(_tokenize(candidate_text)))
            scored.append((overlap, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        retrieval = [item[1] for item in scored[:retrieval_top_k] if item[0] > 0]
        retrieval_applied = len(retrieval) > 0

    summary_segment: list[dict[str, Any]] = []
    compression_applied = False
    if len(conversational_messages) >= summary_trigger_messages and historical:
        compression_applied = True
        summary_lines = []
        for item in historical[-12:]:
            role = item.get("role", "user")
            content = str(item.get("content") or "").strip().replace("\n", " ")
            summary_lines.append(f"- {role}: {content[:160]}")
        summary_segment = [
            {
                "role": "system",
                "content": (
                    "Session summary (compacted context, provenance: previous turns):\n"
                    + "\n".join(summary_lines)
                ),
            }
        ]

    candidate = [
        *governance_segment,
        *summary_segment,
        *retrieval,
        *short_term,
        *active_turn,
    ]

    estimated = estimate_prompt_tokens(candidate)
    trim_applied = False
    trim_reason: str | None = None
    selected_short_term = list(short_term)
    selected_retrieval = list(retrieval)

    while estimated > max_prompt_tokens and (selected_retrieval or selected_short_term):
        trim_applied = True
        trim_reason = "context_budget_exceeded"
        if selected_retrieval:
            selected_retrieval.pop()
        elif selected_short_term:
            selected_short_term.pop(0)
        candidate = [
            *governance_segment,
            *summary_segment,
            *selected_retrieval,
            *selected_short_term,
            *active_turn,
        ]
        estimated = estimate_prompt_tokens(candidate)

    if estimated > max_prompt_tokens:
        trim_applied = True
        trim_reason = "hard_trim_to_active_turn"
        candidate = [*governance_segment, *active_turn]
        estimated = estimate_prompt_tokens(candidate)

    mode = CONTEXT_MODE_FULL
    if compression_applied:
        mode = CONTEXT_MODE_COMPACTED
    elif retrieval_applied:
        mode = CONTEXT_MODE_RETRIEVAL_AUGMENTED

    telemetry = ContextTelemetry(
        estimated_prompt_tokens=estimated,
        max_allowed_prompt_tokens=max_prompt_tokens,
        context_mode=mode,
        trim_applied=trim_applied,
        trim_reason=trim_reason,
        token_class=_token_class(estimated, max_prompt_tokens),
        compression_applied=compression_applied,
        retrieval_applied=retrieval_applied,
        selected_segment_counts={
            "governance": len(governance_segment),
            "active_turn": len(active_turn),
            "short_term": len(selected_short_term),
            "retrieval": len(selected_retrieval),
            "summary": len(summary_segment),
        },
    )
    return candidate, telemetry
