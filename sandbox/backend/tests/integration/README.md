# Integration Tests - Constitutional Agents Framework

Comprehensive integration and end-to-end tests for the Constitutional Agents Framework.

## Test Files

### `test_constitutional_integration.py`
**Purpose:** Integration tests with mocked LLM client

**Coverage:**
- Full supervision workflow (LOW/MEDIUM/HIGH/CRITICAL risk)
- CoderAgent + SupervisorAgent integration
- OpsAgent deployment workflow
- ArchitectAgent EU compliance checking
- AXEAgent conversational flow
- Policy Engine integration
- Audit trail recording
- Error handling and fail-safe behavior
- Metrics tracking

**Tests:** 15+ integration tests

**Requires:** None (uses mocks)

### `test_api_e2e.py`
**Purpose:** End-to-end API tests with FastAPI TestClient

**Coverage:**
- All `/api/agent-ops/` endpoints
- HTTP request/response validation
- Error handling (422 validation, 500 server errors)
- Integration flows (supervision → action → metrics)
- Performance tests
- Concurrent request handling

**Tests:** 25+ E2E tests

**Requires:** FastAPI app running

## Running Tests

### All Integration Tests
```bash
cd backend
pytest tests/integration/ -v
```

### Specific Test File
```bash
pytest tests/integration/test_constitutional_integration.py -v
```

### With Coverage
```bash
pytest tests/integration/ --cov=backend.brain.agents --cov=backend.app.api.routes.agent_ops -v
```

### Specific Test
```bash
pytest tests/integration/test_constitutional_integration.py::test_full_supervision_workflow_low_risk -v
```

### Performance Tests Only
```bash
pytest tests/integration/test_api_e2e.py -k "performance" -v
```

## Test Requirements

### Python Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Optional: Real LLM Client
For testing with actual LLM (Ollama):
```bash
# Start Ollama service
systemctl start ollama

# Pull model
ollama pull llama3.2:latest
```

Then run tests with real LLM:
```bash
REAL_LLM=true pytest tests/integration/ -v
```

## Test Categories

### 1. Workflow Tests
Test complete workflows from start to finish:
- `test_full_supervision_workflow_low_risk`
- `test_coder_agent_with_supervisor_integration`
- `test_e2e_code_generation_with_supervision`

### 2. Integration Tests
Test interaction between components:
- `test_policy_engine_denies_high_risk_without_approval`
- `test_coder_to_supervisor_integration`
- `test_full_workflow_supervision_to_action`

### 3. API Tests
Test HTTP endpoints:
- `test_supervisor_supervise_low_risk`
- `test_coder_generate_code`
- `test_architect_review_architecture`

### 4. Error Handling Tests
Test fail-safe behavior:
- `test_llm_failure_fail_safe`
- `test_supervisor_supervise_invalid_risk_level`
- `test_supervisor_supervise_missing_required_fields`

### 5. Performance Tests
Test system performance:
- `test_supervisor_supervise_performance`
- `test_concurrent_supervision_requests`

## Expected Results

### With Mocked LLM (Default)
All tests should pass. Mocks simulate realistic LLM responses.

### With Real LLM (REAL_LLM=true)
Most tests should pass. Some may fail if:
- Ollama service not running
- Model not downloaded
- LLM response doesn't match expected format

## Test Data

### Example Supervision Request
```python
{
    "requesting_agent": "TestAgent",
    "action": "read_logs",
    "context": {"log_type": "application"},
    "risk_level": "low",
    "reason": "Need to check application logs"
}
```

### Example HIGH Risk Request
```python
{
    "requesting_agent": "CoderAgent",
    "action": "process_personal_data",
    "context": {"data_type": "email addresses"},
    "risk_level": "high"
}
```

Expected response: `human_oversight_required: true`

## Debugging Failed Tests

### View Full Output
```bash
pytest tests/integration/test_constitutional_integration.py -v -s
```

### Run with Debug Logging
```bash
LOG_LEVEL=DEBUG pytest tests/integration/ -v
```

### Run Single Test with Traceback
```bash
pytest tests/integration/test_api_e2e.py::test_supervisor_supervise_low_risk -v -tb=short
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration/ -v --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Coverage Goals

- **Overall:** 80%+
- **Constitutional Agents:** 90%+
- **API Routes:** 85%+
- **Critical Paths (HIGH/CRITICAL risk):** 100%

## Contributing

When adding new agents or features:

1. Add integration tests in `test_constitutional_integration.py`
2. Add API tests in `test_api_e2e.py`
3. Ensure coverage stays above 80%
4. Test both success and failure cases
5. Include performance tests for critical paths

## Documentation

- **Agent Implementation:** `backend/brain/agents/`
- **API Routes:** `backend/app/api/routes/agent_ops.py`
- **Schemas:** `backend/app/modules/supervisor/schemas.py`
- **User Guide:** `docs/CONSTITUTIONAL_AGENTS.md`
