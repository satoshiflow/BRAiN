import json
from typing import Any, Dict, Optional

import redis


class EventBus:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    def publish(self, stream: str, event: Dict[str, Any]) -> str:
        data = json.dumps(event)
        return self.client.xadd(stream, {"data": data})

    def publish_mission(self, event: Dict[str, Any]) -> str:
        return self.publish("brain.events.missions", event)

    def publish_domain(self, domain: str, event: Dict[str, Any]) -> str:
        key = f"brain.events.{domain}"
        return self.publish(key, event)