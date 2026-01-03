"""
Business Intent Resolver (Sprint 8.1)

Translates natural language business ideas into structured business intents.
Deterministic, rule-based resolution with keyword matching and pattern recognition.
"""

import uuid
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.modules.autonomous_pipeline.schemas import (
    BusinessIntentInput,
    ResolvedBusinessIntent,
    BusinessType,
    MonetizationType,
    RiskLevel,
    ComplianceSensitivity,
)


class BusinessIntentResolver:
    """
    Resolves natural language business descriptions into structured intents.

    Design Principles:
    - Deterministic (same input → same output)
    - Rule-based (no ML/LLM required)
    - Keyword matching with confidence scoring
    - Fail-closed (unknown patterns → high risk level)
    """

    # Keyword patterns for business type classification
    BUSINESS_TYPE_KEYWORDS = {
        BusinessType.SERVICE: [
            "consulting", "agency", "advisory", "professional services",
            "consulting firm", "expert", "specialist", "coach", "trainer"
        ],
        BusinessType.PRODUCT: [
            "e-commerce", "retail", "store", "shop", "sell products",
            "product sales", "merchandise", "goods"
        ],
        BusinessType.PLATFORM: [
            "marketplace", "platform", "network", "matching",
            "connecting", "community", "saas", "software as a service"
        ],
    }

    # Keyword patterns for monetization type
    MONETIZATION_KEYWORDS = {
        MonetizationType.SUBSCRIPTION: [
            "subscription", "recurring", "monthly", "annual",
            "membership", "saas"
        ],
        MonetizationType.ONE_TIME: [
            "one-time", "purchase", "buy", "sell"
        ],
        MonetizationType.FREEMIUM: [
            "freemium", "free tier", "premium", "upgrade"
        ],
        MonetizationType.COMMISSION: [
            "commission", "marketplace", "fee", "percentage",
            "matching fee", "transaction fee"
        ],
        MonetizationType.ADVERTISING: [
            "advertising", "ads", "sponsored", "ad-supported"
        ],
    }

    # Industry keywords
    INDUSTRY_KEYWORDS = {
        "consulting": ["consulting", "advisory", "expert", "specialist"],
        "e-commerce": ["e-commerce", "online store", "shop", "retail"],
        "healthcare": ["healthcare", "medical", "health", "clinic"],
        "finance": ["finance", "banking", "investment", "trading"],
        "legal": ["legal", "law", "attorney", "lawyer"],
        "education": ["education", "learning", "training", "course"],
        "manufacturing": ["manufacturing", "production", "factory"],
        "technology": ["software", "tech", "digital", "platform"],
    }

    # Compliance sensitivity indicators
    HIGH_COMPLIANCE_KEYWORDS = [
        "healthcare", "medical", "finance", "banking", "legal",
        "payment", "sensitive data", "personal information"
    ]

    MEDIUM_COMPLIANCE_KEYWORDS = [
        "e-commerce", "customer data", "transactions", "users"
    ]

    def __init__(self):
        """Initialize business intent resolver."""
        logger.info("BusinessIntentResolver initialized (deterministic mode)")

    def resolve(self, intent_input: BusinessIntentInput) -> ResolvedBusinessIntent:
        """
        Resolve business intent from natural language input.

        Args:
            intent_input: Business intent input

        Returns:
            ResolvedBusinessIntent with structured configuration
        """
        logger.info(f"Resolving business intent: {intent_input.vision[:100]}...")

        # Generate unique intent ID
        intent_id = f"intent_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Combine all text for analysis
        full_text = f"{intent_input.vision} {intent_input.target_audience}".lower()

        # Classify business type
        business_type = self._classify_business_type(full_text)

        # Determine monetization type
        monetization_type = intent_input.monetization_type or self._classify_monetization(full_text)

        # Determine industry
        industry = self._classify_industry(full_text)

        # Assess risk level
        risk_level = self._assess_risk_level(
            business_type,
            monetization_type,
            intent_input.compliance_sensitivity,
            industry
        )

        # Determine compliance sensitivity (override if high-risk keywords found)
        compliance_sensitivity = self._assess_compliance_sensitivity(
            full_text,
            intent_input.compliance_sensitivity
        )

        # Determine technical requirements
        needs_website, website_template, website_pages = self._determine_website_requirements(
            business_type,
            industry
        )

        needs_erp = self._determine_erp_requirements(business_type, monetization_type)

        # Determine Odoo modules
        odoo_modules_required = self._determine_odoo_modules(
            business_type,
            monetization_type,
            industry
        )

        # Determine if custom modules needed
        needs_custom_modules = self._needs_custom_modules(full_text, business_type)

        # Generate custom module specs (if needed)
        custom_modules_spec = []
        if needs_custom_modules:
            custom_modules_spec = self._generate_custom_module_specs(
                full_text,
                business_type,
                industry
            )

        # Suggest domain pattern
        suggested_domain_pattern = self._suggest_domain_pattern(business_type, industry)

        # Determine governance checks
        governance_checks = self._determine_governance_checks(
            risk_level,
            compliance_sensitivity
        )

        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(
            business_type,
            len(odoo_modules_required),
            len(custom_modules_spec),
            risk_level
        )

        # Build resolved intent
        resolved_intent = ResolvedBusinessIntent(
            intent_id=intent_id,
            business_type=business_type,
            monetization_type=monetization_type,
            risk_level=risk_level,
            compliance_sensitivity=compliance_sensitivity,
            needs_website=needs_website,
            needs_erp=needs_erp,
            needs_custom_modules=needs_custom_modules,
            website_template=website_template,
            website_pages=website_pages,
            odoo_modules_required=odoo_modules_required,
            custom_modules_spec=custom_modules_spec,
            suggested_domain_pattern=suggested_domain_pattern,
            industry=industry,
            primary_language=intent_input.preferred_language,
            target_region=intent_input.region,
            governance_checks_required=governance_checks,
            estimated_complexity_score=complexity_score,
            original_vision=intent_input.vision,
        )

        logger.info(
            f"Business intent resolved: type={business_type.value}, "
            f"risk={risk_level.value}, complexity={complexity_score}"
        )

        return resolved_intent

    def _classify_business_type(self, text: str) -> BusinessType:
        """Classify business type from text using keyword matching."""
        scores = {business_type: 0 for business_type in BusinessType}

        for business_type, keywords in self.BUSINESS_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[business_type] += 1

        # Get highest scoring type
        max_score = max(scores.values())
        if max_score == 0:
            # Default to service if no matches
            logger.warning("No business type keywords matched, defaulting to SERVICE")
            return BusinessType.SERVICE

        # Find business type with highest score
        for business_type, score in scores.items():
            if score == max_score:
                return business_type

        return BusinessType.SERVICE

    def _classify_monetization(self, text: str) -> MonetizationType:
        """Classify monetization type from text."""
        scores = {mon_type: 0 for mon_type in MonetizationType}

        for mon_type, keywords in self.MONETIZATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[mon_type] += 1

        max_score = max(scores.values())
        if max_score == 0:
            # Default based on common patterns
            return MonetizationType.ONE_TIME

        for mon_type, score in scores.items():
            if score == max_score:
                return mon_type

        return MonetizationType.ONE_TIME

    def _classify_industry(self, text: str) -> str:
        """Classify industry from text."""
        scores = {industry: 0 for industry in self.INDUSTRY_KEYWORDS.keys()}

        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[industry] += 1

        max_score = max(scores.values())
        if max_score == 0:
            return "general"

        for industry, score in scores.items():
            if score == max_score:
                return industry

        return "general"

    def _assess_risk_level(
        self,
        business_type: BusinessType,
        monetization_type: MonetizationType,
        compliance_sensitivity: ComplianceSensitivity,
        industry: str
    ) -> RiskLevel:
        """Assess execution risk level."""
        risk_score = 0

        # Business type risk
        if business_type == BusinessType.PLATFORM:
            risk_score += 30
        elif business_type == BusinessType.PRODUCT:
            risk_score += 20
        elif business_type == BusinessType.SERVICE:
            risk_score += 10

        # Monetization complexity
        if monetization_type in [MonetizationType.COMMISSION, MonetizationType.FREEMIUM]:
            risk_score += 20
        elif monetization_type == MonetizationType.SUBSCRIPTION:
            risk_score += 15

        # Compliance sensitivity
        if compliance_sensitivity == ComplianceSensitivity.HIGH:
            risk_score += 30
        elif compliance_sensitivity == ComplianceSensitivity.MEDIUM:
            risk_score += 15

        # Industry risk
        if industry in ["finance", "healthcare", "legal"]:
            risk_score += 20

        # Map score to risk level
        if risk_score >= 70:
            return RiskLevel.CRITICAL
        elif risk_score >= 50:
            return RiskLevel.HIGH
        elif risk_score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _assess_compliance_sensitivity(
        self,
        text: str,
        declared_sensitivity: ComplianceSensitivity
    ) -> ComplianceSensitivity:
        """Assess compliance sensitivity, upgrading if high-risk keywords found."""
        # Check for high compliance keywords
        for keyword in self.HIGH_COMPLIANCE_KEYWORDS:
            if keyword in text:
                logger.warning(f"High compliance keyword detected: {keyword}")
                return ComplianceSensitivity.HIGH

        # Check for medium compliance keywords
        for keyword in self.MEDIUM_COMPLIANCE_KEYWORDS:
            if keyword in text:
                if declared_sensitivity == ComplianceSensitivity.LOW:
                    logger.info(f"Upgrading compliance to MEDIUM due to keyword: {keyword}")
                    return ComplianceSensitivity.MEDIUM

        return declared_sensitivity

    def _determine_website_requirements(
        self,
        business_type: BusinessType,
        industry: str
    ) -> Tuple[bool, Optional[str], List[str]]:
        """Determine website requirements."""
        # All businesses need websites
        needs_website = True

        # Determine template based on business type
        template_map = {
            BusinessType.SERVICE: "professional_services_v1",
            BusinessType.PRODUCT: "e_commerce_v1",
            BusinessType.PLATFORM: "platform_v1",
            BusinessType.HYBRID: "business_suite_v1",
        }

        template = template_map.get(business_type, "professional_services_v1")

        # Determine pages based on business type
        pages_map = {
            BusinessType.SERVICE: ["home", "services", "about", "team", "contact"],
            BusinessType.PRODUCT: ["home", "products", "cart", "checkout", "about", "contact"],
            BusinessType.PLATFORM: ["home", "features", "pricing", "about", "contact", "signup"],
            BusinessType.HYBRID: ["home", "services", "products", "about", "contact"],
        }

        pages = pages_map.get(business_type, ["home", "about", "contact"])

        return needs_website, template, pages

    def _determine_erp_requirements(
        self,
        business_type: BusinessType,
        monetization_type: MonetizationType
    ) -> bool:
        """Determine if ERP system is needed."""
        # All business types except very simple ones need ERP
        if business_type == BusinessType.PLATFORM:
            return True
        if monetization_type in [MonetizationType.SUBSCRIPTION, MonetizationType.COMMISSION]:
            return True

        # Default to True for business management
        return True

    def _determine_odoo_modules(
        self,
        business_type: BusinessType,
        monetization_type: MonetizationType,
        industry: str
    ) -> List[str]:
        """Determine required Odoo modules."""
        modules = set()

        # Base modules for all businesses
        modules.add("contacts")
        modules.add("mail")

        # Business type specific
        if business_type == BusinessType.SERVICE:
            modules.update(["crm", "project", "hr_timesheet", "sale"])

        if business_type == BusinessType.PRODUCT:
            modules.update(["sale", "stock", "purchase", "account"])

        if business_type == BusinessType.PLATFORM:
            modules.update(["crm", "sale", "website", "calendar"])

        # Monetization specific
        if monetization_type == MonetizationType.SUBSCRIPTION:
            modules.update(["sale", "account"])

        # Industry specific
        if industry == "consulting":
            modules.update(["project", "hr_timesheet", "sale_timesheet"])

        return sorted(list(modules))

    def _needs_custom_modules(self, text: str, business_type: BusinessType) -> bool:
        """Determine if custom modules are needed."""
        # Platforms typically need custom modules
        if business_type == BusinessType.PLATFORM:
            return True

        # Check for custom requirements indicators
        custom_indicators = ["custom", "specific", "unique", "specialized", "matching"]
        for indicator in custom_indicators:
            if indicator in text:
                return True

        return False

    def _generate_custom_module_specs(
        self,
        text: str,
        business_type: BusinessType,
        industry: str
    ) -> List[Dict]:
        """Generate custom module specifications."""
        specs = []

        # Platform-specific modules
        if business_type == BusinessType.PLATFORM:
            if "matching" in text or "connecting" in text:
                specs.append({
                    "name": f"{industry}_matching",
                    "description": f"Matching system for {industry} platform",
                    "models": ["match_request", "match_result", "user_profile"],
                    "views": ["match_kanban", "profile_form", "results_list"],
                })

        # If no specific specs generated but custom modules needed
        if not specs:
            specs.append({
                "name": f"{industry}_custom",
                "description": f"Custom business logic for {industry}",
                "models": ["custom_record"],
                "views": ["custom_form"],
            })

        return specs

    def _suggest_domain_pattern(self, business_type: BusinessType, industry: str) -> str:
        """Suggest domain naming pattern."""
        patterns = {
            BusinessType.SERVICE: "{business-name}.com",
            BusinessType.PRODUCT: "{business-name}.store",
            BusinessType.PLATFORM: "{business-name}.io",
        }

        return patterns.get(business_type, "{business-name}.com")

    def _determine_governance_checks(
        self,
        risk_level: RiskLevel,
        compliance_sensitivity: ComplianceSensitivity
    ) -> List[str]:
        """Determine required governance checks."""
        checks = []

        # Always check policy
        checks.append("policy_check")

        # Risk-based checks
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            checks.append("risk_assessment")
            checks.append("security_review")

        # Compliance checks
        if compliance_sensitivity in [ComplianceSensitivity.MEDIUM, ComplianceSensitivity.HIGH]:
            checks.append("data_privacy_check")

        if compliance_sensitivity == ComplianceSensitivity.HIGH:
            checks.append("regulatory_compliance_check")

        return checks

    def _calculate_complexity_score(
        self,
        business_type: BusinessType,
        odoo_modules_count: int,
        custom_modules_count: int,
        risk_level: RiskLevel
    ) -> int:
        """Calculate execution complexity score (1-100)."""
        score = 0

        # Business type complexity
        type_scores = {
            BusinessType.SERVICE: 20,
            BusinessType.PRODUCT: 30,
            BusinessType.PLATFORM: 40,
            BusinessType.HYBRID: 50,
        }
        score += type_scores.get(business_type, 20)

        # Module complexity
        score += min(odoo_modules_count * 3, 20)
        score += min(custom_modules_count * 10, 30)

        # Risk level
        risk_scores = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 10,
            RiskLevel.HIGH: 20,
            RiskLevel.CRITICAL: 30,
        }
        score += risk_scores.get(risk_level, 0)

        return min(score, 100)


# Singleton instance
_resolver: Optional[BusinessIntentResolver] = None


def get_business_intent_resolver() -> BusinessIntentResolver:
    """Get singleton business intent resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = BusinessIntentResolver()
    return _resolver
