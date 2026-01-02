# Hetzner DNS Integration Guide

**Version:** Sprint II (2.0.0)
**Last Updated:** 2025-12-25
**Author:** WebGenesis Team

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [API Endpoints](#api-endpoints)
5. [WebGenesis Integration](#webgenesis-integration)
6. [Allowlist Policy](#allowlist-policy)
7. [Security Model](#security-model)
8. [Troubleshooting](#troubleshooting)
9. [Safety Warnings](#safety-warnings)
10. [Best Practices](#best-practices)

---

## Overview

The Hetzner DNS module provides automated DNS record management for WebGenesis deployments.

### Features

- ✅ **Idempotent upsert** - Create/update/no-op logic
- ✅ **Allowlist enforcement** - Strict zone access control
- ✅ **ENV-based defaults** - Automatic IP injection
- ✅ **LOCAL-only access** - Maximum security (DMZ/EXTERNAL blocked)
- ✅ **Non-blocking deployment** - DNS failures don't fail sites
- ✅ **Comprehensive logging** - Full audit trail

### Architecture

```
WebGenesis Deployment
      ↓
  Health Check Pass
      ↓
  DNS Module (if enabled)
      ↓
  Hetzner DNS API (HTTPS)
      ↓
  DNS Record Created/Updated
```

**Trust Tier:** STRICT LOCAL only (localhost requests only)

---

## Prerequisites

### 1. Hetzner DNS Account

**Required:**
- Active Hetzner DNS account
- Domain(s) delegated to Hetzner nameservers
- API token with DNS management permissions

**Get API Token:**
1. Login to https://dns.hetzner.com
2. Navigate to **API Tokens**
3. Create new token with scope: **DNS Management**
4. Copy token (shown once only)

**Verify Domain Delegation:**
```bash
# Check nameservers
dig NS example.com

# Should return Hetzner nameservers:
# ns1.hetzner.com
# ns2.hetzner.com
# ns3.hetzner.com
```

---

### 2. Public IP Address

**Required for A/AAAA records:**
- Static public IPv4 address
- Optional: Static public IPv6 address

**Find Your Public IP:**
```bash
# IPv4
curl -4 ifconfig.me

# IPv6
curl -6 ifconfig.me
```

---

### 3. Zone Ownership

**⚠️ CRITICAL:** You must **own** or **control** all zones in the allowlist.

**Verify Zone Ownership:**
```bash
# List zones in Hetzner DNS account
curl -H "Auth-API-Token: YOUR_TOKEN" https://dns.hetzner.com/api/v1/zones
```

**Consequences of Misconfiguration:**
- Unauthorized DNS changes to domains you don't own
- Potential domain hijacking attempts
- Service disruption for legitimate owners
- Legal liability

---

## Configuration

### Environment Variables

**Required:**

```bash
# Hetzner DNS API Token
HETZNER_DNS_API_TOKEN=your_token_here

# Allowed DNS zones (comma-separated)
HETZNER_DNS_ALLOWED_ZONES=example.com,subdomain.example.com
```

**Optional:**

```bash
# Default TTL for DNS records (seconds, default: 300)
HETZNER_DNS_DEFAULT_TTL=300

# Public IPv4 address (used when record value not specified)
BRAIN_PUBLIC_IPV4=203.0.113.10

# Public IPv6 address (used when record value not specified)
BRAIN_PUBLIC_IPV6=2001:db8::1

# API request timeout (seconds, default: 30)
HETZNER_DNS_API_TIMEOUT=30
```

### Configuration Example

**`.env` file:**
```bash
# Hetzner DNS Configuration
HETZNER_DNS_API_TOKEN=abc123def456ghi789jkl012mno345pqr678
HETZNER_DNS_ALLOWED_ZONES=example.com,blog.example.com,api.example.com
HETZNER_DNS_DEFAULT_TTL=300
BRAIN_PUBLIC_IPV4=203.0.113.10
BRAIN_PUBLIC_IPV6=2001:db8::1
```

**⚠️ Security:**
- Never commit `.env` to Git
- Use secret management for production (Vault, AWS Secrets Manager, etc.)
- Rotate API tokens regularly (90 days recommended)

---

## API Endpoints

### 1. Apply DNS Record (Idempotent)

**Endpoint:**
```
POST /api/dns/hetzner/apply
```

**Trust Tier:** STRICT LOCAL only (DMZ/EXTERNAL → HTTP 403)

**Request Body:**
```json
{
  "zone": "example.com",
  "record_type": "A",
  "name": "@",
  "value": "203.0.113.10",
  "ttl": 300
}
```

**Parameters:**
- `zone` (required) - Zone name (must be in allowlist)
- `record_type` (required) - A, AAAA, CNAME, MX, TXT, etc.
- `name` (required) - Record name (`@` for root, `www`, `blog`, etc.)
- `value` (optional) - Record value (if omitted: use `BRAIN_PUBLIC_IPV4/IPv6`)
- `ttl` (optional) - TTL in seconds (default: `HETZNER_DNS_DEFAULT_TTL`)

**Response (Created):**
```json
{
  "success": true,
  "zone": "example.com",
  "record_type": "A",
  "name": "@",
  "value": "203.0.113.10",
  "ttl": 300,
  "action": "created",
  "record_id": "rec_abc123",
  "message": "DNS record created successfully",
  "errors": [],
  "warnings": []
}
```

**Response (Updated):**
```json
{
  "success": true,
  "zone": "example.com",
  "record_type": "A",
  "name": "@",
  "value": "203.0.113.11",
  "ttl": 300,
  "action": "updated",
  "record_id": "rec_abc123",
  "message": "DNS record updated successfully (old value: 203.0.113.10)",
  "errors": [],
  "warnings": []
}
```

**Response (No Change):**
```json
{
  "success": true,
  "zone": "example.com",
  "record_type": "A",
  "name": "@",
  "value": "203.0.113.10",
  "ttl": 300,
  "action": "no_change",
  "record_id": "rec_abc123",
  "message": "DNS record already exists with same value (no change needed)",
  "errors": [],
  "warnings": []
}
```

**Error Response (Zone Not Allowed):**
```json
{
  "error": "zone_not_allowed",
  "message": "Zone 'evil.com' not in allowlist",
  "zone": "evil.com",
  "errors": ["Zone not allowed: evil.com"]
}
```

**cURL Example:**
```bash
# From localhost only
curl -X POST http://localhost:8000/api/dns/hetzner/apply \
  -H "Content-Type: application/json" \
  -d '{
    "zone": "example.com",
    "record_type": "A",
    "name": "www",
    "value": "203.0.113.10",
    "ttl": 600
  }'
```

---

### 2. List Allowed Zones

**Endpoint:**
```
GET /api/dns/hetzner/zones
```

**Trust Tier:** STRICT LOCAL only

**Response:**
```json
{
  "zones": [
    {
      "id": "zone_abc123",
      "name": "example.com",
      "ttl": 3600,
      "registrar": "hetzner",
      "legacy_dns_host": "",
      "legacy_ns": [],
      "ns": ["ns1.hetzner.com", "ns2.hetzner.com", "ns3.hetzner.com"],
      "created": "2025-01-01T00:00:00Z",
      "verified": "2025-01-01T01:00:00Z",
      "modified": "2025-01-01T02:00:00Z",
      "project": null,
      "owner": "owner@example.com",
      "permission": "owner",
      "zone_type": "master",
      "status": "verified",
      "paused": false,
      "is_secondary_dns": false,
      "txt_verification": {},
      "records_count": 5
    }
  ],
  "total_count": 1,
  "allowed_zones": ["example.com"]
}
```

**cURL Example:**
```bash
curl http://localhost:8000/api/dns/hetzner/zones
```

---

## WebGenesis Integration

### Automatic DNS on Deployment

DNS records are automatically applied **after successful health check** during WebGenesis deployment.

**Enable in Website Spec:**

```json
{
  "name": "my-site",
  "domain": "example.com",
  "deploy": {
    "target": "compose",
    "domain": "www.example.com",
    "ssl_enabled": true,
    "healthcheck_path": "/",
    "dns": {
      "enable": true,
      "zone": "example.com",
      "record_type": "A",
      "name": "www",
      "value": null,
      "ttl": 300
    }
  }
}
```

**DNS Configuration:**
- `enable: true` - Turn on DNS automation
- `zone` - Zone name (must be in `HETZNER_DNS_ALLOWED_ZONES`)
- `record_type` - A, AAAA, or CNAME
- `name` - Record name (`@` for root, `www`, `blog`, etc.)
- `value: null` - Use `BRAIN_PUBLIC_IPV4` from ENV
- `ttl` - DNS TTL in seconds (default: 300)

---

### Deployment Workflow with DNS

```
1. User submits spec with dns.enable=true
2. WebGenesis generates source
3. WebGenesis builds artifacts
4. WebGenesis deploys with Docker Compose
5. Health check passes ✅
6. DNS module applies record
   ├─ Check zone allowlist
   ├─ Find existing record (if any)
   ├─ Idempotent upsert:
   │  ├─ Create if missing
   │  ├─ Update if different
   │  └─ No-op if identical
   └─ Log result
7. Deployment succeeds (even if DNS fails)
```

**Non-Blocking Behavior:**
- DNS failures are logged as **warnings**, not errors
- Deployment continues and succeeds
- Site remains deployed and accessible
- DNS warnings included in deployment response

**Example Deployment Response:**
```json
{
  "result": {
    "success": true,
    "site_id": "my-site_20250101120000",
    "url": "http://localhost:8080",
    "warnings": [
      "DNS record created: www.example.com -> 203.0.113.10 (may take up to 5 minutes to propagate)"
    ]
  }
}
```

---

### DNS Propagation

**Timeline:**
- **Hetzner API:** Immediate (record created instantly)
- **Nameservers:** 1-2 minutes (ns1/ns2/ns3.hetzner.com)
- **Global DNS:** 5-60 minutes (depends on TTL and caching)

**Verify Propagation:**
```bash
# Query Hetzner nameservers directly
dig @ns1.hetzner.com www.example.com A

# Query your local DNS
dig www.example.com A

# Check global propagation
# https://www.whatsmydns.net/
```

**Reduce Propagation Time:**
- Lower TTL before changes (e.g., 60 seconds)
- Wait for TTL expiry
- Make changes
- Restore higher TTL after (e.g., 3600 seconds)

---

## Allowlist Policy

### Purpose

The allowlist prevents unauthorized DNS changes to domains you don't own.

**Without Allowlist:**
```
❌ User submits spec with zone="evil.com" (domain they don't own)
❌ DNS module creates record for evil.com
❌ Domain hijacking attempt succeeds
```

**With Allowlist:**
```
✅ User submits spec with zone="evil.com"
✅ DNS module checks allowlist
✅ Zone not found in HETZNER_DNS_ALLOWED_ZONES
✅ Request rejected with HTTP 403
```

---

### Configuration

**`.env` file:**
```bash
# Only these zones allowed:
HETZNER_DNS_ALLOWED_ZONES=example.com,blog.example.com,api.example.com
```

**Behavior:**
- Comma-separated list of allowed zones
- Exact match only (no wildcards)
- Case-sensitive
- Spaces trimmed automatically

---

### Subdomain Policy

**Question:** Do I need to add every subdomain?

**Answer:** It depends on your use case.

**Option 1: Zone-level allowlist (Recommended)**
```bash
HETZNER_DNS_ALLOWED_ZONES=example.com
```

**Allows:**
- `@.example.com` (root)
- `www.example.com`
- `blog.example.com`
- `api.example.com`
- Any subdomain under `example.com`

**Option 2: Subdomain-level allowlist (Strict)**
```bash
HETZNER_DNS_ALLOWED_ZONES=www.example.com,blog.example.com
```

**Allows:**
- `www.example.com` only
- `blog.example.com` only

**Blocks:**
- `@.example.com` (root)
- `api.example.com`
- Any other subdomain

**Recommendation:** Use Option 1 (zone-level) unless you have specific security requirements.

---

### Updating Allowlist

**To add a zone:**
1. Update `.env`:
   ```bash
   HETZNER_DNS_ALLOWED_ZONES=example.com,newzone.com
   ```
2. Restart backend:
   ```bash
   docker compose restart backend
   ```

**To remove a zone:**
1. Update `.env` (remove from list)
2. Restart backend

**⚠️ Note:** Allowlist changes require backend restart (no hot reload).

---

## Security Model

### Trust Tier Enforcement: STRICT LOCAL ONLY

**Policy:**
- DNS endpoints are **STRICTLY** LOCAL trust tier only
- DMZ requests → HTTP 403
- EXTERNAL requests → HTTP 403
- Only localhost requests allowed

**Rationale:**
- DNS changes are **high-risk** operations (domain hijacking potential)
- DMZ gateways too broad for DNS access
- Localhost ensures operator physically on server

**Enforcement:**
```python
# router.py
async def validate_local_only(request: Request):
    context = await validator.validate_request(...)

    if context.trust_tier != TrustTier.LOCAL:
        raise HTTPException(403, detail={
            "error": "DNS operations forbidden",
            "reason": "DNS operations require LOCAL trust tier (localhost only)",
            "allowed": "LOCAL",
            "denied": ["DMZ", "EXTERNAL"]
        })
```

**Access Methods:**
- ✅ Direct localhost: `curl http://localhost:8000/api/dns/...`
- ✅ SSH tunnel: `ssh -L 8000:localhost:8000 user@server`
- ❌ DMZ gateway: Blocked
- ❌ Public internet: Blocked

---

### Allowlist Enforcement

**All DNS operations check allowlist:**
- Apply record: Zone must be in `HETZNER_DNS_ALLOWED_ZONES`
- List zones: Returns only allowlisted zones

**Bypass Attempts:**
- Path traversal: Blocked (zone name validated)
- SQL injection: Not applicable (no SQL)
- SSRF: Not applicable (HTTPS client only)

---

### API Token Security

**Best Practices:**
1. **Never commit to Git** - Use `.env` or secret manager
2. **Rotate regularly** - 90 days recommended
3. **Scope minimal permissions** - DNS management only
4. **Monitor token usage** - Check Hetzner audit logs
5. **Revoke on compromise** - Immediately revoke and rotate

**Token Storage:**
- Development: `.env` file (gitignored)
- Production: Environment variables or secret manager (Vault, AWS Secrets Manager)

---

### Audit Trail

**All DNS operations logged:**
- Apply record: Success/failure, action (created/updated/no_change)
- Zone list: Request count, allowed zones
- Allowlist violations: Zone name, requester IP

**Log Format:**
```
[INFO] Applying DNS records for my-site: A www.example.com
[INFO] ✅ DNS record created: A www.example.com -> 203.0.113.10 (ttl=300)
[ERROR] ❌ DNS automation failed for my-site: Zone 'evil.com' not in allowlist
```

**Integration:**
- Current: Loguru structured logs
- Future: WebGenesis audit events

---

## Troubleshooting

### Issue: DNS Record Not Created

**Symptoms:**
- Deployment succeeds
- DNS warnings in response
- Record not in Hetzner DNS

**Diagnosis:**
```bash
# Check ENV configuration
env | grep HETZNER_DNS

# Check allowlist
echo $HETZNER_DNS_ALLOWED_ZONES

# Test manually
curl -X POST http://localhost:8000/api/dns/hetzner/apply \
  -H "Content-Type: application/json" \
  -d '{"zone":"example.com","record_type":"A","name":"@","value":"203.0.113.10"}'
```

**Solutions:**
1. Verify zone in allowlist: `HETZNER_DNS_ALLOWED_ZONES=example.com,...`
2. Check API token: `HETZNER_DNS_API_TOKEN=...` (not empty)
3. Verify token permissions in Hetzner DNS portal
4. Check backend logs: `docker compose logs backend | grep -i dns`

---

### Issue: HTTP 403 Forbidden (Trust Tier)

**Symptoms:**
```json
{
  "error": "DNS operations forbidden",
  "trust_tier": "dmz",
  "reason": "DNS operations require LOCAL trust tier (localhost only)"
}
```

**Diagnosis:**
- Request not from localhost
- DMZ gateway headers present

**Solutions:**
1. Use localhost: `curl http://localhost:8000/api/dns/...`
2. SSH tunnel: `ssh -L 8000:localhost:8000 user@server`
3. Remove DMZ headers (if testing manually)

---

### Issue: Zone Not in Allowlist

**Symptoms:**
```json
{
  "error": "zone_not_allowed",
  "message": "Zone 'example.com' not in allowlist",
  "zone": "example.com"
}
```

**Diagnosis:**
```bash
# Check allowlist
echo $HETZNER_DNS_ALLOWED_ZONES

# Check for typos
# example.com vs example.org
# example.com vs www.example.com
```

**Solutions:**
1. Add zone to allowlist in `.env`
2. Restart backend: `docker compose restart backend`
3. Verify case sensitivity (use exact match)

---

### Issue: DNS Record Not Updating

**Symptoms:**
- Apply returns `action: no_change`
- Record value unchanged
- Expected update to new IP

**Diagnosis:**
```bash
# Check existing record
dig @ns1.hetzner.com www.example.com A

# Check API response
curl -X POST http://localhost:8000/api/dns/hetzner/apply \
  -d '{"zone":"example.com","record_type":"A","name":"www","value":"NEW_IP"}'
```

**Solutions:**
1. Verify `value` parameter in request (not using old IP)
2. Check if TTL also needs update (TTL comparison included)
3. Force update by changing both value and TTL

---

### Issue: Slow DNS Propagation

**Symptoms:**
- Record created in Hetzner
- Still resolves to old IP
- Propagation takes hours

**Diagnosis:**
```bash
# Check Hetzner nameservers (should be fast)
dig @ns1.hetzner.com www.example.com A

# Check local DNS
dig www.example.com A

# Check TTL
dig www.example.com A | grep -i ttl
```

**Solutions:**
1. Wait for old TTL to expire
2. Flush local DNS cache:
   ```bash
   # Linux
   sudo systemd-resolve --flush-caches

   # macOS
   sudo dscacheutil -flushcache

   # Windows
   ipconfig /flushdns
   ```
3. Use Hetzner nameservers directly for testing

---

## Safety Warnings

### ⚠️ Zone Ownership Verification

**CRITICAL:** Only add zones you **own** or **control** to the allowlist.

**Consequences of unauthorized changes:**
- **Domain hijacking** - Redirect traffic to attacker servers
- **Service disruption** - Break legitimate domain owner's services
- **Legal liability** - Unauthorized DNS changes may violate laws
- **Reputation damage** - Abuse of Hetzner API leads to account suspension

**Verification Steps:**
1. Login to domain registrar
2. Verify ownership
3. Confirm nameservers delegated to Hetzner
4. Test DNS changes in staging first

---

### ⚠️ TTL Considerations

**Low TTL (60-300 seconds):**
- ✅ Fast propagation of changes
- ❌ Higher query load on nameservers
- ❌ More bandwidth usage

**High TTL (3600-86400 seconds):**
- ✅ Lower query load
- ✅ Less bandwidth usage
- ❌ Slow propagation of changes

**Recommendations:**
- **Development:** 300 seconds (5 minutes)
- **Production:** 3600 seconds (1 hour)
- **Before changes:** Lower to 60 seconds, wait for expiry
- **After changes:** Restore to 3600 seconds

---

### ⚠️ Record Type Caveats

**A Records:**
- Point to IPv4 address
- Most common
- Value: `203.0.113.10`

**AAAA Records:**
- Point to IPv6 address
- Less common
- Value: `2001:db8::1`

**CNAME Records:**
- Alias to another domain
- Cannot coexist with A/AAAA at same name
- Value: `target.example.com`

**⚠️ WARNING:** Creating CNAME at `@` (root) violates RFC and may break email (MX records).

---

### ⚠️ Deployment Failures (Non-Blocking)

**DNS failures do NOT fail deployments:**
- Site remains deployed
- DNS errors logged as warnings
- Manual DNS configuration may be needed

**Example:**
```
Deployment: ✅ Success
Health Check: ✅ Healthy
DNS Automation: ❌ Failed (zone not in allowlist)
```

**Result:**
- Site accessible at `http://localhost:8080`
- DNS not configured (manual setup needed)

**Manual DNS Setup:**
1. Login to Hetzner DNS
2. Create record manually
3. Or: Add zone to allowlist and retry deployment

---

## Best Practices

### 1. Staging First, Production Second

**Always test DNS changes in staging:**
1. Use separate staging domain (`staging.example.com`)
2. Add to allowlist
3. Test WebGenesis deployment with DNS enabled
4. Verify propagation
5. Only then deploy to production

---

### 2. Use ENV Defaults for IPs

**Instead of hardcoding IPs in specs:**
```json
{
  "dns": {
    "value": null  // ✅ Use BRAIN_PUBLIC_IPV4 from ENV
  }
}
```

**Benefits:**
- Single source of truth (ENV)
- Easy IP rotation (update ENV, redeploy)
- No secrets in specs/Git

---

### 3. Monitor DNS Changes

**Setup monitoring:**
1. DNS change alerts (Hetzner email notifications)
2. Log aggregation (grep DNS logs daily)
3. External DNS monitoring (UptimeRobot, Pingdom)

**Alert on:**
- Unexpected DNS changes
- Allowlist violations
- API authentication failures

---

### 4. Document Zone Ownership

**Maintain inventory:**
```
example.com:
  - Owner: john@example.com
  - Registrar: Namecheap
  - Nameservers: Hetzner
  - Purpose: Production site

staging.example.com:
  - Owner: john@example.com
  - Registrar: Namecheap
  - Nameservers: Hetzner
  - Purpose: Staging environment
```

**Update on changes:**
- Zone additions
- Ownership transfers
- Registrar migrations

---

### 5. Rotate API Tokens

**Token rotation schedule:**
1. Create new token in Hetzner
2. Update `.env` with new token
3. Restart backend
4. Test DNS operations
5. Revoke old token
6. Document rotation date

**Frequency:** 90 days recommended

---

### 6. Use CNAME for Flexibility

**Instead of A records:**
```json
{
  "dns": {
    "record_type": "CNAME",
    "name": "www",
    "value": "lb.example.com"  // Load balancer
  }
}
```

**Benefits:**
- Change backend IPs without DNS updates
- Point multiple names to single target
- Easier load balancer integration

**⚠️ Limitation:** CNAME cannot be used at root (`@`).

---

## Summary

Hetzner DNS integration provides automated DNS management for WebGenesis deployments:

✅ **Idempotent upsert** - Safe to retry
✅ **Allowlist enforcement** - Prevent unauthorized changes
✅ **STRICT LOCAL access** - Maximum security
✅ **Non-blocking deployment** - DNS failures don't break sites
✅ **ENV-based defaults** - Easy IP management
✅ **Comprehensive logging** - Full audit trail

**Quickstart:**
1. Get Hetzner DNS API token
2. Configure `.env` with token and allowlist
3. Add `dns` config to WebGenesis spec
4. Deploy site
5. Verify DNS propagation

**Support:**
- Hetzner DNS Docs: https://dns.hetzner.com/api-docs
- Issues: Create GitHub issue
- Questions: Check CLAUDE.md documentation

---

**Document Version:** Sprint II (2.0.0)
**Last Updated:** 2025-12-25
