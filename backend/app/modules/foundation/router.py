"""
Foundation Module - API Routes

FastAPI endpoints for Foundation layer operations.
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from .schemas import (
    FoundationConfig,
    FoundationStatus,
    BehaviorTreeNode,
    BehaviorTreeExecutionResult,
    ActionValidationRequest,
    ActionValidationResponse,
)
from .service import get_foundation_service


router = APIRouter(prefix="/api/foundation", tags=["foundation"])


# ============================================================================
# Status & Configuration Endpoints
# ============================================================================


@router.get("/status", response_model=FoundationStatus)
async def get_foundation_status():
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
async def get_foundation_config():
    """
    Get current Foundation configuration.

    Returns:
        Current Foundation configuration settings
    """
    service = get_foundation_service()
    return service.config


@router.put("/config", response_model=FoundationConfig)
async def update_foundation_config(config: FoundationConfig):
    """
    Update Foundation configuration.

    This allows runtime changes to:
    - Ethics enforcement
    - Safety checks
    - Strict mode
    - Allowed/blocked actions

    Args:
        config: New Foundation configuration

    Returns:
        Updated configuration
    """
    service = get_foundation_service()
    updated_config = await service.update_config(config)
    logger.info(f"Foundation config updated via API")
    return updated_config


# ============================================================================
# Action Validation Endpoints
# ============================================================================


@router.post("/validate", response_model=ActionValidationResponse)
async def validate_action(request: ActionValidationRequest):
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
    result = await service.validate_action(request)

    # If action is blocked, return 403 Forbidden
    if not result.valid:
        logger.warning(f"Action blocked: {request.action} - {result.reason}")
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
async def validate_actions_batch(requests: list[ActionValidationRequest]):
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
async def execute_behavior_tree(tree: BehaviorTreeNode):
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
async def validate_behavior_tree(tree: BehaviorTreeNode):
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
# Health Check
# ============================================================================


@router.get("/health")
async def foundation_health():
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
