from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import html
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
        self.service_token = os.getenv("OPENCLAW_BRAIN_SERVICE_TOKEN") or os.getenv("BRAIN_WORKER_SERVICE_TOKEN") or ""
        self.permit_secret = os.getenv("BRAIN_EXTERNAL_EXECUTOR_PERMIT_SECRET", "")
        self.controldeck_base_url = os.getenv("CONTROLDECK_BASE_URL", "http://localhost:3003").rstrip("/")
        self.execution_fallback_enabled = _bool_env(
            "OPENCLAW_EXECUTION_FALLBACK_ENABLED",
            os.getenv("BRAIN_RUNTIME_MODE", "local").strip().lower() == "local",
        )
        self.trust_exchange_url = _bool_env("OPENCLAW_TRUST_EXCHANGE_URL", False)
        self._access_token: str | None = None
        self._shutdown = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._recent_executions: dict[str, dict[str, Any]] = {}
        self.logger = logging.getLogger("openclaw_worker")

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
            return

        required_fields = ["executor_type", "skill_run_id", "issued_at", "expires_at", "signature"]
        for field in required_fields:
            if not permit.get(field):
                raise RuntimeError(f"execution_permit missing field: {field}")

        if str(permit.get("executor_type")).strip().lower() != "openclaw":
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

    async def _login(self, client: httpx.AsyncClient) -> None:
        if not self.login_password:
            raise RuntimeError("OPENCLAW_BRAIN_PASSWORD or BRAIN_ADMIN_PASSWORD must be set")
        response = await client.post(
            f"{self.brain_api_base}/api/auth/login",
            json={"email": self.login_email, "password": self.login_password},
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Auth response missing access_token")
        self._access_token = token

    async def _request_with_auth(self, client: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
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

    def _default_exchange_url(self) -> str:
        return f"{self.brain_api_base}/api/external-apps/openclaw/handoff/exchange"

    def _exchange_url(self, exchange_url: str | None = None) -> str:
        candidate = (exchange_url or "").strip()
        if self.trust_exchange_url and candidate.startswith(("http://", "https://")):
            return candidate
        return self._default_exchange_url()

    def _record_execution(self, execution: dict[str, Any]) -> dict[str, Any]:
        execution_id = str(
            execution.get("execution_id")
            or execution.get("task_id")
            or execution.get("skill_run_id")
            or f"exec_{hashlib.sha1(utc_now().encode('utf-8')).hexdigest()[:12]}"
        )
        stored = {**execution, "execution_id": execution_id, "updated_at": utc_now()}
        self._recent_executions[execution_id] = stored
        ordered = sorted(self._recent_executions, key=lambda key: self._recent_executions[key].get("updated_at", ""), reverse=True)
        for stale_key in ordered[100:]:
            self._recent_executions.pop(stale_key, None)
        return stored

    def list_recent_executions(self) -> list[dict[str, Any]]:
        return sorted(self._recent_executions.values(), key=lambda item: item.get("updated_at", ""), reverse=True)

    def get_execution(self, execution_ref: str) -> dict[str, Any] | None:
        if execution_ref in self._recent_executions:
            return self._recent_executions[execution_ref]
        for item in self._recent_executions.values():
            if execution_ref in {
                str(item.get("execution_id") or ""),
                str(item.get("task_id") or ""),
                str(item.get("skill_run_id") or ""),
            }:
                return item
        return None

    async def get_execution_context(self, execution_ref: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.request_timeout_seconds)) as client:
            response = await self._request_with_auth(
                client,
                "GET",
                f"{self.brain_api_base}/api/external-apps/openclaw/executions/{execution_ref}",
            )
            return response.json()

    async def exchange_handoff_context(self, token: str, exchange_url: str | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.request_timeout_seconds)) as client:
            response = await client.post(
                self._exchange_url(exchange_url),
                json={"token": token},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def submit_action_request(self, token: str, action: str, reason: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.request_timeout_seconds)) as client:
            response = await client.post(
                f"{self.brain_api_base}/api/external-apps/openclaw/actions",
                json={"token": token, "action": action, "reason": reason},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def perform_embedded_execution(self, request_body: dict[str, Any]) -> dict[str, Any]:
        request_input = request_body.get("input") if isinstance(request_body.get("input"), dict) else {}
        execution = self._record_execution(
            {
                "execution_id": request_body.get("task_id") or request_body.get("skill_run_id"),
                "task_id": request_body.get("task_id"),
                "skill_run_id": request_body.get("skill_run_id"),
                "executor_type": "openclaw",
                "intent": request_body.get("intent"),
                "prompt": request_body.get("prompt") or request_input.get("prompt") or "",
                "mode": request_body.get("mode"),
                "correlation_id": request_body.get("correlation_id"),
                "status": "completed",
                "summary": f"OpenClaw accepted execution for {request_body.get('intent') or 'worker_bridge_execute'}",
                "input": request_input,
            }
        )
        return {
            "status": "completed",
            "execution_id": execution["execution_id"],
            "task_id": execution.get("task_id"),
            "skill_run_id": execution.get("skill_run_id"),
            "summary": execution.get("summary"),
            "operational_path": f"/app/executions/{execution['execution_id']}",
            "processed_at": execution.get("updated_at"),
        }

    def _render_page(self, title: str, intro: str, body_html: str) -> str:
        return f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{html.escape(title)}</title>
    <style>
      :root {{ color-scheme: dark; --bg:#090f1a; --panel:#111b2e; --border:#2b3d61; --text:#e8eefc; --muted:#95a7c6; --accent:#8b5cf6; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; font-family:Inter,system-ui,sans-serif; background:radial-gradient(circle at top,#1d2540 0%,var(--bg) 55%); color:var(--text); }}
      a {{ color:#c4b5fd; text-decoration:none; }}
      .shell {{ max-width:1100px; margin:0 auto; padding:32px 20px 56px; }}
      .card {{ background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:18px; margin-bottom:18px; }}
      .grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }}
      .button {{ display:inline-flex; align-items:center; gap:8px; padding:11px 15px; border-radius:999px; background:#1b2846; border:1px solid var(--border); color:var(--text); }}
      .muted {{ color:var(--muted); }}
      .mono {{ font-family:ui-monospace, monospace; word-break:break-all; }}
      .pill {{ display:inline-block; margin:4px 6px 0 0; padding:6px 10px; border-radius:999px; background:rgba(139,92,246,.15); color:#ddd6fe; font-size:12px; }}
      .item {{ border:1px solid var(--border); border-radius:14px; padding:12px; background:rgba(14,24,42,.6); }}
      input, textarea, button {{ font:inherit; }}
    </style>
  </head>
  <body>
    <main class=\"shell\">
      <div style=\"display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:24px;flex-wrap:wrap;\">
        <div>
          <div class=\"muted\" style=\"text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:700;\">OpenClaw MissionCenter</div>
          <h1 style=\"margin:10px 0 8px;font-size:42px;line-height:1.05;\">{html.escape(title)}</h1>
          <p class=\"muted\">{html.escape(intro)}</p>
        </div>
        <div style=\"display:flex;gap:10px;flex-wrap:wrap;\">
          <a class=\"button\" href=\"{html.escape(self.controldeck_base_url)}/external-operations\">Return to ControlDeck</a>
          <a class=\"button\" href=\"/app\">Open MissionCenter</a>
        </div>
      </div>
      {body_html}
    </main>
  </body>
</html>
"""

    def _render_action_forms(self, available_actions: list[str], handoff_token: str | None) -> str:
        if not handoff_token:
            return ""
        labels = {
            "request_approval": "Request approval",
            "request_retry": "Request retry",
            "request_escalation": "Request escalation",
        }
        forms = []
        for action in available_actions:
            if action not in labels:
                continue
            forms.append(
                f"""
                <form method=\"post\" action=\"/handoff/openclaw/action\" class=\"item\">
                  <strong>{html.escape(labels[action])}</strong>
                  <input type=\"hidden\" name=\"token\" value=\"{html.escape(handoff_token)}\" />
                  <input type=\"hidden\" name=\"action\" value=\"{html.escape(action)}\" />
                  <input type=\"text\" name=\"reason\" required minlength=\"3\" maxlength=\"1000\" placeholder=\"Why should BRAiN review this request?\" style=\"margin-top:10px;width:100%;padding:10px 12px;border-radius:12px;border:1px solid var(--border);background:#0f1b30;color:var(--text);\" />
                  <button type=\"submit\" class=\"button\" style=\"margin-top:10px;cursor:pointer;\">{html.escape(labels[action])}</button>
                </form>
                """
            )
        if not forms:
            return ""
        return f"<section class=\"card\"><h2 style=\"margin:0 0 12px;\">Governed actions</h2><div class=\"grid\">{''.join(forms)}</div></section>"

    def render_home_page(self) -> str:
        rows = []
        for execution in self.list_recent_executions()[:12]:
            rows.append(
                f"<div class=\"item\"><strong>{html.escape(str(execution.get('execution_id') or 'unknown'))}</strong><div class=\"muted mono\">task: {html.escape(str(execution.get('task_id') or '-'))}</div><div class=\"muted\">{html.escape(str(execution.get('summary') or 'Execution record'))}</div></div>"
            )
        body = f"""
        <section class=\"card\"><strong>Bounded operational console.</strong><p class=\"muted\">Governance remains in BRAiN. Use ControlDeck for approvals, retry policy and supervisor review.</p></section>
        <section class=\"grid\">
          <div class=\"card\"><div class=\"muted\">Worker</div><div style=\"margin-top:8px;font-size:22px;font-weight:700;\">{html.escape(self.agent_id)}</div></div>
          <div class=\"card\"><div class=\"muted\">Recent executions</div><div style=\"margin-top:8px;font-size:22px;font-weight:700;\">{len(self._recent_executions)}</div></div>
          <div class=\"card\"><div class=\"muted\">Fallback mode</div><div style=\"margin-top:8px;font-size:22px;font-weight:700;\">{html.escape('enabled' if self.execution_fallback_enabled else 'fail-closed')}</div></div>
        </section>
        <section class=\"card\"><h2 style=\"margin:0 0 12px;\">Recent operational activity</h2><div class=\"grid\">{''.join(rows) or '<p class="muted">No executions recorded yet.</p>'}</div></section>
        """
        return self._render_page("Operational overview", "Operational visibility for OpenClaw bounded work under BRAiN governance.", body)

    def render_execution_page(self, execution_ref: str, execution_context: dict[str, Any] | None = None, handoff_token: str | None = None) -> str:
        if execution_context is not None:
            task = execution_context.get("task") if isinstance(execution_context.get("task"), dict) else {}
            skill_run = execution_context.get("skill_run") if isinstance(execution_context.get("skill_run"), dict) else None
            available_actions = execution_context.get("available_actions") if isinstance(execution_context.get("available_actions"), list) else []
            body = f"""
            <section class=\"grid\">
              <div class=\"card\"><div class=\"muted\">TaskLease</div><div style=\"margin-top:8px;font-size:20px;font-weight:700;\">{html.escape(str(task.get('task_id') or execution_ref))}</div></div>
              <div class=\"card\"><div class=\"muted\">Status</div><div style=\"margin-top:8px;font-size:20px;font-weight:700;\">{html.escape(str(task.get('status') or '-'))}</div></div>
              <div class=\"card\"><div class=\"muted\">SkillRun</div><div class=\"mono\" style=\"margin-top:8px;\">{html.escape(str((skill_run or {}).get('id') or task.get('skill_run_id') or '-'))}</div></div>
            </section>
            <section class=\"card\"><h2 style=\"margin:0 0 10px;\">Execution summary</h2><p>{html.escape(str((task.get('payload') or {}).get('prompt') or task.get('description') or task.get('name') or 'Execution'))}</p><div>{''.join(f'<span class="pill">{html.escape(str(action))}</span>' for action in available_actions)}</div></section>
            {self._render_action_forms([str(action) for action in available_actions], handoff_token)}
            <section class=\"card\"><h2 style=\"margin:0 0 10px;\">Canonical BRAiN context</h2><pre class=\"mono\">{html.escape(json.dumps(execution_context, indent=2, sort_keys=True, ensure_ascii=True))}</pre></section>
            """
            return self._render_page(f"Execution {execution_ref}", "Bounded operational view of an OpenClaw-managed execution record.", body)

        execution = self.get_execution(execution_ref)
        if execution is None:
            body = f"<section class=\"card\"><strong>Execution not materialized yet.</strong><p class=\"muted\">The ref <span class=\"mono\">{html.escape(execution_ref)}</span> has no local OpenClaw record yet.</p></section>"
        else:
            body = f"<section class=\"card\"><h2 style=\"margin:0 0 10px;\">Execution payload</h2><pre class=\"mono\">{html.escape(json.dumps(execution, indent=2, sort_keys=True, ensure_ascii=True))}</pre></section>"
        return self._render_page(f"Execution {execution_ref}", "Bounded operational view of an OpenClaw-managed execution record.", body)

    def render_entity_page(self, entity_type: str, entity_ref: str, handoff_token: str | None = None, permissions: list[str] | None = None) -> str:
        forms = self._render_action_forms(["request_escalation"] if (permissions and "request_escalation" in permissions) else [], handoff_token)
        body = f"""
        <section class=\"card\"><strong>Bounded operational context.</strong><p class=\"muted\">This {html.escape(entity_type)} surface is an OpenClaw-side operational view. Runtime truth and approvals remain in BRAiN.</p></section>
        <section class=\"card\"><h2 style=\"margin:0 0 10px;\">Resolved context</h2><div class=\"pill\">entity: {html.escape(entity_type)}</div><div class=\"pill\">ref: {html.escape(entity_ref)}</div></section>
        {forms}
        """
        return self._render_page(f"{entity_type.title()} {entity_ref}", "Operational drill-down reached through a governed BRAiN handoff.", body)

    def render_handoff_page(self, context: dict[str, Any]) -> str:
        target_type = str(context.get("target_type") or "execution")
        target_ref = str(context.get("target_ref") or "unknown")
        permissions = [str(permission) for permission in (context.get("permissions") or [])]
        if target_type == "execution" and isinstance(context.get("execution_context"), dict):
            return self.render_execution_page(target_ref, execution_context=context["execution_context"], handoff_token=str(context.get("handoff_token") or "") or None)
        return self.render_entity_page(target_type, target_ref, handoff_token=str(context.get("handoff_token") or "") or None, permissions=permissions)

    def render_handoff_error_page(self, message: str, *, status_code: int) -> str:
        body = f"<section class=\"card\"><strong>Handoff could not be completed.</strong><p class=\"muted\">{html.escape(message)} ({status_code})</p></section>"
        return self._render_page("Handoff failed", "OpenClaw rejected or could not validate the inbound handoff context.", body)

    def render_action_result_page(self, result: dict[str, Any]) -> str:
        body = f"""
        <section class=\"card\"><strong>Governed action request submitted.</strong><p class=\"muted\">{html.escape(str(result.get('message') or 'Action request recorded.'))}</p></section>
        <section class=\"grid\">
          <div class=\"card\"><div class=\"muted\">Request</div><div style=\"margin-top:8px;font-size:20px;font-weight:700;\">{html.escape(str(result.get('request_id') or '-'))}</div></div>
          <div class=\"card\"><div class=\"muted\">Action</div><div style=\"margin-top:8px;font-size:20px;font-weight:700;\">{html.escape(str(result.get('action') or '-'))}</div></div>
          <div class=\"card\"><div class=\"muted\">Target</div><div style=\"margin-top:8px;font-size:20px;font-weight:700;\">{html.escape(str(result.get('target_ref') or '-'))}</div></div>
        </section>
        """
        return self._render_page("Action requested", "BRAiN received the bounded OpenClaw action request and can now govern the next step.", body)

    async def _claim_task(self, client: httpx.AsyncClient) -> dict[str, Any] | None:
        params = [("task_types", task_type) for task_type in self.task_types]
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
        await self._request_with_auth(client, "POST", f"{self.brain_api_base}/api/tasks/{task_id}/start", json={"agent_id": self.agent_id})

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
        self._validate_execution_permit(task)
        payload = task.get("payload") or {}
        if not self.execution_fallback_enabled:
            result = {
                "worker": "openclaw",
                "agent_id": self.agent_id,
                "task_id": task.get("task_id"),
                "skill_run_id": payload.get("skill_run_id"),
                "status": "completed",
                "processed_at": utc_now(),
                "output": {
                    "text": f"OpenClaw executed task for prompt: {payload.get('prompt', '')}",
                    "mode": payload.get("mode", "plan"),
                    "worker_type": payload.get("worker_type", "openclaw"),
                },
            }
            self._record_execution({
                "execution_id": task.get("task_id"),
                "task_id": task.get("task_id"),
                "skill_run_id": payload.get("skill_run_id"),
                "status": result.get("status"),
                "summary": result["output"]["text"],
                "prompt": payload.get("prompt", ""),
                "mode": payload.get("mode", "plan"),
            })
            return result

        request_body = {
            "task_id": task.get("task_id"),
            "skill_run_id": payload.get("skill_run_id"),
            "intent": payload.get("intent", "worker_bridge_execute"),
            "prompt": payload.get("prompt", ""),
            "mode": payload.get("mode", "plan"),
            "correlation_id": task.get("correlation_id"),
            "input": payload,
        }
        return await self.perform_embedded_execution(request_body)

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
                    await self._start_task(client, task_id)
                    result = await self._execute_task(task)
                    await self._complete_task(client, task_id, result)
                except Exception as exc:
                    try:
                        if "task" in locals() and task and task.get("task_id"):
                            await self._fail_task(client, task["task_id"], f"openclaw worker failed: {exc}")
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
logging.basicConfig(level=os.getenv("OPENCLAW_LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="OpenClaw Worker Runtime", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "worker": "openclaw",
        "agent_id": worker.agent_id,
        "task_types": worker.task_types,
        "brain_api_base": worker.brain_api_base,
        "execution_fallback_enabled": worker.execution_fallback_enabled,
    }


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(worker.render_home_page())


@app.get("/app", response_class=HTMLResponse)
async def app_home() -> HTMLResponse:
    return HTMLResponse(worker.render_home_page())


@app.get("/app/executions/{execution_ref}", response_class=HTMLResponse)
async def execution_page(execution_ref: str) -> HTMLResponse:
    execution_context = None
    try:
        execution_context = await worker.get_execution_context(execution_ref)
    except Exception:
        execution_context = None
    return HTMLResponse(worker.render_execution_page(execution_ref, execution_context=execution_context))


@app.get("/app/issues/{issue_ref}", response_class=HTMLResponse)
async def issue_page(issue_ref: str) -> HTMLResponse:
    return HTMLResponse(worker.render_entity_page("issue", issue_ref))


@app.get("/app/projects/{project_ref}", response_class=HTMLResponse)
async def project_page(project_ref: str) -> HTMLResponse:
    return HTMLResponse(worker.render_entity_page("project", project_ref))


@app.get("/app/agents/{agent_ref}", response_class=HTMLResponse)
async def agent_page(agent_ref: str) -> HTMLResponse:
    return HTMLResponse(worker.render_entity_page("agent", agent_ref))


@app.get("/app/companies/{company_ref}", response_class=HTMLResponse)
async def company_page(company_ref: str) -> HTMLResponse:
    return HTMLResponse(worker.render_entity_page("company", company_ref))


@app.get("/handoff/openclaw", response_class=HTMLResponse)
async def openclaw_handoff_page(token: str, exchange_url: str | None = None) -> HTMLResponse:
    try:
        context = await worker.exchange_handoff_context(token, exchange_url=exchange_url)
        if str(context.get("target_type") or "") == "execution":
            try:
                execution_context = await worker.get_execution_context(str(context.get("target_ref") or ""))
            except Exception:
                execution_context = None
            if execution_context is not None:
                context = {**context, "execution_context": execution_context}
        context = {**context, "handoff_token": token}
        return HTMLResponse(worker.render_handoff_page(context))
    except httpx.HTTPStatusError as exc:
        message = f"BRAiN exchange rejected the handoff ({exc.response.status_code})."
        if exc.response.text:
            message = f"{message} {exc.response.text[:280]}"
        return HTMLResponse(worker.render_handoff_error_page(message, status_code=exc.response.status_code), status_code=exc.response.status_code)
    except Exception as exc:
        return HTMLResponse(worker.render_handoff_error_page(str(exc), status_code=502), status_code=502)


@app.post("/handoff/openclaw/action", response_class=HTMLResponse)
async def openclaw_handoff_action(request: Request) -> HTMLResponse:
    form = await request.form()
    token = str(form.get("token") or "").strip()
    action = str(form.get("action") or "").strip()
    reason = str(form.get("reason") or "").strip()
    if len(token) < 16 or len(reason) < 3 or not action:
        return HTMLResponse(worker.render_handoff_error_page("Invalid action request payload.", status_code=400), status_code=400)
    try:
        result = await worker.submit_action_request(token, action, reason)
        return HTMLResponse(worker.render_action_result_page(result))
    except httpx.HTTPStatusError as exc:
        message = f"BRAiN rejected the action request ({exc.response.status_code})."
        if exc.response.text:
            message = f"{message} {exc.response.text[:280]}"
        return HTMLResponse(worker.render_handoff_error_page(message, status_code=exc.response.status_code), status_code=exc.response.status_code)
    except Exception as exc:
        return HTMLResponse(worker.render_handoff_error_page(str(exc), status_code=502), status_code=502)


@app.post("/api/executions")
async def embedded_execution(request: Request) -> dict[str, Any]:
    return await worker.perform_embedded_execution(await request.json())
