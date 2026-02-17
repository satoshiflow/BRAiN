"""
IR Governance Configuration for WebGenesis (Sprint 10)

Environment-based feature flags for IR opt-in integration.
"""

from enum import Enum
from pydantic import BaseModel, Field
import os


class IRMode(str, Enum):
    """IR enforcement mode."""
    OFF = "off"  # IR disabled, legacy behavior
    OPT_IN = "opt_in"  # IR optional, accept both IR and legacy requests
    REQUIRED = "required"  # IR mandatory, block legacy requests


class IRWebGenesisConfig(BaseModel):
    """
    Configuration for IR governance in WebGenesis pipeline.

    Environment Variables:
    - WEBGENESIS_IR_MODE: off|opt_in|required (default: opt_in)
    - WEBGENESIS_REQUIRE_APPROVAL_TIER: Minimum tier requiring approval (default: 2)
    - WEBGENESIS_MAX_BUDGET: Maximum budget in cents (optional)
    - WEBGENESIS_DRY_RUN_DEFAULT: Default dry_run value (default: true)
    """

    ir_mode: IRMode = Field(default=IRMode.OPT_IN)
    require_approval_tier: int = Field(default=2, ge=0, le=3)
    max_budget_cents: int | None = Field(default=None)
    dry_run_default: bool = Field(default=True)

    # Internal flags
    emit_audit_events: bool = Field(default=True)
    strict_diff_audit: bool = Field(default=True)

    @classmethod
    def from_env(cls) -> "IRWebGenesisConfig":
        """Load configuration from environment variables."""
        return cls(
            ir_mode=IRMode(os.getenv("WEBGENESIS_IR_MODE", "opt_in")),
            require_approval_tier=int(os.getenv("WEBGENESIS_REQUIRE_APPROVAL_TIER", "2")),
            max_budget_cents=int(os.getenv("WEBGENESIS_MAX_BUDGET")) if os.getenv("WEBGENESIS_MAX_BUDGET") else None,
            dry_run_default=os.getenv("WEBGENESIS_DRY_RUN_DEFAULT", "true").lower() == "true",
        )

    def is_ir_enabled(self) -> bool:
        """Check if IR is enabled (opt_in or required)."""
        return self.ir_mode in [IRMode.OPT_IN, IRMode.REQUIRED]

    def is_ir_required(self) -> bool:
        """Check if IR is mandatory (legacy requests should be rejected)."""
        return self.ir_mode == IRMode.REQUIRED


# Singleton instance
_config: IRWebGenesisConfig | None = None


def get_ir_config() -> IRWebGenesisConfig:
    """Get IR configuration singleton."""
    global _config
    if _config is None:
        _config = IRWebGenesisConfig.from_env()
    return _config


def reload_ir_config():
    """Reload configuration from environment (for testing)."""
    global _config
    _config = IRWebGenesisConfig.from_env()
