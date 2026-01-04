# BRAiN Phase 3 Development Plan

**Date:** 2026-01-04
**Current Branch:** `claude/governor-phase2c-locked-fields-4fQqY`
**Status:** Phase 2c complete, ready for Phase 3 planning

---

## 📊 Phase 2c Completion Status

### ✅ Implementation Complete (100%)

**Deliverables:**
- ✅ LockedFieldEnforcer class (430 lines)
- ✅ Governor integration (142 lines added)
- ✅ Event system extension (63 lines added)
- ✅ 19 comprehensive tests (531 lines)
- ✅ Complete documentation (545 lines)
- ✅ Git commit and push

**Total Impact:** 1,708 lines added

**Branch:** `claude/governor-phase2c-locked-fields-4fQqY`
**Commit:** `6d4f19d1`

---

## 🔄 Immediate Next Steps (Phase 2c Closure)

### Step 1: Test Suite Verification ⏳

**Objective:** Ensure all tests pass in Docker environment

**Action Items:**
```bash
# 1. Rebuild backend container with new code
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend

# 2. Run Governor test suite
docker compose exec backend pytest backend/brain/governor/tests/ -v --tb=short

# 3. Run full test suite (all modules)
docker compose exec backend pytest backend/tests/ -v --cov=backend --cov-report=term-missing

# 4. Check for import errors
docker compose exec backend python -c "from backend.brain.governor.enforcement.locks import LockedFieldEnforcer; print('✓ Import successful')"
```

**Expected Results:**
- All 19 locked fields tests pass
- No import errors
- Coverage >95% for enforcement module
- No regression in existing Governor tests

**Estimated Time:** 15 minutes

---

### Step 2: Code Review ⏳

**Self-Review Checklist:**

**Architecture:**
- [ ] Follows existing Governor patterns (Phase 2a/2b)
- [ ] Integrates cleanly with evaluate_creation() flow
- [ ] Event system follows dual-write pattern
- [ ] No breaking changes to existing API

**Code Quality:**
- [ ] Type hints for all functions
- [ ] Async/await for I/O operations (N/A - validation is synchronous)
- [ ] Error handling (PolicyViolationError with detailed violations)
- [ ] Logging at appropriate levels
- [ ] No hardcoded values (uses manifest configuration)

**Security:**
- [ ] Prevents privilege escalation (can_create_agents locked)
- [ ] Enforces DSGVO Art. 22 (human_override locked)
- [ ] Protects governance integrity (can_modify_governor locked)
- [ ] Genesis exception properly scoped

**Testing:**
- [ ] Unit tests cover all validation scenarios
- [ ] Integration tests verify Governor blocking
- [ ] Event emission tests verify audit trail
- [ ] Edge cases handled (unknown types, invalid paths)
- [ ] Performance benchmarks (<10ms per validation)

**Documentation:**
- [ ] README_PHASE_2C.md complete
- [ ] API reference with examples
- [ ] Troubleshooting guide
- [ ] Security considerations documented

**Compliance:**
- [ ] DSGVO Art. 22 compliance verified
- [ ] EU AI Act Art. 16 compliance verified
- [ ] Audit trail complete (dual-write)

**Estimated Time:** 20 minutes

---

### Step 3: Merge to v2 Branch ⏳

**Pre-Merge Actions:**
```bash
# 1. Ensure on Phase 2c branch
git checkout claude/governor-phase2c-locked-fields-4fQqY

# 2. Pull latest v2 (check for conflicts)
git fetch origin v2
git merge origin/v2

# 3. Resolve any conflicts (if needed)

# 4. Final verification
git log --oneline -5
git diff origin/v2...HEAD --stat
```

**Merge Strategy:**

**Option A: Direct Merge (if tests pass)**
```bash
git checkout v2
git merge claude/governor-phase2c-locked-fields-4fQqY
git push origin v2
```

**Option B: Pull Request (recommended for team review)**
1. Create PR via GitHub UI
2. Add description with implementation summary
3. Request review from team (if applicable)
4. Merge after approval

**Post-Merge Verification:**
```bash
# Verify merge successful
git log --oneline -10

# Deploy to dev environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Test live system
curl https://dev.brain.falklabs.de/api/health
```

**Estimated Time:** 15 minutes

---

## 🚀 Phase 3 Feature Analysis

Based on the Phase 3 prompt, here are the available development tracks:

### Option 1: NeuroRail Phase 2 (High Priority)

**Status:** Phase 1 complete (observe-only), Phase 2 planned

**Objectives:**
- Budget enforcement (timeout wrapper, token limits, resource quotas)
- Reflex system (cooldown periods, probing strategies, auto-suspend)
- Manifest-driven governance (replace hard-coded rules)

**Implementation Scope:**
- Enable enforcement flags (currently disabled)
- Implement timeout wrappers for execution
- Add budget tracking and enforcement
- Implement reflex system with cooldown
- Create manifest-driven rule engine
- Add ControlDeck UI components (Trace Explorer, Health Matrix)
- WebSocket real-time updates

**Files to Modify:**
- `backend/app/modules/neurorail/execution/service.py`
- `backend/app/modules/neurorail/telemetry/service.py`
- `backend/app/modules/governor/governor.py` (manifest integration)
- `frontend/control_deck/app/neurorail/` (new UI pages)

**Estimated Effort:** 6-8 hours

**Dependencies:**
- Governor Phase 2c (locked fields) ✅ COMPLETE
- NeuroRail Phase 1 (infrastructure) ✅ COMPLETE

**Impact:**
- High - Enables production-ready execution governance
- Completes NeuroRail enforcement stack
- Critical for resource management

---

### Option 2: Fleet Management (Medium Priority)

**Status:** Module structure exists, RYR agents partially implemented

**Objectives:**
- Complete FleetAgent, SafetyAgent, NavigationAgent
- Integrate with Fleet Management module
- Add multi-robot coordination logic
- Implement task distribution algorithms

**Implementation Scope:**
- Finish agent implementations
- Add fleet coordination logic
- Create agent blueprints
- Add fleet management UI
- Implement safety rules and collision avoidance

**Files to Modify:**
- `backend/brain/agents/fleet_agent.py`
- `backend/brain/agents/safety_agent.py`
- `backend/brain/agents/navigation_agent.py`
- `backend/app/modules/fleet/service.py`
- `frontend/control_deck/app/fleet/` (new UI pages)

**Estimated Effort:** 5-7 hours

**Dependencies:**
- Agent system base classes ✅ COMPLETE
- Fleet module API ✅ COMPLETE

**Impact:**
- Medium - Enables multi-robot operations
- RYR integration milestone
- Foundation for warehouse automation

---

### Option 3: Constitutional Agents Enhancement (Low-Medium Priority)

**Status:** 5 agents implemented (Supervisor, Coder, Ops, Architect, AXE)

**Objectives:**
- Enhanced DSGVO compliance features
- Improved EU AI Act validation
- Automated compliance reporting
- Constitutional LLM check improvements

**Implementation Scope:**
- Add automated compliance reports
- Enhance human-in-the-loop workflows
- Improve risk assessment algorithms
- Add compliance dashboard UI
- Implement policy version control

**Files to Modify:**
- `backend/brain/agents/supervisor_agent.py`
- `backend/brain/agents/architect_agent.py`
- `backend/app/api/routes/agent_ops.py`
- `frontend/control_deck/app/constitutional/` (UI enhancements)

**Estimated Effort:** 4-6 hours

**Dependencies:**
- Constitutional agents ✅ COMPLETE
- Policy Engine ✅ COMPLETE

**Impact:**
- Low-Medium - Incremental compliance improvements
- Better audit trail
- Reduced manual compliance checks

---

### Option 4: Frontend Polish (Low-Medium Priority)

**Status:** 14 pages functional, 50+ components, some UI/UX rough edges

**Objectives:**
- Improve Control Deck UI/UX
- Add loading states and error boundaries
- Implement real-time updates (WebSocket)
- Add data visualization components
- Improve mobile responsiveness

**Implementation Scope:**
- Refactor common components
- Add skeleton loaders
- Implement error boundaries
- Add WebSocket hooks for live data
- Create chart components (Recharts)
- Polish dashboard layouts

**Files to Modify:**
- `frontend/control_deck/components/ui/` (shadcn components)
- `frontend/control_deck/app/*/page.tsx` (page layouts)
- `frontend/control_deck/hooks/` (React Query + WebSocket hooks)

**Estimated Effort:** 5-7 hours

**Dependencies:**
- None (independent track)

**Impact:**
- Medium - Better user experience
- Easier monitoring and debugging
- Professional appearance

---

### Option 5: Testing Suite (High Priority)

**Status:** Some pytest tests exist, coverage incomplete

**Objectives:**
- Achieve >80% test coverage across all modules
- Add integration tests for critical flows
- Add E2E tests for API endpoints
- Set up CI/CD pipeline with automatic testing

**Implementation Scope:**
- Write pytest tests for all modules
- Add fixtures for common test data
- Create integration test scenarios
- Add API endpoint tests (TestClient)
- Set up pytest-cov for coverage reporting
- Configure GitHub Actions for CI/CD

**Files to Create:**
- `backend/tests/test_neurorail_*.py`
- `backend/tests/test_fleet_*.py`
- `backend/tests/test_constitutional_agents.py`
- `.github/workflows/test.yml`

**Estimated Effort:** 6-8 hours

**Dependencies:**
- None (can test any existing feature)

**Impact:**
- High - Prevents regressions
- Enables confident refactoring
- Required for production deployment

---

### Option 6: Documentation (Medium Priority)

**Status:** CLAUDE.md comprehensive, module READMEs partial

**Objectives:**
- Complete all module README files
- Add architecture diagrams
- Create API documentation (Swagger/OpenAPI)
- Write developer onboarding guide
- Create deployment playbook

**Implementation Scope:**
- Update all module READMEs
- Generate OpenAPI schema from FastAPI
- Add architecture diagrams (mermaid)
- Write deployment guide
- Create troubleshooting runbook

**Files to Create/Modify:**
- `backend/app/modules/*/README.md` (17+ modules)
- `docs/ARCHITECTURE.md`
- `docs/API_REFERENCE.md`
- `docs/DEPLOYMENT.md`
- `docs/TROUBLESHOOTING.md`

**Estimated Effort:** 4-6 hours

**Dependencies:**
- None (documents existing features)

**Impact:**
- Medium - Better team onboarding
- Easier maintenance
- External contributor friendly

---

## 📈 Recommended Prioritization

### Tier 1: Critical Path (Complete First)

1. **Phase 2c Closure** ⏳ NEXT
   - Run tests
   - Code review
   - Merge to v2
   - **Estimated:** 1 hour

2. **Testing Suite (Option 5)** 🔴 HIGH PRIORITY
   - Prevents regressions during Phase 3 development
   - Enables confident iteration
   - **Estimated:** 6-8 hours
   - **Rationale:** Foundation for all other work

3. **NeuroRail Phase 2 (Option 1)** 🔴 HIGH PRIORITY
   - Completes execution governance stack
   - Critical for production readiness
   - **Estimated:** 6-8 hours
   - **Rationale:** Highest technical value

### Tier 2: High Value Features

4. **Fleet Management (Option 2)** 🟡 MEDIUM PRIORITY
   - Unlocks multi-robot use cases
   - RYR integration milestone
   - **Estimated:** 5-7 hours

5. **Frontend Polish (Option 4)** 🟡 MEDIUM PRIORITY
   - Improves user experience
   - Better monitoring capabilities
   - **Estimated:** 5-7 hours

### Tier 3: Incremental Improvements

6. **Documentation (Option 6)** 🟢 LOW-MEDIUM PRIORITY
   - Important but not blocking
   - Can be done incrementally
   - **Estimated:** 4-6 hours

7. **Constitutional Agents Enhancement (Option 3)** 🟢 LOW-MEDIUM PRIORITY
   - Incremental compliance improvements
   - Not critical for core functionality
   - **Estimated:** 4-6 hours

---

## 🎯 Proposed Phase 3 Roadmap

### Week 1: Foundation & Governance

**Days 1-2: Phase 2c Closure + Testing Foundation**
- Complete Phase 2c merge
- Set up comprehensive test suite
- Achieve 60%+ test coverage
- Configure pytest-cov reporting

**Days 3-5: NeuroRail Phase 2**
- Implement budget enforcement
- Add reflex system
- Create manifest-driven rules
- Add ControlDeck UI components
- Achieve 80%+ test coverage for NeuroRail

### Week 2: Fleet & Polish

**Days 6-8: Fleet Management**
- Complete RYR agent implementations
- Add fleet coordination logic
- Create fleet management UI
- Add fleet simulation tests

**Days 9-10: Frontend Polish**
- Add WebSocket hooks
- Improve UI/UX for key pages
- Add loading states and error boundaries
- Mobile responsiveness improvements

### Week 3: Documentation & Enhancements

**Days 11-12: Documentation**
- Complete all module READMEs
- Generate API documentation
- Create architecture diagrams
- Write deployment playbook

**Days 13-14: Constitutional Agents Enhancement**
- Add automated compliance reports
- Improve human-in-the-loop workflows
- Add compliance dashboard features

---

## 🚦 Decision Point: Choose Your Track

### Option A: Sequential (Recommended)
Follow the roadmap in order:
1. Phase 2c closure → Testing Suite → NeuroRail Phase 2 → Fleet → Frontend → Docs

**Pros:**
- Systematic approach
- Each phase builds on previous
- High test coverage throughout

**Cons:**
- Longer time to complete all features
- Less flexibility

### Option B: Parallel Tracks
Pick 2-3 independent features and work in parallel:
- Track 1: NeuroRail Phase 2 (critical path)
- Track 2: Frontend Polish (independent)
- Track 3: Documentation (independent)

**Pros:**
- Faster overall completion
- Can context-switch between tasks
- Variety reduces fatigue

**Cons:**
- Risk of incomplete features
- Harder to maintain focus
- Merge conflicts possible

### Option C: User Priority
Let user choose the most important feature to implement next.

**Pros:**
- Aligns with business priorities
- Maximizes immediate value
- User engagement

**Cons:**
- May skip critical foundation work (testing)
- Technical debt accumulation risk

---

## 🎬 Immediate Action Plan

### Next 30 Minutes

1. **Run Phase 2c Tests** (10 min)
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend
   docker compose exec backend pytest backend/brain/governor/tests/test_locked_fields_enforcement.py -v
   ```

2. **Code Review** (10 min)
   - Review implementation against checklist
   - Verify no regressions
   - Check documentation completeness

3. **Merge Decision** (10 min)
   - Create PR or direct merge
   - Update v2 branch
   - Verify deployment

### Next 2 Hours

**Option 1: Start Testing Suite**
- Set up pytest structure
- Write tests for NeuroRail modules
- Configure coverage reporting
- Aim for 60%+ coverage

**Option 2: Start NeuroRail Phase 2**
- Enable enforcement flags
- Implement timeout wrappers
- Add budget tracking
- Create initial UI components

**Option 3: Start Frontend Polish**
- Add WebSocket hooks
- Improve dashboard layouts
- Add loading states
- Mobile responsiveness

---

## 📋 User Decision Required

**Please choose ONE of the following:**

### A. Complete Phase 2c Closure (Recommended First)
- Run tests
- Code review
- Merge to v2
- **Then choose next feature**

### B. Start Specific Phase 3 Feature
Choose one:
1. NeuroRail Phase 2 (budget enforcement + reflex system)
2. Fleet Management (RYR agent completion)
3. Constitutional Agents (compliance enhancements)
4. Frontend Polish (UI/UX improvements)
5. Testing Suite (comprehensive coverage)
6. Documentation (API docs + guides)

### C. Custom Feature
Specify your own priority or combination

---

## 📊 Success Metrics

### Phase 2c Success Criteria ✅
- [x] LockedFieldEnforcer implemented
- [x] Governor integration complete
- [x] 19 tests written
- [x] Documentation complete
- [x] Code committed and pushed
- [ ] Tests pass in Docker ⏳
- [ ] Merged to v2 ⏳

### Phase 3 Success Criteria (TBD)
Will be defined based on chosen feature track.

---

**Ready to proceed! What would you like to tackle next?**

1. **Complete Phase 2c closure** (test + merge)
2. **Start Phase 3 feature** (specify which one)
3. **Review this plan** (ask questions or modify)
