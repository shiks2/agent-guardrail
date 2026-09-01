"""
Agent Guardrail — Month 1 core.

A tiny mock API that stands in for a real backend (CRM, email, etc).
Point your AI agent at this instead of production, and it will get
a 200 or 403 back depending on the synthetic user's policy — with
every decision written to audit.jsonl.

Run:
    uvicorn policy_engine:app --reload --port 8080
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Agent Guardrail")

POLICY_PATH = Path(__file__).parent / "policy.json"
AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"


def load_policy() -> dict:
    """Reload policy.json on every request so edits take effect without a restart."""
    with open(POLICY_PATH) as f:
        return json.load(f)


def log_decision(agent_id: str, user_id: str, action: str, decision: str) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_id,
        "user": user_id,
        "action": action,
        "decision": decision,
    }
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"{'✅ ALLOW' if decision == 'ALLOW' else '🚫 DENY'}: "
          f"agent={agent_id} user={user_id} action={action}")


def check_permission(user_id: str, permission_key: str) -> tuple[bool, dict | None]:
    """Returns (is_allowed, user_policy). user_policy is None if the user doesn't exist."""
    policy = load_policy()
    user_policy = policy["synthetic_users"].get(user_id)
    if user_policy is None:
        return False, None
    return user_policy.get(permission_key, False), user_policy


@app.get("/api/users/{user_id}/emails")
async def read_emails(user_id: str, agent_id: str = "unknown"):
    allowed, user_policy = check_permission(user_id, "can_read_emails")

    if user_policy is None:
        raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")

    decision = "ALLOW" if allowed else "DENY"
    log_decision(agent_id, user_id, "read_emails", decision)

    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by sandbox policy")

    # Fake data — never real user data
    return {"user": user_id, "emails": ["hello@example.com", "invoice@example.com"]}


@app.delete("/api/users/{user_id}/records")
async def delete_records(user_id: str, agent_id: str = "unknown"):
    allowed, user_policy = check_permission(user_id, "can_delete_records")

    if user_policy is None:
        raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")

    decision = "ALLOW" if allowed else "DENY"
    log_decision(agent_id, user_id, "delete_records", decision)

    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by sandbox policy")

    return {"user": user_id, "status": "records deleted (simulated)"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}