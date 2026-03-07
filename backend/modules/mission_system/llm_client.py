# backend/modules/mission_system/llm_client.py
"""
DEPRECATED – use backend.modules.llm_client instead.
"""

from pathlib import Path
import sys

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.append(str(_repo_root))

from backend.modules.llm_client import LLMClient, get_llm_client

__all__ = ["LLMClient", "get_llm_client"]
