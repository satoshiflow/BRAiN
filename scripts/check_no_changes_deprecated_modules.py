#!/usr/bin/env python3
"""Block non-allowed changes in Wave-1 deprecated modules."""

import re
import subprocess
import sys
import os

# Wave-1 deprecated module paths
DEPRECATED_PATHS = [
    "backend/app/modules/factory_executor/",
    "backend/app/modules/webgenesis/service.py",
    "backend/app/modules/webgenesis/ops_service.py",
    "backend/app/modules/webgenesis/releases.py",
    "backend/app/modules/webgenesis/rollback.py",
    "backend/app/modules/webgenesis/router.py",
    "backend/app/modules/course_factory/webgenesis_integration.py",
]

# Allowed change line patterns (bypass gate)
ALLOWED_PATTERNS = [
    re.compile(r"DEPRECATION NOTICE"),
    re.compile(r"^#\s*Status:"),
    re.compile(r"^#\s*Owner:"),
    re.compile(r"^#\s*Replacement Target:"),
    re.compile(r"^#\s*Sunset Phase:"),
    re.compile(r"^#\s*Rule:"),
    re.compile(r"opencode_execution_consolidation_plan\.md"),
    re.compile(r"^#\s*={3,}"),
    re.compile(r"TODO\("),
    re.compile(r"FIXME\("),
    re.compile(r"#\s*SECURITY:"),
    re.compile(r"#\s*CRITICAL:"),
]


def get_changed_files() -> list[str]:
    """Get changed files from compare range or local workspace diff."""
    compare_range = os.getenv("GUARDRAIL_COMPARE_RANGE", "").strip()
    if compare_range:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", compare_range],
                capture_output=True,
                text=True,
                check=True,
            )
            return [line.strip() for line in result.stdout.split("\n") if line.strip()]
        except subprocess.CalledProcessError:
            return []

    # Default: only current workspace changes
    try:
        staged = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            check=True,
        )
        unstaged = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = {
            line.strip()
            for output in (staged.stdout, unstaged.stdout)
            for line in output.split("\n")
            if line.strip()
        }
        return sorted(files)
    except subprocess.CalledProcessError:
        return []


def is_deprecated_path(filepath: str) -> bool:
    """Check if file is in a deprecated module path."""
    for dep_path in DEPRECATED_PATHS:
        if filepath.startswith(dep_path) or filepath == dep_path:
            return True
    return False


def get_diff_for_file(filepath: str) -> str:
    """Get diff content for a specific file."""
    compare_range = os.getenv("GUARDRAIL_COMPARE_RANGE", "").strip()
    if compare_range:
        try:
            result = subprocess.run(
                ["git", "diff", compare_range, "--", filepath],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    try:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--", filepath],
            capture_output=True,
            text=True,
            check=True,
        )
        unstaged = subprocess.run(
            ["git", "diff", "--", filepath],
            capture_output=True,
            text=True,
            check=True,
        )
        return f"{staged.stdout}\n{unstaged.stdout}".strip()
    except subprocess.CalledProcessError:
        return ""


def is_allowed_change(diff_content: str) -> bool:
    """Check if changes are allowed (header/docs/critical only)."""
    added_lines = [
        line[1:].strip()
        for line in diff_content.split("\n")
        if line.startswith("+") and not line.startswith("+++")
    ]
    
    if not added_lines:
        return True  # No additions, likely deletions (allowed)
    
    # Check if all added lines match allowed patterns
    for line in added_lines:
        if not line:  # Empty lines ok
            continue
        
        # Check against allowed patterns
        allowed = any(pattern.search(line) for pattern in ALLOWED_PATTERNS)
        if not allowed:
            return False  # Found non-allowed addition
    
    return True  # All additions are allowed


def main():
    """Main entry point."""
    print("[guardrail] Checking deprecated module changes...")
    print()
    
    changed_files = get_changed_files()
    
    if not changed_files:
        print("✅ No changes detected")
        sys.exit(0)
    
    deprecated_changes = []
    
    for filepath in changed_files:
        if is_deprecated_path(filepath):
            diff = get_diff_for_file(filepath)
            
            if not is_allowed_change(diff):
                deprecated_changes.append(filepath)
    
    if not deprecated_changes:
        print("✅ No new features in deprecated modules")
        sys.exit(0)
    
    # Block: new feature changes in deprecated modules
    print("❌ BLOCKED: New feature changes detected in deprecated modules")
    print()
    print("Deprecated modules (Wave-1 consolidation):")
    for filepath in deprecated_changes:
        print(f"  • {filepath}")
    
    print()
    print("Policy: No new features allowed in deprecated modules.")
    print("Allowed changes:")
    print("  ✓ Deprecation header updates")
    print("  ✓ Documentation updates")
    print("  ✓ Security patches (tagged with # SECURITY:)")
    print("  ✓ Critical bugfixes (tagged with # CRITICAL:)")
    print()
    print("See: docs/specs/opencode_execution_consolidation_plan.md")
    
    sys.exit(1)


if __name__ == "__main__":
    main()
