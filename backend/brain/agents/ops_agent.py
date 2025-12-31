"""
ops_agent.py

OpsAgent - Operations & Deployment with Risk Assessment

Responsibilities:
- System operations (deployments, configurations, updates)
- Infrastructure management
- Service orchestration
- Risk assessment for operational changes
- Integration with SupervisorAgent for critical operations

Constitutional Requirements:
- Production deployments require HIGH-risk supervision
- Database operations require approval
- System-wide changes need human oversight
- Audit trail for all operations
- Rollback capability mandatory
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from backend.brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient
from backend.app.modules.supervisor.schemas import RiskLevel, SupervisionRequest

# Supervisor integration
try:
    from backend.brain.agents.supervisor_agent import get_supervisor_agent
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False
    logger.warning("SupervisorAgent not available - OpsAgent will work without supervision")


# ============================================================================
# Constitutional Prompt for Ops LLM
# ============================================================================

OPS_CONSTITUTIONAL_PROMPT = """Du bist der Operations-Agent (OpsAgent) des BRAiN-Systems.

Deine Aufgabe: **Sichere Systemverwaltung und Deployment-Operationen**.

=Ü VERFASSUNGSRAHMEN:
- **Sicherheit vor Geschwindigkeit** - keine riskanten Deployments
- **Vier-Augen-Prinzip** bei kritischen Operationen
- **Rollback-Fähigkeit** ist Pflicht
- **Transparenz** - alle Operationen müssen nachvollziehbar sein
- **Produktionssicherheit** - keine ungetesteten Änderungen in Production

=4 KRITISCHE OPERATIONEN (IMMER SUPERVISOR + HUMAN):
- Production-Deployments
- Datenbank-Migrationen in Production
- Systemweite Konfigurationsänderungen
- Sicherheits-Updates
- Service-Neustarts in Production

=á MITTLERE RISIKOOPERATIONEN (SUPERVISOR):
- Staging-Deployments
- Development-Datenbank-Änderungen
- Service-Konfigurationen in Non-Prod
- Log-Rotationen
- Cache-Clearing

=â NIEDRIGE RISIKOOPERATIONEN (AUTO-APPROVE):
- Status-Checks
- Log-Analysen
- Monitoring-Abfragen
- Read-Only Operationen

=à TECHNISCHE ANFORDERUNGEN:
- Immer Backups vor kritischen Operationen
- Dry-Run vor tatsächlicher Ausführung
- Health-Checks nach Deployment
- Rollback-Plan dokumentieren

Handle verantwortungsvoll - Systemausfälle kosten Geld und Vertrauen.
"""


# ============================================================================
# Custom Exceptions
# ============================================================================


class OperationError(Exception):
    """Base exception for operation failures"""
    pass


class DeploymentError(OperationError):
    """Raised when deployment fails"""
    pass


class ConfigurationError(OperationError):
    """Raised when configuration is invalid"""
    pass


# ============================================================================
# OpsAgent Implementation
# ============================================================================


class OpsAgent(BaseAgent):
    """
    Operations & Deployment Agent with Risk Assessment.

    Features:
    - Safe deployment orchestration
    - Infrastructure management
    - Risk-based operation approval
    - Automatic rollback on failure
    - Comprehensive audit trail
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="OpsAgent",
                role="OPS",
                model="phi3",
                system_prompt=OPS_CONSTITUTIONAL_PROMPT,
                temperature=0.1,  # Very low - deterministic operations
                max_tokens=2048,
                tools=[
                    "deploy_application",
                    "configure_service",
                    "run_migration",
                    "health_check",
                    "rollback_deployment"
                ],
                permissions=["DEPLOY", "CONFIGURE", "MIGRATE", "ROLLBACK"],
            )

        if llm_client is None:
            from backend.brain.agents.llm_client import get_llm_client
            llm_client = get_llm_client()

        super().__init__(llm_client, config)

        # Register tools
        self.register_tool("deploy_application", self.deploy_application)
        self.register_tool("configure_service", self.configure_service)
        self.register_tool("run_migration", self.run_migration)
        self.register_tool("health_check", self.health_check)
        self.register_tool("rollback_deployment", self.rollback_deployment)

        # Operation history for rollback
        self.operation_history: List[Dict[str, Any]] = []

        logger.info(
            "™ OpsAgent initialized | Supervisor: %s",
            "enabled" if SUPERVISOR_AVAILABLE else "disabled"
        )

    # ------------------------------------------------------------------------
    # High-Level Operation Methods
    # ------------------------------------------------------------------------

    async def deploy_application(
        self,
        app_name: str,
        version: str,
        environment: str,
        config: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Deploy application to specified environment.

        Args:
            app_name: Application name
            version: Version to deploy
            environment: Target environment (dev/staging/production)
            config: Optional deployment configuration

        Returns:
            AgentResult with deployment status
        """
        logger.info(
            "=€ Deployment requested | app=%s version=%s env=%s",
            app_name,
            version,
            environment
        )

        # 1. Assess risk based on environment
        risk_level = self._assess_deployment_risk(environment)

        # 2. Prepare supervision context
        supervision_context = {
            "app_name": app_name,
            "version": version,
            "environment": environment,
            "config": config or {},
            "risk_level": risk_level.value,
        }

        # 3. Request supervisor approval for HIGH/CRITICAL
        if SUPERVISOR_AVAILABLE and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                await self._request_supervision(
                    action="deploy_application",
                    context=supervision_context,
                    risk_level=risk_level,
                )
            except Exception as e:
                logger.error("Deployment denied by supervisor | reason=%s", str(e))
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": f"Deployment denied: {str(e)}",
                    "error": str(e),
                    "meta": supervision_context,
                }

        # 4. Pre-deployment checks
        logger.info(" Supervisor approved - running pre-deployment checks")

        pre_check_result = await self._pre_deployment_checks(app_name, environment)

        if not pre_check_result["passed"]:
            logger.error("Pre-deployment checks failed | issues=%s", pre_check_result["issues"])
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Pre-deployment checks failed",
                "error": f"Issues: {pre_check_result['issues']}",
                "meta": pre_check_result,
            }

        # 5. Create backup/snapshot
        backup_id = await self._create_backup(app_name, environment)

        # 6. Execute deployment (simulated - in reality would call Docker/K8s APIs)
        try:
            deployment_result = await self._execute_deployment(
                app_name=app_name,
                version=version,
                environment=environment,
                config=config,
            )

            # 7. Post-deployment health check
            health_check_result = await self.health_check(app_name, environment)

            if not health_check_result.get("success"):
                logger.error("Post-deployment health check failed - initiating rollback")

                # Automatic rollback
                rollback_result = await self.rollback_deployment(
                    app_name=app_name,
                    environment=environment,
                    backup_id=backup_id,
                )

                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": "Deployment failed health check - rolled back",
                    "error": "Health check failed",
                    "meta": {
                        "deployment": deployment_result,
                        "health_check": health_check_result,
                        "rollback": rollback_result,
                    }
                }

            # 8. Success - log operation
            self._record_operation({
                "type": "deployment",
                "app_name": app_name,
                "version": version,
                "environment": environment,
                "backup_id": backup_id,
                "status": "success",
            })

            logger.info(" Deployment successful | app=%s version=%s env=%s", app_name, version, environment)

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"Deployment of {app_name} v{version} to {environment} successful",
                "meta": {
                    "deployment": deployment_result,
                    "health_check": health_check_result,
                    "backup_id": backup_id,
                    "risk_level": risk_level.value,
                }
            }

        except Exception as e:
            logger.exception("Deployment failed: %s", e)

            # Attempt rollback
            try:
                await self.rollback_deployment(app_name, environment, backup_id)
            except Exception as rollback_err:
                logger.error("Rollback also failed: %s", rollback_err)

            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Deployment failed",
                "error": str(e),
                "meta": {"backup_id": backup_id},
            }

    async def run_migration(
        self,
        migration_name: str,
        environment: str,
        dry_run: bool = True
    ) -> AgentResult:
        """
        Run database migration.

        Args:
            migration_name: Migration identifier
            environment: Target environment
            dry_run: If True, only simulate (default: True for safety)

        Returns:
            AgentResult with migration status
        """
        logger.info(
            "=¾ Migration requested | name=%s env=%s dry_run=%s",
            migration_name,
            environment,
            dry_run
        )

        # Migrations are always HIGH risk in production
        risk_level = RiskLevel.CRITICAL if environment == "production" else RiskLevel.HIGH

        # Supervisor approval required
        if SUPERVISOR_AVAILABLE:
            try:
                await self._request_supervision(
                    action="run_migration",
                    context={
                        "migration_name": migration_name,
                        "environment": environment,
                        "dry_run": dry_run,
                    },
                    risk_level=risk_level,
                )
            except Exception as e:
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": f"Migration denied: {str(e)}",
                    "error": str(e),
                }

        # Execute migration
        try:
            # In reality: alembic upgrade head, etc.
            result = {
                "migration": migration_name,
                "environment": environment,
                "dry_run": dry_run,
                "status": "simulated" if dry_run else "executed",
                "changes_applied": 0 if dry_run else 1,
            }

            logger.info(" Migration completed | %s", result)

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"Migration {'simulated' if dry_run else 'executed'} successfully",
                "meta": result,
            }

        except Exception as e:
            logger.exception("Migration failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Migration failed",
                "error": str(e),
            }

    async def configure_service(
        self,
        service_name: str,
        configuration: Dict[str, Any],
        environment: str
    ) -> AgentResult:
        """
        Configure service settings.

        Args:
            service_name: Service to configure
            configuration: Configuration parameters
            environment: Target environment

        Returns:
            AgentResult with configuration status
        """
        logger.info(
            "™ Service configuration requested | service=%s env=%s",
            service_name,
            environment
        )

        risk_level = self._assess_configuration_risk(configuration, environment)

        # Supervision for HIGH/CRITICAL
        if SUPERVISOR_AVAILABLE and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                await self._request_supervision(
                    action="configure_service",
                    context={
                        "service_name": service_name,
                        "configuration": configuration,
                        "environment": environment,
                    },
                    risk_level=risk_level,
                )
            except Exception as e:
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": f"Configuration denied: {str(e)}",
                    "error": str(e),
                }

        # Apply configuration
        try:
            # Simulated - in reality would update config files, env vars, etc.
            result = {
                "service": service_name,
                "environment": environment,
                "configuration": configuration,
                "status": "applied",
            }

            self._record_operation({
                "type": "configuration",
                "service": service_name,
                "environment": environment,
                "status": "success",
            })

            logger.info(" Service configured | service=%s", service_name)

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"Service {service_name} configured successfully",
                "meta": result,
            }

        except Exception as e:
            logger.exception("Configuration failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Configuration failed",
                "error": str(e),
            }

    async def health_check(
        self,
        app_name: str,
        environment: str
    ) -> Dict[str, Any]:
        """
        Perform health check on application.

        Args:
            app_name: Application name
            environment: Environment to check

        Returns:
            Health check results
        """
        logger.info("<å Health check | app=%s env=%s", app_name, environment)

        # Simulated health check - in reality would ping /health endpoints
        try:
            health_status = {
                "app_name": app_name,
                "environment": environment,
                "status": "healthy",
                "checks": {
                    "api": "ok",
                    "database": "ok",
                    "redis": "ok",
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(" Health check passed | app=%s", app_name)

            return {
                "success": True,
                **health_status,
            }

        except Exception as e:
            logger.error("Health check failed | app=%s error=%s", app_name, e)
            return {
                "success": False,
                "error": str(e),
            }

    async def rollback_deployment(
        self,
        app_name: str,
        environment: str,
        backup_id: str
    ) -> AgentResult:
        """
        Rollback deployment to previous version.

        Args:
            app_name: Application name
            environment: Environment to rollback
            backup_id: Backup/snapshot to restore

        Returns:
            AgentResult with rollback status
        """
        logger.warning(
            "= Rollback initiated | app=%s env=%s backup=%s",
            app_name,
            environment,
            backup_id
        )

        try:
            # Simulated rollback - in reality would restore from backup
            result = {
                "app_name": app_name,
                "environment": environment,
                "backup_id": backup_id,
                "status": "rolled_back",
                "timestamp": datetime.utcnow().isoformat(),
            }

            self._record_operation({
                "type": "rollback",
                "app_name": app_name,
                "environment": environment,
                "backup_id": backup_id,
                "status": "success",
            })

            logger.info(" Rollback completed | app=%s", app_name)

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"Rollback of {app_name} in {environment} successful",
                "meta": result,
            }

        except Exception as e:
            logger.exception("Rollback failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Rollback failed",
                "error": str(e),
            }

    # ------------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------------

    async def _request_supervision(
        self,
        action: str,
        context: Dict[str, Any],
        risk_level: RiskLevel,
    ) -> None:
        """Request supervisor approval (raises exception if denied)"""
        if not SUPERVISOR_AVAILABLE:
            logger.warning("Supervisor not available - skipping supervision check")
            return

        supervisor = get_supervisor_agent()

        request = SupervisionRequest(
            requesting_agent=self.config.name,
            action=action,
            context=context,
            risk_level=risk_level,
            reason=f"Operations task: {action}",
        )

        response = await supervisor.supervise_action(request)

        if not response.approved:
            raise OperationError(f"Supervisor denied: {response.reason}")

        logger.info(" Supervision approved | action=%s", action)

    def _assess_deployment_risk(self, environment: str) -> RiskLevel:
        """Assess deployment risk based on environment"""
        environment = environment.lower()

        if environment == "production":
            return RiskLevel.CRITICAL
        elif environment in ("staging", "stage"):
            return RiskLevel.HIGH
        elif environment in ("development", "dev"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _assess_configuration_risk(
        self,
        configuration: Dict[str, Any],
        environment: str
    ) -> RiskLevel:
        """Assess configuration change risk"""
        # Check for sensitive config keys
        sensitive_keys = ["database", "secret", "password", "api_key", "token"]

        has_sensitive = any(
            key.lower() in str(config_key).lower()
            for config_key in configuration.keys()
            for key in sensitive_keys
        )

        if has_sensitive and environment == "production":
            return RiskLevel.CRITICAL
        elif has_sensitive:
            return RiskLevel.HIGH
        elif environment == "production":
            return RiskLevel.HIGH
        else:
            return RiskLevel.MEDIUM

    async def _pre_deployment_checks(
        self,
        app_name: str,
        environment: str
    ) -> Dict[str, Any]:
        """Run pre-deployment checks"""
        # Simulated checks
        checks = {
            "disk_space": "ok",
            "memory": "ok",
            "dependencies": "ok",
            "configuration": "ok",
        }

        issues = [k for k, v in checks.items() if v != "ok"]

        return {
            "passed": len(issues) == 0,
            "checks": checks,
            "issues": issues,
        }

    async def _create_backup(self, app_name: str, environment: str) -> str:
        """Create backup/snapshot before deployment"""
        backup_id = f"backup-{app_name}-{environment}-{uuid.uuid4().hex[:8]}"

        logger.info("=¾ Creating backup | id=%s", backup_id)

        # Simulated - in reality would create actual backup
        return backup_id

    async def _execute_deployment(
        self,
        app_name: str,
        version: str,
        environment: str,
        config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute the actual deployment"""
        logger.info("=€ Executing deployment | app=%s version=%s", app_name, version)

        # Simulated deployment
        # In reality: docker pull, kubectl apply, etc.
        await asyncio.sleep(0.5)  # Simulate deployment time

        return {
            "app_name": app_name,
            "version": version,
            "environment": environment,
            "status": "deployed",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _record_operation(self, operation: Dict[str, Any]) -> None:
        """Record operation in history for audit/rollback"""
        operation["timestamp"] = datetime.utcnow().isoformat()
        operation["agent_id"] = self.id

        self.operation_history.append(operation)

        logger.debug("=Ý Operation recorded | type=%s", operation.get("type"))


# ============================================================================
# Convenience Function
# ============================================================================


def get_ops_agent(llm_client: Optional[LLMClient] = None) -> OpsAgent:
    """Get an OpsAgent instance"""
    return OpsAgent(llm_client=llm_client)
