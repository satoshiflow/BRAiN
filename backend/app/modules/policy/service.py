from datetime import datetime, timezone
from .schemas import PolicyHealth, PolicyInfo

MODULE_NAME = "brain.policy"
MODULE_VERSION = "1.0.0"

async def get_health() -> PolicyHealth:
    return PolicyHealth(status="ok", timestamp=datetime.now(timezone.utc))

async def get_info() -> PolicyInfo:
    return PolicyInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
