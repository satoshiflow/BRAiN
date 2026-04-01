from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperclipWorker:
    def __init__(self) -> None:
        self.brain_api_base = os.getenv("BRAIN_API_BASE_URL", "http://backend:8000").rstrip("/")
        self.paperclip_base_url = os.getenv("PAPERCLIP_BASE_URL", "http://paperclip:8000").rstrip("/")
        self.paperclip_execution_endpoint = os.getenv("PAPERCLIP_EXECUTION_ENDPOINT", "/api/executions")
        self.paperclip_api_key = os.getenv("PAPERCLIP_API_KEY", "")
        self.agent_id = os.getenv("PAPERCLIP_AGENT_ID", "paperclip-worker")
        self.task_types = [
            t.strip() for t in os.getenv("PAPERCLIP_WORKER_TASK_TYPES", "paperclip_work").split(",") if t.strip()
        ]
        self.poll_interval_seconds = float(os.getenv("PAPERCLIP_POLL_INTERVAL_SECONDS", "2.0"))
        self.request_timeout_seconds = float(os.getenv("PAPERCLIP_REQUEST_TIMEOUT_SECONDS", "20"))
        self.login_email = os.getenv("PAPERCLIP_BRAIN_EMAIL", "admin@test.com")
        self.login_password = os.getenv("PAPERCLIP_BRAIN_PASSWORD", os.getenv("BRAIN_ADMIN_PASSWORD", ""))
        self.service_token = (
            os.getenv("PAPERCLIP_BRAIN_SERVICE_TOKEN")
            or os.getenv("BRAIN_WORKER_SERVICE_TOKEN")
            or ""
        )
        self.permit_secret = os.getenv("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET", "")
        self._access_token: str | None = None
        self._shutdown = asyncio.Event()
        self._task: asyncio.Task | None = None
        self.logger = logging.getLogger("paperclip_worker")

    @property
    def headers(self) -> dict[str, str]:
        if self.service_token:
            return {"Authorization": f"Bearer {self.service_token}"}
        if not self._access_token:
            return {}
        return {"Authorization": f"Bearer {self._access_token}"}

    def _validate_execution_permit(self, task: dict[str, Any]) -> None:
        payload = task.get("payload") or {}
        permit = payload.get("execution_permit")
        if not isinstance(permit, dict):
            raise RuntimeError("execution_permit required for paperclip executor")

        required_fields = [
            "executor_type",
            "skill_run_id",
            "issued_at",
            "expires_at",
            "signature",
        ]
        for field in required_fields:
            if not permit.get(field):
                raise RuntimeError(f"execution_permit missing field: {field}")

        if str(permit.get("executor_type")).strip().lower() != "paperclip":
            raise RuntimeError("execution_permit executor_type mismatch")

        if str(permit.get("skill_run_id")) != str(payload.get("skill_run_id")):
            raise RuntimeError("execution_permit skill_run_id mismatch")

        expires_at = str(permit.get("expires_at"))
        expires_ts = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_ts:
            raise RuntimeError("execution_permit expired")

        if not self.permit_secret:
            raise RuntimeError("permit secret not configured")

        signed_payload = {
            "executor_type": permit.get("executor_type"),
            "skill_run_id": permit.get("skill_run_id"),
            "allowed_actions": permit.get("allowed_actions", []),
            "allowed_connectors": permit.get("allowed_connectors", []),
            "issued_at": permit.get("issued_at"),
            "expires_at": permit.get("expires_at"),
            "task_id": permit.get("task_id"),
            "correlation_id": permit.get("correlation_id"),
        }
        message = json.dumps(signed_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(self.permit_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, str(permit.get("signature"))):
            raise RuntimeError("execution_permit signature invalid")

    @property
    def paperclip_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.paperclip_api_key:
            headers["Authorization"] = f"Bearer {self.paperclip_api_key}"
        return headers

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not self.login_password:
            raise RuntimeError("PAPERCLIP_BRAIN_PASSWORD or BRAIN_ADMIN_PASSWORD must be set")
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
        if self.service_token:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response

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

    async def _execute_task(self, client: httpx.AsyncClient, task: dict[str, Any]) -> dict[str, Any]:
        self._validate_execution_permit(task)
        payload = task.get("payload") or {}
        request_body = {
            "task_id": task.get("task_id"),
            "skill_run_id": payload.get("skill_run_id"),
            "executor_type": "paperclip",
            "intent": payload.get("intent", "worker_bridge_execute"),
            "prompt": payload.get("prompt", ""),
            "mode": payload.get("mode", "plan"),
            "input": payload,
            "correlation_id": task.get("correlation_id"),
        }

        endpoint = f"{self.paperclip_base_url}{self.paperclip_execution_endpoint}"
        try:
            response = await client.post(endpoint, json=request_body, headers=self.paperclip_headers)
            if response.status_code < 400:
                external_data = response.json()
            else:
                external_data = {
                    "status": "fallback",
                    "message": f"Paperclip endpoint returned {response.status_code}",
                }
        except Exception:
            external_data = {
                "status": "fallback",
                "message": "Paperclip endpoint unavailable, returning local fallback result",
            }

        return {
            "worker": "paperclip",
            "agent_id": self.agent_id,
            "task_id": task.get("task_id"),
            "skill_run_id": payload.get("skill_run_id"),
            "status": "completed",
            "processed_at": utc_now(),
            "external_refs": {
                "paperclip_endpoint": endpoint,
            },
            "output": {
                "text": f"Paperclip executed task for prompt: {payload.get('prompt', '')}",
                "mode": payload.get("mode", "plan"),
                "worker_type": payload.get("worker_type", "paperclip"),
                "external_result": external_data,
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
                    result = await self._execute_task(client, task)
                    await self._complete_task(client, task_id, result)
                    self.logger.info("Completed task %s", task_id)
                except Exception as exc:
                    try:
                        if "task" in locals() and task and task.get("task_id"):
                            await self._fail_task(client, task["task_id"], f"paperclip worker failed: {exc}")
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


worker = PaperclipWorker()
app = FastAPI(title="Paperclip Worker Runtime", version="0.1.0")
logging.basicConfig(level=os.getenv("PAPERCLIP_LOG_LEVEL", "INFO"))


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
        "worker": "paperclip",
        "agent_id": worker.agent_id,
        "task_types": worker.task_types,
        "brain_api_base": worker.brain_api_base,
        "paperclip_base_url": worker.paperclip_base_url,
    }
