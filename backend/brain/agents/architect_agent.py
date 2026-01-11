"""
architect_agent.py

ArchitectAgent - System Architecture & EU Compliance Auditor

Responsibilities:
- Review system architecture decisions
- Ensure EU AI Act and DSGVO compliance in design
- Evaluate scalability and maintainability
- Assess security architecture
- Provide architectural recommendations

Constitutional Requirements:
- All high-risk AI systems must comply with EU AI Act
- Privacy by Design mandatory (DSGVO Art. 25)
- No vendor lock-in to non-EU providers
- Transparent, auditable architecture
- Data sovereignty in EU
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient
from app.modules.supervisor.schemas import RiskLevel, SupervisionRequest

# Supervisor integration
try:
    from brain.agents.supervisor_agent import get_supervisor_agent
    SUPERVISOR_AVAILABLE = True
except ImportError:
    SUPERVISOR_AVAILABLE = False
    logger.warning("SupervisorAgent not available - ArchitectAgent will work without supervision")


# ============================================================================
# Constitutional Prompt for Architect LLM
# ============================================================================

ARCHITECT_CONSTITUTIONAL_PROMPT = """Du bist der Architektur-Agent (ArchitectAgent) des BRAiN-Systems.

Deine Aufgabe: **Systemarchitektur-Bewertung mit EU-Rechtskonformität**.

=Ü VERFASSUNGSRAHMEN:

1. **EU AI Act Compliance (Regulation 2024/1689)**
   - Art. 5: Verbotene KI-Praktiken erkennen
   - Art. 6-7: High-Risk AI identifizieren
   - Art. 9-13: Anforderungen an High-Risk-Systeme
   - Art. 16: Menschliche Aufsicht sicherstellen
   - Art. 52: Transparenzpflichten

2. **DSGVO Compliance (EU 2016/679)**
   - Art. 25: Privacy by Design & by Default
   - Art. 32: Technische Sicherheitsmaßnahmen
   - Art. 35: Datenschutz-Folgenabschätzung
   - Art. 44-50: Internationale Datentransfers

3. **Architekturprinzipien**
   - **Modularität**: Lose Kopplung, hohe Kohäsion
   - **Skalierbarkeit**: Horizontal skalierbar
   - **Resilience**: Fehlertoleranz, Graceful Degradation
   - **Security by Design**: Defense in Depth
   - **Vendor Independence**: Keine Lock-ins

=« ARCHITECTURAL RED FLAGS:
- Monolithische Systeme ohne Modulgrenzen
- Hardcodierte Cloud-Provider (AWS, GCP) ohne Abstraction
- Fehlende Fehlerbehandlung
- Keine Audit-Trails
- Biometrische Datenverarbeitung ohne Rechtsgrundlage
- US-Cloud-Abhängigkeiten ohne DPA

 BEST PRACTICES:
- Microservices/Modular Monolith
- Event-Driven Architecture
- API-First Design
- CQRS/Event Sourcing wo sinnvoll
- EU-Hosting (Hetzner, OVH, etc.)
- Open Standards (keine proprietären Formate)

AUSGABE:
- compliance_score: 0-100
- risk_level: LOW/MEDIUM/HIGH/CRITICAL
- violations: Liste von Verstößen
- recommendations: Architektur-Empfehlungen
"""


# ============================================================================
# Architecture Assessment Models
# ============================================================================


class ComplianceViolation:
    """Represents a compliance violation"""
    def __init__(
        self,
        regulation: str,  # "EU AI Act Art. 5", "DSGVO Art. 25"
        severity: RiskLevel,
        description: str,
        recommendation: str,
    ):
        self.regulation = regulation
        self.severity = severity
        self.description = description
        self.recommendation = recommendation


class ArchitectureAssessment:
    """Results of architecture assessment"""
    def __init__(self):
        self.compliance_score: float = 0.0
        self.risk_level: RiskLevel = RiskLevel.LOW
        self.violations: List[ComplianceViolation] = []
        self.recommendations: List[str] = []
        self.strengths: List[str] = []
        self.weaknesses: List[str] = []


# ============================================================================
# ArchitectAgent Implementation
# ============================================================================


class ArchitectAgent(BaseAgent):
    """
    System Architecture & EU Compliance Auditor.

    Features:
    - Architecture review and assessment
    - EU AI Act compliance checking
    - DSGVO Privacy by Design validation
    - Scalability and maintainability analysis
    - Security architecture review
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="ArchitectAgent",
                role="ARCHITECT",
                model="phi3",
                system_prompt=ARCHITECT_CONSTITUTIONAL_PROMPT,
                temperature=0.2,  # Low - analytical thinking
                max_tokens=4096,  # Longer for architectural analysis
                tools=[
                    "review_architecture",
                    "check_eu_compliance",
                    "assess_scalability",
                    "audit_security",
                    "recommend_improvements"
                ],
                permissions=["ARCHITECTURE_REVIEW", "COMPLIANCE_AUDIT", "RECOMMEND"],
            )

        if llm_client is None:
            from brain.agents.llm_client import get_llm_client
            llm_client = get_llm_client()

        super().__init__(llm_client, config)

        # Register tools
        self.register_tool("review_architecture", self.review_architecture)
        self.register_tool("check_eu_compliance", self.check_eu_compliance)
        self.register_tool("assess_scalability", self.assess_scalability)
        self.register_tool("audit_security", self.audit_security)
        self.register_tool("recommend_improvements", self.recommend_improvements)

        # Assessment history
        self.assessments: List[Dict[str, Any]] = []

        logger.info(
            "<Û ArchitectAgent initialized | Supervisor: %s",
            "enabled" if SUPERVISOR_AVAILABLE else "disabled"
        )

    # ------------------------------------------------------------------------
    # High-Level Assessment Methods
    # ------------------------------------------------------------------------

    async def review_architecture(
        self,
        system_name: str,
        architecture_spec: Dict[str, Any],
        high_risk_ai: bool = False
    ) -> AgentResult:
        """
        Comprehensive architecture review.

        Args:
            system_name: Name of the system to review
            architecture_spec: Architecture specification including:
                - components: List of components/modules
                - data_flows: Data flow descriptions
                - external_dependencies: External services
                - deployment_target: Where it will be deployed
                - uses_personal_data: bool
                - uses_ai: bool
            high_risk_ai: Whether this is a high-risk AI system (EU AI Act)

        Returns:
            AgentResult with assessment
        """
        logger.info("<Û Architecture review requested | system=%s high_risk=%s", system_name, high_risk_ai)

        assessment = ArchitectureAssessment()

        # 1. EU AI Act Compliance Check
        if architecture_spec.get("uses_ai", False) or high_risk_ai:
            ai_compliance = await self._check_ai_act_compliance(architecture_spec, high_risk_ai)
            assessment.violations.extend(ai_compliance["violations"])

        # 2. DSGVO Compliance Check
        if architecture_spec.get("uses_personal_data", False):
            gdpr_compliance = await self._check_gdpr_compliance(architecture_spec)
            assessment.violations.extend(gdpr_compliance["violations"])

        # 3. Architecture Quality Assessment
        quality_assessment = await self._assess_architecture_quality(architecture_spec)
        assessment.strengths.extend(quality_assessment["strengths"])
        assessment.weaknesses.extend(quality_assessment["weaknesses"])

        # 4. Security Audit
        security_audit = await self._audit_security_architecture(architecture_spec)
        assessment.violations.extend(security_audit["violations"])

        # 5. Calculate compliance score
        total_violations = len(assessment.violations)
        critical_violations = sum(
            1 for v in assessment.violations
            if v.severity in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )

        if critical_violations > 0:
            assessment.compliance_score = max(0, 50 - (critical_violations * 15))
            assessment.risk_level = RiskLevel.CRITICAL
        elif total_violations > 5:
            assessment.compliance_score = max(50, 80 - (total_violations * 5))
            assessment.risk_level = RiskLevel.HIGH
        elif total_violations > 0:
            assessment.compliance_score = 85
            assessment.risk_level = RiskLevel.MEDIUM
        else:
            assessment.compliance_score = 95
            assessment.risk_level = RiskLevel.LOW

        # 6. Generate recommendations
        assessment.recommendations = await self._generate_recommendations(assessment)

        # 7. Store assessment
        self.assessments.append({
            "system_name": system_name,
            "timestamp": datetime.utcnow().isoformat(),
            "compliance_score": assessment.compliance_score,
            "risk_level": assessment.risk_level.value,
            "violations_count": total_violations,
        })

        logger.info(
            " Architecture review completed | score=%.1f risk=%s violations=%d",
            assessment.compliance_score,
            assessment.risk_level.value,
            total_violations
        )

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": f"Architecture review completed for {system_name}",
            "meta": {
                "compliance_score": assessment.compliance_score,
                "risk_level": assessment.risk_level.value,
                "violations": [
                    {
                        "regulation": v.regulation,
                        "severity": v.severity.value,
                        "description": v.description,
                        "recommendation": v.recommendation,
                    }
                    for v in assessment.violations
                ],
                "recommendations": assessment.recommendations,
                "strengths": assessment.strengths,
                "weaknesses": assessment.weaknesses,
            }
        }

    async def check_eu_compliance(
        self,
        system_spec: Dict[str, Any]
    ) -> AgentResult:
        """
        Focused EU compliance check (AI Act + DSGVO).

        Args:
            system_spec: System specification

        Returns:
            AgentResult with compliance status
        """
        logger.info("<ê<ú EU compliance check requested")

        violations: List[Dict[str, Any]] = []

        # 1. Check for prohibited AI practices (AI Act Art. 5)
        prohibited_practices = [
            "social_scoring",
            "subliminal_manipulation",
            "exploitation_of_vulnerabilities",
            "biometric_categorization",
            "real_time_remote_biometric_identification"
        ]

        for practice in prohibited_practices:
            if practice in system_spec.get("ai_capabilities", []):
                violations.append({
                    "regulation": "EU AI Act Art. 5",
                    "severity": "CRITICAL",
                    "description": f"Prohibited AI practice detected: {practice}",
                    "recommendation": "Remove this capability - it is banned under EU law"
                })

        # 2. Check data transfer locations
        external_deps = system_spec.get("external_dependencies", [])
        for dep in external_deps:
            if dep.get("location", "").lower() in ["us", "usa", "united states"]:
                if not dep.get("has_dpa"):  # Data Processing Agreement
                    violations.append({
                        "regulation": "DSGVO Art. 44-46",
                        "severity": "HIGH",
                        "description": f"Data transfer to US without DPA: {dep.get('name')}",
                        "recommendation": "Obtain Standard Contractual Clauses (SCC) or use EU provider"
                    })

        # 3. Check for Privacy by Design
        if system_spec.get("uses_personal_data") and not system_spec.get("privacy_by_design"):
            violations.append({
                "regulation": "DSGVO Art. 25",
                "severity": "HIGH",
                "description": "Privacy by Design not implemented",
                "recommendation": "Implement data minimization, pseudonymization, encryption"
            })

        compliance_status = "COMPLIANT" if len(violations) == 0 else "NON_COMPLIANT"

        logger.info(" EU compliance check completed | status=%s violations=%d", compliance_status, len(violations))

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": f"EU compliance: {compliance_status}",
            "meta": {
                "status": compliance_status,
                "violations": violations,
                "checked_regulations": ["EU AI Act", "DSGVO"],
            }
        }

    async def assess_scalability(
        self,
        architecture_spec: Dict[str, Any]
    ) -> AgentResult:
        """
        Assess system scalability.

        Args:
            architecture_spec: Architecture specification

        Returns:
            AgentResult with scalability assessment
        """
        logger.info("=È Scalability assessment requested")

        issues: List[str] = []
        recommendations: List[str] = []

        # Check for monolithic patterns
        if architecture_spec.get("architecture_type") == "monolithic":
            if architecture_spec.get("expected_users", 0) > 10000:
                issues.append("Monolithic architecture may not scale beyond 10k users")
                recommendations.append("Consider microservices or modular monolith")

        # Check for database bottlenecks
        if not architecture_spec.get("database_replication"):
            issues.append("Single database instance - potential bottleneck")
            recommendations.append("Implement read replicas and connection pooling")

        # Check for caching
        if not architecture_spec.get("caching_layer"):
            issues.append("No caching layer - high database load")
            recommendations.append("Add Redis/Memcached for caching")

        # Check for async processing
        if not architecture_spec.get("async_task_queue"):
            issues.append("No async task queue - blocking operations")
            recommendations.append("Implement Celery/RQ for background tasks")

        scalability_score = max(0, 100 - (len(issues) * 20))

        logger.info(" Scalability assessment completed | score=%d issues=%d", scalability_score, len(issues))

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": "Scalability assessment completed",
            "meta": {
                "scalability_score": scalability_score,
                "issues": issues,
                "recommendations": recommendations,
            }
        }

    async def audit_security(
        self,
        architecture_spec: Dict[str, Any]
    ) -> AgentResult:
        """
        Security architecture audit.

        Args:
            architecture_spec: Architecture specification

        Returns:
            AgentResult with security audit
        """
        logger.info("= Security audit requested")

        vulnerabilities: List[Dict[str, str]] = []

        # Check authentication
        if not architecture_spec.get("authentication"):
            vulnerabilities.append({
                "severity": "CRITICAL",
                "issue": "No authentication mechanism",
                "recommendation": "Implement OAuth2/JWT authentication"
            })

        # Check encryption
        if not architecture_spec.get("encryption_at_rest"):
            vulnerabilities.append({
                "severity": "HIGH",
                "issue": "No encryption at rest",
                "recommendation": "Enable database encryption (e.g., PostgreSQL encryption)"
            })

        if not architecture_spec.get("encryption_in_transit"):
            vulnerabilities.append({
                "severity": "HIGH",
                "issue": "No TLS/HTTPS",
                "recommendation": "Enforce HTTPS with Let's Encrypt certificates"
            })

        # Check input validation
        if not architecture_spec.get("input_validation"):
            vulnerabilities.append({
                "severity": "HIGH",
                "issue": "No input validation",
                "recommendation": "Use Pydantic for request validation"
            })

        # Check rate limiting
        if not architecture_spec.get("rate_limiting"):
            vulnerabilities.append({
                "severity": "MEDIUM",
                "issue": "No rate limiting",
                "recommendation": "Implement rate limiting (e.g., slowapi, nginx)"
            })

        security_score = max(0, 100 - (len(vulnerabilities) * 15))

        logger.info(" Security audit completed | score=%d vulnerabilities=%d", security_score, len(vulnerabilities))

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": "Security audit completed",
            "meta": {
                "security_score": security_score,
                "vulnerabilities": vulnerabilities,
            }
        }

    async def recommend_improvements(
        self,
        assessment_result: Dict[str, Any]
    ) -> AgentResult:
        """
        Generate prioritized improvement recommendations.

        Args:
            assessment_result: Previous assessment results

        Returns:
            AgentResult with prioritized recommendations
        """
        logger.info("=¡ Generating improvement recommendations")

        # Use LLM to generate prioritized recommendations
        prompt = f"""Basierend auf dieser Architektur-Bewertung:

Compliance Score: {assessment_result.get('compliance_score', 0)}
Risk Level: {assessment_result.get('risk_level', 'UNKNOWN')}
Violations: {assessment_result.get('violations', [])}

Erstelle eine **priorisierte Liste** von Verbesserungsvorschlägen:

1. **KRITISCH** (sofort umsetzen)
2. **HOCH** (in nächsten 2 Wochen)
3. **MITTEL** (in nächsten 2 Monaten)
4. **NIEDRIG** (langfristig)

Für jeden Vorschlag:
- Konkrete Maßnahme
- Begründung (EU AI Act/DSGVO Artikel)
- Geschätzter Aufwand (Stunden)
"""

        recommendations_text = await self.call_llm(prompt)

        return {
            "id": str(uuid.uuid4()),
            "success": True,
            "message": "Improvement recommendations generated",
            "raw_response": recommendations_text,
            "meta": {
                "recommendations": recommendations_text,
            }
        }

    # ------------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------------

    async def _check_ai_act_compliance(
        self,
        spec: Dict[str, Any],
        high_risk: bool
    ) -> Dict[str, Any]:
        """Check EU AI Act compliance"""
        violations: List[ComplianceViolation] = []

        # High-risk AI systems requirements (Art. 9-13)
        if high_risk:
            required_elements = [
                ("risk_management_system", "EU AI Act Art. 9"),
                ("data_governance", "EU AI Act Art. 10"),
                ("technical_documentation", "EU AI Act Art. 11"),
                ("record_keeping", "EU AI Act Art. 12"),
                ("transparency_obligations", "EU AI Act Art. 13"),
                ("human_oversight", "EU AI Act Art. 14"),
            ]

            for element, regulation in required_elements:
                if not spec.get(element):
                    violations.append(ComplianceViolation(
                        regulation=regulation,
                        severity=RiskLevel.CRITICAL,
                        description=f"High-risk AI missing: {element}",
                        recommendation=f"Implement {element} as required by {regulation}"
                    ))

        return {"violations": violations}

    async def _check_gdpr_compliance(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Check DSGVO/GDPR compliance"""
        violations: List[ComplianceViolation] = []

        # Privacy by Design checks
        privacy_elements = [
            ("data_minimization", "DSGVO Art. 5"),
            ("pseudonymization", "DSGVO Art. 25"),
            ("encryption", "DSGVO Art. 32"),
            ("right_to_deletion", "DSGVO Art. 17"),
        ]

        for element, regulation in privacy_elements:
            if not spec.get(element):
                violations.append(ComplianceViolation(
                    regulation=regulation,
                    severity=RiskLevel.HIGH,
                    description=f"Missing: {element}",
                    recommendation=f"Implement {element} per {regulation}"
                ))

        return {"violations": violations}

    async def _assess_architecture_quality(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Assess general architecture quality"""
        strengths: List[str] = []
        weaknesses: List[str] = []

        # Check modularity
        if spec.get("modular_design"):
            strengths.append("Modular design promotes maintainability")
        else:
            weaknesses.append("Lack of modularity will hinder maintenance")

        # Check API-first
        if spec.get("api_first"):
            strengths.append("API-first approach enables flexibility")

        # Check vendor independence
        if spec.get("vendor_independent"):
            strengths.append("Vendor-independent architecture avoids lock-in")
        else:
            weaknesses.append("Vendor lock-in risk detected")

        return {"strengths": strengths, "weaknesses": weaknesses}

    async def _audit_security_architecture(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Audit security architecture"""
        violations: List[ComplianceViolation] = []

        # Check for security basics
        if not spec.get("authentication"):
            violations.append(ComplianceViolation(
                regulation="DSGVO Art. 32",
                severity=RiskLevel.CRITICAL,
                description="No authentication mechanism",
                recommendation="Implement secure authentication (OAuth2/JWT)"
            ))

        return {"violations": violations}

    async def _generate_recommendations(self, assessment: ArchitectureAssessment) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        for violation in assessment.violations:
            recommendations.append(violation.recommendation)

        for weakness in assessment.weaknesses:
            recommendations.append(f"Address: {weakness}")

        return list(set(recommendations))  # Remove duplicates


# ============================================================================
# Convenience Function
# ============================================================================


def get_architect_agent(llm_client: Optional[LLMClient] = None) -> ArchitectAgent:
    """Get an ArchitectAgent instance"""
    return ArchitectAgent(llm_client=llm_client)
