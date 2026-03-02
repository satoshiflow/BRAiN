# Control Deck Deployment Manual
## Domain: falklabs.de

## Option 1: Automated Deployment (Recommended)

### Prerequisites
1. Coolify API Token
   - Login: https://coolify.falklabs.de
   - Navigate: Settings → API Tokens
   - Create Token → Copy token

2. Set Environment Variable
```bash
export COOLIFY_TOKEN='your-token-here'
```

### Run Deployment Script
```bash
cd /home/oli/dev/brain-v2
python3 deploy_control_deck.py
```

This script will:
- ✅ Find Control Deck application
- ✅ Generate secure AUTH_SECRET
- ✅ Set environment variables
- ✅ Trigger deployment
- ✅ Save credentials to file

---

## Option 2: Manual Deployment via Coolify UI

### Step 1: Set Environment Variables

Login to https://coolify.falklabs.de → Find Control Deck Application

**Go to: Environment Variables Tab**

Add the following variables:

```bash
# Authentication (CRITICAL - generate with: openssl rand -base64 48)
AUTH_SECRET=<generate-secure-secret-here>

# API Base URL
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.falklabs.de

# Node Environment
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

### Step 2: Set Build Arguments

**Go to: Build Configuration → Build Arguments**

Add:
```bash
NEXT_PUBLIC_BRAIN_API_BASE=https://brain-api.falklabs.de
```

### Step 3: Deploy

Click "Deploy" button

Monitor logs for errors.

### Step 4: Verify Deployment

**Test Endpoints:**
```bash
# Health check
curl https://control-deck.falklabs.de

# Test AXE Identity page (in browser)
https://control-deck.falklabs.de/axe/identity

# Test AXE Knowledge page (in browser)
https://control-deck.falklabs.de/axe/knowledge
```

---

## Troubleshooting

### Build Failed - Out of Memory

**Solution:** Increase memory limits in Coolify

Go to: Resource Limits
- Memory Limit: 4096 MB
- Memory Reservation: 2048 MB

### Build Failed - TypeScript Errors

**Note:** TypeScript errors are ignored in production build (see `next.config.mjs`)

If build still fails, check Coolify Debug Logs for actual error.

### AUTH_SECRET Not Set

**Symptom:** Application crashes with "AUTH_SECRET is required"

**Solution:**
1. Generate secret: `openssl rand -base64 48`
2. Add to Environment Variables in Coolify
3. Redeploy

### API Connection Errors

**Symptom:** Frontend can't connect to backend

**Check:**
1. Backend is running at https://brain-api.falklabs.de
2. CORS is configured correctly in backend
3. NEXT_PUBLIC_BRAIN_API_BASE is set correctly

**Test Backend:**
```bash
curl https://brain-api.falklabs.de/health
curl https://brain-api.falklabs.de/api/axe/identity/active
```

---

## Post-Deployment Checklist

- [ ] Application accessible at https://control-deck.falklabs.de
- [ ] Login page works
- [ ] Dashboard loads
- [ ] AXE Identity page loads (/axe/identity)
- [ ] AXE Knowledge page loads (/axe/knowledge)
- [ ] Can create new identity
- [ ] Can create new knowledge document
- [ ] Mobile menu works on mobile devices
- [ ] No console errors in browser DevTools

---

## Backend Deployment

**Note:** Control Deck requires backend to be deployed first!

### Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/brain

# CORS Origins (CRITICAL)
CORS_ORIGINS=https://control-deck.falklabs.de,https://axe.falklabs.de

# Other backend vars...
```

### Database Migration

SSH into backend container and run:
```bash
alembic upgrade head
```

This creates:
- `axe_identities` table
- `axe_knowledge_documents` table
- Default AXE identity

---

## Security Checklist

- [ ] AUTH_SECRET is > 32 characters
- [ ] AUTH_SECRET is stored securely (password manager)
- [ ] HTTPS enabled for all domains
- [ ] CORS origins whitelisted in backend
- [ ] No secrets in git repository
- [ ] Backend API endpoints require authentication

---

## Support

### View Deployment Logs
https://coolify.falklabs.de → Application → Logs

### Debug Build Errors
https://coolify.falklabs.de → Application → Deployments → Show Debug Logs

### Check Application Status
```bash
# Via Coolify API
curl -H "Authorization: Bearer $COOLIFY_TOKEN" \
  https://coolify.falklabs.de/api/v1/applications
```

---

**Last Updated:** 2026-02-19
**Version:** 1.0.0
