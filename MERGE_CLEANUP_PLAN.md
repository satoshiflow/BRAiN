# BRAiN Branch Merge & Cleanup Plan
**Date:** 2026-01-02
**Analyst:** Claude
**Status:** Action Required

---

## 📊 Current Situation

- **Total Claude Branches:** 46
- **✅ Already Merged:** 26 (safe to delete)
- **⚠️ NOT Merged:** 20 (need review/merge)

---

## 🔥 CRITICAL: Branches with Important Features NOT in v2

### 1. NeuroRail Implementation (HIGH PRIORITY) ⭐⭐⭐
**Branch:** `claude/implement-egr-neuroail-mx4cJ`
**Status:** MERGED TO MAIN, NOT MERGED TO V2 ❌

**Features:**
- ✅ Budget Enforcement (Phase 2 - Sprint 2)
- ✅ Reflex System (Phase 3 - Sprint 3)
- ✅ SSE Streams & RBAC (Phase 4 - Sprint 4)
- ✅ NeuroRail ControlDeck UI (Phase 5+6 - Sprints 5+6)
- ✅ Tests + Documentation (Sprint 7)

**Action:** MUST MERGE INTO V2 IMMEDIATELY

**How to check:**
```bash
git log origin/v2..origin/claude/implement-egr-neuroail-mx4cJ --oneline
```

---

### 2. WebGenesis MVP (HIGH PRIORITY) ⭐⭐⭐
**Branches:**
- `claude/webgenesis-sprint1-mvp-OgCyN` (Sprint 1 - Core)
- `claude/webgenesis-sprint2-ops-dns-OgCyN` (Sprint 2 - Ops)
- `claude/webgenesis-sprint3-ui-OgCyN` (Sprint 3 - UI)

**Features (Sprint 1):**
- ✅ Static Template Generator (Phase 2)
- ✅ Build System with Artifact Hashing (Phase 3)
- ✅ Docker Compose Deployment (Phase 4)
- ✅ API Router with Trust Tier Enforcement (Phase 5)
- ✅ Tests & Documentation (Phase 6)

**Action:** MERGE ALL 3 SPRINTS SEQUENTIALLY

---

### 3. LiteLLM Multi-Provider Integration (MEDIUM PRIORITY) ⭐⭐
**Branch:** `claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5`

**Features:**
- ✅ LiteLLM integration for multiple LLM providers
- ✅ Provider fallback strategy
- ✅ Unified LLM interface

**Action:** REVIEW AND MERGE IF COMPATIBLE

---

### 4. Paycore Integration (MEDIUM PRIORITY) ⭐⭐
**Branches:**
- `claude/paycore-course-subscribers-zGI9H`
- `claude/paycore-payment-module-NN5VV`

**Action:** REVIEW - May be project-specific, decide if needed for v2

---

### 5. Other Unmerged Branches (LOW PRIORITY) ⭐
**To Review:**
- `claude/analyze-brain-repo-qp8MQ` - Analysis branch (probably delete)
- `claude/brain-audit-system-review-AzS3H` - Audit review (check if findings merged)
- `claude/update-claude-md-s0YmV` - Documentation update (review CLAUDE.md)
- `claude/module-migration-guide-uVAq9` - Migration guide (check if needed)

**Action:** REVIEW EACH - Merge docs/guides, delete analysis branches

---

## ✅ Safe to Delete (26 Branches Already Merged)

These branches are ALREADY in v2 and can be safely deleted:

```
claude/add-claude-md-docs-UcPWc
claude/analyze-backend-structure-onyLg
claude/brain-aro-phase-1-7apAO
claude/brain-audit-stress-test-Jc5Qi
claude/brain-genesis-agents-gOKcy
claude/brain-status-documentation-4e9sM
claude/claude-md-mj1ds9flk951n3n2-01JLqXnZos9M4nZ64zUSLD4M
claude/claude-md-v2-01JLqXnZos9M4nZ64zUSLD4M
claude/cleanup-and-docs-wkWc4
claude/complete-tasks-sprint-17-ASbyi
claude/consolidate-event-system-565zb
claude/control-center-admin-ui-pX4X9
claude/docker-egress-enforcement-71gy4
claude/event-sourcing-foundation-GmJza
claude/explore-cognee-brain-1tUVe
claude/fix-ci-dependencies-vke23
claude/generic-api-client-framework-KZut1
claude/genesis-agent-phase-1-Q0tWO
claude/hardening-audit-report-565zb
claude/merge-constitutional-framework-onyLg
claude/nginx-config-01JLqXnZos9M4nZ64zUSLD4M
claude/phase-2a-prompt-constraints-g0PRe
claude/physical-agents-gateway-C5nql
claude/sovereign-mode-offline-bundle-D214N
claude/webdev-cluster-agents-dpEt9
(+ 1 more)
```

---

## 🎯 Recommended Action Plan

### Phase 1: Critical Features (DO THIS FIRST)
```bash
# 1. Checkout v2
git checkout v2
git pull origin v2

# 2. Merge NeuroRail (CRITICAL!)
git merge origin/claude/implement-egr-neuroail-mx4cJ --no-ff -m "feat: Merge NeuroRail implementation (Sprints 1-7)"

# 3. Merge WebGenesis Sprint 1
git merge origin/claude/webgenesis-sprint1-mvp-OgCyN --no-ff -m "feat: Merge WebGenesis Sprint 1 MVP"

# 4. Merge WebGenesis Sprint 2
git merge origin/claude/webgenesis-sprint2-ops-dns-OgCyN --no-ff -m "feat: Merge WebGenesis Sprint 2 (Ops & DNS)"

# 5. Merge WebGenesis Sprint 3
git merge origin/claude/webgenesis-sprint3-ui-OgCyN --no-ff -m "feat: Merge WebGenesis Sprint 3 (UI)"

# 6. Push to v2
git push origin v2
```

### Phase 2: Review & Decide
```bash
# Review these branches individually:
git log origin/v2..origin/claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5 --oneline
git log origin/v2..origin/claude/paycore-course-subscribers-zGI9H --oneline
git log origin/v2..origin/claude/update-claude-md-s0YmV --oneline
```

### Phase 3: Cleanup
```bash
# Run the cleanup script (deletes 26 already-merged branches)
./cleanup_merged_branches.sh
```

---

## ⚠️ CONFLICT RESOLUTION

If you get merge conflicts during Phase 1:

1. **Check conflict files:**
   ```bash
   git status
   ```

2. **Resolve conflicts manually:**
   - Open conflicted files
   - Keep the most recent/complete version
   - Test the merged code

3. **Complete merge:**
   ```bash
   git add .
   git commit -m "fix: Resolve merge conflicts in <feature>"
   ```

---

## 📝 Post-Merge Checklist

After merging all critical features:

- [ ] Run backend tests: `pytest backend/tests/`
- [ ] Build frontend: `npm run build` (in each frontend app)
- [ ] Check Docker Compose: `docker compose build`
- [ ] Update CHANGELOG.md with merged features
- [ ] Tag new version: `git tag v2.1.0`
- [ ] Push tags: `git push --tags`

---

## 🔍 Verification Commands

**Check what's merged:**
```bash
git branch -r --merged origin/v2 | grep claude | wc -l
```

**Check what's NOT merged:**
```bash
git branch -r --no-merged origin/v2 | grep claude
```

**See commit diff between branches:**
```bash
git log origin/v2..origin/claude/BRANCH_NAME --oneline
```

---

## 📞 Support

If you need help with any step:
1. Check git logs for conflicts
2. Review CLAUDE.md for architecture decisions
3. Ask Claude to help with specific conflicts

---

**IMPORTANT:** DO NOT delete any branches until Phase 1 is complete and tested!
