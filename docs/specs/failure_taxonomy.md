# Failure Taxonomy Specification

**Version:** 1.0  
**Status:** Active  
**Date:** 2026-03-10  
**Sprint:** Sprint C - Runtime Diagnostics & Error Framework  
**Roadmap:** BRAIN_HARDENING_ROADMAP.md

## Purpose

This specification defines the standardized failure classification, error handling patterns, and diagnostic contracts for the BRAiN backend runtime. It establishes a common language for failure recording, correlation, provenance, and operator triage.

## Design Principles

1. **Deterministic Classification**: Every runtime failure maps to exactly one failure class and failure code.
2. **Correlation-First**: All failures capture correlation_id at the earliest possible point.
3. **Provenance-Linked**: Failures in learning pipelines link back to source records (ExperienceRecord, InsightCandidate, PatternCandidate).
4. **Redaction-Safe**: All failure records redact sensitive data before persistence or transmission.
5. **Operator-Actionable**: Every failure includes recommended operator action for triage.
6. **Recovery-Routable**: Retryability classification enables safe immune/recovery policy routing.

## Failure Taxonomy

### Failure Classes

BRAiN runtime failures are classified into six high-level classes:

| Failure Class | Description | Example Scenarios |
|---------------|-------------|-------------------|
| `request_failure` | Client request validation, auth, routing errors | Invalid input, missing auth token, rate limiting |
| `execution_failure` | Runtime execution, worker, queue failures | Timeout, resource exhaustion, unhandled exceptions |
| `integration_failure` | External dependency, database, provider failures | Database timeout, Redis connection loss, API errors |
| `governance_failure` | Policy violation, approval, capability failures | Approval denied, quota exceeded, tenant isolation violation |
| `observability_failure` | Audit, event, signal pipeline failures | Audit write failed, event publish failed, correlation missing |
| `learning_pipeline_failure` | Experience/Insight/Pattern/Consolidation/Evolution failures | Experience capture failed, insight extraction failed |

### Failure Codes by Class

#### 1. Request Failures (`request_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `validation_error` | WARNING | NO_RETRY | NONE | Input validation failed (client error) |
| `auth_missing` | WARNING | NO_RETRY | NONE | Authentication credentials missing |
| `auth_invalid` | WARNING | NO_RETRY | NONE | Authentication credentials invalid |
| `auth_expired` | WARNING | SAFE_RETRY | NONE | Authentication token expired (client can refresh) |
| `forbidden` | WARNING | NO_RETRY | INVESTIGATE | Authorization denied for requested resource |
| `rate_limited` | WARNING | SAFE_RETRY | MONITOR | Request rate limit exceeded (backoff and retry) |
| `malformed_input` | WARNING | NO_RETRY | NONE | Request body or parameters malformed |
| `resource_not_found` | WARNING | NO_RETRY | NONE | Requested resource does not exist |
| `conflict` | WARNING | NO_RETRY | INVESTIGATE | Request conflicts with existing resource state |
| `precondition_failed` | WARNING | NO_RETRY | INVESTIGATE | Request precondition not met (e.g., If-Match header) |

#### 2. Execution Failures (`execution_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `timeout` | ERROR | SAFE_RETRY | MONITOR | Operation exceeded time limit |
| `resource_exhausted` | ERROR | SAFE_RETRY | INVESTIGATE | Memory, CPU, or other resource exhausted |
| `dependency_unavailable` | ERROR | SAFE_RETRY | INVESTIGATE | Required internal dependency unavailable |
| `skill_execution_error` | ERROR | IDEMPOTENT_RETRY | INVESTIGATE | Skill execution failed (check SkillRun logs) |
| `worker_crash` | CRITICAL | UNSAFE_RETRY | ESCALATE | Background worker process crashed |
| `queue_overflow` | ERROR | SAFE_RETRY | MONITOR | Task queue capacity exceeded |
| `circuit_open` | WARNING | SAFE_RETRY | MONITOR | Circuit breaker open (dependency degraded) |
| `unhandled_exception` | CRITICAL | UNSAFE_RETRY | ESCALATE | Unhandled runtime exception (bug) |

#### 3. Integration Failures (`integration_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `database_error` | CRITICAL | SAFE_RETRY | ESCALATE | PostgreSQL query or connection error |
| `redis_error` | ERROR | SAFE_RETRY | INVESTIGATE | Redis connection or operation error |
| `eventstream_error` | ERROR | SAFE_RETRY | INVESTIGATE | EventStream publish or subscribe error |
| `external_api_error` | ERROR | SAFE_RETRY | MONITOR | External API request failed (provider, gateway) |
| `provider_error` | ERROR | IDEMPOTENT_RETRY | INVESTIGATE | LLM/capability provider error |
| `network_error` | ERROR | SAFE_RETRY | MONITOR | Network connectivity error |
| `serialization_error` | ERROR | NO_RETRY | INVESTIGATE | JSON serialization or schema error |

#### 4. Governance Failures (`governance_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `approval_required` | WARNING | NO_RETRY | NONE | Action requires governance approval |
| `approval_denied` | WARNING | NO_RETRY | INVESTIGATE | Governance approval explicitly denied |
| `policy_violation` | ERROR | NO_RETRY | INVESTIGATE | Request violates governance policy |
| `quota_exceeded` | WARNING | NO_RETRY | REMEDIATE | Tenant quota exceeded (manual increase required) |
| `tenant_isolation_violation` | CRITICAL | NO_RETRY | ESCALATE | Tenant isolation boundary violated (security) |
| `capability_missing` | WARNING | NO_RETRY | REMEDIATE | Required capability not available for tenant |
| `lifecycle_violation` | ERROR | NO_RETRY | INVESTIGATE | Module lifecycle state violation |

#### 5. Observability Failures (`observability_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `audit_write_failed` | CRITICAL | SAFE_RETRY | ESCALATE | Audit log write failed (data durability risk) |
| `event_publish_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Event publication to EventStream failed |
| `signal_ingestion_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Observer signal ingestion failed |
| `correlation_missing` | WARNING | NO_RETRY | MONITOR | Correlation ID missing from execution path |
| `provenance_link_broken` | WARNING | NO_RETRY | INVESTIGATE | Provenance link to source record broken |
| `telemetry_dropped` | WARNING | NO_RETRY | MONITOR | Telemetry/metrics dropped (observability gap) |

#### 6. Learning Pipeline Failures (`learning_pipeline_failure`)

| Failure Code | Severity | Retryability | Operator Action | Description |
|--------------|----------|--------------|-----------------|-------------|
| `experience_capture_failed` | ERROR | SAFE_RETRY | INVESTIGATE | ExperienceRecord capture failed |
| `insight_extraction_failed` | ERROR | SAFE_RETRY | INVESTIGATE | InsightCandidate extraction failed |
| `pattern_candidate_failed` | ERROR | SAFE_RETRY | INVESTIGATE | PatternCandidate creation failed |
| `consolidation_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Consolidation layer operation failed |
| `evolution_selection_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Evolution selection decision failed |
| `deliberation_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Deliberation layer operation failed |
| `discovery_failed` | ERROR | SAFE_RETRY | INVESTIGATE | Discovery layer operation failed |
| `economy_signal_failed` | ERROR | SAFE_RETRY | MONITOR | Economy signal publication failed |

## Standard Failure Envelope

All backend failures must emit a `FailureRecord` with the following fields:

```python
from app.core.diagnostics import FailureRecord, build_failure_record

failure = build_failure_record(
    tenant_id="tenant_xyz",
    entity="skill_engine",
    failure_class=FailureClass.EXECUTION_FAILURE,
    failure_code=ExecutionFailureCode.TIMEOUT,
    severity=Severity.ERROR,
    message="Skill execution timed out after 300s",
    correlation_id="corr_abc123",
    skill_run_id="run_def456",
    retryability=Retryability.SAFE_RETRY,
    operator_action=OperatorAction.MONITOR,
    technical_details={"timeout_seconds": 300, "skill_id": "skill_xyz"},
    audit_ref="audit_789",
    provenance_refs=["experience_record:exp_123:corr_abc123"],
)
```

### Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tenant_id` | `str` | Yes | Tenant context for isolation |
| `entity` | `str` | Yes | Failing module/service/worker name |
| `failure_class` | `FailureClass` | Yes | High-level failure classification |
| `failure_code` | `str` | Yes | Specific failure code from taxonomy |
| `severity` | `Severity` | Yes | Severity level (INFO, WARNING, ERROR, CRITICAL) |
| `message` | `str` | Yes | Human-readable failure summary |
| `retryability` | `Retryability` | Yes | Retry safety classification |
| `operator_action` | `OperatorAction` | Yes | Recommended operator action |

### Optional Fields (Strongly Recommended)

| Field | Type | Description |
|-------|------|-------------|
| `correlation_id` | `str \| None` | Request/execution correlation ID |
| `skill_run_id` | `str \| None` | Associated SkillRun ID if applicable |
| `mission_id` | `str \| None` | Associated Mission ID if applicable |
| `technical_details` | `dict` | Technical context (automatically redacted) |
| `stack_trace` | `str \| None` | Stack trace if available (automatically redacted) |
| `audit_ref` | `str \| None` | Reference to audit record |
| `event_ref` | `str \| None` | Reference to published event |
| `provenance_refs` | `list[str]` | Links to source records |

## Correlation ID Propagation

Correlation IDs must be propagated through all execution layers:

1. **HTTP Request → correlation_id**: Extract from `X-Correlation-ID` or `X-Request-ID` header, or generate new
2. **SkillRun → correlation_id**: Link SkillRun.id to correlation_id
3. **Audit → correlation_id**: Include correlation_id in audit event extra_data
4. **Event → correlation_id**: Include correlation_id in event payload
5. **Observer → correlation_id**: Capture correlation_id in ObserverSignal
6. **FailureRecord → correlation_id**: Always include correlation_id

### Correlation ID Patterns

- Request-scoped: `corr_<uuid>`
- Skill-scoped: `corr_skill_<skill_run_id>`
- Mission-scoped: `corr_mission_<mission_id>`

## Provenance Linking

Learning pipeline failures must link to source records:

- **ExperienceRecord**: `experience_record:<record_id>[:<correlation_id>]`
- **InsightCandidate**: `insight_candidate:<record_id>[:<correlation_id>]`
- **PatternCandidate**: `pattern_candidate:<record_id>[:<correlation_id>]`
- **EvolutionSelection**: `evolution_selection:<record_id>[:<correlation_id>]`

Example:
```python
provenance_refs=[
    "experience_record:exp_123:corr_abc",
    "insight_candidate:ins_456:corr_abc",
]
```

## Redaction Rules

All `FailureRecord` instances are automatically redacted before persistence or transmission:

1. **Stack Traces**: Redact tokens, secrets, emails
2. **Technical Details**: Redact keys: `password`, `token`, `api_key`, `secret`, `authorization`
3. **Client Responses**: Strip `stack_trace`, replace `technical_details` with `{"redacted": true}`

## Operator Diagnostic Surfaces

### Incident Timeline API

Endpoint: `GET /api/observer/incidents/timeline`

Query parameters:
- `correlation_id`: Filter by correlation ID
- `skill_run_id`: Filter by skill run ID
- `mission_id`: Filter by mission ID
- `entity_type`: Filter by entity type
- `entity_id`: Filter by entity ID
- `time_window_minutes`: Time window (default 60, max 1440)
- `limit`: Max signals (default 100, max 500)

Response:
```json
{
  "signals": [...],
  "correlation_groups": {"corr_abc": 5, "corr_def": 3},
  "severity_distribution": {"error": 4, "warning": 2, "critical": 1},
  "timeline_start": "2026-03-10T10:00:00Z",
  "timeline_end": "2026-03-10T11:00:00Z",
  "total_signals": 8
}
```

### Use Cases

1. **Failure Sequence Analysis**: Retrieve all signals for a failed SkillRun by `correlation_id`
2. **Causal Chain Reconstruction**: Identify upstream failures leading to downstream failures
3. **Last Known Good State**: Find last successful signal before failure cascade
4. **Impacted Entity Discovery**: Identify all entities affected by a failure

## Observability SLOs

Target metrics for diagnostics quality:

| Metric | Target | Measured By |
|--------|--------|-------------|
| Correlation completeness | ≥ 95% | % of FailureRecords with correlation_id |
| Audit link coverage | ≥ 90% | % of FailureRecords with audit_ref |
| Unknown error rate | < 5% | % of failures with `unhandled_exception` code |
| Dropped event rate | < 1% | % of events that fail to publish |
| Provenance completeness | ≥ 85% | % of learning pipeline failures with provenance_refs |

## Integration with Other Systems

### Health System (Sprint B)

- Health transitions emit `observability_failure` if audit/event publishing fails
- Health degradation consumes `FailureRecord` severity for rollup

### Immune System (Sprint D)

- Immune consumes `retryability` and `operator_action` for recovery policy routing
- High-risk recovery actions require `approval_required` governance gate

### Self-Healing (Sprint E)

- Self-healing control loop only acts on failures with verified `correlation_id` and `audit_ref`
- `UNSAFE_RETRY` failures require manual approval before retry

## Error Handling Patterns

### Pattern 1: Request Validation Failure

```python
from fastapi import HTTPException, status
from app.core.diagnostics import build_failure_record, FailureClass, Severity, Retryability, OperatorAction, RequestFailureCode

# Emit FailureRecord (for observability)
failure = build_failure_record(
    tenant_id=tenant_id,
    entity="skill_router",
    failure_class=FailureClass.REQUEST_FAILURE,
    failure_code=RequestFailureCode.VALIDATION_ERROR,
    severity=Severity.WARNING,
    message="Invalid skill_id format",
    correlation_id=correlation_id,
    retryability=Retryability.NO_RETRY,
    operator_action=OperatorAction.NONE,
    technical_details={"skill_id": invalid_skill_id},
)
# Log failure (will be ingested by observer)
logger.warning(f"[{correlation_id}] Request validation failed: {failure.message}")

# Return sanitized HTTP error to client
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=failure.to_sanitized_dict(),
)
```

### Pattern 2: Execution Failure with Retry

```python
from app.core.diagnostics import build_failure_record, FailureClass, ExecutionFailureCode, Severity, Retryability, OperatorAction

try:
    result = await execute_skill_with_timeout(skill_run_id, timeout=300)
except asyncio.TimeoutError as exc:
    failure = build_failure_record(
        tenant_id=tenant_id,
        entity="skill_engine",
        failure_class=FailureClass.EXECUTION_FAILURE,
        failure_code=ExecutionFailureCode.TIMEOUT,
        severity=Severity.ERROR,
        message=f"Skill execution timed out after 300s",
        correlation_id=correlation_id,
        skill_run_id=skill_run_id,
        retryability=Retryability.SAFE_RETRY,
        operator_action=OperatorAction.MONITOR,
        technical_details={"timeout_seconds": 300},
        stack_trace=traceback.format_exc(),
    )
    logger.error(f"[{correlation_id}] Skill execution timeout: {failure.message}")
    # Publish to immune for recovery policy evaluation
    await publish_failure_signal(failure)
    raise
```

### Pattern 3: Learning Pipeline Failure with Provenance

```python
from app.core.diagnostics import build_failure_record, FailureClass, LearningPipelineFailureCode, Severity, Retryability, OperatorAction

try:
    insight = await extract_insight_from_experience(experience_record)
except Exception as exc:
    failure = build_failure_record(
        tenant_id=tenant_id,
        entity="insight_layer",
        failure_class=FailureClass.LEARNING_PIPELINE_FAILURE,
        failure_code=LearningPipelineFailureCode.INSIGHT_EXTRACTION_FAILED,
        severity=Severity.ERROR,
        message="Failed to extract insight from experience",
        correlation_id=experience_record.correlation_id,
        skill_run_id=experience_record.skill_run_id,
        retryability=Retryability.SAFE_RETRY,
        operator_action=OperatorAction.INVESTIGATE,
        technical_details={"experience_id": str(experience_record.id)},
        provenance_refs=[f"experience_record:{experience_record.id}:{experience_record.correlation_id}"],
        stack_trace=traceback.format_exc(),
    )
    logger.error(f"[{failure.correlation_id}] Insight extraction failed: {failure.message}")
    await publish_failure_signal(failure)
    raise
```

## Migration and Adoption

### Phase 1: Core Infrastructure (Sprint C - Current)

- [x] Create `app.core.diagnostics` module
- [x] Define failure taxonomy and enumerations
- [x] Implement `FailureRecord` and builder
- [x] Add correlation ID propagation helpers
- [x] Add provenance linking utilities
- [x] Add redaction utilities
- [x] Create incident timeline API in observer_core
- [x] Add test suite

### Phase 2: Rollout to Core Modules (Post-Sprint C)

- [ ] Adopt FailureRecord in skill_engine
- [ ] Adopt FailureRecord in mission_control
- [ ] Adopt FailureRecord in learning layers (experience, insight, pattern, consolidation, evolution, deliberation, discovery, economy)
- [ ] Adopt FailureRecord in immune/recovery modules

### Phase 3: Observability Integration (Sprint D)

- [ ] Wire failure signals to immune intake
- [ ] Wire failure signals to health degradation
- [ ] Add SLO tracking for correlation/audit/provenance completeness

## References

- `docs/roadmap/BRAIN_HARDENING_ROADMAP.md` (Sprint C)
- `backend/app/core/diagnostics.py` (implementation)
- `backend/app/modules/observer_core/router.py` (incident timeline API)
- `backend/tests/test_diagnostics.py` (test suite)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-10 | Initial specification (Sprint C delivery) |
