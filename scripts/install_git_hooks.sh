#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -d "$ROOT_DIR/.githooks" ]]; then
  echo "Missing .githooks directory in repo root."
  exit 1
fi

chmod +x "$ROOT_DIR/.githooks/pre-push"
chmod +x "$ROOT_DIR/scripts/local_ci_gate.sh"

git -C "$ROOT_DIR" config core.hooksPath .githooks

echo "Git hooks installed for this repository."
echo "- core.hooksPath: .githooks"
echo "- active pre-push hook: .githooks/pre-push"
echo
echo "Optional overrides:"
echo "- Skip once: SKIP_LOCAL_CI=1 git push"
echo "- Force mode: LOCAL_CI_MODE=all git push"
