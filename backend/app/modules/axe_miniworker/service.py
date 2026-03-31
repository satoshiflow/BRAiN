"""Pi-backed AXE miniworker execution service."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import resource
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal
from app.modules.config_management.service import get_config_service
from app.modules.credits.service import consume_agent_credits
from app.modules.governor.manifest.schemas import Budget
from app.modules.neurorail.enforcement.cost import CostTracker
from app.modules.opencode_repair.schemas import RepairTicketCreateRequest, RepairTicketSeverity
from app.modules.opencode_repair.service import get_opencode_repair_service

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_FILES = 3
DEFAULT_MAX_LLM_TOKENS = 6000
DEFAULT_MAX_COST_CREDITS = 30.0
READ_ONLY_TOOLS = "read,grep,find,ls"
ENV_PASSTHROUGH_KEYS = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENWEBUI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENROUTER_BASE_URL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "LOCAL_LLM_MODE",
)


@dataclass
class MiniworkerRuntimeConfig:
    enabled: bool
    command: str
    provider: str | None
    model: str | None
    workdir: Path
    timeout_seconds: int
    max_files: int
    max_llm_tokens: int | None
    max_cost_credits: float | None
    allow_bounded_apply: bool
    env_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class MiniworkerHealthSnapshot:
    status: str = "unknown"
    total_runs: int = 0
    success_runs: int = 0
    failed_runs: int = 0
    degraded_runs: int = 0
    timeout_runs: int = 0
    credit_failures: int = 0
    average_duration_ms: float = 0.0
    average_prompt_tokens: float = 0.0
    average_completion_tokens: float = 0.0
    average_cost_credits: float = 0.0
    last_error: str | None = None
    last_run_at: float | None = None
    last_peak_rss_mb: float | None = None


class MiniworkerTelemetry:
    def __init__(self) -> None:
        self._snapshot = MiniworkerHealthSnapshot()

    def record(
        self,
        *,
        success: bool,
        degraded: bool,
        timeout: bool,
        duration_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        cost_credits: float,
        peak_rss_mb: float | None,
        error: str | None = None,
        credit_failure: bool = False,
    ) -> None:
        snapshot = self._snapshot
        previous_runs = snapshot.total_runs
        snapshot.total_runs += 1
        snapshot.success_runs += int(success)
        snapshot.failed_runs += int(not success)
        snapshot.degraded_runs += int(degraded)
        snapshot.timeout_runs += int(timeout)
        snapshot.credit_failures += int(credit_failure)
        snapshot.average_duration_ms = _weighted_average(
            snapshot.average_duration_ms,
            previous_runs,
            duration_ms,
        )
        snapshot.average_prompt_tokens = _weighted_average(
            snapshot.average_prompt_tokens,
            previous_runs,
            float(prompt_tokens),
        )
        snapshot.average_completion_tokens = _weighted_average(
            snapshot.average_completion_tokens,
            previous_runs,
            float(completion_tokens),
        )
        snapshot.average_cost_credits = _weighted_average(
            snapshot.average_cost_credits,
            previous_runs,
            cost_credits,
        )
        snapshot.last_peak_rss_mb = peak_rss_mb
        snapshot.last_run_at = time.time()
        snapshot.last_error = error
        if timeout:
            snapshot.status = "degraded"
        elif degraded:
            snapshot.status = "degraded"
        elif success:
            snapshot.status = "healthy"
        else:
            snapshot.status = "degraded"

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self._snapshot.status,
            "total_runs": self._snapshot.total_runs,
            "success_runs": self._snapshot.success_runs,
            "failed_runs": self._snapshot.failed_runs,
            "degraded_runs": self._snapshot.degraded_runs,
            "timeout_runs": self._snapshot.timeout_runs,
            "credit_failures": self._snapshot.credit_failures,
            "average_duration_ms": round(self._snapshot.average_duration_ms, 2),
            "average_prompt_tokens": round(self._snapshot.average_prompt_tokens, 2),
            "average_completion_tokens": round(self._snapshot.average_completion_tokens, 2),
            "average_cost_credits": round(self._snapshot.average_cost_credits, 4),
            "last_error": self._snapshot.last_error,
            "last_run_at": self._snapshot.last_run_at,
            "last_peak_rss_mb": self._snapshot.last_peak_rss_mb,
        }


_telemetry = MiniworkerTelemetry()


def get_miniworker_health_snapshot() -> dict[str, Any]:
    return _telemetry.snapshot()


class AXEMiniworkerService:
    def __init__(self) -> None:
        self.config_service = get_config_service()
        self.cost_tracker = CostTracker()
        self.repair_service = get_opencode_repair_service()

    async def dispatch(
        self,
        *,
        db: AsyncSession,
        principal: Principal,
        payload: Any,
        worker_run_id: str,
    ) -> dict[str, Any]:
        config = await self._load_config(db)
        if not config.enabled:
            raise ValueError("AXE miniworker is disabled. Set AXE_MINIWORKER_ENABLED to true.")
        if payload.execution_mode == "bounded_apply" and not config.allow_bounded_apply:
            raise ValueError("AXE miniworker bounded_apply is disabled for this environment")

        scoped_paths = self._resolve_scope(config, payload.file_scope, payload.max_files)
        prompt = self._build_prompt(payload, scoped_paths)
        command = self._build_command(config, payload, prompt, scoped_paths)

        before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        started = time.perf_counter()
        stdout = ""
        stderr = ""
        returncode = 1
        timed_out = False

        try:
            stdout, stderr, returncode = await self._run_command(
                command,
                cwd=config.workdir,
                env={**os.environ, **config.env_overrides},
                timeout_seconds=config.timeout_seconds,
            )
        except TimeoutError as exc:
            timed_out = True
            stderr = str(exc)

        duration_ms = (time.perf_counter() - started) * 1000.0
        after_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        peak_rss_mb = _rss_delta_mb(before_rss, after_rss)

        parsed = self._parse_output(stdout)
        prompt_tokens = _estimate_tokens(prompt)
        completion_tokens = _estimate_tokens(parsed["text"])
        estimated_cost = round(1.0 + ((prompt_tokens + completion_tokens) / 1000.0), 4)
        budget = Budget(
            timeout_ms=config.timeout_seconds * 1000,
            max_llm_tokens=config.max_llm_tokens,
            max_cost_credits=config.max_cost_credits,
        )

        credit_failure = False
        try:
            self.cost_tracker.track_llm_tokens(
                attempt_id=worker_run_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                budget=budget,
                context={"worker_type": "miniworker", "principal_id": principal.principal_id},
            )
            self.cost_tracker.track_api_call(
                attempt_id=worker_run_id,
                cost_credits=estimated_cost,
                budget=budget,
                context={"worker_type": "miniworker", "principal_id": principal.principal_id},
            )
            await self._consume_credits(principal=principal, cost_credits=estimated_cost)
        except Exception as exc:  # pragma: no cover - best effort path
            credit_failure = True
            logger.warning("AXE miniworker credits tracking degraded: %s", exc)

        success = returncode == 0 and not timed_out
        degraded = credit_failure or not success or parsed["should_escalate"]
        error_message = None if success else (stderr or parsed["summary"])
        _telemetry.record(
            success=success,
            degraded=degraded,
            timeout=timed_out,
            duration_ms=duration_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_credits=estimated_cost,
            peak_rss_mb=peak_rss_mb,
            error=error_message,
            credit_failure=credit_failure,
        )

        artifacts = self._build_artifacts(parsed, prompt_tokens, completion_tokens, estimated_cost, peak_rss_mb)
        if not success:
            await self._create_repair_ticket(
                db=db,
                principal=principal,
                worker_run_id=worker_run_id,
                payload=payload,
                summary=error_message or "AXE miniworker execution failed",
                severity=RepairTicketSeverity.MEDIUM if timed_out else RepairTicketSeverity.LOW,
            )

        return {
            "worker_run_id": worker_run_id,
            "session_id": payload.session_id,
            "message_id": payload.message_id,
            "status": "completed" if success else "failed",
            "label": "AXE miniworker completed" if success else "AXE miniworker failed",
            "detail": self._build_detail(parsed, stderr, success, timed_out),
            "artifacts": artifacts,
            "backend_run_id": f"miniworker:{worker_run_id}",
            "backend_run_type": "miniworker_job",
        }

    async def _load_config(self, db: AsyncSession) -> MiniworkerRuntimeConfig:
        command = str(
            await self.config_service.resolve_effective_value(
                db,
                "AXE_MINIWORKER_COMMAND",
                default="pi",
            )
        ).strip()
        workdir_raw = str(
            await self.config_service.resolve_effective_value(
                db,
                "AXE_MINIWORKER_WORKDIR",
                default=str(REPO_ROOT),
            )
        ).strip()
        workdir = Path(workdir_raw).expanduser().resolve()
        if not workdir.exists():
            raise ValueError(f"AXE miniworker workdir does not exist: {workdir}")

        env_overrides: dict[str, str] = {}
        for key in ENV_PASSTHROUGH_KEYS:
            value = await self.config_service.resolve_effective_value(db, key)
            if value is None:
                continue
            env_overrides[key] = str(value)

        provider = await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_PROVIDER")
        model = await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_MODEL")

        return MiniworkerRuntimeConfig(
            enabled=_as_bool(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_ENABLED", default="false")),
            command=command,
            provider=str(provider).strip() if provider else None,
            model=str(model).strip() if model else None,
            workdir=workdir,
            timeout_seconds=int(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_TIMEOUT_SECONDS", default=DEFAULT_TIMEOUT_SECONDS)),
            max_files=int(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_MAX_FILES", default=DEFAULT_MAX_FILES)),
            max_llm_tokens=_as_optional_int(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_MAX_LLM_TOKENS", default=DEFAULT_MAX_LLM_TOKENS)),
            max_cost_credits=_as_optional_float(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_MAX_COST_CREDITS", default=DEFAULT_MAX_COST_CREDITS)),
            allow_bounded_apply=_as_bool(await self.config_service.resolve_effective_value(db, "AXE_MINIWORKER_ALLOW_BOUNDED_APPLY", default="false")),
            env_overrides=env_overrides,
        )

    def _resolve_scope(self, config: MiniworkerRuntimeConfig, file_scope: list[str], requested_max_files: int) -> list[Path]:
        max_files = max(1, min(config.max_files, requested_max_files or config.max_files))
        resolved: list[Path] = []
        for raw in file_scope[:max_files]:
            candidate = (config.workdir / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
            try:
                candidate.relative_to(config.workdir)
            except ValueError as exc:
                raise ValueError(f"AXE miniworker scope escapes workdir: {raw}") from exc
            if not candidate.exists():
                raise ValueError(f"AXE miniworker scoped path does not exist: {raw}")
            resolved.append(candidate)
        return resolved

    def _build_prompt(self, payload: Any, scoped_paths: list[Path]) -> str:
        scope_text = "\n".join(f"- {path.relative_to(REPO_ROOT)}" for path in scoped_paths) or "- no explicit file scope supplied"
        return (
            "You are AXE miniworker running in proposal mode for BRAiN.\n"
            "Stay bounded, minimal, and repository-aware.\n"
            f"Execution mode: {payload.execution_mode}\n"
            f"Expected output: {payload.expected_output}\n"
            f"Scoped paths:\n{scope_text}\n"
            "Do not claim to have edited files. Return JSON only with keys: "
            "status, summary, analysis, patch, tests_recommended, affected_paths, risks, should_escalate.\n"
            "status must be one of: patch_proposal, analysis_only, test_proposal, cannot_comply.\n"
            f"User task:\n{payload.prompt.strip()}"
        )

    def _build_command(
        self,
        config: MiniworkerRuntimeConfig,
        payload: Any,
        prompt: str,
        scoped_paths: list[Path],
    ) -> list[str]:
        args = shlex.split(config.command)
        if not args:
            raise ValueError("AXE miniworker command is empty")
        args.extend(["--no-session", "--tools", READ_ONLY_TOOLS, "-p"])
        if config.provider:
            args.extend(["--provider", config.provider])
        if config.model:
            args.extend(["--model", config.model])
        for scoped_path in scoped_paths:
            args.append(f"@{scoped_path.relative_to(config.workdir)}")
        args.append(prompt)
        if payload.execution_mode == "bounded_apply":
            raise ValueError("AXE miniworker bounded_apply is not enabled in proposal-first runtime")
        return args

    async def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> tuple[str, str, int]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TimeoutError(f"AXE miniworker timed out after {timeout_seconds} seconds") from exc
        return (
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
            process.returncode or 0,
        )

    def _parse_output(self, stdout: str) -> dict[str, Any]:
        text = stdout.strip()
        if not text:
            return {
                "status": "cannot_comply",
                "summary": "Pi miniworker returned no output",
                "analysis": "",
                "patch": "",
                "tests_recommended": [],
                "affected_paths": [],
                "risks": ["empty_output"],
                "should_escalate": True,
                "text": "",
            }

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                parsed = json.loads(candidate)
                parsed.setdefault("status", "analysis_only")
                parsed.setdefault("summary", "AXE miniworker proposal generated")
                parsed.setdefault("analysis", "")
                parsed.setdefault("patch", "")
                parsed.setdefault("tests_recommended", [])
                parsed.setdefault("affected_paths", [])
                parsed.setdefault("risks", [])
                parsed.setdefault("should_escalate", False)
                parsed["text"] = text
                return parsed
            except json.JSONDecodeError:
                pass

        return {
            "status": "analysis_only",
            "summary": "AXE miniworker returned non-JSON output; preserved as analysis",
            "analysis": text,
            "patch": "",
            "tests_recommended": [],
            "affected_paths": [],
            "risks": ["non_json_output"],
            "should_escalate": False,
            "text": text,
        }

    def _build_artifacts(
        self,
        parsed: dict[str, Any],
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
        peak_rss_mb: float | None,
    ) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = [
            {
                "type": "report",
                "label": "AXE miniworker metrics",
                "url": "inline://metrics",
                "metadata": {
                    "estimated_prompt_tokens": prompt_tokens,
                    "estimated_completion_tokens": completion_tokens,
                    "estimated_cost_credits": estimated_cost,
                    "approx_peak_rss_mb": peak_rss_mb,
                    "status": parsed.get("status"),
                    "should_escalate": parsed.get("should_escalate", False),
                },
            }
        ]
        if parsed.get("patch"):
            artifacts.append(
                {
                    "type": "patch",
                    "label": "AXE miniworker patch proposal",
                    "url": "inline://patch",
                    "content": str(parsed["patch"]),
                }
            )
        if parsed.get("analysis"):
            artifacts.append(
                {
                    "type": "analysis",
                    "label": "AXE miniworker analysis",
                    "url": "inline://analysis",
                    "content": str(parsed["analysis"]),
                }
            )
        return artifacts

    def _build_detail(self, parsed: dict[str, Any], stderr: str, success: bool, timed_out: bool) -> str:
        summary = str(parsed.get("summary") or "AXE miniworker finished")
        if success:
            return summary
        if timed_out:
            return f"{summary} (timeout)"
        if stderr:
            return f"{summary} | stderr: {stderr[:400]}"
        return summary

    async def _create_repair_ticket(
        self,
        *,
        db: AsyncSession,
        principal: Principal,
        worker_run_id: str,
        payload: Any,
        summary: str,
        severity: RepairTicketSeverity,
    ) -> None:
        try:
            await self.repair_service.create_ticket(
                RepairTicketCreateRequest(
                    source_module="axe_miniworker",
                    source_event_type="axe.miniworker.failed",
                    title=f"AXE miniworker repair request {worker_run_id}",
                    description=summary,
                    severity=severity,
                    correlation_id=worker_run_id,
                    actor=principal.principal_id,
                    evidence={
                        "prompt": payload.prompt,
                        "execution_mode": payload.execution_mode,
                        "file_scope": payload.file_scope,
                    },
                ),
                db=db,
            )
        except Exception as exc:  # pragma: no cover - best effort path
            logger.warning("AXE miniworker repair ticket creation skipped: %s", exc)

    async def _consume_credits(self, *, principal: Principal, cost_credits: float) -> None:
        try:
            await consume_agent_credits(
                agent_id=principal.principal_id,
                amount=max(0.01, cost_credits),
                reason="AXE miniworker execution",
                actor_id=principal.principal_id,
            )
        except Exception as exc:  # pragma: no cover - best effort path
            raise RuntimeError(f"credits consumption unavailable: {exc}") from exc


def _rss_delta_mb(before: int, after: int) -> float | None:
    if after <= before:
        return None
    # Linux ru_maxrss is KiB.
    return round((after - before) / 1024.0, 3)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _weighted_average(current: float, count: int, new_value: float) -> float:
    if count <= 0:
        return new_value
    return ((current * count) + new_value) / (count + 1)


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_optional_int(value: Any) -> int | None:
    if value in {None, "", "none"}:
        return None
    return int(value)


def _as_optional_float(value: Any) -> float | None:
    if value in {None, "", "none"}:
        return None
    return float(value)
