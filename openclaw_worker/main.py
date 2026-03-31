from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpenClawWorker:
    def __init__(self) -> None:
        self.brain_api_base = os.getenv("BRAIN_API_BASE_URL", "http://backend:8000").rstrip("/")
        self.agent_id = os.getenv("OPENCLAW_AGENT_ID", "openclaw-worker")
        self.task_types = [
            t.strip() for t in os.getenv("OPENCLAW_WORKER_TASK_TYPES", "openclaw_work").split(",") if t.strip()
        ]
        self.poll_interval_seconds = float(os.getenv("OPENCLAW_POLL_INTERVAL_SECONDS", "2.0"))
        self.request_timeout_seconds = float(os.getenv("OPENCLAW_REQUEST_TIMEOUT_SECONDS", "20"))
        self.login_email = os.getenv("OPENCLAW_BRAIN_EMAIL", "admin@test.com")
        self.login_password = os.getenv("OPENCLAW_BRAIN_PASSWORD", os.getenv("BRAIN_ADMIN_PASSWORD", ""))
        self._access_token: str | None = None
        self._shutdown = asyncio.Event()
        self._task: asyncio.Task | None = None
        self.logger = logging.getLogger("openclaw_worker")

    @property
    def headers(self) -> dict[str, str]:
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not self.login_password:
            raise RuntimeError("OPENCLAW_BRAIN_PASSWORD or BRAIN_ADMIN_PASSWORD must be set")
        payload = {"email": self.login_email, "password": self.login_password}
        response = await client.post(f"{self.brain_api_base}/api/auth/login", json=payload)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Auth response missing access_token")
        self._access_token = token
        self.logger.info("Authenticated against BRAiN as %s", self.login_email)

    async def _request_with_auth(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        if self._access_token is None:
            await self._login(client)
        response = await client.request(method, url, headers=self.headers, **kwargs)
        if response.status_code == 401:
            await self._login(client)
            response = await client.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response

    async def _claim_task(self, client: httpx.AsyncClient) -> dict[str, Any] | None:
        params: list[tuple[str, str]] = []
        for task_type in self.task_types:
            params.append(("task_types", task_type))

        response = await self._request_with_auth(
            client,
            "POST",
            f"{self.brain_api_base}/api/tasks/claim",
            params=params,
            json={"agent_id": self.agent_id},
        )
        body = response.json()
        if not body.get("success"):
            return None
        return body.get("task")

    async def _start_task(self, client: httpx.AsyncClient, task_id: str) -> None:
        await self._request_with_auth(
            client,
            "POST",
            f"{self.brain_api_base}/api/tasks/{task_id}/start",
            json={"agent_id": self.agent_id},
        )

    async def _complete_task(self, client: httpx.AsyncClient, task_id: str, result: dict[str, Any]) -> None:
        await self._request_with_auth(
            client,
            "POST",
            f"{self.brain_api_base}/api/tasks/{task_id}/complete",
            json={"agent_id": self.agent_id, "result": result},
        )

    async def _fail_task(self, client: httpx.AsyncClient, task_id: str, message: str) -> None:
        await self._request_with_auth(
            client,
            "POST",
            f"{self.brain_api_base}/api/tasks/{task_id}/fail",
            json={"agent_id": self.agent_id, "error_message": message, "retry": False},
        )

    async def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = task.get("payload") or {}
        prompt = payload.get("prompt", "")
        return {
            "worker": "openclaw",
            "agent_id": self.agent_id,
            "task_id": task.get("task_id"),
            "skill_run_id": payload.get("skill_run_id"),
            "status": "completed",
            "processed_at": utc_now(),
            "output": {
                "text": f"OpenClaw executed task for prompt: {prompt}",
                "mode": payload.get("mode", "plan"),
                "worker_type": payload.get("worker_type", "openclaw"),
            },
        }

    async def run(self) -> None:
        timeout = httpx.Timeout(self.request_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            while not self._shutdown.is_set():
                try:
                    task = await self._claim_task(client)
                    if task is None:
                        await asyncio.sleep(self.poll_interval_seconds)
                        continue

                    task_id = task["task_id"]
                    self.logger.info("Claimed task %s", task_id)
                    await self._start_task(client, task_id)
                    result = await self._execute_task(task)
                    await self._complete_task(client, task_id, result)
                    self.logger.info("Completed task %s", task_id)
                except Exception as exc:
                    try:
                        if "task" in locals() and task and task.get("task_id"):
                            await self._fail_task(client, task["task_id"], f"openclaw worker failed: {exc}")
                            self.logger.exception("Failed task %s", task["task_id"])
                    except Exception:
                        pass
                    await asyncio.sleep(self.poll_interval_seconds)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._task is not None:
            await self._task


worker = OpenClawWorker()
app = FastAPI(title="OpenClaw Worker Runtime", version="0.1.0")
logging.basicConfig(level=os.getenv("OPENCLAW_LOG_LEVEL", "INFO"))


@app.on_event("startup")
async def startup_event() -> None:
    await worker.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await worker.stop()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "worker": "openclaw",
        "agent_id": worker.agent_id,
        "task_types": worker.task_types,
        "brain_api_base": worker.brain_api_base,
    }
