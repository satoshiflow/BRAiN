# 🌐 DNS Migration Plan - do.de → Hetzner DNS

**Current Provider:** Domain Offensive (do.de)
**Target Provider:** Hetzner DNS
**Reason:** Hetzner DNS API for automated DNS management with Coolify

---

## 📋 Overview

### Current State
```
Domain: falklabs.de
Provider: do.de (Domain Offensive)
Nameservers: do.de nameservers

Subdomains (assumption):
├── brain.falklabs.de       → 46.224.37.114 (A Record)
├── dev.brain.falklabs.de   → ? (needs to be created)
├── stage.brain.falklabs.de → ? (needs to be created)
└── coolify.falklabs.de     → ? (needs to be created)
```

### Target State
```
Domain: falklabs.de
Provider: Hetzner DNS (via Hetzner Cloud Console)
Nameservers: Hetzner DNS nameservers

Subdomains:
├── brain.falklabs.de       → 46.224.37.114 (A Record)
├── dev.brain.falklabs.de   → 46.224.37.114 (A Record)
├── stage.brain.falklabs.de → 46.224.37.114 (A Record)
├── coolify.falklabs.de     → 46.224.37.114 (A Record)
└── ... (other existing records)
```

---

## 🎯 Two Options

### Option A: Full Migration to Hetzner DNS (Recommended)

**Advantages:**
- ✅ Full Hetzner API integration
- ✅ Coolify can auto-manage DNS records
- ✅ Automatic SSL via DNS-01 challenge (optional)
- ✅ All domains in one place

**Disadvantages:**
- ⚠️ Domain remains registered at do.de (separate from DNS)
- ⚠️ Need to update nameservers at do.de

**Time:** ~30 minutes + DNS propagation (0-48h)

---

### Option B: Manual DNS Records (Temporary)

**Advantages:**
- ✅ Quick setup (no provider change)
- ✅ No nameserver changes
- ✅ No DNS propagation wait

**Disadvantages:**
- ❌ No Hetzner API integration
- ❌ Manual DNS record creation for each subdomain
- ❌ SSL via HTTP-01 challenge only (port 80 required)

**Time:** ~10 minutes

---

## 🚀 RECOMMENDED: Option A (Full Migration)

### Phase 1: Preparation

#### Step 1: Document Current DNS Records

**On do.de Control Panel:**
1. Login to do.de
2. Go to Domain Management → falklabs.de
3. Export/Screenshot ALL DNS records:
   - A Records
   - CNAME Records
   - MX Records (email!)
   - TXT Records (SPF, DKIM, etc.)
   - Other records

**Example:**
```
Type  | Name              | Value
------|-------------------|------------------
A     | @                 | 46.224.37.114
A     | brain             | 46.224.37.114
MX    | @                 | mail.falklabs.de (priority 10)
TXT   | @                 | "v=spf1 ..."
TXT   | _dmarc            | "v=DMARC1; ..."
CNAME | www               | falklabs.de
... (all other records)
```

⚠️ **CRITICAL: Don't forget MX records (email will break!)** ⚠️

#### Step 2: Create Hetzner DNS Zone

**Hetzner Cloud Console:**
1. Login to https://console.hetzner.cloud/
2. Navigate to **DNS**
3. Click **"Add Zone"**
4. Enter domain: `falklabs.de`
5. Click **"Create Zone"**

**Result:**
- Hetzner provides nameservers:
  - `hydrogen.ns.hetzner.com`
  - `oxygen.ns.hetzner.com`
  - `helium.ns.hetzner.de`

#### Step 3: Replicate DNS Records in Hetzner

**For EACH record from Step 1:**

1. Hetzner DNS → falklabs.de → **"Add Record"**
2. Copy Type, Name, Value from do.de
3. **Verify MX records especially!**

**New Records for BRAiN + Coolify:**
```
Type  | Name     | Value           | TTL
------|----------|-----------------|-----
A     | brain    | 46.224.37.114   | 300
A     | dev      | 46.224.37.114   | 300
A     | stage    | 46.224.37.114   | 300
A     | coolify  | 46.224.37.114   | 300
```

**Note:** `brain` might already exist - just verify IP.

#### Step 4: Generate Hetzner API Token

**Hetzner Cloud Console:**
1. Settings → **API Tokens**
2. Click **"Generate API Token"**
3. Name: `Coolify DNS Management`
4. Permissions: **Read & Write**
5. Copy token: `xxxxxxxxxxxxxxxxxxxxxxxxxx`
6. **SAVE SECURELY** (only shown once!)

---

### Phase 2: Testing (Before Switching Nameservers)

#### Step 1: Test DNS Resolution

**On your local machine:**
```bash
# Test against Hetzner nameservers directly
dig @hydrogen.ns.hetzner.com brain.falklabs.de
dig @hydrogen.ns.hetzner.com dev.falklabs.de
dig @hydrogen.ns.hetzner.com coolify.falklabs.de

# Should return: 46.224.37.114
```

#### Step 2: Verify MX Records

```bash
dig @hydrogen.ns.hetzner.com falklabs.de MX

# Should return your mail server
```

⚠️ **If MX records are wrong, email will break after nameserver switch!** ⚠️

---

### Phase 3: Nameserver Switch

#### Step 1: Update Nameservers at do.de

**do.de Control Panel:**
1. Domain Management → falklabs.de → **Nameserver**
2. Change from do.de nameservers to:
   ```
   hydrogen.ns.hetzner.com
   oxygen.ns.hetzner.com
   helium.ns.hetzner.de
   ```
3. **Save**

#### Step 2: Wait for DNS Propagation

**Propagation time:** 0-48 hours (usually 1-4 hours)

**Check propagation:**
```bash
# Your local machine
dig falklabs.de NS

# Should show: hetzner nameservers
```

**Online tools:**
- https://dnschecker.org/
- https://www.whatsmydns.net/

#### Step 3: Verify Everything Works

**After propagation complete:**
```bash
# Test all subdomains
dig brain.falklabs.de
dig dev.falklabs.de
dig stage.falklabs.de
dig coolify.falklabs.de

# Test MX (email)
dig falklabs.de MX

# Test existing services
curl http://brain.falklabs.de:3001
```

---

### Phase 4: Coolify Integration

#### Step 1: Configure Hetzner DNS in Coolify

**Coolify UI → Settings → DNS:**
1. Click **"Add DNS Provider"**
2. Provider: **Hetzner DNS**
3. API Token: `[YOUR_HETZNER_API_TOKEN]`
4. Test Connection: ✅

#### Step 2: Enable Auto-DNS for Projects

**Coolify UI → Projects → brain-dev:**
1. Settings → DNS
2. **Enable Auto-DNS:** ✅
3. Provider: Hetzner DNS
4. Zone: falklabs.de

**Result:**
- Coolify automatically creates DNS records when deploying
- SSL certificates via DNS-01 challenge (more reliable)

---

## ⚡ ALTERNATIVE: Option B (Manual DNS - Quick Start)

**If you want to start TODAY without nameserver migration:**

### Step 1: Add DNS Records at do.de

**do.de Control Panel:**
```
Type  | Name     | Value           | TTL
------|----------|-----------------|-----
A     | dev      | 46.224.37.114   | 300
A     | stage    | 46.224.37.114   | 300
A     | coolify  | 46.224.37.114   | 300
```

**Propagation:** Usually 5-30 minutes for do.de

### Step 2: Install Coolify without DNS API

**Coolify will:**
- Use HTTP-01 challenge for SSL (requires port 80)
- No auto-DNS management
- Manual DNS record creation for new subdomains

---

## 🎯 MY RECOMMENDATION

**For TODAY (Immediate Start):**
1. ✅ **Option B:** Add manual DNS records at do.de (quick!)
2. ✅ Install Coolify on port 9000
3. ✅ Deploy BRAiN to dev/stage

**For LATER (This Week):**
4. ⏳ **Option A:** Migrate to Hetzner DNS (proper solution)
5. ⏳ Configure Hetzner API in Coolify
6. ⏳ Enable auto-DNS management

**Why?**
- You can start TODAY without waiting for DNS propagation
- Hetzner migration can happen in parallel (no downtime)
- Best of both worlds: Speed + proper setup later

---

## 📋 Quick Checklist

### Before Nameserver Switch
- [ ] Document ALL current DNS records
- [ ] **Especially MX records (email!)**
- [ ] Create Hetzner DNS zone
- [ ] Copy all records to Hetzner
- [ ] Add new records (dev, stage, coolify)
- [ ] Generate Hetzner API token
- [ ] Test DNS resolution against Hetzner NS
- [ ] Verify MX records work

### During Switch
- [ ] Update nameservers at do.de
- [ ] Monitor propagation
- [ ] Verify all subdomains resolve
- [ ] **Test email still works!**

### After Switch
- [ ] Configure Hetzner API in Coolify
- [ ] Enable auto-DNS for projects
- [ ] Test SSL certificate generation
- [ ] Monitor for 24h

---

## 🆘 Emergency Rollback

**If something breaks after nameserver switch:**

```bash
# Revert nameservers at do.de to original:
# (Your original do.de nameservers)
ns1.namespace4you.de
ns2.namespace4you.de

# DNS propagation: 0-48h
```

**Time to rollback:** Same as propagation time

**Prevention:**
- ✅ Always document current DNS records BEFORE switching
- ✅ Test everything against new nameservers BEFORE switching
- ✅ Verify MX records especially (email)

---

## 📞 Support Contacts

**do.de Support:**
- https://www.do.de/support/
- Email: support@do.de

**Hetzner Support:**
- https://console.hetzner.cloud/
- Support Ticket System

---

**Decision Required:**

**A)** Full migration to Hetzner DNS now (30 min + propagation)
**B)** Quick manual records at do.de today, migrate later (5 min)

**Which do you prefer?** 🎯
