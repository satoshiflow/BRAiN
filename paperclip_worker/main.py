from __future__ import annotations

import asyncio
import hashlib
import html
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class PaperclipWorker:
    def __init__(self) -> None:
        self.brain_api_base = os.getenv("BRAIN_API_BASE_URL", "http://backend:8000").rstrip("/")
        self.paperclip_base_url = os.getenv("PAPERCLIP_BASE_URL", "http://paperclip:8000").rstrip("/")
        self.controldeck_base_url = os.getenv("CONTROLDECK_BASE_URL", "http://localhost:3003").rstrip("/")
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
        self.execution_fallback_enabled = _bool_env(
            "PAPERCLIP_EXECUTION_FALLBACK_ENABLED",
            os.getenv("BRAIN_RUNTIME_MODE", "local").strip().lower() == "local",
        )
        self.trust_exchange_url = _bool_env("PAPERCLIP_TRUST_EXCHANGE_URL", False)
        self._access_token: str | None = None
        self._shutdown = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._recent_executions: dict[str, dict[str, Any]] = {}
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

    def _default_exchange_url(self) -> str:
        return f"{self.brain_api_base}/api/external-apps/paperclip/handoff/exchange"

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
        stored = {
            **execution,
            "execution_id": execution_id,
            "updated_at": utc_now(),
        }
        self._recent_executions[execution_id] = stored
        ordered_keys = sorted(
            self._recent_executions,
            key=lambda key: self._recent_executions[key].get("updated_at", ""),
            reverse=True,
        )
        for stale_key in ordered_keys[100:]:
            self._recent_executions.pop(stale_key, None)
        return stored

    async def get_execution_context(self, execution_ref: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.request_timeout_seconds)) as client:
            response = await self._request_with_auth(
                client,
                "GET",
                f"{self.brain_api_base}/api/external-apps/paperclip/executions/{execution_ref}",
            )
            return response.json()

    def list_recent_executions(self) -> list[dict[str, Any]]:
        return sorted(
            self._recent_executions.values(),
            key=lambda item: item.get("updated_at", ""),
            reverse=True,
        )

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

    def _render_page(self, title: str, intro: str, body_html: str) -> str:
        safe_title = html.escape(title)
        safe_intro = html.escape(intro)
        return f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{safe_title}</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #07111f;
        --panel: rgba(9, 21, 39, 0.92);
        --panel-soft: rgba(14, 28, 52, 0.75);
        --border: rgba(120, 166, 255, 0.2);
        --text: #e6eefc;
        --muted: #8ea4c7;
        --accent: #7dd3fc;
        --accent-strong: #38bdf8;
        --banner: rgba(14, 65, 90, 0.55);
        --ok: #86efac;
        --warn: #fbbf24;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        background: radial-gradient(circle at top, #0f2748 0%, var(--bg) 45%, #040914 100%);
        color: var(--text);
      }}
      a {{ color: var(--accent); text-decoration: none; }}
      a:hover {{ color: var(--accent-strong); }}
      .shell {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
      .masthead {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 24px; }}
      .eyebrow {{ color: var(--accent); text-transform: uppercase; letter-spacing: 0.12em; font-size: 12px; font-weight: 700; }}
      h1 {{ margin: 10px 0 8px; font-size: clamp(30px, 6vw, 46px); line-height: 1.05; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
      .actions {{ display: flex; flex-wrap: wrap; gap: 12px; }}
      .button {{
        display: inline-flex; align-items: center; gap: 8px; padding: 12px 16px; border-radius: 999px;
        border: 1px solid var(--border); background: rgba(13, 27, 47, 0.85); color: var(--text); font-weight: 600;
      }}
      .banner {{ margin-bottom: 22px; padding: 16px 18px; border-radius: 18px; border: 1px solid var(--border); background: var(--banner); }}
      .grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-bottom: 22px; }}
      .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 22px; padding: 18px; box-shadow: 0 18px 48px rgba(0, 0, 0, 0.2); }}
      .card h2, .card h3 {{ margin: 0 0 10px; font-size: 18px; }}
      .metric {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
      .metric-value {{ margin-top: 8px; font-size: 22px; font-weight: 700; color: var(--text); }}
      .list {{ display: grid; gap: 12px; }}
      .item {{ border: 1px solid var(--border); border-radius: 16px; padding: 14px; background: var(--panel-soft); }}
      .item strong {{ display: block; margin-bottom: 4px; }}
      .pill-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
      .pill {{ padding: 6px 10px; border-radius: 999px; font-size: 12px; background: rgba(56, 189, 248, 0.16); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.2); }}
      .mono {{ font-family: "SFMono-Regular", ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; color: #c8d5eb; word-break: break-all; }}
      .status-ok {{ color: var(--ok); }}
      .status-warn {{ color: var(--warn); }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ padding: 12px 8px; border-bottom: 1px solid rgba(120, 166, 255, 0.12); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
      @media (max-width: 720px) {{
        .masthead {{ flex-direction: column; }}
        .actions {{ width: 100%; }}
      }}
    </style>
  </head>
  <body>
    <main class=\"shell\">
      <section class=\"masthead\">
        <div>
          <div class=\"eyebrow\">Paperclip MissionCenter</div>
          <h1>{safe_title}</h1>
          <p>{safe_intro}</p>
        </div>
        <div class=\"actions\">
          <a class=\"button\" href=\"{html.escape(self.controldeck_base_url)}/external-operations\">Return to ControlDeck</a>
          <a class=\"button\" href=\"/app\">Open MissionCenter</a>
        </div>
      </section>
      {body_html}
    </main>
  </body>
</html>
"""

    def render_home_page(self) -> str:
        recent_rows = []
        for execution in self.list_recent_executions()[:12]:
            execution_id = html.escape(str(execution.get("execution_id") or "unknown"))
            task_id = html.escape(str(execution.get("task_id") or "-"))
            skill_run_id = html.escape(str(execution.get("skill_run_id") or "-"))
            updated_at = html.escape(str(execution.get("updated_at") or "-"))
            status = html.escape(str(execution.get("status") or "completed"))
            summary = html.escape(str(execution.get("summary") or execution.get("prompt") or "Execution record"))
            recent_rows.append(
                f"<tr><td><a href=\"/app/executions/{execution_id}\">{execution_id}</a></td><td>{task_id}</td><td>{skill_run_id}</td><td>{status}</td><td>{updated_at}</td><td>{summary}</td></tr>"
            )
        recent_table = "".join(recent_rows) or "<tr><td colspan=\"6\">No executions recorded yet.</td></tr>"

        body = f"""
        <section class=\"banner\">
          <strong>Bounded operational console.</strong>
          <p>Governance remains in BRAiN. Use ControlDeck for policy, overrides and runtime diagnostics.</p>
        </section>
        <section class=\"grid\">
          <article class=\"card\"><div class=\"metric\">Worker</div><div class=\"metric-value\">{html.escape(self.agent_id)}</div></article>
          <article class=\"card\"><div class=\"metric\">Recent executions</div><div class=\"metric-value\">{len(self._recent_executions)}</div></article>
          <article class=\"card\"><div class=\"metric\">Fallback mode</div><div class=\"metric-value\">{html.escape('enabled' if self.execution_fallback_enabled else 'fail-closed')}</div></article>
        </section>
        <section class=\"card\">
          <h2>Recent operational activity</h2>
          <table>
            <thead>
              <tr><th>Execution</th><th>Task</th><th>SkillRun</th><th>Status</th><th>Updated</th><th>Summary</th></tr>
            </thead>
            <tbody>{recent_table}</tbody>
          </table>
        </section>
        """
        return self._render_page(
            title="Operational overview",
            intro="Operational visibility for bounded external work, with governance delegated back to BRAiN.",
            body_html=body,
        )

    def _render_execution_section(self, execution_ref: str) -> str:
        execution = self.get_execution(execution_ref)
        safe_ref = html.escape(execution_ref)
        if execution is None:
            return (
                f"<section class=\"banner\"><strong>Execution not materialized yet.</strong>"
                f"<p>The execution ref <span class=\"mono\">{safe_ref}</span> has no local Paperclip record yet. "
                "ControlDeck still owns the authoritative SkillRun/TaskLease timeline.</p></section>"
            )

        prompt = html.escape(str(execution.get("prompt") or execution.get("summary") or "Execution"))
        payload_pretty = html.escape(json.dumps(execution, indent=2, sort_keys=True, ensure_ascii=True))
        return f"""
        <section class=\"grid\">
          <article class=\"card\"><div class=\"metric\">Execution</div><div class=\"metric-value\">{html.escape(str(execution.get('execution_id')))}</div></article>
          <article class=\"card\"><div class=\"metric\">TaskLease</div><div class=\"metric-value\">{html.escape(str(execution.get('task_id') or '-'))}</div></article>
          <article class=\"card\"><div class=\"metric\">SkillRun</div><div class=\"metric-value\">{html.escape(str(execution.get('skill_run_id') or '-'))}</div></article>
        </section>
        <section class=\"card\"><h2>Execution summary</h2><p>{prompt}</p><div class=\"pill-row\"><span class=\"pill\">status: {html.escape(str(execution.get('status') or 'completed'))}</span><span class=\"pill\">mode: {html.escape(str(execution.get('mode') or '-'))}</span><span class=\"pill\">executor: paperclip</span></div></section>
        <section class=\"card\"><h2>Execution payload</h2><pre class=\"mono\">{payload_pretty}</pre></section>
        """

    def _render_entity_section(self, entity_type: str, entity_ref: str, handoff_token: str | None = None, permissions: list[str] | None = None) -> str:
        safe_entity_type = html.escape(entity_type)
        safe_entity_ref = html.escape(entity_ref)
        action_section = ""
        if handoff_token and permissions and "request_escalation" in permissions:
            action_section = f"""
            <section class=\"card\"><h2>Governed actions</h2><div class=\"list\"><form method=\"post\" action=\"/handoff/paperclip/action\" class=\"item\"><strong>Request escalation</strong><input type=\"hidden\" name=\"token\" value=\"{html.escape(handoff_token)}\" /><input type=\"hidden\" name=\"action\" value=\"request_escalation\" /><input type=\"text\" name=\"reason\" required minlength=\"3\" maxlength=\"1000\" placeholder=\"Why should BRAiN review this request?\" style=\"margin-top:10px;width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(120,166,255,0.2);background:rgba(13,27,47,0.85);color:#e6eefc;\" /><button type=\"submit\" class=\"button\" style=\"margin-top:10px;cursor:pointer;\">Request escalation</button></form></div></section>
            """
        return f"""
        <section class=\"banner\"><strong>Bounded operational context.</strong><p>This {safe_entity_type} surface is a Paperclip-side operational view. Runtime truth and approvals remain in BRAiN.</p></section>
        <section class=\"card\"><h2>{safe_entity_type.title()} context</h2><p>Resolved ref: <span class=\"mono\">{safe_entity_ref}</span></p><div class=\"pill-row\"><span class=\"pill\">entity: {safe_entity_type}</span><span class=\"pill\">ref: {safe_entity_ref}</span></div></section>
        {action_section}
        """

    def _render_canonical_execution_section(self, context: dict[str, Any], handoff_token: str | None = None) -> str:
        task = context.get("task") if isinstance(context.get("task"), dict) else {}
        skill_run = context.get("skill_run") if isinstance(context.get("skill_run"), dict) else None
        task_payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
        task_config = task.get("config") if isinstance(task.get("config"), dict) else {}
        runtime_decision = (
            ((skill_run or {}).get("provider_selection_snapshot") or {}).get("runtime_decision")
            if isinstance((skill_run or {}).get("provider_selection_snapshot"), dict)
            else {}
        ) or {}

        prompt = html.escape(str(task_payload.get("prompt") or task.get("description") or task.get("name") or "Execution"))
        required_worker = html.escape(str(task_config.get("required_worker") or "paperclip"))
        task_id = html.escape(str(task.get("task_id") or context.get("target_ref") or "-"))
        task_status = html.escape(str(task.get("status") or "unknown"))
        task_updated_at = html.escape(str(task.get("updated_at") or "-"))
        correlation_id = html.escape(str(task.get("correlation_id") or "-"))
        decision_id = html.escape(str(runtime_decision.get("decision_id") or "-"))
        selected_route = html.escape(str(runtime_decision.get("selected_route") or "-"))
        selected_worker = html.escape(str(runtime_decision.get("selected_worker") or required_worker))
        skill_run_id = html.escape(str((skill_run or {}).get("id") or task.get("skill_run_id") or "-"))
        skill_run_state = html.escape(str((skill_run or {}).get("state") or "-"))
        failure_reason = html.escape(str((skill_run or {}).get("failure_reason_sanitized") or task.get("error_message") or "-"))
        payload_pretty = html.escape(json.dumps(context, indent=2, sort_keys=True, ensure_ascii=True))
        available_actions = context.get("available_actions") if isinstance(context.get("available_actions"), list) else []
        labels = {
            "request_approval": "Request approval",
            "request_retry": "Request retry",
            "request_escalation": "Request escalation",
        }
        forms = []
        if handoff_token:
            safe_token = html.escape(handoff_token)
            for action in available_actions:
                if not isinstance(action, str) or action not in labels:
                    continue
                forms.append(
                    f"""
                    <form method=\"post\" action=\"/handoff/paperclip/action\" class=\"item\">
                      <strong>{html.escape(labels[action])}</strong>
                      <input type=\"hidden\" name=\"token\" value=\"{safe_token}\" />
                      <input type=\"hidden\" name=\"action\" value=\"{html.escape(action)}\" />
                      <input type=\"text\" name=\"reason\" required minlength=\"3\" maxlength=\"1000\" placeholder=\"Why should BRAiN review this request?\" style=\"margin-top:10px;width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(120,166,255,0.2);background:rgba(13,27,47,0.85);color:#e6eefc;\" />
                      <button type=\"submit\" class=\"button\" style=\"margin-top:10px;cursor:pointer;\">{html.escape(labels[action])}</button>
                    </form>
                    """
                )
        action_section = (
            f"<section class=\"card\"><h2>Governed actions</h2><div class=\"list\">{''.join(forms)}</div></section>"
            if forms
            else ""
        )

        return f"""
        <section class=\"grid\">
          <article class=\"card\"><div class=\"metric\">TaskLease</div><div class=\"metric-value\">{task_id}</div></article>
          <article class=\"card\"><div class=\"metric\">Task status</div><div class=\"metric-value\">{task_status}</div></article>
          <article class=\"card\"><div class=\"metric\">SkillRun</div><div class=\"metric-value\">{skill_run_id}</div></article>
          <article class=\"card\"><div class=\"metric\">SkillRun state</div><div class=\"metric-value\">{skill_run_state}</div></article>
        </section>
        <section class=\"card\"><h2>Execution summary</h2><p>{prompt}</p><div class=\"pill-row\"><span class=\"pill\">required worker: {required_worker}</span><span class=\"pill\">selected worker: {selected_worker}</span><span class=\"pill\">route: {selected_route}</span></div></section>
        <section class=\"grid\">
          <div class=\"item\"><strong>Decision ID</strong><span class=\"mono\">{decision_id}</span></div>
          <div class=\"item\"><strong>Correlation ID</strong><span class=\"mono\">{correlation_id}</span></div>
          <div class=\"item\"><strong>Updated</strong><span class=\"mono\">{task_updated_at}</span></div>
          <div class=\"item\"><strong>Failure reason</strong><span class=\"mono\">{failure_reason}</span></div>
        </section>
        {action_section}
        <section class=\"card\"><h2>Canonical BRAiN context</h2><pre class=\"mono\">{payload_pretty}</pre></section>
        """

    def render_execution_page(
        self,
        execution_ref: str,
        execution_context: dict[str, Any] | None = None,
        handoff_token: str | None = None,
    ) -> str:
        return self._render_page(
            title=f"Execution {execution_ref}",
            intro="Bounded operational view of a Paperclip-managed execution record.",
            body_html=(
                self._render_canonical_execution_section(execution_context, handoff_token=handoff_token)
                if execution_context is not None
                else self._render_execution_section(execution_ref)
            ),
        )

    def render_entity_page(self, entity_type: str, entity_ref: str, handoff_token: str | None = None, permissions: list[str] | None = None) -> str:
        return self._render_page(
            title=f"{entity_type.title()} {entity_ref}",
            intro="Operational drill-down reached through a governed BRAiN handoff.",
            body_html=self._render_entity_section(entity_type, entity_ref, handoff_token=handoff_token, permissions=permissions),
        )

    def render_handoff_page(self, context: dict[str, Any]) -> str:
        target_type = str(context.get("target_type") or "execution")
        target_ref = str(context.get("target_ref") or "unknown")
        permissions = context.get("permissions") or []
        permission_pills = "".join(
            f"<span class=\"pill\">{html.escape(str(permission))}</span>" for permission in permissions
        ) or "<span class=\"pill\">view</span>"
        governance_banner = html.escape(
            str(context.get("governance_banner") or "Governed by BRAiN. Sensitive actions require BRAiN approval.")
        )
        resolved_path = html.escape(str(context.get("suggested_path") or "/app"))
        detail_rows = []
        for label, value in (
            ("Principal", context.get("principal_id") or "unknown"),
            ("Tenant", context.get("tenant_id") or "-"),
            ("Mission", context.get("mission_id") or "-"),
            ("SkillRun", context.get("skill_run_id") or "-"),
            ("Decision", context.get("decision_id") or "-"),
            ("Correlation", context.get("correlation_id") or "-"),
            ("Expiry", context.get("expires_at") or "-"),
            ("JTI", context.get("jti") or "-"),
        ):
            detail_rows.append(
                f"<div class=\"item\"><strong>{html.escape(label)}</strong><span class=\"mono\">{html.escape(str(value))}</span></div>"
            )
        if target_type == "execution":
            if isinstance(context.get("execution_context"), dict):
                operational_block = self._render_canonical_execution_section(
                    context["execution_context"],
                    handoff_token=str(context.get("handoff_token") or "") or None,
                )
            else:
                operational_block = self._render_execution_section(target_ref)
        else:
            operational_block = self._render_entity_section(
                target_type,
                target_ref,
                handoff_token=str(context.get("handoff_token") or "") or None,
                permissions=[str(permission) for permission in permissions],
            )
        body = f"""
        <section class=\"banner\"><strong>{governance_banner}</strong><p>Context handoff succeeded. This surface carries context, not authority.</p></section>
        <section class=\"grid\">
          <article class=\"card\"><div class=\"metric\">Target type</div><div class=\"metric-value\">{html.escape(target_type)}</div></article>
          <article class=\"card\"><div class=\"metric\">Target ref</div><div class=\"metric-value\">{html.escape(target_ref)}</div></article>
          <article class=\"card\"><div class=\"metric\">Resolved path</div><div class=\"metric-value\"><a href=\"{resolved_path}\">{resolved_path}</a></div></article>
        </section>
        <section class=\"card\"><h2>Bounded permissions</h2><div class=\"pill-row\">{permission_pills}</div></section>
        <section class=\"grid\">{''.join(detail_rows)}</section>
        {operational_block}
        """
        return self._render_page(
            title=f"{target_type.title()} handoff",
            intro="Governed drill-down from ControlDeck into Paperclip MissionCenter.",
            body_html=body,
        )

    def render_handoff_error_page(self, message: str, *, status_code: int) -> str:
        tone = "status-warn" if status_code < 500 else "status-ok"
        body = f"""
        <section class=\"banner\"><strong>Handoff could not be completed.</strong><p class=\"{tone}\">{html.escape(message)}</p></section>
        <section class=\"card\"><h2>Next step</h2><p>Return to ControlDeck to inspect the control-plane timeline and validate policy, expiry or replay conditions.</p></section>
        """
        return self._render_page(
            title="Handoff failed",
            intro="Paperclip rejected or could not validate the inbound handoff context.",
            body_html=body,
        )

    def render_action_result_page(self, result: dict[str, Any]) -> str:
        action = html.escape(str(result.get("action") or "request"))
        request_id = html.escape(str(result.get("request_id") or "-"))
        target_ref = html.escape(str(result.get("target_ref") or "-"))
        message = html.escape(str(result.get("message") or "Action request recorded."))
        body = f"""
        <section class=\"banner\"><strong>Governed action request submitted.</strong><p>{message}</p></section>
        <section class=\"grid\">
          <div class=\"card\"><div class=\"metric\">Request</div><div class=\"metric-value\">{request_id}</div></div>
          <div class=\"card\"><div class=\"metric\">Action</div><div class=\"metric-value\">{action}</div></div>
          <div class=\"card\"><div class=\"metric\">Execution</div><div class=\"metric-value\">{target_ref}</div></div>
        </section>
        """
        return self._render_page(
            title="Action requested",
            intro="BRAiN received the bounded action request and can now govern the next step.",
            body_html=body,
        )

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
                f"{self.brain_api_base}/api/external-apps/paperclip/actions",
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
                "executor_type": "paperclip",
                "intent": request_body.get("intent"),
                "prompt": request_body.get("prompt") or request_input.get("prompt") or "",
                "mode": request_body.get("mode"),
                "correlation_id": request_body.get("correlation_id"),
                "status": "completed",
                "summary": f"Paperclip accepted execution for {request_body.get('intent') or 'worker_bridge_execute'}",
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
                raise RuntimeError(f"Paperclip endpoint returned {response.status_code}")
        except Exception as exc:
            if not self.execution_fallback_enabled:
                raise RuntimeError(f"Paperclip execution failed closed: {exc}") from exc
            external_data = await self.perform_embedded_execution(request_body)
            external_data["status"] = "fallback"
            external_data["message"] = f"Embedded fallback used after upstream execution failure: {exc}"

        self._record_execution(
            {
                "execution_id": external_data.get("execution_id") or task.get("task_id"),
                "task_id": task.get("task_id"),
                "skill_run_id": payload.get("skill_run_id"),
                "executor_type": "paperclip",
                "intent": request_body.get("intent"),
                "prompt": payload.get("prompt", ""),
                "mode": payload.get("mode", "plan"),
                "correlation_id": task.get("correlation_id"),
                "status": external_data.get("status") or "completed",
                "summary": external_data.get("summary") or f"Paperclip executed task for {payload.get('prompt', '')}",
                "external_result": external_data,
            }
        )

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
logging.basicConfig(level=os.getenv("PAPERCLIP_LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="Paperclip Worker Runtime", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "worker": "paperclip",
        "agent_id": worker.agent_id,
        "task_types": worker.task_types,
        "brain_api_base": worker.brain_api_base,
        "paperclip_base_url": worker.paperclip_base_url,
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


@app.get("/handoff/paperclip", response_class=HTMLResponse)
async def paperclip_handoff_page(token: str, exchange_url: str | None = None) -> HTMLResponse:
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
        return HTMLResponse(
            worker.render_handoff_error_page(message, status_code=exc.response.status_code),
            status_code=exc.response.status_code,
        )
    except Exception as exc:
        return HTMLResponse(
            worker.render_handoff_error_page(str(exc), status_code=502),
            status_code=502,
        )


@app.post("/api/executions")
async def embedded_execution(request: Request) -> dict[str, Any]:
    request_body = await request.json()
    return await worker.perform_embedded_execution(request_body)


@app.post("/handoff/paperclip/action", response_class=HTMLResponse)
async def paperclip_handoff_action(request: Request) -> HTMLResponse:
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
