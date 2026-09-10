# Code Conventions & Patterns

## Coding Style & Standards
- **Python Standard**: Follows PEP 8 with explicit type annotations (`user_id: str`, `doc: object`, `tuple[bool, dict | None, str]`).
- **Formatting**: 4-space indentation, clear module and function docstrings with usage examples.
- **Naming Conventions**:
  - Functions & variables: `snake_case` (e.g., `check_permission`, `clean_agent_id`, `_audit_lock`)
  - Classes & Exceptions: `PascalCase` (e.g., `PolicyError`)
  - Global Constants: `UPPER_SNAKE_CASE` (e.g., `POLICY_PATH`, `AUDIT_LOG_PATH`, `MAX_AGENT_ID_LEN`)
  - Private helper functions: Leading underscore (e.g., `_require_bool`)

## Key Patterns Observed

### 1. Strict Boolean Type Enforcement
Because in Python `bool` inherits from `int` (`isinstance(True, int) == True`), type checks use strict identity:
```python
if type(value) is not bool:
    raise PolicyError(...)
```
This prevents accidental truthiness coercion from strings (such as `"false"` or `"0"`).

### 2. Audit-Before-Raise Pattern
In API endpoints, `log_decision()` is invoked **prior** to throwing `HTTPException(status_code=...)`:
```python
decision = "ALLOW" if allowed else "DENY"
log_decision(agent_id, user_id, resource, action, decision, reason=reason, method=method)

if user_policy is None:
    raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")
if not allowed:
    raise HTTPException(status_code=403, detail="Access denied by sandbox policy")
```

### 3. Explicit Test Imports (No Hidden Conftest Magic)
Test modules explicitly import needed helpers (`from policy_test_utils import audit, env, set_policy`) to make dependency trees transparent.

### 4. Zero-State Filesystem Mocking in Tests
Tests avoid touching repo root `policy.json` or `audit.jsonl` by setting up isolated temporary paths via pytest's `tmp_path` and `monkeypatch`.
