# Codebase Structure

## Directory Tree

```
agent-guardrail/
├── Dockerfile                  # Hardened container definition (non-root, healthcheck, volume)
├── LICENSE                     # MIT License
├── README.md                   # Project overview, SDK usage, examples, and roadmap
├── pyproject.toml              # Build & tool configuration (pythonpath, pyright)
├── requirements.txt            # Production dependencies (FastAPI, Uvicorn, Pydantic)
├── requirements-dev.txt        # Development dependencies (pytest, httpx)
├── .dockerignore               # Container build ignore rules
├── .github/workflows/ci.yml    # GitHub Actions matrix CI workflow
├── examples/
│   ├── langchain_guardrail.py      # LangChain tool integration example
│   ├── crewai_guardrail.py         # CrewAI multi-agent role attribution example
│   └── test_agent_boundary_eval.py # Pytest CI boundary evaluation recipe
├── src/
│   ├── __init__.py             # Python package marker
│   ├── models.py               # Pydantic schemas (PolicyModel with StrictBool, AuditRecord)
│   ├── policy.py               # Policy loading, JSON parsing, and action-method resolution
│   ├── audit.py                # Audit logging and size-based rotation (RotatingFileHandler)
│   ├── engine.py               # Pure permission decision engine
│   ├── cli.py                  # Zero-dependency report & CI gate CLI
│   ├── client.py               # Zero-dependency Python Client SDK (GuardrailClient)
│   ├── policy.json             # Synthetic user policy definitions
│   └── policy_engine.py        # FastAPI app, synchronous threadpool routes, exception safety net
└── tests/
    ├── policy_test_utils.py    # Test fixtures and shared testing utilities
    ├── test_agent_id.py        # Regression suite: Agent ID bounding and sanitization
    ├── test_audit_reasons.py   # Regression suite: Audit reasons, HTTP method binding
    ├── test_policy_validation.py # Regression suite: Pydantic StrictBool validation, 503 fail-closed
    ├── test_cli.py             # CLI reporting, JSON output, and rotation tests
    └── test_client.py          # Python Client SDK tests
```

## Module Responsibilities

### `src/models.py`
- **Domain Schemas**: Defines `PolicyModel` with `StrictBool` validation to prevent truthiness bypasses. Defines `AuditRecord` for standardized audit logs.

### `src/policy.py`
- **Configuration & Resolution**: Loads JSON files, validates against `PolicyModel`, and resolves action-to-HTTP-method bindings (`action_methods_for`).

### `src/audit.py`
- **Audit Pipeline**: Uses Python standard library `RotatingFileHandler` to log immutable, machine-readable JSON lines with bounded size and backups. Sanitizes caller-supplied `X-Agent-Id` headers.

### `src/engine.py`
- **Authorization Engine**: Evaluates permissions and returns `(is_allowed, user_policy, reason)` with strict fail-closed codes.

### `src/cli.py`
- **CLI & CI Gate**: Analyzes audit logs, formats summary tables, outputs JSON, and exits with non-zero code on `--fail-on-deny`.

### `src/client.py`
- **SDK**: Zero-dependency `GuardrailClient` for Python applications and evaluation test suites.

### `src/policy_engine.py`
- **Web API**: FastAPI application routing dynamic requests (`/api/{resource}/{user_id}/{action}`) and health checks (`/healthz`) to worker threads with a global exception safety net.
