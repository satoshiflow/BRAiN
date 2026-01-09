# Pull Request: Traefik Configuration Fix

**Branch:** `claude/fix-traefik-config-eYoK3` → `dev` → `main`

**Create PR here:** https://github.com/satoshiflow/BRAiN/pull/new/claude/fix-traefik-config-eYoK3

---

## Title
```
fix(coolify/traefik): correct Host() rule generation, remove UI domain override
```

---

## Description

### 🐛 Problem

**Backend returning 504 Gateway Timeout:**
```bash
curl https://dev.brain.falklabs.de/api/health
# HTTP/2 504 Gateway Timeout
```

**Traefik Parser Errors:**
```
error while parsing rule Host(``) && PathPrefix(`dev.brain.falklabs.de`): empty args for matcher Host, []
```

**Affected Services:**
- ❌ `backend` (dev.brain.falklabs.de)
- ❌ `control_deck` (dev.brain.falklabs.de)
- ❌ `axe_ui` (axe.dev.brain.falklabs.de)

---

## 🔍 Root Cause

**Coolify generated faulty Traefik HTTP Router labels:**

❌ **Incorrect (before):**
```yaml
traefik.http.routers.http-0-...-backend.rule: "Host(``) && PathPrefix(`dev.brain.falklabs.de`)"
```

✅ **Correct (after):**
```yaml
traefik.http.routers.http-0-...-backend.rule: "Host(`dev.brain.falklabs.de`) && PathPrefix(`/`)"
```

**Why:** Coolify UI domains configured with `https://` prefix caused label generation bug.

---

## ✅ Solution

1. **Correct domain format** in Coolify UI: `dev.brain.falklabs.de` (ohne https://)
2. **Use "Generate Domain"** feature für korrektes Format
3. **Delete "Domains for backend"** in Coolify UI komplett
4. **Redeploy** → docker-compose.yml labels sind source of truth

---

## 🧪 Validation

### ✅ Backend API
```bash
curl https://dev.brain.falklabs.de/api/health
{"status":"ok","message":"BRAiN Core Backend is running","version":"0.3.0"}
```

### ✅ Traefik Logs
- Letzte "empty args" errors: 14:21:26 (vor Fix)
- Seit 15:34: **Keine neuen Errors** ✅

### ✅ SSL Certificates
- Let's Encrypt certificates für alle 3 Services ✅

---

## 📝 Files Changed

- `PHASE_0_VALIDATION_REPORT.md` - Validation report
- `COOLIFY_UI_FIX_EXACT_STEPS.md` - Fix guide
- `fix-*.sh` - Reference scripts

**Keine Code-Änderungen.** Nur Dokumentation.

---

## 🎓 Lessons Learned

1. **Coolify Domains:** Immer ohne `https://` prefix
2. **Label Priority:** Coolify UI überschreibt docker-compose.yml
3. **Solution:** UI domains löschen → compose labels nutzen

---

## ✅ Testing

- [x] Backend 200 OK
- [x] Control Deck accessible
- [x] AXE UI accessible
- [x] SSL certificates valid
- [x] Traefik keine Errors

---

**Status:** ✅ Phase 0 COMPLETED - Ready to merge
