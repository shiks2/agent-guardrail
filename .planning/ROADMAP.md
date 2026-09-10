# Project Roadmap

## Milestone 1: Core Foundation & Reliability (Completed)

- [x] **Phase 1: Dynamic Route & Policy Engine Core**
  - Parameterized route `/api/{resource}/{user_id}/{action}`
  - Initial `policy.json` schema parser and evaluator
  - Basic ALLOW / DENY response simulation

- [x] **Phase 2: Strict Boolean Validation & Fail-Closed Hardening**
  - Exact `type(value) is bool` leaf enforcement (prevent `"false"` truthiness bug)
  - `PolicyError` exception with `503 Service Unavailable` response
  - `/healthz` dynamic health probe

- [x] **Phase 3: Machine-Readable Audit Logging & Attribution**
  - Machine-readable reason codes (`POLICY_ALLOW`, `UNKNOWN_USER`, etc.)
  - Audit-before-raise lifecycle to capture 404/403/503 traces
  - Sanitized and length-capped `agent_id` / `X-Agent-Id` attribution
  - HTTP method tracking in `audit.jsonl`

- [x] **Phase 4: Docker Support & Local Dev Ergonomics**
  - `Dockerfile` using `python:3.12-slim`
  - `AGENT_GUARDRAIL_PORT` environment variable support

---

## Milestone 2: Ecosystem & Developer Experience (In Progress)

- [x] **Phase 5: Automated CI/CD & Testing Automation**
  - GitHub Actions workflow running regression tests (`pytest`) across Python 3.11, 3.12, 3.13
  - Smoke test job with live curls for README examples
  - CLI `guardrail report` with `--fail-on-deny` flag for CI verification

- [x] **Phase 6: Framework Integrations & Reference Examples**
  - Zero-dependency Python Client SDK (`src/client.py` - GuardrailClient)
  - LangChain tool wrapper example (`examples/langchain_guardrail.py`)
  - CrewAI tool integration example (`examples/crewai_guardrail.py`)
  - Automated CI boundary evaluation recipe (`examples/test_agent_boundary_eval.py`)

- [ ] **Phase 7: Custom Mock Payloads & High-Throughput I/O**
  - Dynamic synthetic return data per resource/action
  - Asynchronous file I/O optimization for high concurrency
