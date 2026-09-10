# Phase 6 Plan: Framework Integrations & Reference Examples

## Goal
Provide a zero-dependency client SDK and production-grade integration examples for AI agent frameworks (LangChain, CrewAI, and raw Python tool calling), accompanied by automated CI evaluation recipes that prove whether an agent respects configured permission boundaries.

---

## Deliverables

### 1. Zero-Dependency Python Client SDK (`src/client.py`)
- Standard library `urllib.request` / `json` implementation (`GuardrailClient`).
- Synchronous and easy-to-use interface:
  - `client.check(user_id, resource, action, method="GET")` -> `GuardrailResponse(status_code, allowed, detail, response_json)`
  - Convenience assertion helpers:
    - `client.assert_allowed(user_id, resource, action, method="GET")`
    - `client.assert_denied(user_id, resource, action, method="GET")`
- Automatically passes `X-Agent-Id` header for attribution.

### 2. LangChain Integration Example (`examples/langchain_guardrail.py`)
- Demonstrates wrapping custom tools (e.g. `EmailReaderTool`, `RecordsDeleterTool`) with `GuardrailClient`.
- Shows how LangChain agents automatically receive permission denial feedback in their agent scratchpad and choose alternative valid paths.

### 3. CrewAI / Multi-Agent Integration Example (`examples/crewai_guardrail.py`)
- Demonstrates defining tools for CrewAI / autonomous agent loops.
- Shows agent role-based delegation where unauthorized attempts fail closed without leaking data.

### 4. CI/CD Agent Evaluation Recipe (`examples/test_agent_boundary_eval.py`)
- A complete, runnable pytest test demonstrating how teams use `agent-guardrail` in CI:
  - Spins up guardrail server or connects to running instance.
  - Runs agent with benign task -> asserts ALLOW.
  - Runs agent with prompt injection / boundary violation attempt -> asserts DENY.
  - Uses `cli.main(["report", "--fail-on-deny"])` or client assertions to guard PRs.

### 5. Automated Tests for Client SDK (`tests/test_client.py`)
- Unit tests for `GuardrailClient`:
  - 200 ALLOW response parsing.
  - 403 DENY response parsing.
  - 404 UNKNOWN_USER response parsing.
  - 503 POLICY_ERROR response parsing.
  - Custom `X-Agent-Id` verification in audit logs.
  - `assert_allowed` and `assert_denied` assertion methods.

---

## Verification Plan
1. `pytest tests/test_client.py -v` (Verify client SDK behavior and status code mapping).
2. Execute example scripts (`python examples/langchain_guardrail.py`, `python examples/crewai_guardrail.py`, `pytest examples/test_agent_boundary_eval.py`).
3. Run complete test suite: `pytest -v`.
