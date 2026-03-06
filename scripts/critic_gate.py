#!/usr/bin/env python3
"""Critic gate for high-risk changes.

Evaluates changed paths against `configs/model_routing_policy.json` and reports
whether a mandatory critic review is required.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path("/home/oli/dev/brain-v2")
POLICY_PATH = ROOT / "configs" / "model_routing_policy.json"


def _git_changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        paths.append(candidate.strip())
    return paths


def _load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _matches(path: str, pattern: str) -> bool:
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return path.startswith(pattern)


def evaluate(paths: list[str], policy: dict) -> dict:
    rules = policy.get("risk_path_rules", [])
    hits: list[dict] = []

    for path in paths:
        for rule in rules:
            pattern = rule.get("pattern", "")
            if pattern and _matches(path, pattern):
                hits.append(
                    {
                        "path": path,
                        "pattern": pattern,
                        "tier": rule.get("tier", policy.get("default_tier", "low_cost")),
                        "critic_required": bool(rule.get("critic_required", False)),
                    }
                )

    critic_required = any(hit["critic_required"] for hit in hits)
    highest_tier = "low_cost"
    tier_order = {"low_cost": 0, "medium_cost": 1, "high_quality": 2}
    for hit in hits:
        if tier_order.get(hit["tier"], 0) > tier_order.get(highest_tier, 0):
            highest_tier = hit["tier"]

    return {
        "changed_paths": paths,
        "matches": hits,
        "critic_required": critic_required,
        "recommended_tier": highest_tier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate critic gate against changed files")
    parser.add_argument("--report", default="reports/critic/critic_gate_report.json")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when critic review is required")
    args = parser.parse_args()

    policy = _load_policy()
    paths = _git_changed_paths()
    result = evaluate(paths, policy)

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"Report written to: {report_path}")

    if args.strict and result["critic_required"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
