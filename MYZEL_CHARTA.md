# Myzel-Hybrid-Charta v2.0

**BRAiN Constitutional Framework for Credit System and Governance**

Version: 2.0.0
Last Updated: 2025-12-30
Status: **ACTIVE**
Compliance: DSGVO, EU AI Act

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Credit System Philosophy](#credit-system-philosophy)
3. [Governance Rules](#governance-rules)
4. [Agent Behavior Rules](#agent-behavior-rules)
5. [Mission Execution Rules](#mission-execution-rules)
6. [Cooperation Incentives](#cooperation-incentives)
7. [Edge-of-Chaos Regulation](#edge-of-chaos-regulation)
8. [Human Oversight Requirements](#human-oversight-requirements)
9. [Fail-Closed Mechanisms](#fail-closed-mechanisms)
10. [Audit and Transparency](#audit-and-transparency)
11. [Enforcement](#enforcement)

---

## Core Principles

### 1. **Cooperation Over Competition**

**Principle:** The BRAiN system operates on cooperation, not competition. Resources (credits) are "nourishment" for productive work, not rewards for outperforming others.

**Implementation:**
- ✅ Credit allocation based on **skill level** and **mission complexity** (deterministic formulas)
- ✅ Collaboration bonuses (Synergie-Mechanik)
- ✅ Work reuse detection and credit refunds
- ❌ NO leaderboards, rankings, or competitive scoring
- ❌ NO performance-based resource deprivation

**Code Location:** `backend/app/modules/credits/calculator.py`

**Validation Rule:**
```python
# RULE: Credits MUST be allocated deterministically based on:
# - Agent skill level (0.0-1.0)
# - Mission complexity (0.5-5.0)
# - Collaboration events (bonus)
# NO subjective performance comparisons allowed
```

---

### 2. **Deterministic Resource Allocation**

**Principle:** Credit allocation follows transparent, deterministic formulas. No arbitrary decisions, no opaque algorithms.

**Implementation:**
- ✅ Base agent allocation: `BASE_CREDITS * skill_multiplier` (skill_multiplier: 0.8-1.5)
- ✅ Mission budget: `BASE_COST + (COMPLEXITY_FACTOR * complexity) + (duration * regen_rate * 0.5)`
- ✅ Regeneration rate: `BASE_RATE * edge_of_chaos_multiplier`
- ✅ Withdrawal: `current_balance * severity_percentage` (10%-75%)

**Code Location:** `backend/app/modules/credits/calculator.py`

**Validation Rule:**
```python
# RULE: All credit calculations MUST be:
# 1. Deterministic (same inputs → same output)
# 2. Documented (formula in docstring)
# 3. Auditable (ledger entry with metadata)
```

---

### 3. **Edge-of-Chaos Self-Regulation**

**Principle:** The system regulates itself passively through credit flow modulation based on the Edge-of-Chaos score (optimal: 0.5-0.7).

**Implementation:**
- ✅ **Too Ordered (< 0.5):** Increase regeneration → encourage activity
- ✅ **Optimal (0.5-0.7):** Maintain current settings
- ✅ **Too Chaotic (> 0.7):** Reduce regeneration, enable backpressure

**Code Location:** `backend/app/modules/credits/eoc_controller.py`

**Validation Rule:**
```python
# RULE: Edge-of-Chaos regulation MUST be passive:
# - Modulate credit regeneration rates (✅)
# - Enable/disable backpressure (✅)
# - Request human approval for structural changes (✅)
# - NEVER force agent creation/deletion without approval (❌)
```

---

### 4. **Fail-Closed by Default**

**Principle:** When uncertain, the system errs on the side of caution. Reduce activity, require approval, preserve integrity.

**Implementation:**
- ✅ Missing Edge-of-Chaos score → reduce regeneration to 80%
- ✅ Critical actions → require human approval (HIGH/CRITICAL severity)
- ✅ Ledger integrity failure → halt credit operations, alert admin
- ✅ Security violations → immediate credit withdrawal (critical severity)

**Code Location:**
- `backend/app/modules/credits/eoc_controller.py`
- `backend/app/modules/credits/approval_gates.py`

**Validation Rule:**
```python
# RULE: In case of uncertainty or error:
# 1. Reduce system activity (lower regeneration)
# 2. Enable protective measures (backpressure, circuit breaker)
# 3. Request human approval if structural change needed
# 4. Log all fail-closed events with reasoning
```

---

### 5. **Human-in-the-Loop for Irreversible Actions**

**Principle:** Structural changes and irreversible actions require human approval (DSGVO Art. 22, EU AI Act Art. 16).

**Implementation:**

| Severity | Action Examples | Approvals Required | Timeout |
|----------|----------------|-------------------|---------|
| **LOW** | Credit adjustment < 10% | 0 (auto-approved) | 1 hour |
| **MEDIUM** | Agent skill update | 1 approval | 24 hours |
| **HIGH** | Add/remove agent | 1 approval + justification | 48 hours |
| **CRITICAL** | System architecture change | 2 approvals + review period | 72 hours |

**Code Location:** `backend/app/modules/credits/approval_gates.py`

**Validation Rule:**
```python
# RULE: Actions requiring human approval:
# - Add agent (HIGH)
# - Remove agent (HIGH)
# - Modify system architecture (CRITICAL)
# - Credit withdrawal > 50% of balance (HIGH)
# - Security policy changes (CRITICAL)
```

---

## Credit System Philosophy

### Resource as "Nourishment" Not Rewards

**Myzel-Hybrid Philosophy:** Credits are **nourishment** that enables agents to perform work, not **rewards** for past performance.

**Anti-Patterns (FORBIDDEN):**
- ❌ Withholding credits to "punish" poor performance
- ❌ Bonus credits for "beating" other agents
- ❌ Credit scarcity to force competition

**Correct Patterns (REQUIRED):**
- ✅ Allocate credits based on **needs** (mission complexity, skill level)
- ✅ Regenerate credits periodically (all active agents)
- ✅ Bonus credits for **cooperation** (collaboration events)
- ✅ Credit refunds for **work reuse** (Synergie-Mechanik)

**Code Location:** `backend/app/modules/credits/lifecycle.py`

---

### Credit Entzug (Withdrawal) as Governance

**Purpose:** Credit withdrawal is a governance mechanism for violations, not punishment.

**When to Withdraw:**
- ✅ AGENT_FAILURE events (deadlock, cascade failure)
- ✅ SECURITY_VIOLATION events (immediate critical withdrawal)
- ✅ PERFORMANCE_DEGRADATION (if agent-caused)
- ❌ Poor mission scores alone (use skill development recommendations instead)

**Severity-Based Withdrawal:**
- **LOW:** 10% withdrawal (minor issues)
- **MEDIUM:** 25% withdrawal (moderate violations)
- **HIGH:** 50% withdrawal (serious violations)
- **CRITICAL:** 75% withdrawal (security/safety violations)

**Code Location:**
- `backend/app/modules/credits/calculator.py:calculate_withdrawal_amount()`
- `backend/app/modules/immune/core/service.py:_withdraw_agent_credits()`

---

## Governance Rules

### 1. **Append-Only Ledger (IMMUTABLE)**

**RULE:** The credit ledger is append-only. No modifications, no deletions.

**Enforcement:**
```python
# RULE: LedgerEntry is frozen (Pydantic BaseModel with Config.frozen = True)
# Any attempt to modify entry raises FrozenInstanceError
# All transactions cryptographically signed (HMAC-SHA256)
```

**Code Location:** `backend/app/modules/credits/ledger.py:LedgerEntry`

---

### 2. **Ledger Integrity Verification**

**RULE:** Ledger integrity MUST be verifiable at any time.

**Verification Steps:**
1. Verify HMAC-SHA256 signatures for all entries
2. Verify blockchain-style hash chain (previous_hash linkage)
3. Verify balance calculations (balance_after = balance_before + amount)

**Enforcement:**
```python
# RULE: Integrity check MUST pass before:
# - Credit consumption
# - Credit withdrawal
# - System health reporting
# Integrity failure → halt credit operations, alert admin
```

**Code Location:** `backend/app/modules/credits/ledger.py:verify_integrity()`

---

### 3. **No Negative Balances (Except Withdrawal)**

**RULE:** Agents cannot consume more credits than they have, EXCEPT during ImmuneService withdrawal (Entzug).

**Enforcement:**
```python
# RULE: Before credit consumption:
# if balance_after < 0 and transaction_type != WITHDRAWAL:
#     raise ValueError("Insufficient credits")
# Withdrawal transactions CAN create negative balances (governance mechanism)
```

**Code Location:** `backend/app/modules/credits/ledger.py:append()`

---

### 4. **Credit Regeneration Transparency**

**RULE:** Credit regeneration MUST be transparent and predictable.

**Formula:**
```
regeneration = BASE_RATE * hours_elapsed * eoc_multiplier

where:
  BASE_RATE = 5.0 credits/hour
  eoc_multiplier = f(edge_of_chaos_score)
    - Optimal (0.5-0.7): 1.0 (full regeneration)
    - Outside optimal: 1.0 - (distance_from_optimal * 0.5)
    - Minimum: 0.2 (20% regeneration)
```

**Code Location:** `backend/app/modules/credits/calculator.py:calculate_regeneration()`

---

## Agent Behavior Rules

### 1. **Skill-Based Allocation**

**RULE:** Agent credit allocation MUST consider skill level, NOT performance history.

**Formula:**
```
allocation = BASE_AGENT_CREDITS * skill_multiplier

where:
  skill_multiplier = 0.8 + (skill_level * 0.7)  # Range: 0.8 - 1.5
  skill_level ∈ [0.0, 1.0]
```

**Code Location:** `backend/app/modules/credits/calculator.py:calculate_agent_allocation()`

---

### 2. **Collaboration Incentives (Synergie-Mechanik)**

**RULE:** Agents MUST be rewarded for cooperation, not penalized for collaboration.

**Bonus Formula:**
```
collaboration_bonus = (collaborations_count * 2.0) + (shared_resources_count * 1.5)
```

**Triggering Collaboration Events:**
- Knowledge sharing between agents
- Resource sharing (tools, data)
- Joint mission execution

**Code Location:**
- `backend/app/modules/credits/calculator.py:calculate_cooperation_bonus()`
- `backend/app/modules/credits/synergie_mechanik.py:record_collaboration()`

---

### 3. **Mission Matching (No Competition)**

**RULE:** Agents are matched to missions based on **skill fit**, not competition.

**Matching Score Formula:**
```
match_score =
  (skill_match * 0.6) +          # 60% weight: Does agent have required skills?
  (experience_match * 0.2) +     # 20% weight: Does experience match complexity?
  (collaboration_fit * 0.1) +    # 10% weight: Is agent good at collaboration?
  (success_rate * 0.1)           # 10% weight: Historical success rate
```

**Code Location:** `backend/app/modules/credits/mission_rating.py:_calculate_match_score()`

---

## Mission Execution Rules

### 1. **Pre-Execution Credit Check**

**RULE:** Before executing a mission, verify agent has sufficient credits.

**Enforcement:**
```python
# RULE: Before mission execution:
required_credits = calculate_mission_cost(complexity, duration)
if agent_balance < required_credits:
    raise InsufficientCreditsError()
```

**Code Location:** `backend/app/modules/credits/service.py:check_sufficient_credits()`

---

### 2. **Work Reuse Detection (Synergie-Mechanik)**

**RULE:** Before executing a mission, check if similar work exists and offer credit refund.

**Similarity Thresholds:**
- **High Similarity (≥90%):** 95% credit refund (almost complete reuse)
- **Moderate Similarity (70-90%):** 70-80% credit refund (partial reuse)
- **Low Similarity (50-70%):** 35-50% credit refund (minimal reuse)

**Enforcement:**
```python
# RULE: Before mission execution:
duplicates = synergie_mechanik.check_for_duplicates(mission_id)
if duplicates and duplicates[0]['similarity'] >= 0.7:
    # Offer reuse with credit refund
    reuse_detection = synergie_mechanik.detect_reuse_opportunity(...)
    if reuse_detection:
        refund_credits(mission_id, reuse_detection.refund_amount)
```

**Code Location:** `backend/app/modules/credits/synergie_mechanik.py`

---

### 3. **Mission Rating and Performance Feedback**

**RULE:** Mission performance is rated on **quality**, **efficiency**, and **collaboration**, NOT relative to other agents.

**Rating Formula:**
```
overall_score =
  (quality_score * 0.5) +         # 50% weight: Quality of work
  (efficiency_score * 0.3) +      # 30% weight: Time/resource efficiency
  (collaboration_score * 0.2)     # 20% weight: Collaboration quality
```

**Agent Profile Update:**
- Success rate: Exponential moving average (EMA)
- Collaboration score: EMA
- Experience level: Based on mission complexity exposure

**Code Location:** `backend/app/modules/credits/mission_rating.py:rate_mission()`

---

## Cooperation Incentives

### 1. **Collaboration Bonuses**

**Implementation:** See [Agent Behavior Rules > Collaboration Incentives](#2-collaboration-incentives-synergie-mechanik)

---

### 2. **Work Reuse Refunds**

**Implementation:** See [Mission Execution Rules > Work Reuse Detection](#2-work-reuse-detection-synergie-mechanik)

---

### 3. **Shared Resource Pools** (Future)

**Principle:** Agents can contribute to and benefit from shared resource pools (knowledge bases, code libraries).

**Status:** NOT YET IMPLEMENTED (Phase 7)

---

## Edge-of-Chaos Regulation

### Regulation Strategy

**Objective:** Keep system in optimal Edge-of-Chaos range (0.5-0.7) through passive credit flow modulation.

### Regulation Tiers

| EoC Score | State | Credit Regeneration | Backpressure | Human Review |
|-----------|-------|---------------------|--------------|--------------|
| < 0.3 | Critically Too Ordered | 1.5x (max) | Disabled | Required |
| 0.3-0.5 | Too Ordered | 1.0-1.5x | Disabled | No |
| 0.5-0.7 | **OPTIMAL** | 1.0x | Disabled | No |
| 0.7-0.85 | Too Chaotic | 0.5-1.0x | Enabled | No |
| > 0.85 | Critically Too Chaotic | 0.5x (min) | Enabled + Throttling | Required |

**Code Location:** `backend/app/modules/credits/eoc_controller.py:regulate()`

---

## Human Oversight Requirements

### Approval Tiers

See [Core Principles > Human-in-the-Loop](#5-human-in-the-loop-for-irreversible-actions) for approval tiers.

### Approval Process

1. **Request Approval:** System creates ApprovalRequest with severity level
2. **Notification:** Admin/supervisor receives notification (Control Deck UI)
3. **Review:** Human reviews action description, context, reasoning
4. **Decision:**
   - **APPROVE:** Provide justification (required for HIGH/CRITICAL)
   - **REJECT:** Provide reason (required)
5. **Execution:** If approved, system executes action
6. **Audit:** All decisions logged in approval audit trail

**Code Location:** `backend/app/modules/credits/approval_gates.py`

---

## Fail-Closed Mechanisms

### Trigger Conditions

| Condition | Response | Code Location |
|-----------|----------|---------------|
| Edge-of-Chaos score unavailable | Reduce regeneration to 80% | `eoc_controller.py:regulate()` |
| Ledger integrity failure | Halt credit operations, alert admin | `ledger.py:verify_integrity()` |
| Critical EoC score (>0.85) | Emergency: reduce regen to 50%, enable backpressure + throttling, request human review | `eoc_controller.py:regulate()` |
| Security violation (ImmuneService) | Immediate credit withdrawal (75% of balance) | `immune/core/service.py:_withdraw_agent_credits()` |

---

## Audit and Transparency

### 1. **Append-Only Ledger**

**Audit Trail:** Every credit transaction recorded with:
- Transaction ID
- Timestamp
- Entity ID (agent/mission)
- Amount
- Balance before/after
- Transaction type
- Reason
- Metadata
- HMAC-SHA256 signature
- Previous hash (blockchain linkage)

**Code Location:** `backend/app/modules/credits/ledger.py:LedgerEntry`

---

### 2. **Approval Audit Trail**

**Audit Trail:** Every approval request recorded with:
- Request ID
- Action type and description
- Severity level
- Requested by
- Approvals received (approver ID, timestamp, justification)
- Rejections received (approver ID, timestamp, reason)
- Final decision
- Decided at/by

**Code Location:** `backend/app/modules/credits/approval_gates.py:get_audit_trail()`

---

### 3. **Evolution Analysis Reports**

**Audit Trail:** System evolution analysis recorded with:
- Trends (metric, direction, significance)
- Recommendations (type, priority, reasoning, risks)
- Overall health assessment

**Code Location:** `backend/app/modules/credits/evolution_analyzer.py:analyze_system_evolution()`

---

## Enforcement

### Automated Enforcement

**Implementation:**
- ✅ Ledger immutability enforced by Pydantic frozen models
- ✅ Credit balance checks enforced in `ledger.append()`
- ✅ Approval requirements enforced in `approval_gates.request_approval()`
- ✅ Edge-of-Chaos regulation enforced in `eoc_controller.regulate()`

### Human Enforcement

**Responsibilities:**
- Review and approve/reject HIGH/CRITICAL actions
- Monitor audit trails (ledger, approvals, evolution)
- Investigate anomalies (sudden credit changes, repeated violations)
- Update Charta rules if needed (with versioning)

### Violation Handling

**Types of Violations:**
1. **Technical Violations:** Ledger integrity failure, calculation errors
2. **Policy Violations:** Unapproved structural changes, forbidden actions
3. **Security Violations:** Malicious behavior, data breaches

**Response:**
1. **Immediate:** Halt operation, log violation
2. **Technical:** Fix issue, restore integrity, notify admin
3. **Policy:** Trigger approval gate, escalate to human
4. **Security:** Credit withdrawal (critical), alert ImmuneService, notify admin

**Code Location:**
- `immune/core/service.py:_withdraw_agent_credits()`
- `approval_gates.py:request_approval()`

---

## Compliance Matrix

| Requirement | Implementation | Validation |
|-------------|----------------|------------|
| **DSGVO Art. 22** (No automated decisions with legal effects) | Human approval gates for structural changes | `approval_gates.py` |
| **DSGVO Art. 25** (Privacy by Design) | Minimal data collection, pseudonymized agent IDs | Throughout system |
| **EU AI Act Art. 16** (Human oversight for high-risk AI) | HIGH/CRITICAL approval tiers | `approval_gates.py` |
| **EU AI Act Art. 5** (Prohibited practices) | No social scoring, no subliminal manipulation | System design |
| **Transparency** | Append-only ledger, audit trails | `ledger.py`, `approval_gates.py` |
| **Accountability** | All decisions logged with reasoning | Throughout system |

---

## Version History

### v2.0.0 (2025-12-30)
- ✅ Full credit system implementation
- ✅ Edge-of-Chaos Controller
- ✅ Mission Rating System
- ✅ Evolution Analyzer
- ✅ Synergie-Mechanik
- ✅ Human Approval Gates
- ✅ ImmuneService integration
- ✅ Comprehensive audit trails

### v1.0.0 (Conceptual)
- Initial framework design
- Core principles established
- Myzel-Hybrid philosophy defined

---

## References

- **DSGVO (GDPR):** https://gdpr-info.eu/
- **EU AI Act:** https://www.europarl.europa.eu/doceo/document/TA-9-2024-0138_EN.html
- **BRAiN Credit System:** `backend/app/modules/credits/`
- **ChatGPT Myzel-Hybrid-Charta:** Original conceptual framework (conversation context)

---

**END OF MYZEL-HYBRID-CHARTA v2.0**
