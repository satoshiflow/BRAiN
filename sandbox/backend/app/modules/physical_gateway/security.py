"""
Physical Gateway Security

Handles authentication, authorization, and validation for physical agents.

Security Features:
- Challenge-response authentication
- Command validation
- Safety checks
- Rate limiting
- Fail-closed design
- No direct system access
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from loguru import logger

from .schemas import (
    GatewayCommand,
    CommandPriority,
    ValidationResult,
    SecurityHandshake,
    HandshakeResponse,
    PhysicalAgentInfo,
)


# ============================================================================
# Security Manager
# ============================================================================


class SecurityManager:
    """
    Manages security for physical agents gateway.

    Features:
    - Challenge-response authentication
    - Session token management
    - Command authorization
    - Rate limiting per agent
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        session_timeout_minutes: int = 60,
    ):
        """
        Initialize security manager.

        Args:
            master_key: Master secret key for HMAC (defaults to BRAIN_PHYSICAL_GATEWAY_MASTER_KEY env var)
            session_timeout_minutes: Session token validity period

        Raises:
            ValueError: If master_key not provided and BRAIN_PHYSICAL_GATEWAY_MASTER_KEY env var not set
        """
        if master_key is None:
            master_key = os.environ.get("BRAIN_PHYSICAL_GATEWAY_MASTER_KEY")
            if not master_key:
                raise ValueError(
                    "BRAIN_PHYSICAL_GATEWAY_MASTER_KEY environment variable must be set"
                )
        self.master_key = master_key.encode("utf-8")
        self.session_timeout = timedelta(minutes=session_timeout_minutes)

        # Active sessions: agent_id -> (token, expires_at)
        self.sessions: Dict[str, tuple[str, datetime]] = {}

        # Active challenges: agent_id -> (challenge, created_at)
        self.challenges: Dict[str, tuple[str, datetime]] = {}

        # Rate limiting: agent_id -> command_timestamps
        self.rate_limit_window_seconds = 60.0
        self.max_commands_per_window = 100
        self.command_history: Dict[str, List[float]] = {}

        # Blocked agents
        self.blocked_agents: Set[str] = set()

        logger.info("Security Manager initialized")

    # ========================================================================
    # Authentication
    # ========================================================================

    def generate_challenge(self, agent_id: str) -> str:
        """
        Generate authentication challenge for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Challenge nonce (32-byte hex string)
        """
        challenge = secrets.token_hex(32)
        self.challenges[agent_id] = (challenge, datetime.utcnow())

        logger.info(f"Challenge generated for agent: {agent_id}")
        return challenge

    def verify_handshake(
        self,
        handshake: SecurityHandshake,
    ) -> HandshakeResponse:
        """
        Verify security handshake from agent.

        Args:
            handshake: Handshake request from agent

        Returns:
            Handshake response with session token
        """
        agent_id = handshake.agent_id

        # Check if agent is blocked
        if agent_id in self.blocked_agents:
            logger.warning(f"Blocked agent attempted handshake: {agent_id}")
            return HandshakeResponse(
                success=False,
                error_message="Agent is blocked",
            )

        # Verify challenge exists
        if agent_id not in self.challenges:
            logger.warning(f"No challenge found for agent: {agent_id}")
            return HandshakeResponse(
                success=False,
                error_message="No active challenge for agent",
            )

        challenge, created_at = self.challenges[agent_id]

        # Check challenge expiry (5 minutes)
        if (datetime.utcnow() - created_at).total_seconds() > 300:
            logger.warning(f"Expired challenge for agent: {agent_id}")
            del self.challenges[agent_id]
            return HandshakeResponse(
                success=False,
                error_message="Challenge expired",
            )

        # Verify response
        expected_response = self._compute_challenge_response(agent_id, challenge)

        if not hmac.compare_digest(handshake.response, expected_response):
            logger.warning(f"Invalid handshake response from agent: {agent_id}")
            return HandshakeResponse(
                success=False,
                error_message="Invalid challenge response",
            )

        # Generate session token
        session_token = self._generate_session_token(agent_id)
        expires_at = datetime.utcnow() + self.session_timeout

        self.sessions[agent_id] = (session_token, expires_at)
        del self.challenges[agent_id]

        logger.info(f"✅ Agent authenticated: {agent_id}")

        return HandshakeResponse(
            success=True,
            session_token=session_token,
            expires_at=expires_at,
        )

    def _compute_challenge_response(self, agent_id: str, challenge: str) -> str:
        """
        Compute expected challenge response using HMAC.

        Args:
            agent_id: Agent identifier
            challenge: Challenge nonce

        Returns:
            Expected HMAC response
        """
        message = f"{agent_id}:{challenge}".encode("utf-8")
        return hmac.new(self.master_key, message, hashlib.sha256).hexdigest()

    def _generate_session_token(self, agent_id: str) -> str:
        """
        Generate session token for authenticated agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Session token
        """
        timestamp = int(time.time())
        message = f"{agent_id}:{timestamp}:{secrets.token_hex(16)}".encode("utf-8")
        return hmac.new(self.master_key, message, hashlib.sha256).hexdigest()

    # ========================================================================
    # Authorization
    # ========================================================================

    def authorize_command(
        self,
        agent_id: str,
        command: GatewayCommand,
        session_token: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Authorize command execution.

        Args:
            agent_id: Agent identifier
            command: Command to authorize
            session_token: Session token from agent

        Returns:
            (authorized, error_message)
        """
        # Check if agent is blocked
        if agent_id in self.blocked_agents:
            return False, "Agent is blocked"

        # Verify session token
        if command.requires_authorization:
            if not session_token:
                return False, "Session token required"

            if agent_id not in self.sessions:
                return False, "No active session"

            stored_token, expires_at = self.sessions[agent_id]

            if datetime.utcnow() > expires_at:
                del self.sessions[agent_id]
                return False, "Session expired"

            if not hmac.compare_digest(session_token, stored_token):
                return False, "Invalid session token"

        # Check rate limiting
        if not self._check_rate_limit(agent_id):
            return False, "Rate limit exceeded"

        logger.info(f"✅ Command authorized for agent: {agent_id}")
        return True, None

    def _check_rate_limit(self, agent_id: str) -> bool:
        """
        Check if agent is within rate limits.

        Args:
            agent_id: Agent identifier

        Returns:
            True if within limits
        """
        now = time.time()
        cutoff = now - self.rate_limit_window_seconds

        # Initialize if needed
        if agent_id not in self.command_history:
            self.command_history[agent_id] = []

        # Remove old timestamps
        self.command_history[agent_id] = [
            ts for ts in self.command_history[agent_id] if ts > cutoff
        ]

        # Check limit
        if len(self.command_history[agent_id]) >= self.max_commands_per_window:
            logger.warning(f"Rate limit exceeded for agent: {agent_id}")
            return False

        # Record new command
        self.command_history[agent_id].append(now)
        return True

    # ========================================================================
    # Agent Management
    # ========================================================================

    def block_agent(self, agent_id: str, reason: str = "Security violation"):
        """
        Block an agent from accessing the gateway.

        Args:
            agent_id: Agent to block
            reason: Reason for blocking
        """
        self.blocked_agents.add(agent_id)

        # Invalidate session
        if agent_id in self.sessions:
            del self.sessions[agent_id]

        logger.warning(f"🚫 Agent blocked: {agent_id} ({reason})")

    def unblock_agent(self, agent_id: str):
        """
        Unblock an agent.

        Args:
            agent_id: Agent to unblock
        """
        if agent_id in self.blocked_agents:
            self.blocked_agents.remove(agent_id)
            logger.info(f"✅ Agent unblocked: {agent_id}")

    def revoke_session(self, agent_id: str):
        """
        Revoke agent's session.

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self.sessions:
            del self.sessions[agent_id]
            logger.info(f"Session revoked for agent: {agent_id}")

    # ========================================================================
    # Cleanup
    # ========================================================================

    def cleanup_expired_sessions(self):
        """Remove expired sessions and challenges."""
        now = datetime.utcnow()

        # Clean sessions
        expired_sessions = [
            agent_id
            for agent_id, (_, expires_at) in self.sessions.items()
            if now > expires_at
        ]

        for agent_id in expired_sessions:
            del self.sessions[agent_id]
            logger.debug(f"Expired session removed: {agent_id}")

        # Clean challenges (expire after 5 minutes)
        expired_challenges = [
            agent_id
            for agent_id, (_, created_at) in self.challenges.items()
            if (now - created_at).total_seconds() > 300
        ]

        for agent_id in expired_challenges:
            del self.challenges[agent_id]
            logger.debug(f"Expired challenge removed: {agent_id}")


# ============================================================================
# Command Validator
# ============================================================================


class CommandValidator:
    """
    Validates commands for safety and correctness.

    Validation checks:
    - Parameter validation
    - Safety boundaries
    - Physical constraints
    - Capability matching
    """

    def __init__(self):
        """Initialize command validator."""
        # Safety boundaries (example)
        self.max_velocity_mps = 5.0  # m/s
        self.max_acceleration_mps2 = 2.0  # m/s²
        self.max_force_n = 1000.0  # Newtons

        # Dangerous command patterns
        self.dangerous_patterns = [
            "shutdown",
            "reboot",
            "format",
            "delete_all",
            "factory_reset",
        ]

        logger.info("Command Validator initialized")

    def validate_command(
        self,
        command: GatewayCommand,
        agent: PhysicalAgentInfo,
    ) -> ValidationResult:
        """
        Validate command for execution.

        Args:
            command: Command to validate
            agent: Target agent information

        Returns:
            Validation result with safety score
        """
        errors: List[str] = []
        warnings: List[str] = []
        safety_score = 1.0

        # Check agent state
        if agent.state == "error":
            errors.append("Agent is in error state")
            safety_score *= 0.0

        elif agent.state == "emergency_stop":
            errors.append("Agent is in emergency stop state")
            safety_score *= 0.0

        elif agent.state == "maintenance":
            warnings.append("Agent is in maintenance mode")
            safety_score *= 0.7

        # Check battery level
        if agent.battery_percentage is not None:
            if agent.battery_percentage < 5.0:
                errors.append("Battery level critically low (<5%)")
                safety_score *= 0.0

            elif agent.battery_percentage < 20.0:
                warnings.append("Battery level low (<20%)")
                safety_score *= 0.8

        # Validate command type
        if any(
            pattern in command.command_type.lower()
            for pattern in self.dangerous_patterns
        ):
            warnings.append(f"Potentially dangerous command: {command.command_type}")
            safety_score *= 0.5

        # Validate parameters
        param_errors = self._validate_parameters(command, agent)
        errors.extend(param_errors)
        if param_errors:
            safety_score *= 0.6

        # Priority validation
        if command.priority == CommandPriority.EMERGENCY:
            # Emergency commands bypass some checks
            warnings.append("Emergency priority - reduced validation")

        # Determine validity
        valid = len(errors) == 0 and safety_score >= 0.5

        result = ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            safety_score=safety_score,
            details={
                "agent_state": agent.state,
                "battery_percentage": agent.battery_percentage,
                "command_type": command.command_type,
            },
        )

        if not valid:
            logger.warning(
                f"Command validation failed: {command.command_id} "
                f"(errors: {len(errors)}, safety_score: {safety_score:.2f})"
            )
        else:
            logger.info(
                f"✅ Command validated: {command.command_id} "
                f"(safety_score: {safety_score:.2f})"
            )

        return result

    def _validate_parameters(
        self,
        command: GatewayCommand,
        agent: PhysicalAgentInfo,
    ) -> List[str]:
        """
        Validate command parameters.

        Args:
            command: Command to validate
            agent: Target agent

        Returns:
            List of validation errors
        """
        errors: List[str] = []
        params = command.parameters

        # Velocity validation
        if "velocity" in params:
            velocity = params["velocity"]
            if isinstance(velocity, (int, float)):
                if velocity > self.max_velocity_mps:
                    errors.append(
                        f"Velocity {velocity} m/s exceeds maximum {self.max_velocity_mps} m/s"
                    )

        # Acceleration validation
        if "acceleration" in params:
            acceleration = params["acceleration"]
            if isinstance(acceleration, (int, float)):
                if acceleration > self.max_acceleration_mps2:
                    errors.append(
                        f"Acceleration {acceleration} m/s² exceeds maximum "
                        f"{self.max_acceleration_mps2} m/s²"
                    )

        # Force validation
        if "force" in params:
            force = params["force"]
            if isinstance(force, (int, float)):
                if force > self.max_force_n:
                    errors.append(
                        f"Force {force} N exceeds maximum {self.max_force_n} N"
                    )

        # Position validation (bounds check if available)
        if "target_position" in params:
            # Could add workspace boundary checks here
            pass

        return errors


# ============================================================================
# Singleton
# ============================================================================

_security_manager: Optional[SecurityManager] = None
_command_validator: Optional[CommandValidator] = None


def get_security_manager() -> SecurityManager:
    """Get singleton SecurityManager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


def get_command_validator() -> CommandValidator:
    """Get singleton CommandValidator instance."""
    global _command_validator
    if _command_validator is None:
        _command_validator = CommandValidator()
    return _command_validator
