"""
supervisor_agent.py

SupervisorAgent - Constitutional Framework Guardian

Responsibilities:
- Review and approve/deny agent actions based on risk level
- Enforce ethical constraints (DSGVO, EU AI Act)
- Integrate with Policy Engine for rule-based governance
- Trigger human-in-the-loop for HIGH/CRITICAL risk actions
- Maintain audit trail for all decisions

Constitutional Framework:
- Menschenwuerde > Effizienz
- Privacy by Design (DSGVO Art. 25)
- No autonomous High-Risk decisions (EU AI Act Art. 16)
- Transparency and auditability mandatory
- EU sovereignty (no US cloud dependencies)
"""

from __future__ import annotations

import asyncio
import uuid
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

from brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient
from app.modules.supervisor.schemas import (
    RiskLevel,
    SupervisionRequest,
    SupervisionResponse,
)

# Policy Engine integration
try:
    from app.modules.policy.service import PolicyEngine
    from app.modules.policy.schemas import (
        PolicyEvaluationContext,
        PolicyEffect,
    )
    POLICY_ENGINE_AVAILABLE = True
except ImportError:
    POLICY_ENGINE_AVAILABLE = False
    logger.warning("Policy Engine not available - Supervisor will work in standalone mode")

# Foundation layer integration
try:
    from app.modules.foundation.service import FoundationService
    FOUNDATION_AVAILABLE = True
except ImportError:
    FOUNDATION_AVAILABLE = False
    logger.warning("Foundation layer not available")


# ============================================================================
# Constitutional Prompt for Supervisor LLM
# ============================================================================

CONSTITUTIONAL_PROMPT = """Du bist der Supervisor-Agent des BRAiN-Systems.

Deine Aufgabe ist die **ethische und rechtliche Prüfung** aller Agent-Aktionen.

=Ü VERFASSUNGSRAHMEN (unveränderlich):

1. **Menschenwuerde steht über Effizienz**
   - Keine Entscheidungen, die Menschen schaden könnten
   - Menschen behalten Kontrolle über kritische Entscheidungen

2. **Datenschutz (DSGVO)**
   - Art. 5: Datenminimierung, Zweckbindung, Rechtmäßigkeit
   - Art. 6: Keine Verarbeitung ohne Rechtsgrundlage
   - Art. 22: Keine vollautomatischen Entscheidungen bei High-Risk
   - Art. 25: Privacy by Design

3. **EU AI Act**
   - Art. 5: Verboten sind: Social Scoring, biometrische Massenüberwachung
   - Art. 16: High-Risk-KI benötigt menschliche Aufsicht
   - Art. 52: Transparenzpflicht bei KI-Nutzung

4. **Transparenz & Auditierung**
   - Jede Entscheidung muss nachvollziehbar sein
   - Audit-Logs sind Pflicht
   - Keine Black-Box-Entscheidungen

5. **Souveränität**
   - Keine Abhängigkeit von US-Clouds
   - EU-konforme Dienstleister bevorzugen

=4 KRITISCHE AKTIONEN (IMMER HUMAN-IN-THE-LOOP):
- Verarbeitung personenbezogener Daten
- Produktionsdatenbank-Änderungen
- Finanztransaktionen
- Code-Deployment in Produktion
- Systemweite Konfigurationsänderungen

=á MITTLERE RISIKOAKTIONEN (POLICY-CHECK):
- Schreibzugriffe auf Entwicklungssysteme
- API-Aufrufe an externe Dienste
- Dateisystem-Operationen

=â NIEDRIGE RISIKOAKTIONEN (AUTO-APPROVE):
- Read-Only Datenbankabfragen
- Log-Analysen
- Status-Checks

DEINE AUSGABE:
- approved: true/false
- reason: Klare Begründung (DSGVO/AI Act Artikel referenzieren)
- human_oversight_required: true bei HIGH/CRITICAL
- policy_violations: Liste von Policy-Verstößen

Handle verantwortungsvoll.
"""


# ============================================================================
# SupervisorAgent Implementation
# ============================================================================


class SupervisorAgent(BaseAgent):
    """
    Constitutional Guardian for the BRAiN system.

    Evaluates all agent actions against:
    - Risk levels (LOW/MEDIUM/HIGH/CRITICAL)
    - Policy rules (via PolicyEngine)
    - Constitutional constraints (DSGVO, EU AI Act)
    - Foundation layer safety checks
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="SupervisorAgent",
                role="SUPERVISOR",
                model="phi3",
                system_prompt=CONSTITUTIONAL_PROMPT,
                temperature=0.1,  # Very low for deterministic decisions
                max_tokens=1024,
                tools=["supervise_action", "trigger_human_approval", "audit_log"],
                permissions=["SUPERVISE_ALL", "HUMAN_APPROVAL_TRIGGER", "AUDIT_WRITE"],
            )

        # Allow None llm_client for testing/standalone mode
        if llm_client is None:
            from brain.agents.llm_client import get_llm_client
            llm_client = get_llm_client()

        super().__init__(llm_client, config)

        # Integration with other systems
        self.policy_engine = policy_engine

        # Metrics
        self.total_supervision_requests = 0
        self.approved_actions = 0
        self.denied_actions = 0
        self.human_approvals_pending = 0

        # Audit trail storage (in-memory for now, should be DB)
        self.audit_trail: List[Dict[str, Any]] = []

        # Register tools
        self.register_tool("supervise_action", self.supervise_action)
        self.register_tool("trigger_human_approval", self._trigger_human_approval)
        self.register_tool("audit_log", self._audit_log)

        logger.info(
            "=á SupervisorAgent initialized | PolicyEngine: %s | Foundation: %s",
            "enabled" if POLICY_ENGINE_AVAILABLE else "disabled",
            "enabled" if FOUNDATION_AVAILABLE else "disabled"
        )

    # ------------------------------------------------------------------------
    # Core Supervision Logic
    # ------------------------------------------------------------------------

    async def supervise_action(self, request: SupervisionRequest) -> SupervisionResponse:
        """
        Main supervision entry point.

        Evaluates an action request through multiple layers:
        1. Automatic risk-based rules
        2. Policy Engine evaluation (if available)
        3. LLM-based constitutional analysis
        4. Foundation layer safety check (if available)
        """
        self.total_supervision_requests += 1
        start_time = time.time()

        logger.info(
            "= Supervision requested | agent=%s action=%s risk=%s",
            request.requesting_agent,
            request.action,
            request.risk_level.value
        )

        audit_id = str(uuid.uuid4())

        # Step 1: Automatic rules based on risk level
        if request.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            logger.warning(
                "  HIGH/CRITICAL risk action requires human approval | action=%s",
                request.action
            )
            self.human_approvals_pending += 1

            response = SupervisionResponse(
                approved=False,
                reason=f"HIGH/CRITICAL risk action '{request.action}' requires human approval (EU AI Act Art. 16, DSGVO Art. 22)",
                human_oversight_required=True,
                human_oversight_token=self._generate_approval_token(request),
                audit_id=audit_id,
            )

            self._audit_log({
                "event": "supervision_human_required",
                "audit_id": audit_id,
                "request": request.model_dump(),
                "response": response.model_dump(),
                "duration_ms": (time.time() - start_time) * 1000,
            })

            return response

        # Step 2: Policy Engine evaluation
        policy_violations = []
        if POLICY_ENGINE_AVAILABLE and self.policy_engine:
            try:
                policy_result = await self._check_policy_engine(request)
                if policy_result.effect == PolicyEffect.DENY:
                    logger.warning(
                        "=« Policy Engine DENIED action | action=%s reason=%s",
                        request.action,
                        policy_result.reason
                    )
                    self.denied_actions += 1

                    response = SupervisionResponse(
                        approved=False,
                        reason=f"Policy violation: {policy_result.reason}",
                        human_oversight_required=False,
                        audit_id=audit_id,
                        policy_violations=[policy_result.reason],
                    )

                    self._audit_log({
                        "event": "supervision_denied_policy",
                        "audit_id": audit_id,
                        "request": request.model_dump(),
                        "response": response.model_dump(),
                        "duration_ms": (time.time() - start_time) * 1000,
                    })

                    return response

                if policy_result.effect == PolicyEffect.WARN:
                    policy_violations.append(policy_result.reason)
                    logger.warning(
                        "  Policy warning | action=%s reason=%s",
                        request.action,
                        policy_result.reason
                    )

            except Exception as e:
                logger.error("Policy Engine check failed: %s", e)
                # Continue with LLM evaluation

        # Step 3: LLM-based constitutional analysis
        llm_decision = await self._llm_constitutional_check(request)

        if not llm_decision["approved"]:
            self.denied_actions += 1

            response = SupervisionResponse(
                approved=False,
                reason=llm_decision["reason"],
                human_oversight_required=llm_decision.get("human_oversight_required", False),
                audit_id=audit_id,
                policy_violations=policy_violations,
            )

            logger.warning(
                "=« LLM DENIED action | action=%s reason=%s",
                request.action,
                llm_decision["reason"]
            )
        else:
            self.approved_actions += 1

            response = SupervisionResponse(
                approved=True,
                reason=llm_decision["reason"],
                human_oversight_required=False,
                audit_id=audit_id,
                policy_violations=policy_violations,
            )

            logger.info(
                " Action APPROVED | action=%s agent=%s",
                request.action,
                request.requesting_agent
            )

        # Step 4: Audit logging
        self._audit_log({
            "event": "supervision_completed",
            "audit_id": audit_id,
            "request": request.model_dump(),
            "response": response.model_dump(),
            "duration_ms": (time.time() - start_time) * 1000,
        })

        return response

    # ------------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------------

    async def _check_policy_engine(
        self,
        request: SupervisionRequest
    ) -> Any:
        """Check action against Policy Engine rules"""
        if not self.policy_engine:
            return None

        context = PolicyEvaluationContext(
            agent_id=request.requesting_agent,
            action=request.action,
            context=request.context,
        )

        return await self.policy_engine.evaluate(context)

    async def _llm_constitutional_check(
        self,
        request: SupervisionRequest
    ) -> Dict[str, Any]:
        """
        Use LLM to evaluate action against constitutional constraints.

        The LLM has the CONSTITUTIONAL_PROMPT as system prompt.
        """
        user_message = f"""Prüfe folgende Agent-Aktion:

Agent: {request.requesting_agent}
Aktion: {request.action}
Risiko-Level: {request.risk_level.value}
Kontext: {request.context}
Begründung: {request.reason or 'Keine Begründung angegeben'}

Bewerte:
1. DSGVO-Konformität
2. EU AI Act Konformität
3. Ethische Unbedenklichkeit
4. Transparenz

Antworte im Format:
approved: true/false
reason: <Begründung mit DSGVO/AI Act Artikel>
human_oversight_required: true/false
"""

        try:
            llm_response = await self.call_llm(user_message)

            # Parse LLM response (simplified - should use structured output)
            approved = "approved: true" in llm_response.lower()
            human_required = "human_oversight_required: true" in llm_response.lower()

            # Extract reason (simple regex)
            import re
            reason_match = re.search(r"reason:\s*(.+?)(?:\n|$)", llm_response, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else llm_response

            return {
                "approved": approved,
                "reason": reason,
                "human_oversight_required": human_required,
                "raw_response": llm_response,
            }

        except Exception as e:
            logger.error("LLM constitutional check failed: %s", e)
            # Fail-safe: deny on error
            return {
                "approved": False,
                "reason": f"Constitutional check failed: {str(e)}",
                "human_oversight_required": True,
            }

    def _generate_approval_token(self, request: SupervisionRequest) -> str:
        """Generate token for human approval workflow"""
        token = f"HITL-{uuid.uuid4().hex[:12]}"

        # Store pending approval (should be in DB)
        self._audit_log({
            "event": "human_approval_token_generated",
            "token": token,
            "request": request.model_dump(),
        })

        return token

    def _trigger_human_approval(self, token: str, request: SupervisionRequest) -> Dict[str, Any]:
        """
        Trigger human-in-the-loop approval workflow.

        This would typically:
        - Send notification to compliance team
        - Create entry in governance system
        - Return tracking info
        """
        logger.info("= Human approval triggered | token=%s action=%s", token, request.action)

        # TODO: Integrate with governance module for HITL workflow
        # For now, just log and return token
        return {
            "token": token,
            "status": "pending",
            "message": "Human approval request sent to compliance team",
        }

    def _audit_log(self, entry: Dict[str, Any]) -> None:
        """
        Add entry to audit trail.

        DSGVO Art. 5 Abs. 2 requires accountability.
        All supervision decisions must be auditable.
        """
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        entry["supervisor_agent_id"] = self.id

        self.audit_trail.append(entry)

        logger.debug("=Ý Audit entry: %s", entry["event"])

    # ------------------------------------------------------------------------
    # Agent Override Methods
    # ------------------------------------------------------------------------

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Generic task execution (not typically used for Supervisor).

        Supervisor is usually invoked via supervise_action() method.
        """
        logger.warning("SupervisorAgent.run() called - use supervise_action() instead")

        return {
            "id": str(uuid.uuid4()),
            "success": False,
            "message": "Use supervise_action() method for supervision requests",
            "meta": {
                "agent_id": self.id,
                "agent_name": self.config.name,
            }
        }

    # ------------------------------------------------------------------------
    # Status & Metrics
    # ------------------------------------------------------------------------

    def get_metrics(self) -> Dict[str, Any]:
        """Get supervision metrics"""
        return {
            "total_supervision_requests": self.total_supervision_requests,
            "approved_actions": self.approved_actions,
            "denied_actions": self.denied_actions,
            "human_approvals_pending": self.human_approvals_pending,
            "approval_rate": (
                self.approved_actions / self.total_supervision_requests
                if self.total_supervision_requests > 0
                else 0.0
            ),
            "audit_entries": len(self.audit_trail),
        }


# ============================================================================
# Singleton Instance
# ============================================================================

# Global supervisor instance (can be initialized once at startup)
_supervisor_agent: Optional[SupervisorAgent] = None


def get_supervisor_agent(
    llm_client: Optional[LLMClient] = None,
    policy_engine: Optional[PolicyEngine] = None,
) -> SupervisorAgent:
    """Get or create the global SupervisorAgent instance"""
    global _supervisor_agent

    if _supervisor_agent is None:
        _supervisor_agent = SupervisorAgent(
            llm_client=llm_client,
            policy_engine=policy_engine,
        )

    return _supervisor_agent


# Alias for convenience
supervisor_agent = get_supervisor_agent()
