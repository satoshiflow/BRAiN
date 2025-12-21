"""
Test Data Generator

Generates realistic test data for development and testing.

Features:
- Mission test data
- Agent test data
- User test data
- Audit log test data
- Random data generation with Faker

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List


# ============================================================================
# Mission Test Data
# ============================================================================

def generate_mission(
    status: str = "pending",
    priority: str = "NORMAL",
    **overrides
) -> Dict[str, Any]:
    """
    Generate test mission data.

    Args:
        status: Mission status (pending, queued, running, completed, failed)
        priority: Mission priority (LOW, NORMAL, HIGH, CRITICAL)
        **overrides: Override specific fields

    Returns:
        Mission data dictionary
    """
    mission_types = [
        "deploy_application",
        "run_tests",
        "code_review",
        "data_analysis",
        "system_maintenance",
    ]

    mission = {
        "id": str(uuid.uuid4()),
        "name": f"Test Mission {random.randint(1000, 9999)}",
        "description": random.choice([
            "Deploy application to production",
            "Run integration test suite",
            "Perform code review on PR",
            "Analyze system metrics",
            "Clean up old resources",
        ]),
        "status": status,
        "priority": priority,
        "mission_type": random.choice(mission_types),
        "payload": {
            "environment": random.choice(["development", "staging", "production"]),
            "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
        },
        "created_at": (datetime.utcnow() - timedelta(hours=random.randint(0, 48))).isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "max_retries": 3,
        "retry_count": 0,
    }

    mission.update(overrides)
    return mission


def generate_missions(count: int = 10) -> List[Dict[str, Any]]:
    """Generate multiple test missions."""
    statuses = ["pending", "queued", "running", "completed", "failed"]
    priorities = ["LOW", "NORMAL", "HIGH", "CRITICAL"]

    return [
        generate_mission(
            status=random.choice(statuses),
            priority=random.choice(priorities)
        )
        for _ in range(count)
    ]


# ============================================================================
# Agent Test Data
# ============================================================================

def generate_agent(
    status: str = "active",
    **overrides
) -> Dict[str, Any]:
    """
    Generate test agent data.

    Args:
        status: Agent status (active, inactive, error)
        **overrides: Override specific fields

    Returns:
        Agent data dictionary
    """
    agent_types = [
        "ops_specialist",
        "code_specialist",
        "architect",
        "supervisor",
        "fleet_coordinator",
    ]

    capabilities = [
        ["deployment", "monitoring"],
        ["code_generation", "code_review"],
        ["system_design", "architecture_review"],
        ["task_coordination", "agent_management"],
        ["robot_coordination", "path_planning"],
    ]

    agent_type = random.choice(agent_types)

    agent = {
        "id": str(uuid.uuid4()),
        "name": f"{agent_type}_{random.randint(1000, 9999)}",
        "type": agent_type,
        "status": status,
        "capabilities": random.choice(capabilities),
        "metadata": {
            "version": "1.0.0",
            "created_by": "system",
        },
        "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat(),
        "last_heartbeat": datetime.utcnow().isoformat(),
    }

    agent.update(overrides)
    return agent


def generate_agents(count: int = 5) -> List[Dict[str, Any]]:
    """Generate multiple test agents."""
    statuses = ["active", "inactive", "error"]

    return [
        generate_agent(status=random.choice(statuses))
        for _ in range(count)
    ]


# ============================================================================
# User Test Data
# ============================================================================

def generate_user(**overrides) -> Dict[str, Any]:
    """
    Generate test user data.

    Args:
        **overrides: Override specific fields

    Returns:
        User data dictionary
    """
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

    first_name = random.choice(first_names)
    last_name = random.choice(last_names)

    user = {
        "id": str(uuid.uuid4()),
        "username": f"{first_name.lower()}.{last_name.lower()}",
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "first_name": first_name,
        "last_name": last_name,
        "role": random.choice(["user", "moderator", "admin"]),
        "active": random.choice([True, True, True, False]),  # 75% active
        "created_at": (datetime.utcnow() - timedelta(days=random.randint(30, 365))).isoformat(),
    }

    user.update(overrides)
    return user


def generate_users(count: int = 10) -> List[Dict[str, Any]]:
    """Generate multiple test users."""
    return [generate_user() for _ in range(count)]


# ============================================================================
# Audit Log Test Data
# ============================================================================

def generate_audit_log(**overrides) -> Dict[str, Any]:
    """
    Generate test audit log entry.

    Args:
        **overrides: Override specific fields

    Returns:
        Audit log data dictionary
    """
    actions = [
        "user.login",
        "user.logout",
        "mission.create",
        "mission.update",
        "mission.delete",
        "agent.start",
        "agent.stop",
        "config.update",
    ]

    log = {
        "id": str(uuid.uuid4()),
        "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(0, 72))).isoformat(),
        "user_id": str(uuid.uuid4()),
        "action": random.choice(actions),
        "resource_type": random.choice(["mission", "agent", "user", "config"]),
        "resource_id": str(uuid.uuid4()),
        "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "details": {
            "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
            "endpoint": "/api/missions",
            "status_code": random.choice([200, 201, 204, 400, 404, 500]),
        },
    }

    log.update(overrides)
    return log


def generate_audit_logs(count: int = 100) -> List[Dict[str, Any]]:
    """Generate multiple test audit logs."""
    return [generate_audit_log() for _ in range(count)]


# ============================================================================
# Task Test Data
# ============================================================================

def generate_task(
    status: str = "PENDING",
    **overrides
) -> Dict[str, Any]:
    """
    Generate test Celery task data.

    Args:
        status: Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
        **overrides: Override specific fields

    Returns:
        Task data dictionary
    """
    task_names = [
        "backend.app.tasks.system_tasks.health_check",
        "backend.app.tasks.mission_tasks.process_mission_async",
        "backend.app.tasks.agent_tasks.check_agent_heartbeats",
        "backend.app.tasks.maintenance_tasks.cleanup_audit_logs",
    ]

    task = {
        "task_id": str(uuid.uuid4()),
        "task_name": random.choice(task_names),
        "status": status,
        "args": [],
        "kwargs": {},
        "queue": random.choice(["default", "system", "missions", "agents", "maintenance"]),
        "created_at": (datetime.utcnow() - timedelta(minutes=random.randint(0, 120))).isoformat(),
    }

    if status in ["SUCCESS", "FAILURE"]:
        task["result"] = {
            "status": "success" if status == "SUCCESS" else "failed",
            "duration_ms": random.randint(100, 5000),
        }

    task.update(overrides)
    return task


def generate_tasks(count: int = 20) -> List[Dict[str, Any]]:
    """Generate multiple test tasks."""
    statuses = ["PENDING", "STARTED", "SUCCESS", "FAILURE"]

    return [
        generate_task(status=random.choice(statuses))
        for _ in range(count)
    ]


# ============================================================================
# Metrics Test Data
# ============================================================================

def generate_metrics(**overrides) -> Dict[str, Any]:
    """
    Generate test metrics data.

    Args:
        **overrides: Override specific fields

    Returns:
        Metrics data dictionary
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": random.uniform(10.0, 90.0),
        "memory_percent": random.uniform(30.0, 85.0),
        "disk_percent": random.uniform(20.0, 70.0),
        "api_requests_total": random.randint(1000, 50000),
        "api_requests_per_minute": random.randint(10, 500),
        "avg_response_time_ms": random.uniform(50.0, 500.0),
        "error_rate": random.uniform(0.0, 5.0),
        "active_connections": random.randint(5, 100),
        "active_tasks": random.randint(0, 20),
    }

    metrics.update(overrides)
    return metrics


def generate_metrics_timeseries(count: int = 60) -> List[Dict[str, Any]]:
    """Generate time series metrics data."""
    return [
        generate_metrics(
            timestamp=(datetime.utcnow() - timedelta(minutes=i)).isoformat()
        )
        for i in range(count - 1, -1, -1)
    ]


# ============================================================================
# Bulk Data Generation
# ============================================================================

def generate_test_dataset() -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate complete test dataset.

    Returns:
        Dictionary with all test data types
    """
    return {
        "missions": generate_missions(50),
        "agents": generate_agents(10),
        "users": generate_users(20),
        "audit_logs": generate_audit_logs(200),
        "tasks": generate_tasks(50),
        "metrics": generate_metrics_timeseries(60),
    }


# ============================================================================
# Export Functions
# ============================================================================

def export_to_json(data: Dict[str, Any], output_path: str):
    """Export test data to JSON file."""
    import json
    from pathlib import Path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"✓ Test data exported to {output_path}")


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Generate and export test data."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate test data")
    parser.add_argument(
        "--output",
        "-o",
        default="test_data.json",
        help="Output file path (default: test_data.json)",
    )
    parser.add_argument(
        "--missions",
        type=int,
        default=50,
        help="Number of missions to generate (default: 50)",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=10,
        help="Number of agents to generate (default: 10)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=20,
        help="Number of users to generate (default: 20)",
    )

    args = parser.parse_args()

    print("Generating test data...")

    data = {
        "missions": generate_missions(args.missions),
        "agents": generate_agents(args.agents),
        "users": generate_users(args.users),
        "audit_logs": generate_audit_logs(200),
        "tasks": generate_tasks(50),
        "metrics": generate_metrics_timeseries(60),
    }

    export_to_json(data, args.output)

    print(f"\nGenerated:")
    print(f"  - {len(data['missions'])} missions")
    print(f"  - {len(data['agents'])} agents")
    print(f"  - {len(data['users'])} users")
    print(f"  - {len(data['audit_logs'])} audit logs")
    print(f"  - {len(data['tasks'])} tasks")
    print(f"  - {len(data['metrics'])} metrics entries")


if __name__ == "__main__":
    main()
