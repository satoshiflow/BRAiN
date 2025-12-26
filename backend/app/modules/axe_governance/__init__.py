"""
AXE Trust Tier System

Definiert Trust Levels für AXE-Zugriffe und validiert Request-Herkunft.

SECURITY PRINCIPLE:
- AXE darf NIEMALS direkten Core-Zugriff haben
- Nur DMZ Gateways dürfen AXE nutzen
- Alle Requests müssen authentifiziert und auditiert werden
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from loguru import logger


class TrustTier(str, Enum):
    """
    Trust Tiers für AXE Requests.

    Hierarchie (absteigend):
    - LOCAL: Core-interne Calls (z.B. Tests, Admin-Tools)
    - DMZ: Authentifizierte DMZ Gateway Services
    - EXTERNAL: Unbekannte/nicht authentifizierte Quellen (BLOCKED)
    """

    LOCAL = "local"      # Core-internal - highest trust
    DMZ = "dmz"          # Authenticated DMZ gateways - medium trust
    EXTERNAL = "external"  # Unknown sources - NO TRUST (blocked)


class AXERequestContext(BaseModel):
    """Context für AXE Request Validierung."""

    trust_tier: TrustTier
    source_service: Optional[str] = None  # z.B. "telegram_gateway"
    source_ip: Optional[str] = None
    authenticated: bool = False
    dmz_gateway_token: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

    # Request metadata
    request_id: str
    user_agent: Optional[str] = None

    # Rate limiting
    rate_limit_key: str  # For rate limiting tracking


class AXETrustValidator:
    """
    Validiert Trust Tier für AXE Requests.

    FAIL-CLOSED: Im Zweifel wird Request als EXTERNAL eingestuft und blockiert.
    """

    # DMZ Gateway Shared Secret (sollte aus Environment kommen)
    # In Production: Rotate regelmäßig, pro Gateway unterschiedlich
    DMZ_GATEWAY_SECRET = "REPLACE_WITH_SECURE_SECRET_IN_PRODUCTION"

    # Bekannte DMZ Gateway Services
    KNOWN_DMZ_GATEWAYS = {
        "telegram_gateway",
        "whatsapp_gateway",
        "discord_gateway",
        "email_gateway",
    }

    def __init__(self):
        logger.info("AXE Trust Validator initialized")

    async def validate_request(
        self,
        headers: Dict[str, str],
        client_host: Optional[str] = None,
        request_id: str = "",
    ) -> AXERequestContext:
        """
        Validiert einen AXE Request und bestimmt Trust Tier.

        Args:
            headers: HTTP Headers
            client_host: Client IP/Host
            request_id: Unique Request ID

        Returns:
            AXERequestContext mit Trust Tier

        Trust Tier Bestimmung:
        1. Check DMZ Gateway Header + Token
        2. Check Localhost (127.0.0.1, ::1)
        3. Default: EXTERNAL (blocked)
        """
        # Extract relevant headers
        dmz_gateway_id = headers.get("x-dmz-gateway-id")
        dmz_gateway_token = headers.get("x-dmz-gateway-token")
        user_agent = headers.get("user-agent")

        # Check 1: DMZ Gateway Authentication
        if dmz_gateway_id and dmz_gateway_token:
            if self._validate_dmz_gateway(dmz_gateway_id, dmz_gateway_token):
                logger.info(f"AXE request authenticated as DMZ gateway: {dmz_gateway_id}")

                return AXERequestContext(
                    trust_tier=TrustTier.DMZ,
                    source_service=dmz_gateway_id,
                    source_ip=client_host,
                    authenticated=True,
                    dmz_gateway_token=dmz_gateway_token[:8] + "...",  # Redacted
                    request_id=request_id,
                    user_agent=user_agent,
                    rate_limit_key=f"dmz:{dmz_gateway_id}",
                )

        # Check 2: Localhost (for admin/testing)
        if client_host in ["127.0.0.1", "::1", "localhost"]:
            logger.info(f"AXE request from localhost: {client_host}")

            return AXERequestContext(
                trust_tier=TrustTier.LOCAL,
                source_service="localhost",
                source_ip=client_host,
                authenticated=True,
                request_id=request_id,
                user_agent=user_agent,
                rate_limit_key=f"local:{client_host}",
            )

        # Default: EXTERNAL (not trusted)
        logger.warning(
            f"AXE request from UNTRUSTED source: {client_host} "
            f"(gateway_id={dmz_gateway_id}, user_agent={user_agent})"
        )

        return AXERequestContext(
            trust_tier=TrustTier.EXTERNAL,
            source_service="unknown",
            source_ip=client_host,
            authenticated=False,
            request_id=request_id,
            user_agent=user_agent,
            rate_limit_key=f"external:{client_host}",
        )

    def _validate_dmz_gateway(self, gateway_id: str, token: str) -> bool:
        """
        Validiert DMZ Gateway Token.

        SIMPLIFIED: In Production sollte hier ein echter Token-basierter
        Authentifizierungsmechanismus sein (z.B. JWT, API Keys mit Hash).

        Args:
            gateway_id: DMZ Gateway Identifier
            token: Authentication Token

        Returns:
            True wenn Token valid
        """
        # Check 1: Bekanntes Gateway?
        if gateway_id not in self.KNOWN_DMZ_GATEWAYS:
            logger.warning(f"Unknown DMZ gateway ID: {gateway_id}")
            return False

        # Check 2: Token valid?
        # SIMPLIFIED: In Production hier echte Token-Validierung
        expected_token = self._generate_gateway_token(gateway_id)

        if token == expected_token:
            return True

        logger.warning(f"Invalid token for DMZ gateway: {gateway_id}")
        return False

    def _generate_gateway_token(self, gateway_id: str) -> str:
        """
        Generiert erwarteten Token für Gateway.

        SIMPLIFIED: In Production sollte hier ein echter Token-Mechanismus sein
        (z.B. HMAC, JWT mit Expiry, etc.)
        """
        import hashlib

        # SIMPLIFIED: Hash von Gateway ID + Shared Secret
        raw = f"{gateway_id}:{self.DMZ_GATEWAY_SECRET}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def is_request_allowed(self, context: AXERequestContext) -> bool:
        """
        Entscheidet, ob Request erlaubt ist.

        POLICY:
        - LOCAL: ALLOW (für Admin/Testing)
        - DMZ: ALLOW (authentifizierte Gateways)
        - EXTERNAL: DENY (fail-closed)

        Args:
            context: Request Context

        Returns:
            True wenn Request erlaubt
        """
        if context.trust_tier == TrustTier.EXTERNAL:
            logger.error(
                f"AXE request BLOCKED - EXTERNAL trust tier "
                f"(source={context.source_ip}, request_id={context.request_id})"
            )
            return False

        # LOCAL und DMZ sind erlaubt
        return True


# Singleton
_trust_validator: Optional[AXETrustValidator] = None


def get_axe_trust_validator() -> AXETrustValidator:
    """Get singleton AXE Trust Validator."""
    global _trust_validator
    if _trust_validator is None:
        _trust_validator = AXETrustValidator()
    return _trust_validator
