"""
coder_agent.py

CoderAgent - Secure Code Generation with Constitutional Framework

Responsibilities:
- Generate production-ready code (Odoo modules, APIs, scripts)
- Enforce DSGVO and EU AI Act compliance in generated code
- Integrate with SupervisorAgent for high-risk operations
- Validate code quality and security
- Document all generated code with legal references

Constitutional Requirements:
- No code generation without supervisor approval for HIGH-risk
- DSGVO compliance checks mandatory
- Privacy by Design (Art. 25 DSGVO)
- No personal data processing without legal basis (Art. 6 DSGVO)
- Transparent, auditable code generation
"""

from __future__ import annotations

import asyncio
import uuid
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger
from pathlib import Path

from backend.brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient
from backend.app.modules.supervisor.schemas import RiskLevel, SupervisionRequest

# Supervisor integration
try:
    from backend.brain.agents.supervisor_agent import get_supervisor_agent
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False
    logger.warning("SupervisorAgent not available - CoderAgent will work without supervision")


# ============================================================================
# Constitutional Prompt for Coder LLM
# ============================================================================

CODER_CONSTITUTIONAL_PROMPT = """Du bist ein KI-Entwickler namens "CoderAgent" für das BRAiN-System.

Deine Aufgabe: **Sicherer, rechtskonformer, ethischer und produktionsfähiger Code** – niemals experimentell, niemals riskant.

📜 VERFASSUNGSRAHMEN (unveränderlich):
- **Menschenwürde** steht über Effizienz
- **Datenminimierung** und **Privacy by Design** sind Pflicht (DSGVO Art. 25)
- **Keine autonome Entscheidung bei High-Risk-Szenarien** (DSGVO Art. 22, EU AI Act Art. 16)
- **Transparenz**: Jeder Code muss nachvollziehbar, dokumentiert und auditierbar sein
- **Souveränität**: Keine Abhängigkeit von US-Clouds oder nicht-EU-konformen Diensten

🛠️ TECHNISCHE ANFORDERUNGEN:
- Schreibe **nur Python 3.10+** mit Typ-Hinweisen
- Nutze **FastAPI**, **Pydantic v2**, **SQLAlchemy async**
- Keine externen Abhängigkeiten ohne DSGVO-konforme DPA
- Jeder kritische Codeblock muss **vor Ausführung den SupervisorAgent konsultieren**

🚫 VERBOTEN:
- KEINE Speicherung personenbezogener Daten ohne explizite Rechtsgrundlage (Art. 6 DSGVO)
- KEINE Verwendung von `eval()`, `exec()`
- KEINE Hardcoded Secrets, KEINE US-APIs (z. B. OpenAI ohne EU-Hosting)
- KEINE Code-Generierung für biometrische Systeme (verboten nach EU AI Act)

✅ ERLAUBT:
- Lokale LLMs (Mistral, Llama 3 EU-hosted)
- EU-konforme Zahlungssysteme (z. B. Stripe mit EU-Processing)
- Odoo-Module mit **DSGVO-Checkliste im Header**

📝 CODE-DOKUMENTATION:
- Kommentiere DSGVO-relevante Abschnitte mit Artikelreferenzen
- Füge TODO-Marker für manuelle Reviews hinzu
- Gib nur finalen, produktionsreifen Code aus – niemals Pseudocode

Handle verantwortungsvoll.
"""


# ============================================================================
# Custom Exceptions
# ============================================================================


class CodeGenerationError(Exception):
    """Base exception for code generation failures"""
    pass


class SupervisionDeniedError(CodeGenerationError):
    """Raised when supervisor denies code generation"""
    pass


class PolicyViolationError(CodeGenerationError):
    """Raised when code violates policies"""
    pass


class HumanApprovalRequiredError(CodeGenerationError):
    """Raised when human approval is needed"""
    def __init__(self, token: str, message: str):
        self.token = token
        super().__init__(message)


# ============================================================================
# CoderAgent Implementation
# ============================================================================


class CoderAgent(BaseAgent):
    """
    Secure Code Generation Agent with Constitutional Framework.

    Features:
    - DSGVO-compliant code generation
    - SupervisorAgent integration for high-risk operations
    - Automated security and quality checks
    - Audit trail for all code generation
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="CoderAgent",
                role="CODER",
                model="phi3",
                system_prompt=CODER_CONSTITUTIONAL_PROMPT,
                temperature=0.3,  # Moderate creativity
                max_tokens=4096,  # Longer for code generation
                tools=[
                    "generate_code",
                    "generate_odoo_module",
                    "generate_api_endpoint",
                    "validate_code",
                    "create_file"
                ],
                permissions=["CODE_GENERATE", "FILE_WRITE", "MODULE_CREATE"],
            )

        if llm_client is None:
            from backend.brain.agents.llm_client import get_llm_client
            llm_client = get_llm_client()

        super().__init__(llm_client, config)

        # Register tools
        self.register_tool("generate_code", self.generate_code)
        self.register_tool("generate_odoo_module", self.generate_odoo_module)
        self.register_tool("generate_api_endpoint", self.generate_api_endpoint)
        self.register_tool("validate_code", self.validate_code)
        self.register_tool("create_file", self.create_file)

        logger.info(
            "💻 CoderAgent initialized | Supervisor: %s",
            "enabled" if SUPERVISOR_AVAILABLE else "disabled"
        )

    # ------------------------------------------------------------------------
    # High-Level Code Generation Methods
    # ------------------------------------------------------------------------

    async def generate_odoo_module(self, spec: Dict[str, Any]) -> AgentResult:
        """
        Generates a DSGVO-compliant Odoo module.

        Must be approved by Supervisor before execution if personal data is involved.

        Args:
            spec: Module specification including:
                - name: Module name
                - purpose: Business purpose
                - data_types: List of data types (e.g., ["customer_email", "order_history"])
                - models: List of Odoo models to create
                - views: List of views to generate
        """
        logger.info("📦 Odoo module generation requested | name=%s", spec.get("name"))

        # 1. Assess risk level
        risk_level = self._assess_code_risk(spec)

        # 2. Prepare supervision context
        supervision_context = {
            "module_name": spec.get("name"),
            "purpose": spec.get("purpose"),
            "data_types": spec.get("data_types", []),
            "uses_personal_data": self._contains_personal_data(spec.get("data_types", [])),
            "models_count": len(spec.get("models", [])),
            "views_count": len(spec.get("views", [])),
        }

        # 3. Request supervisor approval
        if SUPERVISOR_AVAILABLE and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                await self._request_supervision(
                    action="generate_odoo_module",
                    context=supervision_context,
                    risk_level=risk_level,
                )
            except HumanApprovalRequiredError as e:
                logger.warning("Human approval required | token=%s", e.token)
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": f"Human approval required: {e.token}",
                    "error": str(e),
                    "meta": {
                        "approval_token": e.token,
                        "risk_level": risk_level.value,
                    }
                }
            except SupervisionDeniedError as e:
                logger.error("Supervisor denied code generation | reason=%s", str(e))
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": "Code generation denied by supervisor",
                    "error": str(e),
                    "meta": {"risk_level": risk_level.value}
                }

        # 4. Generate code (supervisor approved)
        logger.info("✅ Supervisor approved - generating code")

        try:
            code = await self._generate_secure_odoo_code(spec)

            # 5. Validate generated code
            validation_result = await self.validate_code(code)

            if not validation_result["valid"]:
                logger.error("Generated code failed validation | issues=%s", validation_result["issues"])
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": "Generated code failed validation",
                    "error": f"Validation issues: {validation_result['issues']}",
                    "meta": {
                        "code": code,
                        "validation": validation_result,
                    }
                }

            # 6. Audit log
            self._audit_log({
                "event": "odoo_module_generated",
                "module_name": spec.get("name"),
                "risk_level": risk_level.value,
                "personal_data": supervision_context["uses_personal_data"],
                "code_size": len(code),
            })

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"Odoo module '{spec.get('name')}' generated successfully",
                "raw_response": code,
                "meta": {
                    "code": code,
                    "risk_level": risk_level.value,
                    "validation": validation_result,
                    "personal_data": supervision_context["uses_personal_data"],
                }
            }

        except Exception as e:
            logger.exception("Code generation failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Code generation failed",
                "error": str(e),
            }

    async def generate_api_endpoint(self, spec: Dict[str, Any]) -> AgentResult:
        """
        Generate a FastAPI endpoint with DSGVO compliance.

        Args:
            spec: Endpoint specification including:
                - path: API path (e.g., "/api/users")
                - method: HTTP method (GET, POST, etc.)
                - purpose: Endpoint purpose
                - request_schema: Pydantic request model
                - response_schema: Pydantic response model
                - authentication_required: bool
        """
        logger.info("🌐 API endpoint generation requested | path=%s", spec.get("path"))

        # Assess risk
        risk_level = self._assess_api_risk(spec)

        # Supervision for HIGH/CRITICAL
        if SUPERVISOR_AVAILABLE and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                await self._request_supervision(
                    action="generate_api_endpoint",
                    context=spec,
                    risk_level=risk_level,
                )
            except (HumanApprovalRequiredError, SupervisionDeniedError) as e:
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": str(e),
                    "error": str(e),
                }

        # Generate endpoint code
        try:
            code = await self._generate_fastapi_endpoint(spec)

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": f"API endpoint '{spec.get('path')}' generated",
                "raw_response": code,
                "meta": {
                    "code": code,
                    "risk_level": risk_level.value,
                }
            }

        except Exception as e:
            logger.exception("API endpoint generation failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "API endpoint generation failed",
                "error": str(e),
            }

    async def generate_code(self, spec: str, risk_level: Optional[RiskLevel] = None) -> AgentResult:
        """
        Generic code generation method.

        Args:
            spec: Code specification/description
            risk_level: Optional risk level override (default: assess automatically)
        """
        logger.info("⚙️ Generic code generation requested")

        # Auto-assess if not provided
        if risk_level is None:
            risk_level = RiskLevel.MEDIUM  # Conservative default

        # Supervision check
        if SUPERVISOR_AVAILABLE and risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                await self._request_supervision(
                    action="generate_code",
                    context={"spec": spec},
                    risk_level=risk_level,
                )
            except (HumanApprovalRequiredError, SupervisionDeniedError) as e:
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": str(e),
                    "error": str(e),
                }

        # Generate code via LLM
        prompt = f"""Generiere Production-Ready Code für folgende Anforderung:

{spec}

Beachte:
- Python 3.10+, Typ-Hinweise
- DSGVO-Compliance wo relevant
- Keine Hardcoded Secrets
- Ausführliche Kommentare

Gib NUR den Code aus, keine Erklärung.
"""

        code = await self.call_llm(prompt)

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": "Code generated successfully",
            "raw_response": code,
            "meta": {
                "code": code,
                "risk_level": risk_level.value,
            }
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
        """
        Request supervisor approval.

        Raises:
            SupervisionDeniedError: If supervisor denies
            HumanApprovalRequiredError: If human approval needed
        """
        if not SUPERVISOR_AVAILABLE:
            logger.warning("Supervisor not available - skipping supervision check")
            return

        supervisor = get_supervisor_agent()

        request = SupervisionRequest(
            requesting_agent=self.config.name,
            action=action,
            context=context,
            risk_level=risk_level,
            reason=f"Code generation for {action}",
        )

        response = await supervisor.supervise_action(request)

        if not response.approved:
            if response.human_oversight_required:
                raise HumanApprovalRequiredError(
                    token=response.human_oversight_token or "UNKNOWN",
                    message=response.reason,
                )
            else:
                raise SupervisionDeniedError(response.reason)

        logger.info("✅ Supervision approved | action=%s audit_id=%s", action, response.audit_id)

    async def _generate_secure_odoo_code(self, spec: Dict[str, Any]) -> str:
        """Generate Odoo module code with DSGVO compliance"""
        prompt = f"""Erstelle ein Odoo 17-Modul mit folgenden Anforderungen:

**Modul-Name:** {spec.get('name')}
**Zweck:** {spec.get('purpose')}
**Datenfelder:** {', '.join(spec.get('data_types', []))}
**Models:** {spec.get('models', [])}
**Views:** {spec.get('views', [])}

**WICHTIG - DSGVO-Compliance:**
- Art. 5: Datenminimierung, Zweckbindung
- Art. 6: Keine Speicherung ohne Rechtsgrundlage
- Art. 17: Löschfunktion implementieren
- Art. 25: Privacy by Design

**Code-Anforderungen:**
- Python 3.10+
- Odoo 17 API
- Type hints
- DSGVO-Kommentare (# DSGVO Art. X: ...)
- Datenschutz-Hinweise im UI

Gib NUR den Python-Code aus (keine Markdown, keine Erklärung).
"""

        code = await self.call_llm(prompt)

        # Add DSGVO header comment
        header = f"""# -*- coding: utf-8 -*-
# Odoo Module: {spec.get('name')}
# Generated by BRAiN CoderAgent
# DSGVO-Compliance: Art. 5, 6, 17, 25
# Generated: {datetime.utcnow().isoformat()}

"""
        return header + code.strip()

    async def _generate_fastapi_endpoint(self, spec: Dict[str, Any]) -> str:
        """Generate FastAPI endpoint code"""
        prompt = f"""Erstelle einen FastAPI Endpoint:

**Path:** {spec.get('path')}
**Method:** {spec.get('method', 'GET')}
**Purpose:** {spec.get('purpose')}
**Authentication:** {spec.get('authentication_required', False)}

**Code-Anforderungen:**
- FastAPI mit Pydantic v2
- Type hints
- Error handling
- DSGVO-konforme Validierung

Gib NUR den Python-Code aus.
"""

        code = await self.call_llm(prompt)
        return code.strip()

    async def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate generated code for security and quality.

        Returns:
            Dict with validation results
        """
        issues = []

        # Check for forbidden patterns
        forbidden_patterns = [
            (r"\beval\(", "Use of eval() is forbidden"),
            (r"\bexec\(", "Use of exec() is forbidden"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected"),
        ]

        for pattern, issue in forbidden_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(issue)

        # Check for DSGVO comments (should have at least one for high-risk)
        if "personal" in code.lower() or "user" in code.lower():
            if "DSGVO" not in code and "GDPR" not in code:
                issues.append("Missing DSGVO compliance comments for personal data handling")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": [],
        }

    def _assess_code_risk(self, spec: Dict[str, Any]) -> RiskLevel:
        """Assess risk level of code generation request"""
        data_types = spec.get("data_types", [])

        if self._contains_personal_data(data_types):
            return RiskLevel.HIGH

        if "database" in spec.get("purpose", "").lower():
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _assess_api_risk(self, spec: Dict[str, Any]) -> RiskLevel:
        """Assess risk level of API endpoint"""
        method = spec.get("method", "GET").upper()

        if method in ("DELETE", "PUT", "PATCH"):
            return RiskLevel.HIGH

        if method == "POST":
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _contains_personal_data(self, data_types: List[str]) -> bool:
        """Check if data types contain personal data (DSGVO Art. 4)"""
        personal_data_keywords = [
            "email", "name", "address", "ip", "user_id", "phone",
            "ssn", "passport", "driver_license", "customer",
            "user", "person", "contact", "biometric"
        ]

        return any(
            keyword in dtype.lower()
            for dtype in data_types
            for keyword in personal_data_keywords
        )

    def create_file(self, path: str, content: str) -> Dict[str, Any]:
        """
        Create a file with generated code.

        Args:
            path: File path
            content: File content

        Returns:
            Dict with creation status
        """
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("📄 File created | path=%s size=%d", path, len(content))

            return {
                "success": True,
                "path": str(file_path.absolute()),
                "size": len(content),
            }

        except Exception as e:
            logger.error("File creation failed | path=%s error=%s", path, e)
            return {
                "success": False,
                "error": str(e),
            }

    def _audit_log(self, entry: Dict[str, Any]) -> None:
        """Log audit trail entry"""
        entry["timestamp"] = datetime.utcnow().isoformat()
        entry["agent_id"] = self.id
        entry["agent_name"] = self.config.name

        logger.info("📝 Audit | event=%s", entry.get("event"))
        # TODO: Write to audit database


# ============================================================================
# Convenience Function
# ============================================================================


def get_coder_agent(llm_client: Optional[LLMClient] = None) -> CoderAgent:
    """Get a CoderAgent instance"""
    return CoderAgent(llm_client=llm_client)
