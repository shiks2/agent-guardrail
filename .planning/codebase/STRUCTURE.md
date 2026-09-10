# Codebase Structure

## Directory Tree

```
agent-guardrail/
├── Dockerfile                  # Container definition for containerized execution
├── README.md                   # Project overview, quickstart, examples, and roadmap
├── requirements.txt            # Python dependencies (FastAPI, Uvicorn, Pydantic, python-dotenv)
├── src/
│   ├── __init__.py             # Python package marker
│   ├── policy.json             # Synthetic user policy definitions
│   └── policy_engine.py        # Core application, policy validation, and audit logger
└── tests/
    ├── policy_test_utils.py    # Test fixtures and shared testing utilities
    ├── test_agent_id.py        # Regression suite: Agent ID bounding and sanitization
    ├── test_audit_reasons.py   # Regression suite: Audit reasons, HTTP method recording, error traces
    └── test_policy_validation.py # Regression suite: Boolean validation, fail-closed 503 behavior
```

## Module Responsibilities

### `src/policy_engine.py`
- **Application Setup**: Initializes FastAPI app, CORS middleware, and environment variables.
- **Exceptions**: Defines `PolicyError` exception class for invalid configuration states.
- **Validation**:
  - `_require_bool(value, path)`: Enforces that policy leaves are genuine JSON booleans (`type(value) is bool`).
  - `validate_policy(doc)`: Validates nested structure (`synthetic_users -> user -> resource -> action -> bool`).
- **Engine Logic**:
  - `load_policy()`: Loads and parses `policy.json`.
  - `check_permission(user_id, resource, action, policy)`: Evaluates allow/deny status and assigns reason codes (`POLICY_ALLOW`, `POLICY_DENY`, `UNKNOWN_USER`, `UNKNOWN_RESOURCE`, `UNKNOWN_ACTION`).
  - `clean_agent_id(request)`: Extracts, bounds (128 chars), and sanitizes agent identifiers.
  - `log_decision(...)`: Thread-safe file writer for `audit.jsonl` and console logger.
- **Endpoints**:
  - `/api/{resource}/{user_id}/{action}`: Dynamic route handler.
  - `/healthz`: Health check probe.

### `tests/`
- **`policy_test_utils.py`**: Provides the `env` pytest fixture (mocking `POLICY_PATH` and `AUDIT_LOG_PATH` in a temporary directory), helper functions `audit(env)` and `set_policy(env, doc)`.
- **`test_policy_validation.py`**: Verifies exact boolean handling (rejecting strings `"false"`, `0`, `None`), 503 error handling on malformed JSON, and `/healthz` reporting.
- **`test_audit_reasons.py`**: Verifies audit trails for all decisions, reasons, and method auditing.
- **`test_agent_id.py`**: Verifies bounding, control-character stripping, and header extraction for agent IDs.
