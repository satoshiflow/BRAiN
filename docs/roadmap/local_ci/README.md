# Local CI Evidence Folder

This folder stores timestamped local verification reports used when GitHub Actions is unavailable.

Recommended runner:

- `./scripts/local_ci_gate.sh backend`
- `./scripts/local_ci_gate.sh backend-fast`
- `./scripts/local_ci_gate.sh axe`
- `./scripts/local_ci_gate.sh axe-fast`
- `./scripts/local_ci_gate.sh all`

Each run writes a markdown report named:

- `<UTC_TIMESTAMP>_<mode>.md`

## Optional pre-push hook

To enable automatic local checks before push:

- `./scripts/install_git_hooks.sh`

Behavior:

- runs `backend-fast` for backend-related changes
- runs `axe-fast` for `frontend/axe_ui` changes
- runs `all` when both surfaces are touched
- skips when neither surface is affected

Overrides:

- skip once: `SKIP_LOCAL_CI=1 git push`
- force strict mode: `LOCAL_CI_MODE=all git push`
- set AXE API base used by lint/build checks: `BRAIN_LOCAL_CI_AXE_API_BASE=https://api.<your-domain>`

Minimum evidence per delivery slice:

- commands executed
- pass/fail result
- notable warnings/blockers
- timestamp
