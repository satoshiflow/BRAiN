"""
IR ↔ WebGenesis Mapping Layer (Sprint 10)

Maps WebGenesis execution graph to IR steps for governance and diff-audit.
"""

from typing import List, Dict, Any
from loguru import logger

from backend.app.modules.ir_governance import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
    RiskTier,
    step_hash,
)
from backend.app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphSpec,
    ExecutionNodeSpec,
    ExecutionNodeType,
)


class IRMappingError(Exception):
    """Raised when IR mapping fails."""
    pass


class IRWebGenesisMapper:
    """
    Maps WebGenesis execution graph to IR representation.

    Responsibilities:
    - Convert ExecutionNodeSpec → IRStep
    - Generate deterministic step_id and step_hash
    - Map node types to IR actions
    - Attach IR metadata to DAG nodes

    Supported WebGenesis Node Types:
    - webgenesis → webgenesis.site.create / webgenesis.site.update
    - dns → dns.zone.update
    - odoo_module → odoo.install_module
    """

    # Node type → IR action mapping
    NODE_TYPE_TO_ACTION: Dict[ExecutionNodeType, IRAction] = {
        ExecutionNodeType.WEBGENESIS: IRAction.WEBGENESIS_SITE_CREATE,
        ExecutionNodeType.DNS: IRAction.DNS_UPDATE_RECORDS,
        ExecutionNodeType.ODOO_MODULE: IRAction.ODOO_INSTALL_MODULE,
    }

    # Node type → IR provider mapping
    NODE_TYPE_TO_PROVIDER: Dict[ExecutionNodeType, IRProvider] = {
        ExecutionNodeType.WEBGENESIS: IRProvider.WEBGENESIS_V1,
        ExecutionNodeType.DNS: IRProvider.DNS_HETZNER,
        ExecutionNodeType.ODOO_MODULE: IRProvider.ODOO_V16,
    }

    def graph_spec_to_ir(
        self,
        graph_spec: ExecutionGraphSpec,
        tenant_id: str = "default",
    ) -> IR:
        """
        Convert execution graph spec to IR.

        Args:
            graph_spec: Execution graph specification
            tenant_id: Tenant identifier

        Returns:
            IR with all steps mapped

        Raises:
            IRMappingError: If mapping fails
        """
        logger.info(
            f"[IRMapper] Mapping graph {graph_spec.graph_id} to IR "
            f"({len(graph_spec.nodes)} nodes)"
        )

        steps: List[IRStep] = []

        for node_spec in graph_spec.nodes:
            try:
                step = self.node_spec_to_ir_step(node_spec, graph_spec)
                steps.append(step)
                logger.debug(
                    f"[IRMapper] Mapped node {node_spec.node_id} → "
                    f"action={step.action.value}, hash={step_hash(step)[:16]}..."
                )
            except Exception as e:
                raise IRMappingError(
                    f"Failed to map node {node_spec.node_id} to IR: {e}"
                )

        ir = IR(
            tenant_id=tenant_id,
            steps=steps,
            request_id=graph_spec.graph_id,  # Use graph_id as request_id
        )

        logger.info(
            f"[IRMapper] Graph mapped to IR successfully: "
            f"{len(steps)} steps, tenant={tenant_id}"
        )

        return ir

    def node_spec_to_ir_step(
        self,
        node_spec: ExecutionNodeSpec,
        graph_spec: ExecutionGraphSpec,
    ) -> IRStep:
        """
        Convert execution node spec to IR step.

        Args:
            node_spec: Execution node specification
            graph_spec: Parent graph spec (for context)

        Returns:
            IRStep

        Raises:
            IRMappingError: If node type not supported
        """
        # Map node type to IR action
        if node_spec.node_type not in self.NODE_TYPE_TO_ACTION:
            raise IRMappingError(
                f"Unsupported node type for IR mapping: {node_spec.node_type}. "
                f"Supported: {list(self.NODE_TYPE_TO_ACTION.keys())}"
            )

        action = self.NODE_TYPE_TO_ACTION[node_spec.node_type]
        provider = self.NODE_TYPE_TO_PROVIDER[node_spec.node_type]

        # Determine resource identifier
        resource = self._extract_resource(node_spec)

        # Extract parameters
        params = node_spec.executor_params.copy() if node_spec.executor_params else {}

        # Generate idempotency key
        idempotency_key = self._generate_idempotency_key(node_spec, graph_spec)

        # Determine budget (if applicable)
        budget_cents = params.pop("budget_cents", None)

        # Create IR step
        step = IRStep(
            action=action,
            provider=provider,
            resource=resource,
            params=params,
            idempotency_key=idempotency_key,
            budget_cents=budget_cents,
            step_id=node_spec.node_id,  # Use node_id as step_id
        )

        return step

    def _extract_resource(self, node_spec: ExecutionNodeSpec) -> str:
        """
        Extract resource identifier from node spec.

        Examples:
        - WebGenesis: "site:example.com"
        - DNS: "zone:example.com"
        - Odoo: "module:website_sale"
        """
        if node_spec.node_type == ExecutionNodeType.WEBGENESIS:
            domain = node_spec.executor_params.get("domain", "unknown")
            return f"site:{domain}"

        elif node_spec.node_type == ExecutionNodeType.DNS:
            domain = node_spec.executor_params.get("domain", "unknown")
            return f"zone:{domain}"

        elif node_spec.node_type == ExecutionNodeType.ODOO_MODULE:
            module_name = node_spec.executor_params.get("module_name", "unknown")
            return f"module:{module_name}"

        else:
            return f"node:{node_spec.node_id}"

    def _generate_idempotency_key(
        self,
        node_spec: ExecutionNodeSpec,
        graph_spec: ExecutionGraphSpec,
    ) -> str:
        """
        Generate deterministic idempotency key.

        Format: graph_id:node_id
        Example: "graph_123:webgen_0"
        """
        return f"{graph_spec.graph_id}:{node_spec.node_id}"

    def attach_ir_metadata_to_nodes(
        self,
        graph_spec: ExecutionGraphSpec,
        ir: IR,
    ) -> ExecutionGraphSpec:
        """
        Attach IR metadata (step_id, step_hash) to graph nodes.

        This enables diff-audit to verify IR ↔ DAG mapping.

        Args:
            graph_spec: Execution graph specification
            ir: IR with steps

        Returns:
            Modified graph_spec with IR metadata attached

        Raises:
            IRMappingError: If IR steps don't match graph nodes
        """
        logger.info(
            f"[IRMapper] Attaching IR metadata to {len(graph_spec.nodes)} nodes"
        )

        # Build IR step index
        ir_step_index: Dict[str, IRStep] = {}
        for step in ir.steps:
            step_id = step.step_id or str(ir.steps.index(step))
            ir_step_index[step_id] = step

        # Attach metadata to nodes
        for node_spec in graph_spec.nodes:
            if node_spec.node_id not in ir_step_index:
                raise IRMappingError(
                    f"Node {node_spec.node_id} not found in IR steps. "
                    f"IR may be stale or corrupted."
                )

            ir_step = ir_step_index[node_spec.node_id]

            # Attach IR metadata to executor_params
            if not node_spec.executor_params:
                node_spec.executor_params = {}

            node_spec.executor_params["ir_step_id"] = node_spec.node_id
            node_spec.executor_params["ir_step_hash"] = step_hash(ir_step)
            node_spec.executor_params["ir_request_id"] = ir.request_id
            node_spec.executor_params["ir_tenant_id"] = ir.tenant_id

            logger.debug(
                f"[IRMapper] Attached IR metadata to node {node_spec.node_id}: "
                f"hash={step_hash(ir_step)[:16]}..."
            )

        logger.info("[IRMapper] IR metadata attached successfully")

        return graph_spec


# Singleton
_mapper: IRWebGenesisMapper | None = None


def get_ir_mapper() -> IRWebGenesisMapper:
    """Get IR mapper singleton."""
    global _mapper
    if _mapper is None:
        _mapper = IRWebGenesisMapper()
    return _mapper
