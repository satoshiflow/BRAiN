"""
Policy Module - API Routes

FastAPI endpoints for Policy Engine operations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.auth_deps import require_auth, require_role, get_current_principal, Principal
from .service import get_health, get_info, get_policy_engine
from .schemas import (
    PolicyHealth,
    PolicyInfo,
    Policy,
    PolicyStats,
    PolicyCreateRequest,
    PolicyUpdateRequest,
    PolicyListResponse,
    PolicyEvaluationContext,
    PolicyEvaluationResult,
)


router = APIRouter(
    prefix="/api/policy",
    tags=["policy"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Legacy Endpoints (backward compatibility)
# ============================================================================


@router.get("/health", response_model=PolicyHealth)
async def policy_health(principal: Principal = Depends(get_current_principal)):
    """Legacy health check endpoint"""
    return await get_health()


@router.get("/info", response_model=PolicyInfo)
async def policy_info(principal: Principal = Depends(get_current_principal)):
    """Legacy info endpoint"""
    return await get_info()


# ============================================================================
# Policy Engine Endpoints (NEW in v2.0)
# ============================================================================


@router.get("/stats", response_model=PolicyStats)
async def get_policy_stats():
    """
    Get policy system statistics.

    Returns metrics about policies, rules, and evaluations.
    """
    engine = get_policy_engine()
    return await engine.get_stats()


@router.post("/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_policy(context: PolicyEvaluationContext):
    """
    Evaluate if an action is allowed based on policies.

    This is the main endpoint for policy enforcement.

    Args:
        context: Evaluation context containing:
            - agent_id: ID of agent requesting action
            - agent_role: Agent role/type
            - action: Action being requested
            - resource: Resource being accessed (optional)
            - environment: Environmental context (optional)
            - params: Action parameters (optional)

    Returns:
        PolicyEvaluationResult with decision and reason

    Raises:
        HTTPException 403: If action is denied by policy

    Example:
        ```json
        POST /api/policy/evaluate
        {
          "agent_id": "robot_001",
          "agent_role": "fleet_member",
          "action": "robot.move",
          "resource": "warehouse_zone_a",
          "environment": {"time": "daytime"},
          "params": {"distance": 10}
        }
        ```
    """
    engine = get_policy_engine()
    result = await engine.evaluate(context)

    # If denied, return 403
    if not result.allowed:
        logger.warning(
            f"Policy denied: agent={context.agent_id}, action={context.action}, reason={result.reason}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Action denied by policy",
                "reason": result.reason,
                "effect": result.effect.value,
                "matched_rule": result.matched_rule,
                "matched_policy": result.matched_policy,
            },
        )

    return result


# ============================================================================
# Policy CRUD Endpoints
# ============================================================================


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies():
    """
    List all policies.

    Returns:
        List of all policies in the system
    """
    engine = get_policy_engine()
    policies = await engine.list_policies()
    return PolicyListResponse(total=len(policies), policies=policies)


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(policy_id: str):
    """
    Get a specific policy by ID.

    Args:
        policy_id: Unique policy identifier

    Returns:
        Policy details

    Raises:
        HTTPException 404: If policy not found
    """
    engine = get_policy_engine()
    policy = await engine.get_policy(policy_id)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    return policy


@router.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def create_policy(request: PolicyCreateRequest):
    """
    Create a new policy.

    Args:
        request: Policy creation request

    Returns:
        Created policy

    Example:
        ```json
        POST /api/policy/policies
        {
          "name": "Robot Safety Policy",
          "version": "1.0.0",
          "description": "Safety rules for robot operations",
          "rules": [
            {
              "rule_id": "low_battery_deny",
              "name": "Deny Movement on Low Battery",
              "effect": "deny",
              "conditions": [
                {
                  "field": "environment.battery_level",
                  "operator": "<",
                  "value": 20
                }
              ],
              "priority": 100
            }
          ],
          "default_effect": "deny"
        }
        ```
    """
    engine = get_policy_engine()
    policy = await engine.create_policy(request)
    logger.info(f"Created policy: {policy.policy_id}")
    return policy


@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(policy_id: str, request: PolicyUpdateRequest):
    """
    Update an existing policy.

    Args:
        policy_id: Policy to update
        request: Update request (only changed fields)

    Returns:
        Updated policy

    Raises:
        HTTPException 404: If policy not found
    """
    engine = get_policy_engine()
    policy = await engine.update_policy(policy_id, request)

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    logger.info(f"Updated policy: {policy_id}")
    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(policy_id: str):
    """
    Delete a policy.

    Args:
        policy_id: Policy to delete

    Raises:
        HTTPException 404: If policy not found
    """
    engine = get_policy_engine()
    deleted = await engine.delete_policy(policy_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )

    logger.info(f"Deleted policy: {policy_id}")


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.post("/test-rule")
async def test_policy_rule(context: PolicyEvaluationContext):
    """
    Test policy evaluation without actually enforcing it.

    Useful for debugging policies.

    Returns:
        Same as /evaluate but doesn't raise 403 on deny
    """
    engine = get_policy_engine()
    result = await engine.evaluate(context)
    return result


@router.get("/default-policies", response_model=List[str])
async def list_default_policies():
    """
    List IDs of default policies.

    Returns:
        List of default policy IDs
    """
    return ["admin_full_access", "guest_read_only"]
