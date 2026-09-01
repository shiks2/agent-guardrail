"""
Agent Guardrail — Month 1 core.

A tiny mock API that stands in for a real backend (CRM, email, etc).
Point your AI agent at this instead of production, and it will get
a 200 or 403 back depending on the synthetic user's policy — with
every decision written to audit.jsonl.

Run:
    uvicorn policy_engine:app --reload --port 8080
    AGENT_GUARDRAIL_PORT=9000 uvicorn policy_engine:app --port $AGENT_GUARDRAIL_PORT
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agent Guardrail")

# CORS: harmless to enable, but only matters if a browser calls this API
# directly via fetch/XHR. Server-side agent frameworks (LangChain, CrewAI,
# raw requests/httpx) never hit CORS — it's a browser-only mechanism.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev tool only — never do this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

POLICY_PATH = Path(__file__).parent / "policy.json"
AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"
PORT = int(os.getenv("AGENT_GUARDRAIL_PORT", 8080))

_audit_lock = threading.Lock()


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
    # Defensive: not strictly needed while handlers stay async-def-with-no-await
    # (uvicorn's single event loop serializes them), but this is what protects
    # you the moment you add real async I/O or run with --workers > 1 per process.
    with _audit_lock:
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)