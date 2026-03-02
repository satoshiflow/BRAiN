# AXE Chat Deployment Guide

**Datum:** 2026-02-18
**Status:** ✅ PRODUCTION READY
**Version:** BRAiN v0.3.0

---

## 📋 Überblick

Dieses Dokument beschreibt die erfolgreiche Deployment und Konfiguration des AXE Chat Systems innerhalb der BRAiN-Infrastruktur.

### Komponenten

1. **AXE UI** - Next.js Frontend für Chat-Interface
2. **AXE Fusion** - Backend-Modul für Chat-API
3. **AXEllm** - OpenAI-kompatible API für Ollama
4. **Ollama** - LLM-Service (qwen2.5:0.5b)

---

## 🏗️ Architektur

```
User Browser
    ↓
AXE UI (Next.js)
    ↓ https://axe.brain.falklabs.de
BRAiN Backend API
    ↓ /api/axe/chat
AXE Fusion Service
    ↓ Internal HTTP
AXEllm (OpenAI-Compatible Wrapper)
    ↓ http://xkg0gc00sgcg0sc0g8wowskw-180855623729:11434
Ollama (qwen2.5:0.5b)
    ↓
LLM Response
```

### Shared Ollama Architecture

**Ein Ollama für alle Services:**

```
┌─────────────────────────────────────────┐
│         Ollama Container                │
│  xkg0gc00sgcg0sc0g8wowskw-180855623729 │
│                                         │
│  Network Aliases:                       │
│  - ollama                               │
│  - xkg0gc00sgcg0sc0g8wowskw-180855... │
└─────────────┬───────────────────────────┘
              │
      ┌───────┴────────┐
      ▼                ▼
┌──────────┐    ┌──────────┐
│ Backend  │    │  AXEllm  │
│ API      │    │  Service │
└──────────┘    └──────────┘
```

**Vorteile:**
- ✅ Nur ein Ollama-Prozess (Ressourcen-effizient)
- ✅ Modell nur einmal im RAM (397 MB statt 794 MB)
- ✅ Beide Services nutzen gleiche Modelle
- ✅ Einfachere Wartung

---

## 🚀 Deployment Steps

### 1. AXE Stack Service (Coolify)

**Service Config (`docker-compose.axe-stack.yml`):**

```yaml
version: '3.8'
services:
  axellm:
    image: 'ghcr.io/satoshiflow/brain/axellm:latest'
    container_name: axellm
    networks:
      - coolify
    environment:
      - 'OLLAMA_BASE_URL=http://xkg0gc00sgcg0sc0g8wowskw-180855623729:11434'
      - 'DEFAULT_MODEL=qwen2.5:0.5b'
      - REQUEST_TIMEOUT_SECONDS=60
      - LOG_LEVEL=info
    restart: unless-stopped
networks:
  coolify:
    external: true
```

**Wichtig:**
- ⚠️ Coolify speichert Docker Compose in seiner **Datenbank**, nicht aus Git
- ✅ Änderungen müssen über Coolify API oder UI gemacht werden
- ✅ `OLLAMA_BASE_URL` muss den **Container-Namen** verwenden, nicht Service-Namen

### 2. Ollama Network Alias Setup

**Problem:** Backend sucht `http://ollama:11434` aber Container heißt `xkg0gc00sgcg0sc0g8wowskw-180855623729`

**Lösung - Netzwerk-Alias hinzufügen:**

```bash
# Container von Netzwerk trennen
docker network disconnect coolify xkg0gc00sgcg0sc0g8wowskw-180855623729

# Mit Alias wieder verbinden
docker network connect \
  --alias ollama \
  --alias xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  coolify \
  xkg0gc00sgcg0sc0g8wowskw-180855623729

# Backend neu starten
docker restart vosss8wcg8cs80kcss8cgccc-193229452316
```

**Verifizierung:**

```bash
docker inspect xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  | jq '.[0].NetworkSettings.Networks.coolify.Aliases'

# Expected Output:
# [
#   "ollama",
#   "xkg0gc00sgcg0sc0g8wowskw-180855623729"
# ]
```

### 3. Model Setup

**Model Pull:**

```bash
docker exec xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  ollama pull qwen2.5:0.5b

# Verify
docker exec xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  ollama list
```

**Model Info:**
- Name: `qwen2.5:0.5b`
- Size: 397 MB
- Language: Multilingual (EN, DE, etc.)

---

## 🧪 Testing & Verification

### Quick Test Script

**File:** `test_axe_quick.sh`

```bash
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
```

### Full Stack Test

```bash
# Backend Health
curl -s https://api.brain.falklabs.de/health | jq .

# Expected:
# {
#   "status": "healthy",
#   "ollama_host": "http://ollama:11434",
#   "ollama_reachable": true,
#   "models_available": 1,
#   "models": ["qwen2.5:0.5b"]
# }

# AXE Health
curl -s https://api.brain.falklabs.de/api/axe/health | jq .

# Expected:
# {
#   "status": "healthy",
#   "axellm": "reachable",
#   "error": null
# }

# Chat Test
curl -s -X POST https://api.brain.falklabs.de/api/axe/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:0.5b",
    "messages": [
      {"role": "user", "content": "Was ist 2+2?"}
    ]
  }' | jq .

# Expected:
# {
#   "text": "Die Antwort ist 4...",
#   "raw": { ... }
# }
```

---

## 🔍 Troubleshooting

### Problem: "AXEllm Service nicht verfügbar (503)"

**Ursache:** AXEllm kann Ollama nicht erreichen

**Diagnose:**

```bash
# Check AXEllm logs
docker logs --tail 50 axellm-mg400ss0o80gcs0owo0ckskc

# Check environment variable
docker exec axellm-mg400ss0o80gcs0owo0ckskc env | grep OLLAMA_BASE_URL

# Check if both containers are in same network
docker inspect axellm-mg400ss0o80gcs0owo0ckskc | jq '.[0].NetworkSettings.Networks | keys'
docker inspect xkg0gc00sgcg0sc0g8wowskw-180855623729 | jq '.[0].NetworkSettings.Networks | keys'
```

**Fix:** Update `OLLAMA_BASE_URL` to use correct container name

### Problem: "Cannot connect to Ollama service"

**Ursache:** Backend findet Ollama nicht unter `http://ollama:11434`

**Diagnose:**

```bash
# Check backend logs
docker logs --tail 50 vosss8wcg8cs80kcss8cgccc-193229452316

# Check Ollama aliases
docker inspect xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  | jq '.[0].NetworkSettings.Networks.coolify.Aliases'
```

**Fix:** Add network alias (siehe Deployment Steps #2)

### Problem: Chat returns null or error

**Checklist:**

1. ✅ Model name korrekt? (`qwen2.5:0.5b` nicht `qwen:0.5b`)
2. ✅ Ollama Container läuft?
3. ✅ Model ist gepullt? (`ollama list`)
4. ✅ Netzwerk-Konnektivität? (beide im `coolify` network)
5. ✅ Environment Variables korrekt?

---

## 📊 Production Endpoints

### Public APIs

| Service | URL | Status |
|---------|-----|--------|
| Control Deck | https://control.brain.falklabs.de | ✅ Live |
| AXE UI | https://axe.brain.falklabs.de | ✅ Live |
| Backend API | https://api.brain.falklabs.de | ✅ Live |
| AXE Chat API | https://api.brain.falklabs.de/api/axe/chat | ✅ Live |

### Internal Services

| Service | Container | Network | Aliases |
|---------|-----------|---------|---------|
| Ollama | xkg0gc00sgcg0sc0g8wowskw-180855623729 | coolify | ollama, xkg0gc00... |
| AXEllm | axellm-mg400ss0o80gcs0owo0ckskc | coolify | axellm |
| Backend | vosss8wcg8cs80kcss8cgccc-193229452316 | coolify | vosss8wcg8... |

---

## 🔐 Security Notes

### Network Isolation

- ✅ Alle Services im internen `coolify` Netzwerk
- ✅ Ollama **nicht** öffentlich exposed (nur intern via Docker-Netzwerk)
- ✅ AXEllm **nicht** öffentlich exposed
- ✅ Nur Backend API ist öffentlich (über Traefik/Coolify Proxy)

### Authentication

- ✅ AXE UI: Keine Auth (öffentlicher Chat)
- ✅ Control Deck: NextAuth.js (Login required)
- ✅ Backend API: Je nach Endpoint (Skills, Missions, etc. geschützt)

### Rate Limiting

- ✅ Backend hat Rate Limiting aktiviert
- ✅ AXE Chat: Subject to backend rate limits

---

## 📈 Performance & Monitoring

### Resource Usage

```bash
# Check Ollama memory usage
docker stats xkg0gc00sgcg0sc0g8wowskw-180855623729 --no-stream

# Check AXEllm
docker stats axellm-mg400ss0o80gcs0owo0ckskc --no-stream

# Check Backend
docker stats vosss8wcg8cs80kcss8cgccc-193229452316 --no-stream
```

**Expected:**
- Ollama: ~500-800 MB RAM (mit geladenem Modell)
- AXEllm: ~50-100 MB RAM
- Backend: ~200-400 MB RAM

### Response Times

- Health Check: ~50-100ms
- Chat Request: ~1-3s (abhängig von Prompt-Länge)

### Monitoring

- Uptime Kuma: https://uptimekuma-bgo8s400o00w80804okoc040.46.224.37.114.sslip.io:3001
- Coolify Dashboard: https://coolify.falklabs.de

---

## 🔄 Maintenance

### Model Updates

```bash
# Pull new model version
docker exec xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  ollama pull qwen2.5:0.5b

# Remove old models
docker exec xkg0gc00sgcg0sc0g8wowskw-180855623729 \
  ollama rm <old-model-name>
```

### AXEllm Updates

```bash
# Via Coolify API
curl -X POST https://coolify.falklabs.de/api/v1/deploy \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"uuid":"mg400ss0o80gcs0owo0ckskc","force":true}'
```

### Backend Updates

Automatic via Coolify on git push to main branch.

---

## 🐛 Known Issues & Limitations

### 1. Coolify Compose Storage

**Issue:** Coolify speichert docker-compose.yml in Datenbank, nicht aus Git

**Workaround:** Änderungen via Coolify API (base64-encoded) pushen

**Example:**
```bash
ENCODED=$(base64 -w 0 /path/to/compose.yml)
curl -X PATCH https://coolify.falklabs.de/api/v1/services/<uuid> \
  -H "Authorization: Bearer <token>" \
  -d "{\"docker_compose_raw\": \"$ENCODED\"}"
```

### 2. Container Names vs Service Names

**Issue:** Docker DNS nutzt Container-Namen, nicht Service-Namen aus Coolify

**Solution:** Immer vollständige Container-Namen verwenden oder Netzwerk-Aliase

### 3. Model in Container-Namen

**Issue:** Test-Scripts müssen mit richtigem Modellnamen (`qwen2.5:0.5b`) aufgerufen werden

**Solution:** Environment Variable `DEFAULT_MODEL` nutzen oder Modellname in Config

---

## 📝 Changelog

### 2026-02-18 - Initial Deployment

**Commits:**
- `6ec3294` - fix(axe-stack): Configure AXEllm to use existing Ollama container
- `35c073b` - feat(axe): Add AXE Chat test script and Docker build helper

**Changes:**
- ✅ AXE UI deployed to production
- ✅ AXE Fusion module activated
- ✅ AXEllm service configured
- ✅ Ollama network alias setup
- ✅ Test scripts added

**Result:** Full AXE Chat stack operational

---

## 🎯 Success Criteria

- [x] AXE UI accessible at https://axe.brain.falklabs.de
- [x] Chat page functional
- [x] Backend API healthy
- [x] Ollama reachable from Backend
- [x] Ollama reachable from AXEllm
- [x] Chat requests return LLM responses
- [x] Response time < 5 seconds
- [x] No 503 errors
- [x] Single Ollama instance for all services

---

## 📞 Support

**Issues?** Check:
1. Container logs: `docker logs <container-name>`
2. Health endpoints: `/health` und `/api/axe/health`
3. Network connectivity: `docker network inspect coolify`
4. Environment variables: `docker exec <container> env | grep OLLAMA`

**Documentation:**
- AXE Architecture: `/docs/AXE_ARCHITECTURE.md`
- Backend API: `https://api.brain.falklabs.de/docs`
- Coolify API: `https://coolify.io/docs/api`

---

**Last Updated:** 2026-02-18
**Maintained by:** FalkLabs DevOps Team
**Version:** 1.0.0
