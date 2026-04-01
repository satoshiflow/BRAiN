from __future__ import annotations

from app.modules.axe_fusion.context_management import (
    CONTEXT_MODE_COMPACTED,
    CONTEXT_MODE_FULL,
    CONTEXT_MODE_RETRIEVAL_AUGMENTED,
    build_context_envelope,
)


def test_context_envelope_keeps_governance_segment() -> None:
    messages = [
        {"role": "system", "content": "governance: tenant isolation required"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    selected, telemetry = build_context_envelope(messages, max_prompt_tokens=128)
    assert any(item.get("role") == "system" for item in selected)
    assert telemetry.context_mode == CONTEXT_MODE_FULL


def test_context_envelope_applies_retrieval_when_overlap_exists() -> None:
    messages = [
        {"role": "user", "content": "We troubleshoot worker queue starvation in task lease"},
        {"role": "assistant", "content": "Acknowledged"},
        {"role": "user", "content": "Please re-check worker lease queue for starvation"},
    ]

    selected, telemetry = build_context_envelope(
        messages,
        max_prompt_tokens=512,
        short_term_turns=1,
        retrieval_top_k=2,
    )
    assert telemetry.retrieval_applied is True
    assert telemetry.context_mode in {CONTEXT_MODE_RETRIEVAL_AUGMENTED, CONTEXT_MODE_FULL}
    assert len(selected) >= 2


def test_context_envelope_compacts_large_history() -> None:
    messages = [{"role": "system", "content": "governance prompt"}]
    for idx in range(35):
        role = "user" if idx % 2 == 0 else "assistant"
        messages.append({"role": role, "content": f"turn-{idx} lorem ipsum context payload"})

    selected, telemetry = build_context_envelope(
        messages,
        max_prompt_tokens=300,
        summary_trigger_messages=20,
        short_term_turns=6,
    )

    assert telemetry.compression_applied is True
    assert telemetry.context_mode == CONTEXT_MODE_COMPACTED
    assert any("Session summary" in str(item.get("content")) for item in selected)
