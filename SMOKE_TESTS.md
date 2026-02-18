# AXE Chat MVP - Smoke Tests

## Quick Test Commands

### 1. AXEllm Health (intern)
```bash
# Von BRAiN Container
curl http://axellm:8000/health

# Erwartet: {"status":"ok"}
```

### 2. AXEllm Chat (intern)
```bash
# Von BRAiN Container
curl -X POST http://axellm:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen:0.5b",
    "messages": [{"role": "user", "content": "Hallo!"}],
    "temperature": 0.7
  }'

# Erwartet: OpenAI-compatible Response mit choices[0].message.content
```

### 3. BRAiN AXE Health (extern)
```bash
curl https://api.brain.falklabs.de/api/axe/health

# Erwartet: {"status":"healthy","axellm":"reachable"}
```

### 4. BRAiN AXE Chat (extern)
```bash
curl -X POST https://api.brain.falklabs.de/api/axe/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen:0.5b",
    "messages": [{"role": "user", "content": "Hallo!"}],
    "temperature": 0.7
  }'

# Erwartet: {"text":"...","raw":{...}}
```

### 5. Ollama Model Check (intern)
```bash
# Von AXEllm Container
curl http://ollama-qwen:11434/api/tags

# Erwartet: Liste mit Modellen (inkl. qwen:0.5b)
```

### 6. AXE UI Manual Test
```
1. Öffne: https://axe.brain.falklabs.de/chat
2. Gib ein: "Hallo, wer bist du?"
3. Erwarte: Antwort vom Assistant
4. Prüfe: Keine Fehlermeldungen in Console
```

## Deployment Verification

### Step 1: Start Services
```bash
# In Coolify oder via docker-compose
docker-compose -f docker-compose.axe-stack.yml up -d
```

### Step 2: Pull Model
```bash
docker exec ollama-qwen ollama pull qwen:0.5b
```

### Step 3: Verify Internals
```bash
# Test 1-2 von oben ausführen
```

### Step 4: Deploy BRAiN
```bash
# Push to GitHub -> Coolify deploys automatically
```

### Step 5: Verify Externals
```bash
# Test 3-4 von oben ausführen
```

### Step 6: UI Test
```bash
# Test 6 von oben ausführen
```

## Troubleshooting

### "Connection refused" zu AXEllm
- Prüfen: `docker ps | grep axellm`
- Logs: `docker logs axellm`

### "Model not found" in Ollama
- Model pullen: `docker exec ollama-qwen ollama pull qwen:0.5b`
- Liste: `docker exec ollama-qwen ollama list`

### CORS Fehler in Browser
- Prüfen: `curl -I -X OPTIONS https://api.brain.falklabs.de/api/axe/chat`
- Headers sollten `access-control-allow-origin` enthalten

### 503 Service Unavailable
- AXEllm läuft nicht oder ist nicht erreichbar
- Prüfen: Interne Netzwerk-Konnektivität

---
**Date:** 2026-02-18
**Version:** MVP
