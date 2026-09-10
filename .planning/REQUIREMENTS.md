# Requirements & Capabilities

## Status: Baseline Verified (Brownfield Onboarding)

### Baseline Implemented Requirements

- **REQ-01: Dynamic Generic Routing**
  - Path: `/api/{resource}/{user_id}/{action}`
  - Supports HTTP verbs: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
  - Eliminates the need for custom python route definitions per new API resource.

- **REQ-02: Strict Policy Schema & Boolean Enforcement**
  - Requires non-empty `synthetic_users` dictionary.
  - Requires nested structure `user -> resource -> action -> bool`.
  - Rejects non-boolean types (`"true"`, `"false"`, `0`, `1`, `None`, lists, dicts) with `PolicyError` returning `503 Service Unavailable`.

- **REQ-03: Machine-Readable Audit Logging**
  - Appends JSON records to `src/audit.jsonl` under thread lock.
  - Record schema includes: `timestamp`, `agent`, `user`, `resource`, `action`, `method`, `decision`, and `reason`.
  - Machine-readable reason codes: `POLICY_ALLOW`, `POLICY_DENY`, `UNKNOWN_USER`, `UNKNOWN_RESOURCE`, `UNKNOWN_ACTION`, `POLICY_ERROR: <msg>`.
  - Guarantees logging precedes all HTTP exceptions.

- **REQ-04: Agent ID Attribution & Sanitization**
  - Extracts agent identity from `X-Agent-Id` header (preferred) or `agent_id` query parameter.
  - Caps length at 128 characters and strips ASCII control characters (`[\x00-\x1f\x7f]`).
  - Defaults to `"unknown"` if omitted or whitespace/control-only.

- **REQ-05: Zero-Restart Policy Hot-Reloading**
  - Reloads and validates `policy.json` on every request.
  - Changes to policy take effect immediately without process restart.

- **REQ-06: Containerized Execution**
  - Standalone Dockerfile based on `python:3.12-slim` exposing port 8080 (configurable via `AGENT_GUARDRAIL_PORT`).

- **REQ-07: Health Check Probe**
  - `/healthz` endpoint validating `policy.json` syntax on demand.

---

### Backlog & Planned Requirements

- **REQ-08: CI/CD Pipeline (GitHub Actions)**
  - Automated test runner on PRs and merges using GitHub Actions workflow.
  - Enforce automated quality gates across Python versions.

- **REQ-09: Agent Framework Integration Examples**
  - Provide working example scripts demonstrating integration with LangChain (Custom Tool), CrewAI (BaseTool), and raw Python agent loops.

- **REQ-10: Synthetic Fixtures & Custom Mock Return Payloads**
  - Allow `policy.json` (or companion fixture files) to specify custom JSON mock response payloads per resource/action instead of static `{"status": "simulated success"}`.

- **REQ-11: Async File I/O & High-Concurrency Throughput**
  - Refactor blocking synchronous disk operations in `policy_engine.py` to async I/O or background worker queues to support high-throughput load tests.
