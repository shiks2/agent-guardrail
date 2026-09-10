# Testing Strategy & Guidelines

## Framework & Tools
- **Test Runner**: `pytest`
- **HTTP Client**: `fastapi.testclient.TestClient` (backed by `httpx`)
- **Isolation**: `tmp_path` fixture + `monkeypatch` to redirect file operations to temporary directories.

## Test Structure & Levels

The test suite is organized into distinct regression suites:

1. **`tests/test_policy_validation.py` (L1 Regression)**:
   - Verifies baseline README example requests and status codes.
   - Verifies response payload structure for allowed requests.
   - Tests strict rejection of non-boolean policy values (`"false"`, `"true"`, `0`, `1`, `None`, lists, dicts).
   - Verifies that malformed policy files fail closed with `503 Service Unavailable`.
   - Validates `/healthz` behavior with valid and broken policies.

2. **`tests/test_audit_reasons.py` (L2 Regression)**:
   - Verifies that unknown user requests produce an audit entry before returning `404`.
   - Verifies exact reason codes: `UNKNOWN_USER`, `UNKNOWN_RESOURCE`, `UNKNOWN_ACTION`, `POLICY_DENY`, `POLICY_ALLOW`, `POLICY_ERROR`.
   - Verifies 1:1 request-to-audit-log invariant across multiple calls.
   - Verifies HTTP method recording across different HTTP verbs.

3. **`tests/test_agent_id.py` (L3 Regression)**:
   - Verifies default agent ID resolution (`unknown`).
   - Verifies length truncation at `MAX_AGENT_ID_LEN` (128 characters).
   - Verifies removal of ASCII control characters (`\n`, `\t`, etc.).
   - Verifies precedence of `X-Agent-Id` header over query parameter.

## Running Tests

```bash
# Run entire test suite
pytest

# Run a specific test file
pytest tests/test_policy_validation.py
pytest tests/test_audit_reasons.py
pytest tests/test_agent_id.py

# Run with verbose output
pytest -v
```
