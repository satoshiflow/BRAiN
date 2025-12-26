"""
Diff-Audit Gate - Sprint 9 (P0)

Strict mapping validation between IR steps and executable DAG nodes.

Ensures:
- No DAG node without IR step
- No IR step missing from DAG
- Hashes match exactly

On mismatch: BLOCK execution + emit audit event
"""

from typing import List, Dict, Any
from loguru import logger

from backend.app.modules.ir_governance.schemas import (
    IR,
    DiffAuditResult,
)
from backend.app.modules.ir_governance.canonicalization import (
    ir_hash,
    step_hash,
    compute_dag_hash,
)


class DiffAuditGate:
    """
    Diff-audit gate enforces IR ↔ DAG integrity.

    Fail-closed: Any mismatch blocks execution.
    """

    def audit_ir_dag_mapping(
        self,
        ir: IR,
        dag_nodes: List[Dict[str, Any]],
    ) -> DiffAuditResult:
        """
        Audit IR ↔ DAG mapping integrity.

        Each DAG node MUST contain:
        - ir_step_id (stable reference, e.g., step index or UUID)
        - ir_step_hash (canonical step hash)

        Checks:
        - No extra DAG nodes (not in IR)
        - No missing DAG nodes (IR step not in DAG)
        - All hashes match exactly

        Args:
            ir: IR to validate against
            dag_nodes: List of DAG nodes (each must have ir_step_id, ir_step_hash)

        Returns:
            DiffAuditResult

        Audit events:
        - ir.dag_diff_ok (success)
        - ir.dag_diff_failed (mismatch)
        """
        # Compute IR hash
        computed_ir_hash = ir_hash(ir)

        # Compute DAG hash
        try:
            computed_dag_hash = compute_dag_hash(dag_nodes)
        except ValueError as e:
            # DAG nodes missing required fields
            logger.error(f"[DiffAudit] DAG nodes missing required fields: {e}")
            return DiffAuditResult(
                success=False,
                ir_hash=computed_ir_hash,
                dag_hash="",
                extra_dag_nodes=[f"ERROR: {str(e)}"],
                tenant_id=ir.tenant_id,
                request_id=ir.request_id,
            )

        # Build IR step index: step_index -> step_hash
        ir_step_index: Dict[str, str] = {}
        for i, step in enumerate(ir.steps):
            step_id = step.step_id or str(i)  # Use step_id if present, else index
            ir_step_index[step_id] = step_hash(step)

        # Build DAG node index: ir_step_id -> ir_step_hash
        dag_step_index: Dict[str, str] = {}
        for node in dag_nodes:
            node_step_id = node.get("ir_step_id")
            node_step_hash = node.get("ir_step_hash")

            if not node_step_id or not node_step_hash:
                continue  # Already caught by compute_dag_hash

            dag_step_index[node_step_id] = node_step_hash

        # Find violations
        missing_ir_steps = []  # IR steps not in DAG
        extra_dag_nodes = []  # DAG nodes not in IR
        hash_mismatches = []  # Hash mismatches

        # Check: All IR steps have corresponding DAG nodes
        for step_id, expected_hash in ir_step_index.items():
            if step_id not in dag_step_index:
                missing_ir_steps.append(step_id)
            else:
                actual_hash = dag_step_index[step_id]
                if expected_hash != actual_hash:
                    hash_mismatches.append(
                        {
                            "step_id": step_id,
                            "expected_hash": expected_hash[:16] + "...",
                            "actual_hash": actual_hash[:16] + "...",
                        }
                    )

        # Check: All DAG nodes have corresponding IR steps
        for step_id in dag_step_index.keys():
            if step_id not in ir_step_index:
                extra_dag_nodes.append(step_id)

        # Determine success
        success = (
            len(missing_ir_steps) == 0
            and len(extra_dag_nodes) == 0
            and len(hash_mismatches) == 0
        )

        result = DiffAuditResult(
            success=success,
            ir_hash=computed_ir_hash,
            dag_hash=computed_dag_hash,
            missing_ir_steps=missing_ir_steps,
            extra_dag_nodes=extra_dag_nodes,
            hash_mismatches=hash_mismatches,
            tenant_id=ir.tenant_id,
            request_id=ir.request_id,
        )

        # Emit audit event
        if success:
            logger.info(
                f"[DiffAudit] ir.dag_diff_ok: "
                f"tenant_id={ir.tenant_id}, "
                f"request_id={ir.request_id}, "
                f"ir_hash={computed_ir_hash[:16]}..., "
                f"dag_hash={computed_dag_hash[:16]}..., "
                f"steps={len(ir.steps)}"
            )
        else:
            logger.error(
                f"[DiffAudit] ir.dag_diff_failed: "
                f"tenant_id={ir.tenant_id}, "
                f"request_id={ir.request_id}, "
                f"ir_hash={computed_ir_hash[:16]}..., "
                f"dag_hash={computed_dag_hash[:16]}..., "
                f"missing_ir_steps={len(missing_ir_steps)}, "
                f"extra_dag_nodes={len(extra_dag_nodes)}, "
                f"hash_mismatches={len(hash_mismatches)}"
            )

            # Log details for debugging
            if missing_ir_steps:
                logger.error(f"[DiffAudit] Missing IR steps in DAG: {missing_ir_steps}")
            if extra_dag_nodes:
                logger.error(f"[DiffAudit] Extra DAG nodes (not in IR): {extra_dag_nodes}")
            if hash_mismatches:
                logger.error(f"[DiffAudit] Hash mismatches: {hash_mismatches}")

        return result


# Singleton
_diff_audit_gate: Optional['DiffAuditGate'] = None


def get_diff_audit_gate() -> DiffAuditGate:
    """Get singleton diff-audit gate."""
    global _diff_audit_gate
    if _diff_audit_gate is None:
        _diff_audit_gate = DiffAuditGate()
    return _diff_audit_gate
