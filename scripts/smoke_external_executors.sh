#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BRAIN_API_BASE_URL:-http://127.0.0.1:8000}"
ADMIN_EMAIL="${BRAIN_ADMIN_EMAIL:-admin@test.com}"
ADMIN_PASSWORD="${BRAIN_ADMIN_PASSWORD:-admin123}"

echo "[smoke-executors] BASE_URL=${BASE_URL}"

python3 - <<'PY'
import json
import os
import sys
import time

import requests


BASE_URL = os.getenv("BRAIN_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_EMAIL = os.getenv("BRAIN_ADMIN_EMAIL", "admin@test.com")
ADMIN_PASSWORD = os.getenv("BRAIN_ADMIN_PASSWORD", "admin123")
TIMEOUT = 30


def fail(message: str) -> None:
    print(f"[smoke-executors] FAIL: {message}")
    sys.exit(1)


def login() -> str:
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        fail(f"login failed: {response.status_code} {response.text[:300]}")
    token = response.json().get("access_token")
    if not token:
        fail("login response missing access_token")
    return token


def create_and_approve_override(token: str, key: str, value, reason: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    create = requests.post(
        f"{BASE_URL}/api/runtime-control/overrides/requests",
        headers=headers,
        json={
            "key": key,
            "value": value,
            "reason": reason,
            "tenant_scope": "system",
        },
        timeout=TIMEOUT,
    )
    if create.status_code != 201:
        fail(f"override create failed for {key}: {create.status_code} {create.text[:350]}")
    request_id = create.json().get("request_id")
    approve = requests.post(
        f"{BASE_URL}/api/runtime-control/overrides/requests/{request_id}/approve",
        headers=headers,
        json={"reason": "External executor smoke validation"},
        timeout=TIMEOUT,
    )
    if approve.status_code != 200:
        fail(f"override approve failed for {key}: {approve.status_code} {approve.text[:350]}")
    print(f"[smoke-executors] override approved: {key} ({request_id})")


def send_worker_chat(token: str, worker_command: str) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/axe/chat",
        headers=headers,
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": worker_command}],
            "temperature": 0.2,
        },
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        fail(f"chat dispatch failed for `{worker_command}`: {response.status_code} {response.text[:400]}")
    body = response.json()
    raw = body.get("raw") or {}
    task_id = raw.get("task_id")
    skill_run_id = raw.get("skill_run_id")
    if not task_id or not skill_run_id:
        fail(f"missing task_id/skill_run_id for `{worker_command}`: {json.dumps(raw, ensure_ascii=True)}")
    print(f"[smoke-executors] dispatched `{worker_command}` task_id={task_id} skill_run_id={skill_run_id}")
    return str(task_id), str(skill_run_id)


def wait_for_task_completion(token: str, task_id: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(20):
        task_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers, timeout=TIMEOUT)
        if task_response.status_code != 200:
            fail(f"task fetch failed for {task_id}: {task_response.status_code} {task_response.text[:250]}")
        payload = task_response.json()
        state = payload.get("status")
        if state in {"completed", "failed", "cancelled", "timeout"}:
            return payload
        time.sleep(2)
    fail(f"task did not reach terminal state: {task_id}")


def assert_skillrun_succeeded(token: str, skill_run_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/skill-runs/{skill_run_id}", headers=headers, timeout=TIMEOUT)
    if response.status_code != 200:
        fail(f"skill run fetch failed for {skill_run_id}: {response.status_code} {response.text[:250]}")
    state = response.json().get("state")
    if state != "succeeded":
        fail(f"skill run {skill_run_id} ended in state={state}")


token = login()
create_and_approve_override(token, "workers.external.paperclip.enabled", True, "Enable paperclip executor for smoke")
create_and_approve_override(
    token,
    "security.allowed_connectors",
    ["odoo", "openclaw", "opencode", "miniworker", "paperclip"],
    "Allow openclaw/paperclip connector smoke execution",
)

openclaw_task_id, openclaw_skill_run_id = send_worker_chat(token, "/openclaw smoke test")
paperclip_task_id, paperclip_skill_run_id = send_worker_chat(token, "/paperclip smoke test")

openclaw_task = wait_for_task_completion(token, openclaw_task_id)
paperclip_task = wait_for_task_completion(token, paperclip_task_id)

if openclaw_task.get("status") != "completed":
    fail(f"openclaw task not completed: {json.dumps(openclaw_task, ensure_ascii=True)[:500]}")
if paperclip_task.get("status") != "completed":
    fail(f"paperclip task not completed: {json.dumps(paperclip_task, ensure_ascii=True)[:500]}")

assert_skillrun_succeeded(token, openclaw_skill_run_id)
assert_skillrun_succeeded(token, paperclip_skill_run_id)

print("[smoke-executors] PASS: OpenClaw + Paperclip completed via SkillRun/TaskLease")
PY
