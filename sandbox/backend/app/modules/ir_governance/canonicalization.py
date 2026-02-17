"""
Canonicalization & Deterministic Hashing - Sprint 9 (P0)

Provides deterministic, platform-independent hashing for IR and steps.

Rules:
- Sorted keys (json.dumps(sort_keys=True))
- No whitespace (separators=(',',':'))
- UTF-8 encoding
- Unicode normalization (forbid control chars)
- NO FLOATS (use integers or decimal strings)
- Consistent enum serialization

Guarantees: Same IR → Same hash (always)
"""

import json
import hashlib
from typing import Any, Dict
from pydantic import BaseModel


def canonical_json(obj: Any) -> str:
    """
    Convert object to canonical JSON string.

    Rules:
    - Sorted keys
    - No whitespace
    - Consistent encoding (UTF-8)
    - Enums converted to values
    - No floats (will raise error if present)

    Args:
        obj: Object to canonicalize (dict, Pydantic model, etc.)

    Returns:
        Canonical JSON string

    Raises:
        TypeError: If object contains floats
        ValueError: If object contains control characters
    """
    # Convert Pydantic models to dict
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()

    # Validate: no floats allowed
    _check_no_floats(obj)

    # Validate: no control characters in strings
    _check_no_control_chars(obj)

    # Serialize with strict rules
    canonical_str = json.dumps(
        obj,
        sort_keys=True,  # Deterministic key order
        separators=(",", ":"),  # No whitespace
        ensure_ascii=False,  # Allow Unicode (UTF-8)
        default=_json_default,  # Handle enums, datetimes
    )

    return canonical_str


def sha256_hex(canonical_str: str) -> str:
    """
    Compute SHA256 hash of canonical string.

    Args:
        canonical_str: Canonical JSON string

    Returns:
        SHA256 hash (hex string)
    """
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def ir_hash(ir: Any) -> str:
    """
    Compute deterministic hash of IR.

    Args:
        ir: IR object (Pydantic model or dict)

    Returns:
        SHA256 hash (hex string)
    """
    canonical_str = canonical_json(ir)
    return sha256_hex(canonical_str)


def step_hash(step: Any) -> str:
    """
    Compute deterministic hash of IR step.

    Args:
        step: IRStep object (Pydantic model or dict)

    Returns:
        SHA256 hash (hex string)
    """
    canonical_str = canonical_json(step)
    return sha256_hex(canonical_str)


def _json_default(obj: Any) -> Any:
    """
    JSON serialization default handler.

    Handles:
    - Enums → values
    - datetime → ISO format
    - Other: raise TypeError

    Args:
        obj: Object to serialize

    Returns:
        Serializable value

    Raises:
        TypeError: If object is not serializable
    """
    # Handle enums
    if hasattr(obj, "value"):
        return obj.value

    # Handle datetime
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    # Cannot serialize
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _check_no_floats(obj: Any, path: str = "root"):
    """
    Recursively check that object contains no floats.

    Floats are forbidden to ensure deterministic hashing.
    Use integers (cents) or decimal strings instead.

    Args:
        obj: Object to check
        path: Current path (for error messages)

    Raises:
        TypeError: If float found
    """
    if isinstance(obj, float):
        raise TypeError(
            f"Float found at '{path}'. Use integers or decimal strings instead. "
            f"Example: use budget_cents=500 (int) instead of budget_usd=5.00 (float)"
        )

    if isinstance(obj, dict):
        for key, value in obj.items():
            _check_no_floats(value, f"{path}.{key}")

    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _check_no_floats(item, f"{path}[{i}]")


def _check_no_control_chars(obj: Any, path: str = "root"):
    """
    Recursively check that strings contain no control characters.

    Control characters (ASCII < 32) can cause issues with canonicalization.

    Args:
        obj: Object to check
        path: Current path (for error messages)

    Raises:
        ValueError: If control character found
    """
    if isinstance(obj, str):
        if any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in obj):
            raise ValueError(
                f"Control character found in string at '{path}'. "
                f"Only printable characters and standard whitespace allowed."
            )

    elif isinstance(obj, dict):
        # Check both keys and values
        for key, value in obj.items():
            _check_no_control_chars(key, f"{path}[key:{key}]")
            _check_no_control_chars(value, f"{path}.{key}")

    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _check_no_control_chars(item, f"{path}[{i}]")


def compute_dag_hash(dag_nodes: list) -> str:
    """
    Compute deterministic hash of DAG for diff-audit.

    Args:
        dag_nodes: List of DAG nodes (each must have ir_step_id and ir_step_hash)

    Returns:
        SHA256 hash (hex string)

    Raises:
        ValueError: If nodes missing required fields
    """
    # Extract canonical representation
    canonical_nodes = []
    for node in dag_nodes:
        if "ir_step_id" not in node or "ir_step_hash" not in node:
            raise ValueError(
                f"DAG node missing required fields (ir_step_id, ir_step_hash): {node}"
            )

        canonical_nodes.append(
            {
                "ir_step_id": node["ir_step_id"],
                "ir_step_hash": node["ir_step_hash"],
            }
        )

    # Sort nodes by ir_step_id for determinism
    canonical_nodes.sort(key=lambda n: n["ir_step_id"])

    # Canonicalize and hash
    canonical_str = canonical_json(canonical_nodes)
    return sha256_hex(canonical_str)


# ============================================================================
# Utility Functions
# ============================================================================

def verify_hash_match(expected: str, actual: str, context: str = "") -> bool:
    """
    Verify that two hashes match.

    Args:
        expected: Expected hash
        actual: Actual hash
        context: Context for error message

    Returns:
        True if hashes match

    Raises:
        ValueError: If hashes don't match
    """
    if expected != actual:
        raise ValueError(
            f"Hash mismatch{' in ' + context if context else ''}: "
            f"expected={expected[:16]}..., actual={actual[:16]}..."
        )
    return True
