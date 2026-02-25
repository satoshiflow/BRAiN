"""
Foundation Module - API Routes

FastAPI endpoints for Foundation layer operations.
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends, Request
from loguru import logger

from app.core.auth_deps import (
    require_auth,
    require_role,
    SystemRole,
    Principal,
)
from app.core.rate_limit import limiter, RateLimits

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
    AuditLogRequest,
    AuditLogResponse,
)
from .service import get_foundation_service


router = APIRouter(prefix="/api/foundation", tags=["foundation"])


def _audit_log(
    action: str,
    principal: Principal,
    details: Optional[dict] = None,
):
    """Log foundation operations for audit trail"""
    audit_entry = {
        "action": action,
        "principal_id": principal.principal_id,
        "principal_type": principal.principal_type.value,
        "tenant_id": principal.tenant_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] Foundation operation: {audit_entry}")


# ============================================================================
# Status & Configuration Endpoints
# ============================================================================


@router.get("/status", response_model=FoundationStatus)
async def get_foundation_status(
    principal: Principal = Depends(require_auth),
):
    """
    Get Foundation system status and metrics.

    Returns:
        Current Foundation status including:
        - Active state
        - Ethics/safety settings
        - Violation counts
        - Uptime
    """
    service = get_foundation_service()
    return await service.get_status()


@router.get("/config", response_model=FoundationConfig)
async def get_foundation_config(
    principal: Principal = Depends(require_auth),
):
    """
    Get current Foundation configuration.

    Returns:
        Current Foundation configuration settings
    """
    service = get_foundation_service()
    _audit_log("get_foundation_config", principal)
    return service.config


@router.put("/config", response_model=FoundationConfig)
async def update_foundation_config(
    config: FoundationConfig,
    principal: Principal = Depends(require_role(SystemRole.ADMIN)),
):
    """
    Update Foundation configuration.

    This allows runtime changes to:
    - Ethics enforcement
    - Safety checks
    - Strict mode
    - Allowed/blocked actions

    **Requires ADMIN role** - This is a CRITICAL endpoint that modifies
    ethics and safety settings.

    Args:
        config: New Foundation configuration

    Returns:
        Updated configuration
    """
    service = get_foundation_service()

    # Log the config change attempt with before/after for audit trail
    _audit_log(
        "update_foundation_config",
        principal,
        details={
            "config_changes": config.model_dump(),
            "previous_config": service.config.model_dump() if hasattr(service.config, 'model_dump') else str(service.config),
        },
    )

    updated_config = await service.update_config(config)
    logger.info(f"Foundation config updated via API by {principal.principal_id}")

    _audit_log(
        "foundation_config_updated",
        principal,
        details={"config": updated_config.model_dump() if hasattr(updated_config, 'model_dump') else str(updated_config)},
    )

    return updated_config


# ============================================================================
# Action Validation Endpoints
# ============================================================================


@router.post("/validate", response_model=ActionValidationResponse)
@limiter.limit(RateLimits.FOUNDATION_VALIDATE)
async def validate_action(
    request: Request,
    validation_request: ActionValidationRequest,
    principal: Principal = Depends(require_auth),
):
    """
    Validate if an action is ethically and safely permissible.

    This endpoint checks an action against:
    1. Blacklist (always blocked actions)
    2. Whitelist (if strict mode enabled)
    3. Ethics rules
    4. Safety patterns

    Args:
        request: Action validation request containing:
            - action: Action name (e.g., "robot.move")
            - params: Action parameters
            - context: Additional context (agent_id, etc.)

    Returns:
        Validation result indicating if action is allowed

    Raises:
        HTTPException 403: If action is blocked by Foundation layer

    Example:
        ```json
        POST /api/foundation/validate
        {
          "action": "robot.move",
          "params": {"distance": 10, "speed": 2},
          "context": {"agent_id": "robot_001"}
        }
        ```
    """
    service = get_foundation_service()
    result = await service.validate_action(validation_request)

    # If action is blocked, return 403 Forbidden
    if not result.valid:
        logger.warning(f"Action blocked: {validation_request.action} - {result.reason}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Action blocked by Foundation layer",
                "action": result.action,
                "reason": result.reason,
                "severity": result.severity,
                "suggestions": result.suggestions,
            },
        )

    return result


@router.post("/validate-batch", response_model=Dict[str, ActionValidationResponse])
async def validate_actions_batch(
    requests: list[ActionValidationRequest],
    principal: Principal = Depends(require_auth),
):
    """
    Validate multiple actions in batch.

    Useful for pre-validating a sequence of actions.

    Args:
        requests: List of action validation requests

    Returns:
        Dictionary mapping action names to validation results
    """
    service = get_foundation_service()
    results = {}

    for req in requests:
        result = await service.validate_action(req)
        results[req.action] = result

    return results


# ============================================================================
# Behavior Tree Endpoints
# ============================================================================


@router.post("/behavior-tree/execute", response_model=BehaviorTreeExecutionResult)
async def execute_behavior_tree(
    tree: BehaviorTreeNode,
    principal: Principal = Depends(require_auth),
):
    """
    Execute a behavior tree.

    **Note:** This is currently a PLACEHOLDER for RYR integration.
    Real implementation will integrate with ROS2/robotics stack.

    Args:
        tree: Behavior tree root node

    Returns:
        Execution result

    Example:
        ```json
        POST /api/foundation/behavior-tree/execute
        {
          "node_id": "navigation_sequence",
          "node_type": "sequence",
          "children": [
            {
              "node_id": "check_battery",
              "node_type": "condition",
              "action": "battery.check",
              "params": {"min_level": 20}
            },
            {
              "node_id": "move_to_target",
              "node_type": "action",
              "action": "robot.move",
              "params": {"target": "waypoint_1"}
            }
          ]
        }
        ```
    """
    service = get_foundation_service()
    result = await service.execute_behavior_tree(tree)
    return result


@router.post("/behavior-tree/validate", response_model=Dict[str, Any])
async def validate_behavior_tree(
    tree: BehaviorTreeNode,
    principal: Principal = Depends(require_auth),
):
    """
    Validate a behavior tree without executing it.

    Checks:
    - All actions in the tree are ethically/safely permissible
    - Tree structure is valid
    - No cyclic dependencies

    Args:
        tree: Behavior tree to validate

    Returns:
        Validation result with issues (if any)
    """
    service = get_foundation_service()

    # Collect all actions from the tree
    actions = _extract_actions_from_tree(tree)

    # Validate each action
    issues = []
    for action_name, params in actions:
        request = ActionValidationRequest(
            action=action_name, params=params, context={"source": "behavior_tree"}
        )
        result = await service.validate_action(request)

        if not result.valid:
            issues.append(
                {
                    "action": action_name,
                    "reason": result.reason,
                    "severity": result.severity,
                }
            )

    return {
        "valid": len(issues) == 0,
        "tree_id": tree.node_id,
        "total_actions": len(actions),
        "issues": issues,
    }


# ============================================================================
# System Info & Authorization Endpoints
# ============================================================================


@router.get("/info", response_model=FoundationInfo)
async def get_foundation_info(
    principal: Principal = Depends(require_auth),
):
    """
    Get Foundation system information.

    Returns:
        Foundation system details including:
        - System name and version
        - Available capabilities
        - Current status
        - Uptime

    Example:
        ```json
        GET /api/foundation/info
        {
          "name": "BRAiN Foundation Layer",
          "version": "1.0.0",
          "capabilities": [
            "action_validation",
            "ethics_rules",
            "safety_patterns",
            "behavior_trees",
            "authorization",
            "audit_logging"
          ],
          "status": "operational",
          "uptime": 3600.5
        }
        ```
    """
    service = get_foundation_service()
    return await service.get_info()


@router.post("/authorize", response_model=AuthorizationResponse)
async def authorize_action(
    request: AuthorizationRequest,
    principal: Principal = Depends(require_auth),
):
    """
    Check if agent is authorized to perform an action.

    This checks permissions/authorization (different from ethics validation).

    Args:
        request: Authorization request containing:
            - agent_id: Agent requesting authorization
            - action: Action to authorize
            - resource: Resource being accessed
            - context: Additional context

    Returns:
        Authorization result indicating if action is authorized

    Raises:
        HTTPException 403: If action is not authorized

    Example:
        ```json
        POST /api/foundation/authorize
        {
          "agent_id": "ops_agent",
          "action": "deploy_to_production",
          "resource": "brain-backend",
          "context": {"environment": "production"}
        }
        ```
    """
    service = get_foundation_service()

    _audit_log(
        "authorize_action",
        principal,
        details={
            "request_agent_id": request.agent_id,
            "action": request.action,
            "resource": request.resource,
        },
    )

    result = service.authorize_action(request)

    # If not authorized, return 403 Forbidden
    if not result.authorized:
        logger.warning(
            f"Authorization denied: {request.action} for agent {request.agent_id} by principal {principal.principal_id}"
        )
        _audit_log(
            "authorize_action_denied",
            principal,
            details={
                "request_agent_id": request.agent_id,
                "action": request.action,
                "resource": request.resource,
                "reason": result.reason,
                "audit_id": result.audit_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Action not authorized",
                "agent_id": request.agent_id,
                "action": request.action,
                "resource": request.resource,
                "reason": result.reason,
                "audit_id": result.audit_id,
            },
        )

    _audit_log(
        "authorize_action_granted",
        principal,
        details={
            "request_agent_id": request.agent_id,
            "action": request.action,
            "resource": request.resource,
            "audit_id": result.audit_id,
        },
    )

    return result


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    principal: Principal = Depends(require_role(SystemRole.ADMIN)),
):
    """
    Retrieve audit log entries.

    **Requires ADMIN role** - Audit logs contain sensitive security information.

    Query Foundation audit trail with optional filters.

    Query Parameters:
        - agent_id: Filter by agent ID
        - action: Filter by action name
        - event_type: Filter by event type (validation, authorization)
        - outcome: Filter by outcome (allowed, blocked, authorized, denied)
        - limit: Maximum entries to return (1-1000, default 100)
        - offset: Pagination offset (default 0)

    Returns:
        Paginated audit log entries

    Example:
        ```
        GET /api/foundation/audit-log?agent_id=ops_agent&outcome=blocked&limit=50
        {
          "entries": [
            {
              "audit_id": "audit_20260115_170000",
              "timestamp": "2026-01-15T17:00:00Z",
              "event_type": "validation",
              "agent_id": "ops_agent",
              "action": "delete_all",
              "outcome": "blocked",
              "reason": "Action is in blacklist",
              "details": {}
            }
          ],
          "total": 1,
          "limit": 50,
          "offset": 0
        }
        ```
    """
    service = get_foundation_service()

    _audit_log(
        "query_audit_log",
        principal,
        details={
            "filters": {
                "agent_id": agent_id,
                "action": action,
                "event_type": event_type,
                "outcome": outcome,
                "limit": limit,
                "offset": offset,
            }
        },
    )

    request = AuditLogRequest(
        agent_id=agent_id,
        action=action,
        event_type=event_type,
        outcome=outcome,
        limit=limit,
        offset=offset,
    )
    return service.query_audit_log(request)


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def foundation_health(
    principal: Principal = Depends(require_auth),
):
    """
    Health check endpoint for Foundation module.

    Returns:
        Health status
    """
    service = get_foundation_service()
    status_info = await service.get_status()

    return {
        "status": "healthy" if status_info.active else "degraded",
        "module": "foundation",
        "version": "0.1.0",
        "uptime_seconds": status_info.uptime_seconds,
    }


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_actions_from_tree(node: BehaviorTreeNode) -> list[tuple[str, dict]]:
    """
    Recursively extract all actions from a behavior tree.

    Args:
        node: Tree node to extract from

    Returns:
        List of (action_name, params) tuples
    """
    actions = []

    # If this node has an action, add it
    if node.action:
        actions.append((node.action, node.params))

    # Recursively process children
    for child in node.children:
        actions.extend(_extract_actions_from_tree(child))

    return actions
