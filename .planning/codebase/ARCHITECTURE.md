# System Architecture

## Architecture Overview
Agent Guardrail is a lightweight, self-contained mock API server designed to validate permissions and safety boundaries for AI agents before exposing production systems or sensitive data.

```
+----------------------------------------------------------------------+
|                           AI Agent / Client                         |
+----------------------------------------------------------------------+
                                   |
         HTTP (GET, POST, PUT, DELETE, PATCH)
         /api/{resource}/{user_id}/{action}?agent_id=...
                                   v
+----------------------------------------------------------------------+
|                     FastAPI Routing & Middleware                     |
|  - CORS (allow all origins for local dev)                            |
|  - Agent ID sanitization (truncate <= 128 chars, strip control chars)|
+----------------------------------------------------------------------+
                                   |
                                   v
+----------------------------------------------------------------------+
|                           Policy Engine                              |
|  - load_policy(): reads & strictly validates policy.json              |
|  - check_permission(): evaluates user -> resource -> action rules    |
|  - Fail-closed evaluation (unknown user -> 404, unknown res/act -> 403|
|    malformed policy -> 503)                                          |
+----------------------------------------------------------------------+
               |                                           |
               v                                           v
+-----------------------------+             +-----------------------------+
|    Audit Logging Pipeline   |             |   Simulated Response / HTTP |
|  - Thread-safe write lock   |             |   - 200 Simulated Success   |
|  - Appends to audit.jsonl   |             |   - 403/404/503 HTTP errors |
|  - Terminal logging         |             +-----------------------------+
+-----------------------------+
```

## Key Architectural Principles

1. **Dynamic Generic Routing**: Rather than writing dedicated FastAPI handlers per domain entity (`/emails`, `/records`, `/calendar`), a single parameterized path `/api/{resource}/{user_id}/{action}` accepts arbitrary resources and actions defined entirely within `policy.json`.
2. **Fail-Closed Security Posture**:
   - Any unknown synthetic user returns `404` and logs a `DENY` decision with reason `UNKNOWN_USER`.
   - Any unknown resource or action on a known user returns `403` and logs a `DENY` decision with reason `UNKNOWN_RESOURCE` or `UNKNOWN_ACTION`.
   - Malformed JSON or non-boolean permission flags trigger `PolicyError`, return `503 Service Unavailable`, and log a `DENY` decision with reason `POLICY_ERROR`.
3. **Audit-First Lifecycle**: Audit logs are recorded **before** HTTP exceptions are raised. This guarantees that probes, missing users, permission denials, and syntax errors leave persistent evidence in `audit.jsonl`.
4. **Zero-Restart Policy Hot-Reload**: Policy files are reloaded and validated per request rather than stored globally at startup. Modifying `policy.json` immediately alters decision results.
5. **Caller Attribution Sanitization**: Caller-provided attribution (`agent_id` parameter or `X-Agent-Id` header) is treated as untrusted input: stripped of control characters and capped at 128 characters.
