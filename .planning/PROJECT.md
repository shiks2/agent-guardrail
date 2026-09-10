# Project: Agent Guardrail

## Summary
`agent-guardrail` is a lightweight, zero-setup local mock API server for testing whether AI agents respect permission boundaries before interacting with production APIs and sensitive customer data.

Instead of writing custom backend mock handlers for every new API shape, developers define synthetic users, resources, and action permissions inside a simple `policy.json` file. The server evaluates requests against these rules and responds with standard HTTP status codes (`200 OK` for authorized actions, `403 Forbidden` for unauthorized actions, `404 Not Found` for missing synthetic users, and `503 Service Unavailable` for invalid policies) while writing an immutable, machine-readable audit trail to `audit.jsonl`.

## Problem Statement
When developing autonomous or semi-autonomous AI agents (e.g., via LangChain, CrewAI, AutoGen, or custom tool-calling agents), agents frequently generate tool calls with parameter variations or unauthorized scopes. Testing these boundaries directly against production or staging APIs is risky, slow, and hard to inspect. `agent-guardrail` provides an instant sandbox environment to verify permissions, capture attempted violations, and enforce fail-closed security.

## Core Invariants & Guarantees
1. **Fail-Closed Security Posture**: Anything not explicitly permitted is denied. Unknown users return `404` (audited as `UNKNOWN_USER`), unknown resources return `403` (`UNKNOWN_RESOURCE`), unknown actions return `403` (`UNKNOWN_ACTION`), and policy syntax errors return `503` (`POLICY_ERROR`).
2. **Strict Boolean Typing**: Policy permissions must be native JSON booleans (`true`/`false`). Coercion from strings like `"false"` or numbers like `0` is strictly rejected to prevent security bypasses.
3. **Audit-Before-Raise**: Every evaluation is committed to the audit trail (`audit.jsonl`) prior to raising HTTP exceptions, ensuring no request is lost or untracked.
4. **Zero-Restart Hot-Reloading**: `policy.json` is re-evaluated on every request, allowing tests and developers to modify rules dynamically without restarting the server.
5. **Caller Attribution Bounds**: Agent identity inputs are sanitized and capped at 128 characters to prevent unbounded log pollution.

## Tech Stack Overview
- **Language**: Python 3.12+
- **API Framework**: FastAPI 0.115.0 & Uvicorn 0.30.0
- **Validation**: Pydantic 2.7.0
- **Testing**: Pytest & FastAPI TestClient
- **Packaging**: Docker (`Dockerfile`)

## Repository Structure & Context
- [src/policy_engine.py](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/src/policy_engine.py): Core FastAPI application, permission engine, and audit logger.
- [src/policy.json](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/src/policy.json): Synthetic user permission declarations.
- [tests/](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/tests/): Regression suites covering policy validation (L1), audit reasons (L2), and agent ID handling (L3).
- [Dockerfile](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/Dockerfile): Zero-setup containerization.
