# agent-guardrail

**Test whether your AI agent respects permission boundaries — before it touches real data.**

If you're building an agent that eventually calls real APIs (read emails, delete records, touch a calendar), you don't want to find out it ignores a permission boundary in production. `agent-guardrail` is a lightweight local mock server: point your agent at it instead of your real backend, define who's allowed to do what in a JSON file, and get a clean `200` or `403` back — with every decision logged to an immutable audit trail.

---

## How it works

Every resource, action, and synthetic user permission is defined in `policy.json` — no code changes needed to model a new API:

```json
{
  "synthetic_users": {
    "alice": {
      "emails": { "read": true, "delete": false },
      "records": { "read": true, "delete": false },
      "calendar": { "read": true, "write": true }
    },
    "bob": {
      "emails": { "read": false, "delete": false },
      "records": { "read": false, "delete": false },
      "calendar": { "read": true, "write": false }
    }
  }
}
```

Point your agent at `/api/{resource}/{user_id}/{action}` instead of your real API. The server checks the policy and responds accordingly:
- **Fail-closed guarantees**: Anything not explicitly permitted is denied. Unknown resources, unknown actions, and unknown users all fail closed.
- **Strict boolean validation**: Policy leaves must be native JSON booleans (`true`/`false`). Coerced strings (e.g. `"false"`) or malformed configs fail closed with a `503`.
- **Method-to-action binding**: Actions bind to standard HTTP verbs (`read` -> `GET`, `write` -> `POST`/`PUT`, `delete` -> `DELETE`, or verbs directly). Mismatched methods return `403 METHOD_MISMATCH`.

---

## Quick start

```bash
git clone https://github.com/shiks2/agent-guardrail.git
cd agent-guardrail
pip install -r requirements.txt
cd src && uvicorn policy_engine:app --reload --port 8080
```

Try it — verified responses from a running instance:

```bash
$ curl "http://127.0.0.1:8080/api/emails/alice/read?agent_id=test-bot"
{"user":"alice","resource":"emails","action":"read","status":"simulated success"}

$ curl "http://127.0.0.1:8080/api/emails/bob/read?agent_id=test-bot"
{"detail":"Access denied by sandbox policy"}

$ curl -X DELETE "http://127.0.0.1:8080/api/records/alice/delete?agent_id=test-bot"
{"detail":"Access denied by sandbox policy"}

$ curl "http://127.0.0.1:8080/api/calendar/bob/read?agent_id=test-bot"
{"user":"bob","resource":"calendar","action":"read","status":"simulated success"}
```

Every call above is logged to `audit.jsonl` with an explicit reason code:

```json
{"timestamp": "2026-09-10T14:30:00Z", "agent": "test-bot", "user": "alice", "resource": "emails", "action": "read", "method": "GET", "decision": "ALLOW", "reason": "POLICY_ALLOW"}
{"timestamp": "2026-09-10T14:30:00Z", "agent": "test-bot", "user": "bob", "resource": "emails", "action": "read", "method": "GET", "decision": "DENY", "reason": "POLICY_DENY"}
```

---

## Audit Trail Reporting & CI Integration

Inspect and summarize all recorded decisions using the built-in CLI:

```bash
# Print a human-readable audit report
python src/cli.py report --audit src/audit.jsonl

# Output structured JSON for automation
python src/cli.py report --json

# Fail CI build if any unauthorized (DENY) attempts occurred
python src/cli.py report --fail-on-deny
```

---

## Docker Support

Run with zero setup via Docker (hardened non-root user with health check and persistent volume):

```bash
docker build -t agent-guardrail .
docker run -p 8080:8080 -v guardrail-data:/app/src agent-guardrail
```

---

## Python Client SDK & Framework Integrations

Agent Guardrail includes a zero-dependency Python client (`GuardrailClient`) in `src/client.py`:

```python
from client import GuardrailClient

client = GuardrailClient(base_url="http://127.0.0.1:8080", agent_id="my-agent-v1")

# Check permissions
response = client.check(user_id="alice", resource="emails", action="read")
if response.allowed:
    print("Action authorized:", response.detail)
else:
    print("Action blocked:", response.detail)

# CI Assertion Helpers
client.assert_allowed("alice", "emails", "read")
client.assert_denied("bob", "emails", "read")
```

### Reference Examples
- [LangChain Custom Tool Wrapper](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/examples/langchain_guardrail.py)
- [CrewAI / Multi-Agent Role Attribution](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/examples/crewai_guardrail.py)
- [Automated Agent Boundary Conformance CI Test](file:///c:/Users/ratho/OneDrive/Desktop/sachin/ai/agent-guardrail/examples/test_agent_boundary_eval.py)

---

## Roadmap

- [x] Generic, policy-driven ALLOW/DENY engine
- [x] Audit logging with machine-readable reasons (`audit.jsonl`)
- [x] Fail-closed on unknown resource/action/user
- [x] Strict boolean type validation & fail-closed error handling
- [x] HTTP Method ↔ Action binding with zero-config fallback
- [x] Hardened Docker container
- [x] Audit report CLI with `--fail-on-deny` CI gate
- [x] Automated GitHub Actions CI workflow
- [x] Example integration with LangChain / CrewAI & Python Client SDK

---

## Contributing

Issues and PRs welcome! Please ensure all tests pass before submitting (`pytest -v`).

---

## License

MIT