"""
Signature Validator - Ed25519 Bundle Signature Verification

Validates Ed25519 signatures on bundles and enforces signature policy.
Part of G1 - Bundle Signing & Trusted Origin governance implementation.
"""

from typing import Optional
from datetime import datetime
from loguru import logger

from app.modules.sovereign_mode.schemas import (
    ValidationResult,
    Bundle,
    AuditEventType,
)
from app.modules.sovereign_mode.crypto import (
    verify_bundle_signature,
    SignatureError,
)
from app.modules.sovereign_mode.keyring import get_trusted_keyring


class SignaturePolicy:
    """Bundle signature policy configuration."""

    def __init__(
        self,
        require_signature: bool = True,
        require_trusted_key: bool = True,
        allow_unsigned_bundles: bool = False,
        quarantine_on_failure: bool = True,
    ):
        """
        Initialize signature policy.

        Args:
            require_signature: Require bundles to have signatures
            require_trusted_key: Require signing key to be in trusted keyring
            allow_unsigned_bundles: Allow unsigned bundles (overrides require_signature)
            quarantine_on_failure: Quarantine bundles that fail signature validation
        """
        self.require_signature = require_signature
        self.require_trusted_key = require_trusted_key
        self.allow_unsigned_bundles = allow_unsigned_bundles
        self.quarantine_on_failure = quarantine_on_failure

    @classmethod
    def from_mode_config(cls, config: dict) -> "SignaturePolicy":
        """
        Create policy from mode configuration.

        Args:
            config: ModeConfig dictionary

        Returns:
            SignaturePolicy instance
        """
        return cls(
            require_signature=not config.get("allow_unsigned_bundles", False),
            require_trusted_key=True,  # Always require trusted keys
            allow_unsigned_bundles=config.get("allow_unsigned_bundles", False),
            quarantine_on_failure=config.get("quarantine_on_failure", True),
        )


class SignatureValidator:
    """Ed25519 signature validator for bundle verification."""

    VALIDATOR_VERSION = "1.0.0"

    def __init__(self, policy: Optional[SignaturePolicy] = None):
        """
        Initialize signature validator.

        Args:
            policy: Signature policy (default: strict policy)
        """
        self.policy = policy or SignaturePolicy(
            require_signature=True,
            require_trusted_key=True,
            allow_unsigned_bundles=False,
            quarantine_on_failure=True,
        )

        self.keyring = get_trusted_keyring()

        logger.info(
            f"Signature validator initialized (v{self.VALIDATOR_VERSION}): "
            f"require_signature={self.policy.require_signature}, "
            f"require_trusted={self.policy.require_trusted_key}"
        )

    def validate_bundle_signature(
        self, bundle: Bundle, validation_result: ValidationResult
    ) -> ValidationResult:
        """
        Validate bundle signature and update validation result.

        This method modifies the validation_result object in place.

        Args:
            bundle: Bundle to validate
            validation_result: Existing validation result (from hash validation)

        Returns:
            Updated ValidationResult with signature validation status

        Policy Enforcement:
        1. If allow_unsigned_bundles=True: unsigned bundles are allowed
        2. If require_signature=True: bundles MUST have a signature
        3. If require_trusted_key=True: signing key MUST be in trusted keyring
        4. Invalid signatures always fail validation

        Audit Events Emitted:
        - BUNDLE_UNSIGNED: Bundle has no signature
        - BUNDLE_SIGNATURE_VERIFIED: Signature is valid
        - BUNDLE_SIGNATURE_INVALID: Signature verification failed
        - BUNDLE_KEY_UNTRUSTED: Signing key is not in trusted keyring
        """
        try:
            # Check if bundle has signature
            if not bundle.signature:
                validation_result.signature_present = False

                # Policy: Allow unsigned bundles?
                if self.policy.allow_unsigned_bundles:
                    logger.debug(
                        f"Bundle {bundle.id} unsigned (allowed by policy)"
                    )
                    validation_result.warnings.append(
                        "Bundle is unsigned (allowed by policy)"
                    )
                    # Emit audit event
                    self._emit_audit_event(
                        AuditEventType.BUNDLE_UNSIGNED,
                        bundle_id=bundle.id,
                        success=True,
                        reason="Unsigned bundle allowed by policy",
                    )
                    return validation_result

                # Policy: Unsigned bundles not allowed
                logger.error(f"Bundle {bundle.id} is unsigned (policy violation)")
                validation_result.is_valid = False
                validation_result.signature_valid = False
                validation_result.errors.append(
                    "Bundle signature required but not present"
                )

                # Emit audit event
                self._emit_audit_event(
                    AuditEventType.BUNDLE_UNSIGNED,
                    bundle_id=bundle.id,
                    success=False,
                    reason="Unsigned bundle rejected by policy",
                )

                return validation_result

            # Bundle has signature
            validation_result.signature_present = True

            # Check if signature algorithm is supported
            if bundle.signature_algorithm != "ed25519":
                logger.error(
                    f"Bundle {bundle.id} uses unsupported signature algorithm: "
                    f"{bundle.signature_algorithm}"
                )
                validation_result.is_valid = False
                validation_result.signature_valid = False
                validation_result.errors.append(
                    f"Unsupported signature algorithm: {bundle.signature_algorithm}"
                )

                # Emit audit event
                self._emit_audit_event(
                    AuditEventType.BUNDLE_SIGNATURE_INVALID,
                    bundle_id=bundle.id,
                    success=False,
                    reason=f"Unsupported algorithm: {bundle.signature_algorithm}",
                )

                return validation_result

            # Check if signing key is in trusted keyring
            if not bundle.signed_by_key_id:
                logger.error(f"Bundle {bundle.id} missing signing key ID")
                validation_result.is_valid = False
                validation_result.signature_valid = False
                validation_result.key_trusted = False
                validation_result.errors.append("Signing key ID not specified")

                # Emit audit event
                self._emit_audit_event(
                    AuditEventType.BUNDLE_SIGNATURE_INVALID,
                    bundle_id=bundle.id,
                    success=False,
                    reason="Missing signing key ID",
                )

                return validation_result

            validation_result.key_id = bundle.signed_by_key_id

            # Policy: Check if key is trusted
            if self.policy.require_trusted_key:
                if not self.keyring.is_trusted(bundle.signed_by_key_id):
                    logger.error(
                        f"Bundle {bundle.id} signed by untrusted key: "
                        f"{bundle.signed_by_key_id}"
                    )
                    validation_result.is_valid = False
                    validation_result.signature_valid = False
                    validation_result.key_trusted = False
                    validation_result.errors.append(
                        f"Signing key not trusted: {bundle.signed_by_key_id}"
                    )

                    # Emit audit event
                    self._emit_audit_event(
                        AuditEventType.BUNDLE_KEY_UNTRUSTED,
                        bundle_id=bundle.id,
                        key_id=bundle.signed_by_key_id,
                        success=False,
                        reason="Key not in trusted keyring",
                    )

                    return validation_result

            validation_result.key_trusted = True

            # Get public key for verification
            try:
                public_key = self.keyring.get_public_key(bundle.signed_by_key_id)

                if not public_key:
                    logger.error(
                        f"Failed to load public key: {bundle.signed_by_key_id}"
                    )
                    validation_result.is_valid = False
                    validation_result.signature_valid = False
                    validation_result.errors.append(
                        f"Failed to load public key: {bundle.signed_by_key_id}"
                    )

                    # Emit audit event
                    self._emit_audit_event(
                        AuditEventType.BUNDLE_SIGNATURE_INVALID,
                        bundle_id=bundle.id,
                        key_id=bundle.signed_by_key_id,
                        success=False,
                        reason="Failed to load public key",
                    )

                    return validation_result

            except Exception as e:
                logger.error(f"Error loading public key: {e}")
                validation_result.is_valid = False
                validation_result.signature_valid = False
                validation_result.errors.append(f"Public key load error: {e}")

                # Emit audit event
                self._emit_audit_event(
                    AuditEventType.BUNDLE_SIGNATURE_INVALID,
                    bundle_id=bundle.id,
                    key_id=bundle.signed_by_key_id,
                    success=False,
                    reason=f"Public key load error: {e}",
                )

                return validation_result

            # Verify signature
            try:
                bundle_dict = bundle.model_dump()
                is_valid = verify_bundle_signature(
                    bundle_dict=bundle_dict,
                    signature_hex=bundle.signature,
                    public_key=public_key,
                )

                if is_valid:
                    logger.info(
                        f"Bundle {bundle.id} signature VALID (key: {bundle.signed_by_key_id})"
                    )
                    validation_result.signature_valid = True

                    # Emit audit event
                    self._emit_audit_event(
                        AuditEventType.BUNDLE_SIGNATURE_VERIFIED,
                        bundle_id=bundle.id,
                        key_id=bundle.signed_by_key_id,
                        success=True,
                        reason="Signature verified successfully",
                    )

                else:
                    logger.error(
                        f"Bundle {bundle.id} signature INVALID (key: {bundle.signed_by_key_id})"
                    )
                    validation_result.is_valid = False
                    validation_result.signature_valid = False
                    validation_result.errors.append("Ed25519 signature verification failed")

                    # Emit audit event
                    self._emit_audit_event(
                        AuditEventType.BUNDLE_SIGNATURE_INVALID,
                        bundle_id=bundle.id,
                        key_id=bundle.signed_by_key_id,
                        success=False,
                        reason="Signature verification failed",
                    )

                return validation_result

            except SignatureError as e:
                logger.error(f"Signature verification error for {bundle.id}: {e}")
                validation_result.is_valid = False
                validation_result.signature_valid = False
                validation_result.errors.append(f"Signature verification error: {e}")

                # Emit audit event
                self._emit_audit_event(
                    AuditEventType.BUNDLE_SIGNATURE_INVALID,
                    bundle_id=bundle.id,
                    key_id=bundle.signed_by_key_id,
                    success=False,
                    reason=f"Verification error: {e}",
                )

                return validation_result

        except Exception as e:
            logger.error(f"Unexpected error validating signature for {bundle.id}: {e}")
            validation_result.is_valid = False
            validation_result.signature_valid = False
            validation_result.errors.append(f"Signature validation error: {e}")

            # Emit audit event
            self._emit_audit_event(
                AuditEventType.BUNDLE_SIGNATURE_INVALID,
                bundle_id=bundle.id,
                success=False,
                reason=f"Unexpected error: {e}",
            )

            return validation_result

    def _emit_audit_event(
        self,
        event_type: str,
        bundle_id: str,
        key_id: Optional[str] = None,
        success: bool = False,
        reason: str = "",
    ):
        """
        Emit audit event for signature validation.

        Args:
            event_type: Audit event type
            bundle_id: Bundle identifier
            key_id: Signing key ID (optional)
            success: Whether operation succeeded
            reason: Event reason/details
        """
        try:
            from app.modules.sovereign_mode.service import (
                get_sovereign_mode_service,
            )

            service = get_sovereign_mode_service()

            metadata = {
                "bundle_id": bundle_id,
                "signature_algorithm": "ed25519",
            }

            if key_id:
                metadata["key_id"] = key_id

            service._emit_audit_event(
                event_type=event_type,
                success=success,
                reason=reason,
                **metadata,
            )

        except Exception as e:
            logger.error(f"Failed to emit audit event {event_type}: {e}")


# ============================================================================
# Singleton
# ============================================================================

_signature_validator_instance: Optional[SignatureValidator] = None


def get_signature_validator(
    policy: Optional[SignaturePolicy] = None,
) -> SignatureValidator:
    """
    Get singleton signature validator instance.

    Args:
        policy: Optional signature policy (uses default if not specified)

    Returns:
        SignatureValidator instance
    """
    global _signature_validator_instance

    if _signature_validator_instance is None:
        _signature_validator_instance = SignatureValidator(policy=policy)

    return _signature_validator_instance
