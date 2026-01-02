"""
Genesis Agent - Core Implementation

The Genesis Agent is responsible for creating new agents from DNA templates
with comprehensive security, validation, and auditability.

Features:
- Template-based agent creation
- DNA validation and customization
- Idempotency (duplicate request_id handling)
- Template hash tracking for reproducibility
- Event emission for audit trail
- Budget enforcement with reserve protection
- Governor approval integration (Phase 1: stub)

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

import redis.asyncio as redis
import yaml

from .config import GenesisSettings, get_genesis_settings
from .dna_schema import AgentDNA, AgentStatus, DNAMetadata
from .dna_validator import DNAValidator, TemplateNotFoundError, ValidationError
from .events import AuditLog, GenesisEvents, SimpleAuditLog

# Governor v1 integration (Phase 2a)
try:
    from backend.brain.governor import GovernorApproval as Governor_v1_Approval
    GOVERNOR_V1_AVAILABLE = True
except ImportError:
    GOVERNOR_V1_AVAILABLE = False
    Governor_v1_Approval = None

logger = logging.getLogger(__name__)


# ============================================================================
# Protocols
# ============================================================================

class AgentRegistry(Protocol):
    """
    Protocol for agent registry integration.

    The registry stores agent DNA and metadata in persistent storage.
    """

    async def create(
        self,
        dna: AgentDNA,
        request_id: str,
        status: str
    ) -> str:
        """
        Create a new agent record in the registry.

        Args:
            dna: Agent DNA
            request_id: Unique request identifier
            status: Initial status (e.g., "CREATED")

        Returns:
            str: Registry record ID
        """
        ...

    async def get_by_request_id(self, request_id: str) -> Optional[AgentDNA]:
        """
        Get agent by request_id (for idempotency).

        Args:
            request_id: Request identifier

        Returns:
            AgentDNA if found, None otherwise
        """
        ...

    async def get(self, agent_id: str) -> Optional[AgentDNA]:
        """
        Get agent by agent_id.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentDNA if found, None otherwise
        """
        ...


class BudgetService(Protocol):
    """
    Protocol for budget management.

    Tracks and enforces credit limits.
    """

    async def get_available_credits(self) -> int:
        """Get available credits."""
        ...

    async def deduct(self, amount: int, reason: str) -> None:
        """
        Deduct credits from budget.

        Args:
            amount: Credits to deduct
            reason: Reason for deduction
        """
        ...


class GovernorApproval(Protocol):
    """
    Protocol for Governor approval (Phase 3).

    Phase 1: Stub implementation that always approves.
    """

    async def request_approval(self, dna: AgentDNA) -> ApprovalResponse:
        """
        Request approval from Governor.

        Args:
            dna: Agent DNA to approve

        Returns:
            ApprovalResponse with approval decision
        """
        ...


class ApprovalResponse:
    """Response from Governor approval."""

    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason


# ============================================================================
# Genesis Agent
# ============================================================================

class GenesisAgent:
    """
    Genesis Agent - Creates new agents from DNA templates.

    The Genesis Agent is the central authority for agent creation in BRAiN.
    It enforces security, validates DNA, tracks templates, and maintains
    a complete audit trail.

    Features:
    - Idempotent agent creation (duplicate request_id detection)
    - Template hash tracking for reproducibility
    - Customization whitelist enforcement
    - Event emission (Redis + Audit)
    - Budget reserve protection
    - Governor approval integration (Phase 1: stub)

    Example:
        >>> genesis = GenesisAgent(
        ...     registry=registry,
        ...     redis_client=redis,
        ...     audit_log=audit,
        ...     budget=budget,
        ...     settings=settings
        ... )
        >>>
        >>> dna = await genesis.create_agent(
        ...     request_id="req-123",
        ...     template_name="worker_base",
        ...     customizations={"metadata.name": "worker_01"}
        ... )
    """

    def __init__(
        self,
        registry: AgentRegistry,
        redis_client: redis.Redis,
        audit_log: AuditLog,
        budget: BudgetService,
        settings: Optional[GenesisSettings] = None,
        governor: Optional[GovernorApproval] = None,
    ):
        """
        Initialize Genesis Agent.

        Args:
            registry: Agent registry for persistence
            redis_client: Redis client for pub/sub
            audit_log: Audit log for compliance
            budget: Budget service for credit management
            settings: Genesis settings (optional, uses defaults if None)
            governor: Governor approval service (optional, Phase 1: stub)
        """
        self.registry = registry
        self.redis = redis_client
        self.audit_log = audit_log
        self.budget = budget
        self.settings = settings or get_genesis_settings()

        # Governor v1 integration (Phase 2a)
        if governor is None:
            if GOVERNOR_V1_AVAILABLE:
                self.governor = Governor_v1_Approval(
                    redis_client=redis_client,
                    audit_log=audit_log
                )
                logger.info("Governor v1 initialized for agent creation governance")
            else:
                self.governor = StubGovernor()
                logger.warning("Governor v1 not available, using stub (auto-approve)")
        else:
            self.governor = governor

        # Initialize validator
        templates_dir = self.settings.get_templates_dir()
        self.validator = DNAValidator(templates_dir)

        logger.info(
            f"Genesis Agent initialized (templates_dir={templates_dir}, "
            f"enabled={self.settings.enabled})"
        )

    # ========================================================================
    # Core Agent Creation
    # ========================================================================

    async def create_agent(
        self,
        request_id: str,
        template_name: str,
        customizations: Optional[Dict[str, Any]] = None
    ) -> AgentDNA:
        """
        Create a new agent from template.

        This is the main entry point for agent creation. It orchestrates:
        1. Idempotency check
        2. Template loading
        3. Customization application
        4. DNA validation
        5. Governor approval
        6. Registry registration
        7. Event emission
        8. Budget deduction

        Args:
            request_id: Unique request identifier (UUID recommended)
            template_name: Name of base template (e.g., "worker_base")
            customizations: Optional DNA modifications (whitelist-enforced)

        Returns:
            AgentDNA: Validated DNA of created agent

        Raises:
            RuntimeError: If Genesis system is disabled
            ValidationError: If DNA validation fails
            TemplateNotFoundError: If template doesn't exist
            Exception: If creation fails

        Example:
            >>> dna = await genesis.create_agent(
            ...     request_id="req-123",
            ...     template_name="worker_base",
            ...     customizations={"metadata.name": "worker_specialized_01"}
            ... )
        """
        # 0. Check kill switch
        if not self.settings.enabled:
            await GenesisEvents.killswitch_triggered(
                reason="Genesis system disabled by configuration",
                redis_client=self.redis,
                audit_log=self.audit_log
            )
            raise RuntimeError(
                "Genesis Agent system is DISABLED. "
                "Set GENESIS_ENABLED=true to enable."
            )

        customizations = customizations or {}

        # 1. Check idempotency
        existing = await self.registry.get_by_request_id(request_id)
        if existing:
            logger.info(
                f"Duplicate request {request_id}, returning existing agent "
                f"{existing.metadata.id}"
            )
            await GenesisEvents.idempotency_hit(
                request_id=request_id,
                existing_agent_id=str(existing.metadata.id),
                redis_client=self.redis,
                audit_log=self.audit_log
            )
            # Still emit requested event for audit trail
            await GenesisEvents.create_requested(
                request_id=request_id,
                template_name=template_name,
                customizations=customizations,
                redis_client=self.redis,
                audit_log=self.audit_log
            )
            return existing

        # 2. Emit requested event
        await GenesisEvents.create_requested(
            request_id=request_id,
            template_name=template_name,
            customizations=customizations,
            redis_client=self.redis,
            audit_log=self.audit_log
        )

        try:
            # 3. Load template
            template_dna = await self.load_template(template_name)

            # 4. Compute and set template hash
            template_hash = self.validator.compute_template_hash(template_name)
            template_dna.metadata.template_hash = template_hash
            template_dna.metadata.dna_schema_version = "2.0"

            # Emit template loaded event
            await GenesisEvents.template_loaded(
                template_name=template_name,
                template_hash=template_hash,
                redis_client=self.redis,
                audit_log=self.audit_log
            )

            # 5. Apply customizations (if any)
            if customizations:
                self.validator.validate_customizations(customizations)
                template_dna = self.apply_customizations(
                    template_dna, customizations
                )
                # Emit customizations event
                await GenesisEvents.customizations_applied(
                    agent_id=str(template_dna.metadata.id),
                    customizations=customizations,
                    redis_client=self.redis,
                    audit_log=self.audit_log
                )

            # 6. Validate DNA
            self.validator.validate_dna(template_dna)

            # 7. Emit validated event
            dna_hash = self.compute_dna_hash(template_dna)
            await GenesisEvents.create_validated(
                agent_id=str(template_dna.metadata.id),
                dna_hash=dna_hash,
                template_hash=template_hash,
                redis_client=self.redis,
                audit_log=self.audit_log
            )

            # 8. Request Governor approval (Phase 1: stub)
            approval = await self.governor.request_approval(template_dna)
            if not approval.approved:
                raise Exception(
                    f"Governor rejected agent creation: {approval.reason}"
                )

            # 9. Register in Agent Registry
            registry_id = await self.registry.create(
                dna=template_dna,
                request_id=request_id,
                status=AgentStatus.CREATED.value
            )

            # 10. Emit registered event
            await GenesisEvents.create_registered(
                agent_id=str(template_dna.metadata.id),
                registry_id=registry_id,
                status=AgentStatus.CREATED.value,
                redis_client=self.redis,
                audit_log=self.audit_log
            )

            # 11. Deduct credits
            cost = await self.estimate_cost(template_name)
            await self.budget.deduct(cost, reason=f"agent_creation:{template_name}")

            logger.info(
                f"Agent created successfully: "
                f"id={template_dna.metadata.id}, "
                f"name={template_dna.metadata.name}, "
                f"template={template_name}, "
                f"cost={cost}"
            )

            return template_dna

        except Exception as e:
            # Emit failure event
            error_code = type(e).__name__
            await GenesisEvents.create_failed(
                error_code=error_code,
                reason=str(e),
                request_id=request_id,
                redis_client=self.redis,
                audit_log=self.audit_log
            )
            logger.error(f"Agent creation failed: {e}")
            raise

    # ========================================================================
    # Template Loading
    # ========================================================================

    async def load_template(self, template_name: str) -> AgentDNA:
        """
        Load DNA template from YAML file.

        Args:
            template_name: Name of template without extension

        Returns:
            AgentDNA: Loaded and validated DNA

        Raises:
            TemplateNotFoundError: If template file doesn't exist
            ValidationError: If template YAML is invalid

        Example:
            >>> dna = await genesis.load_template("worker_base")
        """
        templates_dir = self.settings.get_templates_dir()
        template_path = templates_dir / f"{template_name}.yaml"

        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template not found: {template_name} "
                f"(expected at {template_path})"
            )

        # Load YAML
        try:
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)
        except Exception as e:
            raise ValidationError(
                f"Failed to load template YAML: {e}"
            )

        # Extract agent_dna section
        if "agent_dna" not in template_data:
            raise ValidationError(
                f"Template {template_name} missing 'agent_dna' section"
            )

        dna_dict = template_data["agent_dna"]

        # Parse into AgentDNA (Pydantic validation)
        try:
            dna = AgentDNA(**dna_dict)
        except Exception as e:
            raise ValidationError(
                f"Template {template_name} has invalid DNA schema: {e}"
            )

        logger.debug(f"Template loaded: {template_name}")
        return dna

    # ========================================================================
    # Customization Application
    # ========================================================================

    def apply_customizations(
        self,
        dna: AgentDNA,
        customizations: Dict[str, Any]
    ) -> AgentDNA:
        """
        Apply customizations to DNA.

        Only whitelisted fields can be modified. This method applies
        the customizations in a safe, controlled manner.

        Args:
            dna: Base DNA to customize
            customizations: Dictionary of field paths to values

        Returns:
            AgentDNA: Customized DNA

        Raises:
            ValidationError: If customization is invalid

        Example:
            >>> dna = genesis.apply_customizations(
            ...     dna,
            ...     {"metadata.name": "worker_specialized_01"}
            ... )
        """
        # Convert DNA to dict for modification
        dna_dict = dna.model_dump()

        for field_path, value in customizations.items():
            # Apply customization based on field path
            if field_path == "metadata.name":
                dna_dict["metadata"]["name"] = value

            elif field_path == "skills[].domains":
                # Append-only: add domains to all skills
                for skill in dna_dict["skills"]:
                    existing_domains = set(skill.get("domains", []))
                    new_domains = set(value)
                    skill["domains"] = list(existing_domains | new_domains)

            elif field_path == "memory_seeds":
                # Append-only: add to existing seeds
                existing_seeds = set(dna_dict.get("memory_seeds", []))
                new_seeds = set(value)
                dna_dict["memory_seeds"] = list(existing_seeds | new_seeds)

        # Reconstruct AgentDNA
        try:
            customized_dna = AgentDNA(**dna_dict)
        except Exception as e:
            raise ValidationError(
                f"Failed to apply customizations: {e}"
            )

        return customized_dna

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def compute_dna_hash(self, dna: AgentDNA) -> str:
        """
        Compute SHA256 hash of complete DNA.

        This provides a fingerprint of the agent DNA for audit trail
        and reproducibility verification.

        Args:
            dna: Agent DNA to hash

        Returns:
            str: SHA256 hash in hex format (not prefixed)

        Example:
            >>> hash_val = genesis.compute_dna_hash(dna)
            >>> print(hash_val)
            'abc123def456...'
        """
        dna_json = dna.model_dump_json(sort_keys=True)
        return hashlib.sha256(dna_json.encode()).hexdigest()

    async def estimate_cost(self, template_name: str) -> int:
        """
        Estimate cost for creating agent from template.

        Args:
            template_name: Name of template

        Returns:
            int: Estimated cost in credits

        Example:
            >>> cost = await genesis.estimate_cost("worker_base")
            >>> print(cost)
            10
        """
        return self.settings.estimate_cost(template_name)

    async def check_budget(self, required_credits: int) -> bool:
        """
        Check if sufficient budget is available (with reserve protection).

        Args:
            required_credits: Required credits

        Returns:
            bool: True if sufficient budget available

        Example:
            >>> has_budget = await genesis.check_budget(100)
        """
        available = await self.budget.get_available_credits()
        reserve = int(available * self.settings.reserve_ratio)
        usable = available - reserve

        if usable < required_credits:
            await GenesisEvents.budget_exceeded(
                available_credits=usable,
                required_credits=required_credits,
                redis_client=self.redis,
                audit_log=self.audit_log
            )
            return False

        return True


# ============================================================================
# Stub Implementations (DEPRECATED - use Governor v1)
# ============================================================================

class StubGovernor:
    """
    Stub Governor implementation (DEPRECATED).

    This is a fallback for testing when Governor v1 is not available.
    Always approves agent creation without governance.

    **DEPRECATED:** Use Governor v1 (backend.brain.governor) instead.
    """

    async def request_approval(self, dna: AgentDNA) -> ApprovalResponse:
        """
        Request approval (DEPRECATED: always approves).

        Args:
            dna: Agent DNA to approve

        Returns:
            ApprovalResponse with approval=True

        Warning:
            This stub bypasses all governance rules. Only use for testing.
        """
        logger.warning(
            "StubGovernor is DEPRECATED and bypasses all governance. "
            "Use Governor v1 for production."
        )
        return ApprovalResponse(
            approved=True,
            reason="DEPRECATED: Stub Governor auto-approves (no governance)"
        )


class InMemoryRegistry:
    """
    Simple in-memory registry for development/testing.

    In production, replace with PostgreSQL-backed registry.
    """

    def __init__(self):
        """Initialize empty registry."""
        self.agents: Dict[str, AgentDNA] = {}
        self.request_map: Dict[str, str] = {}  # request_id -> agent_id

    async def create(
        self,
        dna: AgentDNA,
        request_id: str,
        status: str
    ) -> str:
        """
        Create agent record.

        Args:
            dna: Agent DNA
            request_id: Request identifier
            status: Initial status

        Returns:
            str: Registry record ID (same as agent ID)
        """
        agent_id = str(dna.metadata.id)
        self.agents[agent_id] = dna
        self.request_map[request_id] = agent_id
        return agent_id

    async def get_by_request_id(self, request_id: str) -> Optional[AgentDNA]:
        """Get agent by request_id."""
        agent_id = self.request_map.get(request_id)
        if agent_id:
            return self.agents.get(agent_id)
        return None

    async def get(self, agent_id: str) -> Optional[AgentDNA]:
        """Get agent by agent_id."""
        return self.agents.get(agent_id)


class InMemoryBudget:
    """
    Simple in-memory budget service for development/testing.

    In production, replace with persistent budget tracking.
    """

    def __init__(self, initial_credits: int = 10000):
        """Initialize budget with credits."""
        self.available_credits = initial_credits

    async def get_available_credits(self) -> int:
        """Get available credits."""
        return self.available_credits

    async def deduct(self, amount: int, reason: str) -> None:
        """
        Deduct credits.

        Args:
            amount: Credits to deduct
            reason: Reason for deduction
        """
        self.available_credits -= amount
        logger.info(f"Budget deducted: -{amount} ({reason}), remaining={self.available_credits}")
