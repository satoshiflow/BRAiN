#!/bin/bash
echo "=== Quick AXE Test ==="
echo ""
echo "1. AXE Health:"
curl -s https://api.brain.falklabs.de/api/axe/health | jq .
echo ""
echo "2. Chat Test:"
curl -s -X POST https://api.brain.falklabs.de/api/axe/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:0.5b","messages":[{"role":"user","content":"Say hello"}]}' \
  | jq '.text' 2>/dev/null || echo "ERROR"
