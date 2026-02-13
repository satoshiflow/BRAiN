# backend/brain/agents/llm_client.py
"""
DEPRECATED – use backend.modules.llm_client instead.

Dieser Wrapper existiert nur, um alte Imports nicht zu brechen.
"""

from modules.llm_client import LLMClient, get_llm_client

__all__ = ["LLMClient", "get_llm_client"]