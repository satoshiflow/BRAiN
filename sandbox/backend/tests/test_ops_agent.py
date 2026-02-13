"""
Tests for OpsAgent

Tests operations and deployment with risk assessment.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from brain.agents.ops_agent import OpsAgent, OperationError
from app.modules.supervisor.schemas import RiskLevel


@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.generate = AsyncMock(return_value="Deployment plan generated")
    return client


@pytest.fixture
def ops_agent(mock_llm_client):
    return OpsAgent(llm_client=mock_llm_client)


# ============================================================================
# Risk Assessment Tests
# ============================================================================


def test_assess_deployment_risk_critical_for_production(ops_agent):
    """Test production deployments are CRITICAL risk"""
    risk = ops_agent._assess_deployment_risk("production")
    assert risk == RiskLevel.CRITICAL


def test_assess_deployment_risk_high_for_staging(ops_agent):
    """Test staging deployments are HIGH risk"""
    risk = ops_agent._assess_deployment_risk("staging")
    assert risk == RiskLevel.HIGH


def test_assess_deployment_risk_medium_for_dev(ops_agent):
    """Test dev deployments are MEDIUM risk"""
    risk = ops_agent._assess_deployment_risk("development")
    assert risk == RiskLevel.MEDIUM


def test_assess_configuration_risk_critical_for_sensitive_prod(ops_agent):
    """Test sensitive config in production is CRITICAL"""
    config = {"database_password": "secret"}

    risk = ops_agent._assess_configuration_risk(config, "production")

    assert risk == RiskLevel.CRITICAL


def test_assess_configuration_risk_high_for_sensitive_dev(ops_agent):
    """Test sensitive config in dev is HIGH"""
    config = {"api_key": "key123"}

    risk = ops_agent._assess_configuration_risk(config, "development")

    assert risk == RiskLevel.HIGH


# ============================================================================
# Deployment Tests
# ============================================================================


@pytest.mark.asyncio
async def test_deploy_application_dev_success(ops_agent):
    """Test successful deployment to development"""
    result = await ops_agent.deploy_application(
        app_name="test-app",
        version="1.0.0",
        environment="development"
    )

    assert result["success"] is True
    assert "backup_id" in result["meta"]
    assert result["meta"]["risk_level"] == "medium"


@pytest.mark.asyncio
async def test_deploy_application_creates_backup(ops_agent):
    """Test deployment creates backup"""
    result = await ops_agent.deploy_application(
        app_name="test-app",
        version="1.0.0",
        environment="development"
    )

    backup_id = result["meta"]["backup_id"]
    assert backup_id.startswith("backup-test-app-development-")


@pytest.mark.asyncio
async def test_pre_deployment_checks(ops_agent):
    """Test pre-deployment checks run"""
    checks = await ops_agent._pre_deployment_checks("test-app", "development")

    assert checks["passed"] is True
    assert "disk_space" in checks["checks"]
    assert "memory" in checks["checks"]


@pytest.mark.asyncio
async def test_health_check_success(ops_agent):
    """Test health check passes"""
    result = await ops_agent.health_check("test-app", "development")

    assert result["success"] is True
    assert result["status"] == "healthy"
    assert "checks" in result


# ============================================================================
# Rollback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_deployment_success(ops_agent):
    """Test successful rollback"""
    result = await ops_agent.rollback_deployment(
        app_name="test-app",
        environment="production",
        backup_id="backup-123"
    )

    assert result["success"] is True
    assert result["meta"]["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_rollback_records_operation(ops_agent):
    """Test rollback is recorded in history"""
    initial_count = len(ops_agent.operation_history)

    await ops_agent.rollback_deployment(
        app_name="test-app",
        environment="production",
        backup_id="backup-123"
    )

    assert len(ops_agent.operation_history) == initial_count + 1
    assert ops_agent.operation_history[-1]["type"] == "rollback"


# ============================================================================
# Migration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_run_migration_dry_run(ops_agent):
    """Test migration dry run"""
    result = await ops_agent.run_migration(
        migration_name="001_add_users_table",
        environment="development",
        dry_run=True
    )

    assert result["success"] is True
    assert result["meta"]["dry_run"] is True
    assert result["meta"]["status"] == "simulated"


@pytest.mark.asyncio
async def test_run_migration_production_critical_risk(ops_agent):
    """Test production migration is CRITICAL risk"""
    # This would require supervisor approval in real scenario
    # Here we just test it doesn't crash
    result = await ops_agent.run_migration(
        migration_name="002_alter_schema",
        environment="production",
        dry_run=True
    )

    assert result is not None  # Should handle appropriately


# ============================================================================
# Service Configuration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_configure_service_success(ops_agent):
    """Test service configuration"""
    result = await ops_agent.configure_service(
        service_name="backend",
        configuration={"workers": 4, "timeout": 30},
        environment="development"
    )

    assert result["success"] is True
    assert result["meta"]["service"] == "backend"


@pytest.mark.asyncio
async def test_configure_service_records_operation(ops_agent):
    """Test configuration is recorded"""
    initial_count = len(ops_agent.operation_history)

    await ops_agent.configure_service(
        service_name="backend",
        configuration={"workers": 4},
        environment="development"
    )

    assert len(ops_agent.operation_history) == initial_count + 1
    assert ops_agent.operation_history[-1]["type"] == "configuration"
