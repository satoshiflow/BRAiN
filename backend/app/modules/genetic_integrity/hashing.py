"""Hashing utilities for DNA snapshot integrity."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


def canonical_payload(payload: Dict[str, Any]) -> str:
    """Return deterministic JSON string for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def snapshot_hash(
    *,
    agent_id: str,
    snapshot_version: int,
    parent_snapshot: Optional[int],
    dna_payload: Dict[str, Any],
) -> str:
    payload_str = canonical_payload(dna_payload)
    preimage = f"{agent_id}|{snapshot_version}|{parent_snapshot}|{payload_str}"
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()
