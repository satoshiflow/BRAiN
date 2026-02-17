"""
Run Contract System (Sprint 9-B)

Immutable run snapshots for legal and technical reproducibility.
Every pipeline run gets a cryptographically verifiable contract.
"""

from typing import Dict, List, Optional, Any
import json
import hashlib
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger

from app.modules.autonomous_pipeline.schemas import (
    BusinessIntentInput,
    ResolvedBusinessIntent,
    ExecutionGraphSpec,
    ExecutionGraphResult,
)
from app.modules.autonomous_pipeline.governor_schemas import ExecutionPolicy


class RunContract(BaseModel):
    """
    Immutable snapshot of a pipeline run.

    Cryptographically verifiable contract that captures:
    - Input (business intent)
    - Execution graph (DAG)
    - Policy (budget & governance)
    - Results (execution outcome)
    - Hashes (deterministic verification)

    Use cases:
    - Legal proof of execution
    - Deterministic replay
    - Audit trail
    - Compliance evidence
    """

    # Contract identity
    contract_id: str = Field(..., description="Unique contract ID (UUIDv7)")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Input snapshot
    business_intent_input: Optional[BusinessIntentInput] = Field(
        None,
        description="Original natural language input"
    )
    resolved_intent: Optional[ResolvedBusinessIntent] = Field(
        None,
        description="Resolved business intent"
    )

    # Graph snapshot
    graph_spec: ExecutionGraphSpec = Field(..., description="Execution graph specification")

    # Policy snapshot
    policy: Optional[ExecutionPolicy] = Field(None, description="Execution policy applied")

    # Results (filled after execution)
    result: Optional[ExecutionGraphResult] = Field(None, description="Execution result")

    # Hashes (deterministic verification)
    input_hash: str = Field(..., description="SHA256 hash of business intent input")
    graph_hash: str = Field(..., description="SHA256 hash of execution graph")
    policy_hash: str = Field(..., description="SHA256 hash of execution policy")
    contract_hash: str = Field(..., description="SHA256 hash of entire contract")

    # Metadata
    dry_run: bool = Field(..., description="Whether this was a dry-run")
    replay_of: Optional[str] = Field(None, description="Contract ID if this is a replay")

    # Signature (future)
    signature: Optional[str] = Field(None, description="Ed25519 signature (future)")
    signed_by: Optional[str] = Field(None, description="Who signed the contract")

    class Config:
        json_schema_extra = {
            "example": {
                "contract_id": "contract_01j12k34m56n78p90qrs",
                "created_at": "2025-12-26T12:00:00Z",
                "input_hash": "abc123def456...",
                "graph_hash": "def456abc123...",
                "policy_hash": "123abc456def...",
                "contract_hash": "789xyz012abc...",
                "dry_run": False,
                "replay_of": None,
            }
        }


class RunContractService:
    """
    Service for creating and managing run contracts.

    Features:
    - Immutable contract creation
    - Deterministic hashing
    - Contract storage (filesystem)
    - Contract verification
    - Replay support
    """

    # Storage directory
    CONTRACTS_DIR = Path("storage/run_contracts")

    def __init__(self):
        """Initialize run contract service."""
        self.CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_contract(
        self,
        graph_spec: ExecutionGraphSpec,
        business_intent_input: Optional[BusinessIntentInput] = None,
        resolved_intent: Optional[ResolvedBusinessIntent] = None,
        policy: Optional[ExecutionPolicy] = None,
        dry_run: bool = False,
        replay_of: Optional[str] = None,
    ) -> RunContract:
        """
        Create immutable run contract.

        Args:
            graph_spec: Execution graph specification
            business_intent_input: Original intent input (optional)
            resolved_intent: Resolved business intent (optional)
            policy: Execution policy (optional)
            dry_run: Whether this is a dry-run
            replay_of: Contract ID if replaying (optional)

        Returns:
            RunContract with all hashes computed
        """
        # Generate contract ID (timestamp-based for sortability)
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        contract_id = f"contract_{timestamp_ms}_{graph_spec.graph_id}"

        # Compute hashes
        input_hash = self._hash_business_intent(business_intent_input, resolved_intent)
        graph_hash = self._hash_graph_spec(graph_spec)
        policy_hash = self._hash_policy(policy)

        # Create contract (without result yet)
        contract = RunContract(
            contract_id=contract_id,
            business_intent_input=business_intent_input,
            resolved_intent=resolved_intent,
            graph_spec=graph_spec,
            policy=policy,
            result=None,  # Will be filled after execution
            input_hash=input_hash,
            graph_hash=graph_hash,
            policy_hash=policy_hash,
            contract_hash="",  # Will be computed below
            dry_run=dry_run,
            replay_of=replay_of,
        )

        # Compute contract hash
        contract_hash = self._hash_contract(contract)
        contract.contract_hash = contract_hash

        logger.info(
            f"[RunContract] Created contract {contract_id} "
            f"(input={input_hash[:16]}..., graph={graph_hash[:16]}..., "
            f"policy={policy_hash[:16]}..., contract={contract_hash[:16]}...)"
        )

        return contract

    def finalize_contract(
        self,
        contract: RunContract,
        result: ExecutionGraphResult,
    ) -> RunContract:
        """
        Finalize contract with execution result.

        Args:
            contract: Contract to finalize
            result: Execution result

        Returns:
            Updated contract with result
        """
        contract.result = result

        # Recompute contract hash (now includes result)
        contract_hash = self._hash_contract(contract)
        contract.contract_hash = contract_hash

        logger.info(
            f"[RunContract] Finalized contract {contract.contract_id} "
            f"(success={result.success}, contract_hash={contract_hash[:16]}...)"
        )

        return contract

    def save_contract(self, contract: RunContract) -> Path:
        """
        Save contract to filesystem.

        Args:
            contract: Contract to save

        Returns:
            Path to saved contract file
        """
        # Create filename
        filename = f"{contract.contract_id}.json"
        file_path = self.CONTRACTS_DIR / filename

        # Save as JSON
        with open(file_path, "w") as f:
            json.dump(contract.model_dump(), f, indent=2, default=str)

        logger.info(f"[RunContract] Saved contract to {file_path}")

        return file_path

    def load_contract(self, contract_id: str) -> Optional[RunContract]:
        """
        Load contract from filesystem.

        Args:
            contract_id: Contract ID to load

        Returns:
            RunContract or None if not found
        """
        filename = f"{contract_id}.json"
        file_path = self.CONTRACTS_DIR / filename

        if not file_path.exists():
            logger.warning(f"[RunContract] Contract not found: {contract_id}")
            return None

        with open(file_path, "r") as f:
            data = json.load(f)

        contract = RunContract(**data)

        logger.info(f"[RunContract] Loaded contract {contract_id}")

        return contract

    def verify_contract(self, contract: RunContract) -> bool:
        """
        Verify contract integrity by recomputing hashes.

        Args:
            contract: Contract to verify

        Returns:
            True if all hashes match
        """
        # Verify input hash
        expected_input_hash = self._hash_business_intent(
            contract.business_intent_input,
            contract.resolved_intent
        )
        if expected_input_hash != contract.input_hash:
            logger.error(
                f"[RunContract] Input hash mismatch for {contract.contract_id}: "
                f"expected={expected_input_hash[:16]}..., actual={contract.input_hash[:16]}..."
            )
            return False

        # Verify graph hash
        expected_graph_hash = self._hash_graph_spec(contract.graph_spec)
        if expected_graph_hash != contract.graph_hash:
            logger.error(
                f"[RunContract] Graph hash mismatch for {contract.contract_id}: "
                f"expected={expected_graph_hash[:16]}..., actual={contract.graph_hash[:16]}..."
            )
            return False

        # Verify policy hash
        expected_policy_hash = self._hash_policy(contract.policy)
        if expected_policy_hash != contract.policy_hash:
            logger.error(
                f"[RunContract] Policy hash mismatch for {contract.contract_id}: "
                f"expected={expected_policy_hash[:16]}..., actual={contract.policy_hash[:16]}..."
            )
            return False

        # Verify contract hash
        original_hash = contract.contract_hash
        contract.contract_hash = ""  # Temporarily clear
        expected_contract_hash = self._hash_contract(contract)
        contract.contract_hash = original_hash  # Restore

        if expected_contract_hash != original_hash:
            logger.error(
                f"[RunContract] Contract hash mismatch for {contract.contract_id}: "
                f"expected={expected_contract_hash[:16]}..., actual={original_hash[:16]}..."
            )
            return False

        logger.info(f"[RunContract] Contract {contract.contract_id} verified successfully")
        return True

    def _hash_business_intent(
        self,
        intent_input: Optional[BusinessIntentInput],
        resolved_intent: Optional[ResolvedBusinessIntent],
    ) -> str:
        """
        Compute deterministic hash of business intent.

        Args:
            intent_input: Original input
            resolved_intent: Resolved intent

        Returns:
            SHA256 hash (hex)
        """
        hash_content = {}

        if intent_input:
            hash_content["input"] = intent_input.model_dump(exclude_none=True)

        if resolved_intent:
            # Exclude non-deterministic fields (timestamps, generated IDs)
            resolved_dict = resolved_intent.model_dump(exclude_none=True)
            # Keep only deterministic fields
            hash_content["resolved"] = {
                "business_type": resolved_dict.get("business_type"),
                "monetization_type": resolved_dict.get("monetization_type"),
                "industry": resolved_dict.get("industry"),
                "risk_level": resolved_dict.get("risk_level"),
                "needs_website": resolved_dict.get("needs_website"),
                "needs_erp": resolved_dict.get("needs_erp"),
                "website_template": resolved_dict.get("website_template"),
                "odoo_modules_required": sorted(resolved_dict.get("odoo_modules_required", [])),
            }

        hash_json = json.dumps(hash_content, sort_keys=True)
        return hashlib.sha256(hash_json.encode("utf-8")).hexdigest()

    def _hash_graph_spec(self, graph_spec: ExecutionGraphSpec) -> str:
        """
        Compute deterministic hash of execution graph.

        Args:
            graph_spec: Graph specification

        Returns:
            SHA256 hash (hex)
        """
        graph_dict = graph_spec.model_dump(exclude_none=True)

        # Exclude non-deterministic fields
        hash_content = {
            "nodes": graph_dict.get("nodes", []),
            "dry_run": graph_dict.get("dry_run"),
            "auto_rollback": graph_dict.get("auto_rollback"),
            "stop_on_first_error": graph_dict.get("stop_on_first_error"),
        }

        hash_json = json.dumps(hash_content, sort_keys=True)
        return hashlib.sha256(hash_json.encode("utf-8")).hexdigest()

    def _hash_policy(self, policy: Optional[ExecutionPolicy]) -> str:
        """
        Compute deterministic hash of execution policy.

        Args:
            policy: Execution policy (optional)

        Returns:
            SHA256 hash (hex)
        """
        if policy is None:
            return hashlib.sha256(b"no_policy").hexdigest()

        policy_dict = policy.model_dump(exclude_none=True)

        # Exclude timestamps and non-deterministic fields
        hash_content = {
            "policy_name": policy_dict.get("policy_name"),
            "budget": policy_dict.get("budget"),
            "require_approval_for_nodes": sorted(policy_dict.get("require_approval_for_nodes", [])),
            "require_approval_for_types": sorted(policy_dict.get("require_approval_for_types", [])),
            "critical_nodes": sorted(policy_dict.get("critical_nodes", [])),
        }

        hash_json = json.dumps(hash_content, sort_keys=True)
        return hashlib.sha256(hash_json.encode("utf-8")).hexdigest()

    def _hash_contract(self, contract: RunContract) -> str:
        """
        Compute deterministic hash of entire contract.

        Args:
            contract: Contract to hash

        Returns:
            SHA256 hash (hex)
        """
        # Temporarily clear contract_hash to avoid circular dependency
        original_hash = contract.contract_hash
        contract.contract_hash = ""

        hash_content = {
            "contract_id": contract.contract_id,
            "input_hash": contract.input_hash,
            "graph_hash": contract.graph_hash,
            "policy_hash": contract.policy_hash,
            "dry_run": contract.dry_run,
            "replay_of": contract.replay_of,
            # Exclude result to allow hashing before execution
        }

        hash_json = json.dumps(hash_content, sort_keys=True)
        computed_hash = hashlib.sha256(hash_json.encode("utf-8")).hexdigest()

        # Restore original hash
        contract.contract_hash = original_hash

        return computed_hash


# Singleton
_run_contract_service: Optional[RunContractService] = None


def get_run_contract_service() -> RunContractService:
    """Get singleton run contract service."""
    global _run_contract_service
    if _run_contract_service is None:
        _run_contract_service = RunContractService()
    return _run_contract_service
