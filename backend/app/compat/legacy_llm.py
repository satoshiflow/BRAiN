"""Compatibility bridge for legacy LLM client/config modules."""

from __future__ import annotations

from backend.modules.llm_client import get_llm_client  # noqa: F401
from backend.modules.llm_config import (  # noqa: F401
    LLMConfig,
    LLMConfigUpdate,
    get_llm_config,
    reset_llm_config,
    update_llm_config,
)
