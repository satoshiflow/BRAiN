"""
Foundation Service - Business logic for ethics, safety, and behavior trees

Provides core Foundation layer functionality:
- Action validation (ethics & safety)
- Behavior tree execution (placeholder for RYR integration)
- Foundation status monitoring
"""

import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from loguru import logger

from .schemas import (
    FoundationConfig,
    FoundationStatus,
    FoundationInfo,
    BehaviorTreeNode,
    BehaviorTreeExecutionResult,
    ActionValidationRequest,
    ActionValidationResponse,
    AuthorizationRequest,
    AuthorizationResponse,
    AuditLogEntry,
    AuditLogRequest,
    AuditLogResponse,
    EthicsRule,
)


class FoundationService:
    """
    Foundation Layer Service

    Singleton service that enforces ethics and safety rules across all agent operations.
    """

    def __init__(self, config: Optional[FoundationConfig] = None):
        """
        Initialize Foundation service.

        Args:
            config: Foundation configuration (uses defaults if not provided)
        """
        self.config = config or FoundationConfig()
        self.start_time = time.time()

        # Metrics
        self.violations = 0
        self.overrides = 0
        self.total_validations = 0

        # Ethics rules (can be extended later)
        self.ethics_rules: List[EthicsRule] = []

        # Audit log (in-memory for now)
        self.audit_log: List[AuditLogEntry] = []
        self.max_audit_entries = 10000  # Keep last 10k entries

        logger.info("🏛️ Foundation Service initialized (v0.1.0)")
        logger.info(
            f"   Ethics: {self.config.ethics_enabled}, "
            f"Safety: {self.config.safety_checks}, "
            f"Strict: {self.config.strict_mode}"
        )

    async def validate_action(
        self, request: ActionValidationRequest
    ) -> ActionValidationResponse:
        """
        Validate if an action is ethically and safely permissible.

        Args:
            request: Action validation request (action name, params, context)

        Returns:
            ActionValidationResponse with validation result
        """
        self.total_validations += 1
        action = request.action.lower()
        agent_id = request.context.get("agent_id")

        # If neither ethics nor safety checks are enabled, allow everything
        if not self.config.ethics_enabled and not self.config.safety_checks:
            response = ActionValidationResponse(
                valid=True, action=request.action, severity="info"
            )
            self._log_audit(
                event_type="validation",
                agent_id=agent_id,
                action=request.action,
                outcome="allowed",
                reason="No checks enabled",
                details=request.params,
            )
            return response

        # Check 1: Blacklist (always blocked)
        if self._is_blacklisted(action):
            self.overrides += 1
            logger.warning(f"⚠️ Foundation blocked blacklisted action: {action}")
            response = ActionValidationResponse(
                valid=False,
                action=request.action,
                reason=f"Action '{action}' is explicitly blacklisted (dangerous operation)",
                severity="critical",
                suggestions=self._get_safe_alternatives(action),
            )
            self._log_audit(
                event_type="validation",
                agent_id=agent_id,
                action=request.action,
                outcome="blocked",
                reason=response.reason,
                details={"severity": "critical", "blacklisted": True},
            )
            return response

        # Check 2: Strict mode whitelist
        if self.config.strict_mode:
            if not self._is_whitelisted(action):
                self.violations += 1
                logger.warning(
                    f"⚠️ Foundation blocked non-whitelisted action in strict mode: {action}"
                )
                response = ActionValidationResponse(
                    valid=False,
                    action=request.action,
                    reason=f"Strict mode: Action '{action}' not in whitelist",
                    severity="warning",
                    suggestions=["Use only whitelisted actions"],
                )
                self._log_audit(
                    event_type="validation",
                    agent_id=agent_id,
                    action=request.action,
                    outcome="blocked",
                    reason=response.reason,
                    details={"severity": "warning", "strict_mode": True},
                )
                return response

        # Check 3: Ethics rules (custom rules)
        ethics_violation = self._check_ethics_rules(action, request.params)
        if ethics_violation:
            self.violations += 1
            logger.warning(f"⚠️ Foundation detected ethics violation: {action}")
            response = ActionValidationResponse(
                valid=False,
                action=request.action,
                reason=ethics_violation,
                severity="warning",
            )
            self._log_audit(
                event_type="validation",
                agent_id=agent_id,
                action=request.action,
                outcome="blocked",
                reason=ethics_violation,
                details={"severity": "warning", "ethics_violation": True},
            )
            return response

        # Check 4: Safety heuristics (pattern-based)
        safety_issue = self._check_safety_patterns(action, request.params)
        if safety_issue:
            self.overrides += 1
            logger.warning(f"⚠️ Foundation detected safety issue: {action}")
            response = ActionValidationResponse(
                valid=False,
                action=request.action,
                reason=safety_issue,
                severity="warning",
            )
            self._log_audit(
                event_type="validation",
                agent_id=agent_id,
                action=request.action,
                outcome="blocked",
                reason=safety_issue,
                details={"severity": "warning", "safety_issue": True},
            )
            return response

        # All checks passed
        logger.debug(f"✅ Foundation validated action: {action}")
        response = ActionValidationResponse(
            valid=True, action=request.action, severity="info"
        )
        self._log_audit(
            event_type="validation",
            agent_id=agent_id,
            action=request.action,
            outcome="allowed",
            reason="All checks passed",
            details=request.params,
        )
        return response

    async def execute_behavior_tree(
        self, tree: BehaviorTreeNode
    ) -> BehaviorTreeExecutionResult:
        """
        Execute a behavior tree.

        This is a PLACEHOLDER for RYR integration.
        Real implementation will integrate with ROS2/robotics stack.

        Args:
            tree: Root node of behavior tree

        Returns:
            Execution result
        """
        start_time = time.time()
        logger.info(f"🌳 Executing behavior tree: {tree.node_id}")

        # TODO: Implement real behavior tree execution
        # This is where ROS2/Robotics integration will happen
        # For now, just return a success placeholder

        executed_nodes = self._collect_node_ids(tree)
        execution_time = (time.time() - start_time) * 1000  # ms

        result = BehaviorTreeExecutionResult(
            status="success",
            node_id=tree.node_id,
            message=f"Behavior tree '{tree.node_id}' executed (placeholder)",
            executed_nodes=executed_nodes,
            execution_time_ms=execution_time,
        )

        logger.info(
            f"✅ Behavior tree '{tree.node_id}' completed in {execution_time:.2f}ms"
        )
        return result

    async def get_status(self) -> FoundationStatus:
        """
        Get current Foundation status and metrics.

        Returns:
            FoundationStatus with current state
        """
        uptime = time.time() - self.start_time
        return FoundationStatus(
            active=True,
            ethics_enabled=self.config.ethics_enabled,
            safety_checks=self.config.safety_checks,
            strict_mode=self.config.strict_mode,
            ethics_violations=self.violations,
            safety_overrides=self.overrides,
            total_validations=self.total_validations,
            last_check=datetime.utcnow(),
            uptime_seconds=uptime,
        )

    async def update_config(self, config: FoundationConfig) -> FoundationConfig:
        """
        Update Foundation configuration.

        Args:
            config: New configuration

        Returns:
            Updated configuration
        """
        old_config = self.config
        self.config = config

        logger.info("🔧 Foundation config updated:")
        logger.info(f"   Ethics: {old_config.ethics_enabled} → {config.ethics_enabled}")
        logger.info(
            f"   Safety: {old_config.safety_checks} → {config.safety_checks}"
        )
        logger.info(f"   Strict: {old_config.strict_mode} → {config.strict_mode}")

        return self.config

    def get_uptime(self) -> float:
        """
        Get Foundation service uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time

    async def get_info(self) -> FoundationInfo:
        """
        Get Foundation system information.

        Returns:
            FoundationInfo with system details
        """
        return FoundationInfo(
            name="BRAiN Foundation Layer",
            version="1.0.0",
            capabilities=[
                "action_validation",
                "ethics_rules",
                "safety_patterns",
                "behavior_trees",
                "authorization",
                "audit_logging",
            ],
            status="operational",
            uptime=self.get_uptime(),
        )

    def authorize_action(self, request: AuthorizationRequest) -> AuthorizationResponse:
        """
        Check if agent is authorized to perform an action.

        This checks permissions/authorization (different from ethics validation).

        Args:
            request: Authorization request

        Returns:
            AuthorizationResponse with authorization result
        """
        # Check if action is in blacklist (always unauthorized)
        if request.action in self.config.blocked_actions:
            response = AuthorizationResponse(
                authorized=False,
                reason=f"Action '{request.action}' is globally blocked",
                required_permissions=[],
                audit_id=self._generate_audit_id(),
            )
            self._log_audit(
                event_type="authorization",
                agent_id=request.agent_id,
                action=request.action,
                outcome="denied",
                reason=response.reason,
                details={"resource": request.resource, "context": request.context},
            )
            return response

        # TODO: Integrate with Policy Engine for real permission checks
        # Future: Check agent roles, resource ACLs, policy rules
        # For now, allow all non-blacklisted actions

        response = AuthorizationResponse(
            authorized=True,
            reason="Agent has required permissions",
            required_permissions=[],
            audit_id=self._generate_audit_id(),
        )
        self._log_audit(
            event_type="authorization",
            agent_id=request.agent_id,
            action=request.action,
            outcome="authorized",
            reason=response.reason,
            details={"resource": request.resource, "context": request.context},
        )
        logger.debug(
            f"✅ Foundation authorized action '{request.action}' for agent '{request.agent_id}'"
        )
        return response

    def query_audit_log(self, request: AuditLogRequest) -> AuditLogResponse:
        """
        Query audit log with filters.

        Args:
            request: Audit log query request

        Returns:
            AuditLogResponse with matching entries
        """
        # Filter entries
        entries = self.audit_log

        if request.agent_id:
            entries = [e for e in entries if e.agent_id == request.agent_id]
        if request.action:
            entries = [e for e in entries if e.action == request.action]
        if request.event_type:
            entries = [e for e in entries if e.event_type == request.event_type]
        if request.outcome:
            entries = [e for e in entries if e.outcome == request.outcome]

        # Sort by timestamp descending (newest first)
        entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)

        # Paginate
        total = len(entries)
        paginated = entries[request.offset : request.offset + request.limit]

        logger.debug(
            f"📋 Audit log query: {total} total, returning {len(paginated)} entries"
        )
        return AuditLogResponse(
            entries=paginated,
            total=total,
            limit=request.limit,
            offset=request.offset,
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _is_blacklisted(self, action: str) -> bool:
        """Check if action is in blacklist"""
        return any(blocked in action for blocked in self.config.blocked_actions)

    def _is_whitelisted(self, action: str) -> bool:
        """Check if action is in whitelist"""
        if not self.config.allowed_actions:
            return False
        return any(allowed in action for allowed in self.config.allowed_actions)

    def _check_ethics_rules(
        self, action: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check action against ethics rules.

        Returns:
            Violation message if rule violated, None otherwise
        """
        if not self.config.ethics_enabled:
            return None

        # TODO: Implement real ethics rule engine
        # For now, just some basic heuristics

        # Example: Don't allow actions with "hack" or "exploit"
        if "hack" in action or "exploit" in action:
            return "Action contains unethical keywords (hack/exploit)"

        return None

    def _check_safety_patterns(
        self, action: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check action against safety patterns.

        Returns:
            Safety issue message if detected, None otherwise
        """
        if not self.config.safety_checks:
            return None

        # Pattern 1: Dangerous filesystem operations
        dangerous_fs = ["rm -rf", "del /f", "shred", "wipe"]
        if any(pattern in action for pattern in dangerous_fs):
            return "Detected dangerous filesystem operation"

        # Pattern 2: Database operations on production
        if "drop" in action and "database" in action:
            return "Detected potentially destructive database operation"

        # Pattern 3: Network operations to suspicious domains
        if "connect" in action and params.get("target"):
            target = str(params["target"]).lower()
            suspicious = ["malware", "exploit", "hack"]
            if any(word in target for word in suspicious):
                return "Detected connection to suspicious target"

        return None

    def _get_safe_alternatives(self, blocked_action: str) -> List[str]:
        """
        Suggest safe alternatives for a blocked action.

        Args:
            blocked_action: The action that was blocked

        Returns:
            List of safe alternative actions
        """
        # TODO: Implement intelligent suggestion system
        # For now, return generic suggestions

        if "delete" in blocked_action:
            return ["Use backup_and_delete", "Use archive_instead_of_delete"]

        if "format" in blocked_action:
            return ["Create backup first", "Use safe_wipe with confirmation"]

        return ["Review action safety", "Contact administrator"]

    def _collect_node_ids(self, node: BehaviorTreeNode) -> List[str]:
        """
        Recursively collect all node IDs from a behavior tree.

        Args:
            node: Root node

        Returns:
            List of all node IDs in the tree
        """
        ids = [node.node_id]
        for child in node.children:
            ids.extend(self._collect_node_ids(child))
        return ids

    def _generate_audit_id(self) -> str:
        """
        Generate unique audit ID.

        Returns:
            Audit ID in format "audit_YYYYMMDD_HHMMSS"
        """
        return datetime.now().strftime("audit_%Y%m%d_%H%M%S")

    def _log_audit(
        self,
        event_type: str,
        agent_id: Optional[str],
        action: str,
        outcome: str,
        reason: str,
        details: Dict[str, Any],
    ):
        """
        Log audit event to in-memory audit log.

        Args:
            event_type: Type of event ("validation" or "authorization")
            agent_id: Agent ID (if applicable)
            action: Action that was checked
            outcome: Event outcome ("allowed", "blocked", "authorized", "denied")
            reason: Reason for outcome
            details: Additional event details
        """
        entry = AuditLogEntry(
            audit_id=self._generate_audit_id(),
            timestamp=datetime.now(),
            event_type=event_type,  # type: ignore
            agent_id=agent_id,
            action=action,
            outcome=outcome,  # type: ignore
            reason=reason,
            details=details,
        )

        self.audit_log.append(entry)

        # Keep only last N entries (circular buffer)
        if len(self.audit_log) > self.max_audit_entries:
            self.audit_log = self.audit_log[-self.max_audit_entries :]

        logger.debug(f"📝 Audit logged: {event_type} - {action} - {outcome}")


# ============================================================================
# Singleton Instance
# ============================================================================

_foundation_service: Optional[FoundationService] = None


def get_foundation_service() -> FoundationService:
    """
    Get the singleton Foundation service instance.

    Returns:
        FoundationService instance
    """
    global _foundation_service
    if _foundation_service is None:
        _foundation_service = FoundationService()
    return _foundation_service
