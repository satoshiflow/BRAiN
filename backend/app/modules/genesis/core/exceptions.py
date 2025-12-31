"""
Genesis Core Exceptions

Custom exceptions for Genesis operations.
"""


class GenesisError(Exception):
    """Base exception for Genesis errors."""

    pass


class EthicsViolationError(GenesisError):
    """Raised when ethics validation fails."""

    pass


class BlueprintNotFoundError(GenesisError):
    """Raised when blueprint is not found."""

    pass


class InvalidTraitError(GenesisError):
    """Raised when trait validation fails."""

    pass


class AgentNotFoundError(GenesisError):
    """Raised when agent is not found."""

    pass


class MutationBlockedError(GenesisError):
    """Raised when mutation is blocked by ethics."""

    pass
