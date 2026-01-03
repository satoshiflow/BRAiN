# UTF-8 Encoding Fix - Deployment Guide

**Issue:** German characters (ä, ö, ü) displayed as garbled text (Ã¤, Ã¶, Ã¼)
**Cause:** FastAPI JSON responses missing explicit `charset=utf-8` in Content-Type header
**Fix:** Added UTF8Middleware to ensure all responses have correct charset

---

## What Was Fixed

### Problem
```
Expected: "BRAiN Dev - Backend läuft"
Actual:   "BRAiN Dev - Backend lÃ¤uft"
```

This is a classic UTF-8 → Latin-1 encoding mismatch:
- Backend sends UTF-8 encoded bytes
- Browser/client interprets as Latin-1
- Result: `ä` (UTF-8: 0xC3 0xA4) → `Ã¤` (Latin-1: 0xC3='Ã', 0xA4='¤')

### Solution
Added middleware to explicitly set `charset=utf-8` in Content-Type header:

```python
# backend/main_minimal_v3.py

class UTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Ensure Content-Type has charset=utf-8
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(UTF8Middleware)
```

---

## Deployment Steps

### 1. SSH to Server
```bash
ssh root@brain.falklabs.de
```

### 2. Pull Latest Code
```bash
cd /srv/dev
git pull origin claude/infrastructure-setup-complete-h1NXi
```

**Expected output:**
```
remote: Enumerating objects: 7, done.
remote: Counting objects: 100% (7/7), done.
From github.com:satoshiflow/BRAiN
 * branch            claude/infrastructure-setup-complete-h1NXi -> FETCH_HEAD
   66514de5..ab5cd920  claude/infrastructure-setup-complete-h1NXi -> origin/claude/infrastructure-setup-complete-h1NXi
Updating 66514de5..ab5cd920
Fast-forward
 backend/main_minimal_v3.py | 14 ++++++++++++++
 1 file changed, 14 insertions(+)
```

### 3. Rebuild Backend Container
```bash
cd /srv/dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend
```

**Expected:** Build completes successfully with UTF8Middleware included

### 4. Restart Backend
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend
```

### 5. Verify Container Started
```bash
docker compose ps backend
docker compose logs backend --tail 20
```

**Expected logs:**
```
✅ PostgreSQL connection pool created
✅ Redis connection established
✅ Events service initialized
INFO:     Application startup complete.
```

---

## Testing the Fix

### Test 1: Check Content-Type Header (Local)
```bash
curl -i http://localhost:8001/api/health
```

**Expected:**
```http
HTTP/1.1 200 OK
content-type: application/json; charset=utf-8
content-length: 89

{"status":"healthy","mode":"minimal-v3","timestamp":1735934567.89,"version":"0.3.0"}
```

✅ **Key:** `content-type: application/json; charset=utf-8` (with charset!)

### Test 2: Check Content-Type Header (HTTPS)
```bash
curl -i https://dev.brain.falklabs.de/api/health
```

**Expected:** Same as above, with charset=utf-8

### Test 3: Test with German Characters
Create a test event with German text:

```bash
curl -X POST http://localhost:8001/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test_encoding",
    "severity": "info",
    "message": "Backend läuft einwandfrei! Äpfel, Öl, Übung",
    "source": "encoding_test",
    "details": {"test": "ÄÖÜäöüß"}
  }'
```

**Expected response (properly encoded):**
```json
{
  "id": 15,
  "event_type": "test_encoding",
  "severity": "info",
  "message": "Backend läuft einwandfrei! Äpfel, Öl, Übung",
  "source": "encoding_test",
  "details": {"test": "ÄÖÜäöüß"},
  "created_at": "2026-01-03T15:30:00",
  "updated_at": "2026-01-03T15:30:00"
}
```

Retrieve and verify:
```bash
curl http://localhost:8001/api/events/15
```

**Expected:** German characters display correctly in terminal

### Test 4: Browser Test
Open in browser: https://dev.brain.falklabs.de/api/health

**Expected:** If there's any German text in future responses, it displays correctly

---

## Before & After

### Before Fix
```http
HTTP/1.1 200 OK
content-type: application/json
content-length: 89
```
❌ Missing `charset=utf-8` → Browser guesses encoding → Garbled text

### After Fix
```http
HTTP/1.1 200 OK
content-type: application/json; charset=utf-8
content-length: 89
```
✅ Explicit `charset=utf-8` → Browser uses UTF-8 → Correct display

---

## Technical Details

### Why This Happens

1. **FastAPI Default Behavior:**
   - FastAPI sends JSON as UTF-8 bytes
   - But doesn't always include `charset=utf-8` in Content-Type header
   - Browser must guess encoding (often defaults to Latin-1)

2. **UTF-8 Byte Sequence for "ä":**
   - UTF-8: `0xC3 0xA4` (2 bytes)
   - Latin-1 interpretation: `Ã` (0xC3) + `¤` (0xA4) = "Ã¤"

3. **The Fix:**
   - Middleware intercepts all responses
   - Adds explicit `charset=utf-8` to Content-Type
   - Browser sees charset → Uses UTF-8 → Displays correctly

### Affected Characters

| Character | UTF-8 Bytes | Wrong Display | Correct Display |
|-----------|-------------|---------------|-----------------|
| ä | C3 A4 | Ã¤ | ä |
| ö | C3 B6 | Ã¶ | ö |
| ü | C3 BC | Ã¼ | ü |
| Ä | C3 84 | Ã„ | Ä |
| Ö | C3 96 | Ã– | Ö |
| Ü | C3 9C | Ãœ | Ü |
| ß | C3 9F | ÃŸ | ß |

---

## Rollback (If Needed)

If the fix causes any issues:

```bash
cd /srv/dev
git checkout 66514de5  # Previous commit before UTF-8 fix
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend
```

---

## Additional Notes

### Applies to All Endpoints

The UTF8Middleware applies to **all** JSON endpoints:
- ✅ `/api/health`
- ✅ `/api/events`
- ✅ `/api/events/stats`
- ✅ All future endpoints

### No Performance Impact

The middleware is lightweight:
- Only modifies header string
- No data copying or transformation
- Negligible overhead (~0.1ms)

### Future Compatibility

This fix ensures:
- Correct display of German umlauts
- Support for all Unicode characters (emoji, Chinese, Arabic, etc.)
- Compliance with HTTP standards (RFC 2616, RFC 7231)
- Better browser compatibility

---

## Success Criteria

✅ **Fix is successful when:**

1. `curl -i /api/health` shows `charset=utf-8` in Content-Type
2. Creating events with German text returns correctly encoded JSON
3. Browser displays German characters without garbling
4. No errors in backend logs related to encoding

---

## Related Files Modified

- `backend/main_minimal_v3.py` (+14 lines)
  - Added UTF8Middleware class
  - Added imports (BaseHTTPMiddleware, Request)
  - Applied middleware to app

---

**Commit:** `ab5cd920`
**Branch:** `claude/infrastructure-setup-complete-h1NXi`
**Status:** ✅ Ready for deployment
**Test Status:** Awaiting server testing

---

**Date:** 2026-01-03
**Issue:** UTF-8 encoding garbled text
**Fix:** UTF8Middleware
**Priority:** High (UX issue affecting German text display)
