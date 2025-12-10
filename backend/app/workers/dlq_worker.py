import json
import logging
from typing import Dict, Any

import redis

logger = logging.getLogger(__name__)


class DLQWorker:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client
        self.dead_letter_stream = "brain.events.dead_letter"

    def process_with_dlq(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler,
        max_retries: int = 3,
    ):
        """
        Liest Nachrichten aus stream, ruft handler(event_dict) auf,
        verschiebt bei Fehlern nach max_retries in DLQ.
        """
        self._ensure_group(stream, group)

        resp = self.client.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=10,
            block=1000,
        )
        for s_name, messages in resp:
            for msg_id, fields in messages:
                try:
                    payload = json.loads(fields[b"data"].decode("utf-8"))
                    handler(payload)
                    self.client.xack(stream, group, msg_id)
                except Exception as exc:
                    logger.exception("Error handling message %s", msg_id)
                    retries = int(payload.get("_retries", 0)) + 1
                    payload["_retries"] = retries
                    if retries >= max_retries:
                        logger.warning("Moving message %s to DLQ", msg_id)
                        self.client.xadd(
                            self.dead_letter_stream,
                            {"data": json.dumps(payload)},
                        )
                        self.client.xack(stream, group, msg_id)
                    else:
                        # re-queue
                        self.client.xadd(stream, {"data": json.dumps(payload)})
                        self.client.xack(stream, group, msg_id)

    def _ensure_group(self, stream: str, group: str):
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise