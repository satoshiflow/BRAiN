#!/usr/bin/env bash
#
# Aider + Moonshot Kimi Thinking Launcher
# Uses the larger context model (32k) for complex reasoning tasks
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call main launcher with larger context model
exec "$SCRIPT_DIR/aider-kimi.sh" "openai/moonshot-v1-32k" "$@"
