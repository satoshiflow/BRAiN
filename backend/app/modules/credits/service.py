from datetime import datetime, timezone
from .schemas import CreditsHealth, CreditsInfo

MODULE_NAME = "brain.credits"
MODULE_VERSION = "1.0.0"

async def get_health() -> CreditsHealth:
    return CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

async def get_info() -> CreditsInfo:
    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
