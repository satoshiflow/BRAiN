"""
Prometheus Metrics Collection

Collects and exports metrics for Constitutional Agents Framework.
"""

from prometheus_client import Counter, Gauge, Histogram, Info
from typing import Dict


# ============================================================================
# System Info
# ============================================================================

brain_info = Info("brain_system", "BRAiN system information")
brain_info.info({
    "version": "0.5.0",
    "framework": "constitutional_agents",
})


# ============================================================================
# Supervisor Metrics
# ============================================================================

supervisor_requests_total = Counter(
    "supervisor_requests_total",
    "Total supervision requests",
    ["agent", "risk_level"]
)

supervisor_approvals_total = Counter(
    "supervisor_approvals_total",
    "Total approved actions",
    ["agent", "risk_level"]
)

supervisor_denials_total = Counter(
    "supervisor_denials_total",
    "Total denied actions",
    ["agent", "risk_level", "reason"]
)

supervisor_llm_checks_total = Counter(
    "supervisor_llm_checks_total",
    "Total constitutional LLM checks",
    ["result"]
)

supervisor_response_time = Histogram(
    "supervisor_response_time_seconds",
    "Supervision request response time",
    ["risk_level"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)


# ============================================================================
# HITL Metrics
# ============================================================================

hitl_queue_size = Gauge(
    "hitl_queue_size",
    "Current HITL approval queue size"
)

hitl_approvals_total = Counter(
    "hitl_approvals_total",
    "Total HITL approvals",
    ["decision"]  # approved, denied
)

hitl_expired_total = Counter(
    "hitl_expired_total",
    "Total expired HITL requests"
)

hitl_approval_time = Histogram(
    "hitl_approval_time_seconds",
    "Time to approve HITL requests",
    buckets=[60, 300, 600, 1800, 3600, 7200]  # 1min to 2hrs
)


# ============================================================================
# Policy Engine Metrics
# ============================================================================

policy_evaluations_total = Counter(
    "policy_evaluations_total",
    "Total policy evaluations",
    ["effect"]  # allow, deny, warn, audit
)

policy_rules_total = Gauge(
    "policy_rules_total",
    "Total policy rules in system"
)

policy_active_policies = Gauge(
    "policy_active_policies",
    "Number of active policies"
)

policy_evaluation_time = Histogram(
    "policy_evaluation_time_seconds",
    "Policy evaluation response time",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5]
)


# ============================================================================
# Agent Operations Metrics
# ============================================================================

agent_operations_total = Counter(
    "agent_operations_total",
    "Total agent operations",
    ["agent", "operation", "status"]  # status: success, failure
)

agent_code_generation_total = Counter(
    "agent_code_generation_total",
    "Code generations by CoderAgent",
    ["code_type"]  # python, odoo_module, etc.
)

agent_deployments_total = Counter(
    "agent_deployments_total",
    "Deployments by OpsAgent",
    ["environment", "status"]  # environment: dev, staging, production
)

agent_rollbacks_total = Counter(
    "agent_rollbacks_total",
    "Rollbacks by OpsAgent",
    ["environment", "reason"]
)

agent_compliance_checks_total = Counter(
    "agent_compliance_checks_total",
    "Compliance checks by ArchitectAgent",
    ["framework", "result"]  # framework: dsgvo, eu_ai_act
)


# ============================================================================
# Authentication Metrics
# ============================================================================

auth_login_attempts_total = Counter(
    "auth_login_attempts_total",
    "Total login attempts",
    ["status"]  # success, failure
)

auth_active_sessions = Gauge(
    "auth_active_sessions",
    "Current active authenticated sessions"
)

auth_token_refreshes_total = Counter(
    "auth_token_refreshes_total",
    "Total token refresh operations"
)


# ============================================================================
# Mission System Metrics (Legacy)
# ============================================================================

mission_queue_size = Gauge(
    "mission_queue_size",
    "Current mission queue size"
)

missions_total = Counter(
    "missions_total",
    "Total missions",
    ["status"]  # pending, running, completed, failed
)

mission_execution_time = Histogram(
    "mission_execution_time_seconds",
    "Mission execution duration",
    buckets=[1, 5, 10, 30, 60, 300, 600]
)


# ============================================================================
# Utility Functions
# ============================================================================

def record_supervisor_request(agent: str, risk_level: str, approved: bool, duration: float):
    """Record a supervision request"""
    supervisor_requests_total.labels(agent=agent, risk_level=risk_level).inc()

    if approved:
        supervisor_approvals_total.labels(agent=agent, risk_level=risk_level).inc()
    else:
        supervisor_denials_total.labels(agent=agent, risk_level=risk_level, reason="policy").inc()

    supervisor_response_time.labels(risk_level=risk_level).observe(duration)


def record_hitl_approval(decision: str, time_to_approve: float):
    """Record a HITL approval"""
    hitl_approvals_total.labels(decision=decision).inc()
    hitl_approval_time.observe(time_to_approve)


def record_policy_evaluation(effect: str, duration: float):
    """Record a policy evaluation"""
    policy_evaluations_total.labels(effect=effect).inc()
    policy_evaluation_time.observe(duration)


def record_agent_operation(agent: str, operation: str, success: bool):
    """Record an agent operation"""
    status = "success" if success else "failure"
    agent_operations_total.labels(agent=agent, operation=operation, status=status).inc()


def record_login_attempt(success: bool):
    """Record a login attempt"""
    status = "success" if success else "failure"
    auth_login_attempts_total.labels(status=status).inc()


def update_queue_sizes(hitl_size: int, mission_size: int):
    """Update queue size gauges"""
    hitl_queue_size.set(hitl_size)
    mission_queue_size.set(mission_size)


def update_policy_stats(total_rules: int, active_policies: int):
    """Update policy statistics"""
    policy_rules_total.set(total_rules)
    policy_active_policies.set(active_policies)
