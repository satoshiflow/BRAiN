#!/usr/bin/env python3
"""Run build/test/script pipelines with fault tolerance and diagnosis output.

Features:
- Continue executing next steps even if one step fails
- Per-step retry support
- Timeout support per step
- Lightweight log streaming to disk (RAM friendly)
- Machine-readable diagnosis report for later self-healing analysis
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class StepResult:
    name: str
    command: str
    cwd: str
    attempt: int
    retries: int
    timeout_sec: int | None
    started_at: str
    ended_at: str
    duration_sec: float
    exit_code: int
    status: str
    continue_on_error: bool
    log_file: str
    tail: list[str]
    diagnosis: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def diagnose_output(exit_code: int, tail: list[str]) -> dict[str, Any]:
    text = "\n".join(tail).lower()
    tags: list[str] = []
    recommendations: list[str] = []

    if exit_code == 0:
        return {"tags": ["success"], "recommendations": []}

    if "module not found" in text:
        tags.append("python_import_error")
        recommendations.append("Check PYTHONPATH and package imports.")

    if "validationerror" in text and "pydantic" in text:
        tags.append("config_validation_error")
        recommendations.append("Check environment variables and settings schema alignment.")

    if "attribute name 'metadata' is reserved" in text:
        tags.append("sqlalchemy_model_error")
        recommendations.append("Rename model attribute 'metadata' to non-reserved name (e.g. meta_json).")

    if "no key loaded. call load_key_from_env() first" in text:
        tags.append("jwt_key_not_loaded")
        recommendations.append("Load/generate local JWT key material before auth token tests.")

    if "422" in text and "test_module_auth" in text:
        tags.append("auth_contract_mismatch")
        recommendations.append("Check endpoint request contracts/dependencies vs test expectations (401/403 vs 422).")

    if "failed tests/test_auth_flow.py" in text:
        tags.append("auth_flow_failures")

    if "failed tests/test_module_auth.py" in text:
        tags.append("module_auth_failures")

    if "command not found" in text or "befehl nicht gefunden" in text:
        tags.append("missing_binary")
        recommendations.append("Install required tool or use the correct binary name.")

    if "timed out" in text:
        tags.append("timeout")
        recommendations.append("Increase timeout or split heavy step into smaller steps.")

    if not tags:
        tags.append("unknown_failure")
        recommendations.append("Inspect step log and rerun with verbose output.")

    return {"tags": tags, "recommendations": recommendations}


def run_step(
    *,
    name: str,
    command: str,
    cwd: str,
    retries: int,
    timeout_sec: int | None,
    continue_on_error: bool,
    log_dir: Path,
    tail_lines: int,
) -> StepResult:
    attempt = 0
    last_result: StepResult | None = None

    while attempt <= retries:
        attempt += 1
        started = time.time()
        started_at = now_iso()

        step_log = log_dir / f"{name.replace(' ', '_').lower()}-attempt-{attempt}.log"
        tail = deque(maxlen=tail_lines)

        with step_log.open("w", encoding="utf-8") as logf:
            logf.write(f"# Step: {name}\n")
            logf.write(f"# Command: {command}\n")
            logf.write(f"# CWD: {cwd}\n")
            logf.write(f"# Attempt: {attempt}/{retries + 1}\n")
            logf.write(f"# Started: {started_at}\n\n")

            proc = subprocess.Popen(
                ["bash", "-lc", command],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            timed_out = False
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    logf.write(line)
                    tail.append(line.rstrip("\n"))
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                logf.write("\n[runner] Step timed out and was terminated.\n")

        ended = time.time()
        ended_at = now_iso()
        duration = round(ended - started, 3)
        exit_code = 124 if timed_out else int(proc.returncode or 0)
        status = "success" if exit_code == 0 else "failed"
        diagnosis = diagnose_output(exit_code, list(tail))

        last_result = StepResult(
            name=name,
            command=command,
            cwd=cwd,
            attempt=attempt,
            retries=retries,
            timeout_sec=timeout_sec,
            started_at=started_at,
            ended_at=ended_at,
            duration_sec=duration,
            exit_code=exit_code,
            status=status,
            continue_on_error=continue_on_error,
            log_file=str(step_log),
            tail=list(tail),
            diagnosis=diagnosis,
        )

        if exit_code == 0:
            return last_result
        if attempt <= retries:
            time.sleep(min(2 * attempt, 10))

    assert last_result is not None
    return last_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run resilient build/test/script pipeline")
    parser.add_argument("--plan", required=True, help="Path to pipeline plan JSON")
    parser.add_argument(
        "--output-dir",
        default="reports/self_healing",
        help="Output directory for logs and diagnosis report",
    )
    parser.add_argument("--tail-lines", type=int, default=40, help="Tail lines stored per step")
    parser.add_argument(
        "--always-zero",
        action="store_true",
        help="Always exit with 0 even when steps fail",
    )
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}", file=sys.stderr)
        return 2

    with plan_path.open("r", encoding="utf-8") as f:
        plan = json.load(f)

    steps = plan.get("steps", [])
    if not isinstance(steps, list) or not steps:
        print("Pipeline plan has no steps.", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[StepResult] = []
    start_all = time.time()

    for idx, step in enumerate(steps, start=1):
        name = step.get("name") or f"step-{idx}"
        command = step.get("command")
        if not command:
            print(f"Skipping step '{name}' (missing command)")
            continue

        cwd = step.get("cwd") or os.getcwd()
        retries = int(step.get("retries", 0))
        timeout_sec = step.get("timeout_sec")
        continue_on_error = bool(step.get("continue_on_error", True))

        print(f"[runner] {name}: start")
        result = run_step(
            name=name,
            command=command,
            cwd=cwd,
            retries=retries,
            timeout_sec=timeout_sec,
            continue_on_error=continue_on_error,
            log_dir=run_dir,
            tail_lines=args.tail_lines,
        )
        results.append(result)

        print(f"[runner] {name}: {result.status} (exit={result.exit_code}, attempts={result.attempt})")
        if result.status == "failed" and not continue_on_error:
            print(f"[runner] stopping pipeline because continue_on_error=false on step '{name}'")
            break

    end_all = time.time()
    failed = [r for r in results if r.status != "success"]
    summary = {
        "run_id": run_id,
        "started_at": now_iso(),
        "duration_sec": round(end_all - start_all, 3),
        "steps_total": len(results),
        "steps_failed": len(failed),
        "overall_status": "failed" if failed else "success",
        "results": [r.__dict__ for r in results],
    }

    report_path = run_dir / "diagnosis_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[runner] report: {report_path}")

    if args.always_zero:
        return 0
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
