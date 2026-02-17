# BRAiN Coolify Deployment - Status & Dokumentation

**Stand:** 2026-01-07 04:30 Uhr  
**Status:** ✅ **ERFOLGREICH DEPLOYED**  
**Branch:** `claude/update-claude-md-Q9jY6`

---

## 🎉 Erfolgreich Deployed

### Live URLs
- ✅ **Control Deck:** https://dev.brain.falklabs.de
- ✅ **Backend API:** https://dev.brain.falklabs.de/api/health
- ✅ **API Docs:** https://dev.brain.falklabs.de/docs *(nach nächstem Deploy)*
- ✅ **AXE UI:** https://axe.dev.brain.falklabs.de

### Laufende Services: 7/8
- Backend, Control Deck, AXE UI, PostgreSQL, Redis, Qdrant, Ollama

---

## 🔧 Durchgeführte Fixes

1. **Port-Konflikte** → Alle Port-Mappings entfernt
2. **Netzwerk-Konflikte** → Feste IP-Subnetz entfernt
3. **CORS_ORIGINS** → Robustes CSV/JSON Parsing
4. **OpenWebUI** → Temporär deaktiviert (DATABASE_URL Konflikt)
5. **Traefik-Labels** → Manuell gesetzt (Coolify Bug)
6. **Coolify-Netzwerk** → Services verbunden (mw0ck04s8go048c0g4so48cc)
7. **EntryPoint** → Von `websecure` zu `https` korrigiert
8. **Backend Priority** → Priority=10 für korrektes Routing
9. **API Docs** → `/docs`, `/redoc`, `/openapi.json` hinzugefügt

---

## 📋 Finale Konfiguration

### Traefik Routing
- **backend:** dev.brain.falklabs.de → `/api/*`, `/docs` (Priority 10)
- **control_deck:** dev.brain.falklabs.de → `/` (Priority 1)
- **axe_ui:** axe.dev.brain.falklabs.de → `/`

### Commits (Branch: claude/update-claude-md-Q9jY6)
```
4ac7e6a - feat: Add /docs routes to backend
1219023 - fix: Add priority to backend router  
3bb0c32 - fix: Change entrypoint websecure→https
ee1f2b0 - fix: Connect to Coolify network
04d318e - fix: Add manual Traefik labels
```

---

## 📝 Nächste Schritte

1. **Redeploy** in Coolify für `/docs` Support
2. **GitHub Webhook** einrichten (Auto-Deploy)
3. **Branch mergen** in v2/main
4. **OpenWebUI** später als separates Projekt

---

**Letzte Aktualisierung:** 2026-01-07 04:30 Uhr  
**Alle Services operational!** ✅
