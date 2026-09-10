# Integrations & External Interfaces

## Inbound Interfaces (API Surface)

### 1. Guardrail Policy Evaluation API
- **Endpoint**: `/api/{resource}/{user_id}/{action}`
- **HTTP Methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`
- **Attribution Inputs**:
  - HTTP Header: `X-Agent-Id` (preferred)
  - Query Parameter: `agent_id` (fallback)
- **Response Format**:
  - `200 OK`: `{"user": "{user_id}", "resource": "{resource}", "action": "{action}", "status": "simulated success"}`
  - `403 Forbidden`: `{"detail": "Access denied by sandbox policy"}`
  - `404 Not Found`: `{"detail": "No such synthetic user: {user_id}"}`
  - `503 Service Unavailable`: `{"detail": "Guardrail policy is invalid; see audit.jsonl"}`

### 2. Health Probe
- **Endpoint**: `/healthz`
- **HTTP Method**: `GET`
- **Behavior**: Validates `policy.json` on-the-fly and returns `{"status": "ok"}` or `{"status": "policy_error", "detail": "..."}`

## Outbound & Local Persistence

### 1. Policy Definition (`policy.json`)
- **Location**: `src/policy.json` (configurable in tests via `policy_engine.POLICY_PATH`)
- **Access Pattern**: Read and validated on every request (`load_policy()`) to enable zero-restart policy hot-reloading.

### 2. Audit Trail (`audit.jsonl`)
- **Location**: `src/audit.jsonl` (configurable in tests via `policy_engine.AUDIT_LOG_PATH`)
- **Access Pattern**: Append-only JSON Lines stream written synchronously inside a `threading.Lock()` context.
- **Entry Schema**:
  ```json
  {
    "timestamp": "ISO-8601 UTC timestamp",
    "agent": "string (sanitized <= 128 chars)",
    "user": "string",
    "resource": "string",
    "action": "string",
    "method": "GET | POST | PUT | DELETE | PATCH",
    "decision": "ALLOW | DENY",
    "reason": "POLICY_ALLOW | POLICY_DENY | UNKNOWN_USER | UNKNOWN_RESOURCE | UNKNOWN_ACTION | POLICY_ERROR: <msg>"
  }
  ```

## Target Consumer Frameworks
- AI Agent Orchestrators: LangChain, CrewAI, AutoGen, Microsoft Semantic Kernel, LlamaIndex, raw `httpx`/`requests` clients.
- Direct CLI tools: `curl`, Postman, automated CI evaluation scripts.
