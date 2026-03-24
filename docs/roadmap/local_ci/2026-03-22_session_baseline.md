# Session Baseline - 2026-03-22

- Branch: `feature/discovery-economy-p6-p7`
- Remote relation: `origin/feature/discovery-economy-p6-p7` plus one local commit ahead at session start
- GitHub Actions status: unavailable for practical use due billing lock on the GitHub account/org
- Production/Hetzner status: remote production currently not reachable from this environment

## Active local verification posture

- Local CI fallback enabled in `AGENTS.md`
- Helper runner available: `scripts/local_ci_gate.sh`
- Optional pre-push automation available: `.githooks/pre-push` via `scripts/install_git_hooks.sh`

## Session focus

1. keep auth refresh and invitation flows fail-closed
2. keep AXE UI auth/session behavior deterministic under 401/refresh/logout paths
3. make local AXE chat pipeline reproducible without production dependencies
