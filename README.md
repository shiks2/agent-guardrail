#  agent-guardrail

**Test whether your AI agent respects permission boundaries — before it touches real data.**

If you're building an agent that eventually calls real APIs (read emails, delete records, touch a calendar), you don't want to find out it ignores a permission boundary in production. `agent-guardrail` is a tiny local mock server: point your agent at it instead of your real backend, define who's allowed to do what in a JSON file, and get a clean `200` or `403` back — with every decision logged.

## How it works

Every resource and action is defined in `policy.json` — no code changes needed to model a new API:

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

Point your agent at `/api/{resource}/{user_id}/{action}` instead of your real API. The server checks the policy and responds accordingly. Anything not explicitly allowed is denied — unknown resources, unknown actions, and unknown users all fail closed.

## Quick start

```bash
git clone https://github.com/shiks2/agent-guardrail.git
cd agent-guardrail
pip install -r requirements.txt
cd src && uvicorn policy_engine:app --reload --port 8080
```

Try it — these are real, verified responses from a running instance:

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

Every call above is logged to `audit.jsonl`:

```json
{"timestamp": "2026-09-01T07:07:58Z", "agent": "test-bot", "user": "alice", "resource": "emails", "action": "read", "decision": "ALLOW"}
{"timestamp": "2026-09-01T07:07:58Z", "agent": "test-bot", "user": "bob", "resource": "emails", "action": "read", "decision": "DENY"}
```

## Model your own API

Edit `policy.json` — add whatever resources and actions match your real API's shape (`files`, `crm_contacts`, `payments`, anything). No Python changes required.

```json
{
  "synthetic_users": {
    "charlie": {
      "files": { "read": true, "delete": false }
    }
  }
}
```

```bash
curl "http://127.0.0.1:8080/api/files/charlie/read"     # 200
curl -X DELETE "http://127.0.0.1:8080/api/files/charlie/delete"  # 403
```

## Roadmap

- [x] Generic, policy-driven ALLOW/DENY engine
- [x] Audit logging (`audit.jsonl`)
- [x] Fail-closed on unknown resource/action/user
- [ ] Docker image
- [ ] GitHub Action for CI/CD (fail a PR if an agent attempts unauthorized access)
- [ ] Example integration with LangChain / CrewAI

## Contributing

This is a solo-dev MVP — issues and PRs welcome, especially if you hit a real API shape it doesn't model well.

## License

MIT