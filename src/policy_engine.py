"""
Agent Guardrail — generalized policy engine.

Instead of one Python endpoint per resource, this exposes a single dynamic
route: /api/{resource}/{user_id}/{action}

The resource and action names are whatever you define in policy.json — no
code changes needed to model a new API. Point your agent at this instead
of production, and it gets a 200 or 403 back based on the synthetic user's
policy, with every decision logged to audit.jsonl.

Example policy.json:
    {
      "synthetic_users": {
        "alice": { "emails": { "read": true, "delete": false } },
        "bob":   { "emails": { "read": false, "delete": false } }
      }
    }

Example calls:
    GET    /api/emails/alice/read     -> 200 (allowed)
    GET    /api/emails/bob/read       -> 403 (denied)
    DELETE /api/emails/alice/delete   -> 403 (denied)
    GET    /api/emails/charlie/read   -> 404 (no such synthetic user)

Run:
    uvicorn policy_engine:app --reload --port 8080
    AGENT_GUARDRAIL_PORT=9000 uvicorn policy_engine:app --port $AGENT_GUARDRAIL_PORT
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
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


def log_decision(agent_id: str, user_id: str, resource: str, action: str, decision: str) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_id,
        "user": user_id,
        "resource": resource,
        "action": action,
        "decision": decision,
    }
    with _audit_lock:
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    print(f"{'✅ ALLOW' if decision == 'ALLOW' else '🚫 DENY'}: "
          f"agent={agent_id} user={user_id} resource={resource} action={action}")


def check_permission(user_id: str, resource: str, action: str) -> tuple[bool, dict | None]:
    """
    Returns (is_allowed, user_policy).
    user_policy is None if the synthetic user doesn't exist in policy.json.
    Unknown resources/actions for a known user default to DENY (fail-closed).
    """
    policy = load_policy()
    user_policy = policy["synthetic_users"].get(user_id)
    if user_policy is None:
        return False, None
    resource_policy = user_policy.get(resource, {})
    allowed = resource_policy.get(action, False)
    return allowed, user_policy


@app.api_route("/api/{resource}/{user_id}/{action}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def check_and_simulate(resource: str, user_id: str, action: str, request: Request):
    agent_id = request.query_params.get("agent_id", "unknown")

    allowed, user_policy = check_permission(user_id, resource, action)

    if user_policy is None:
        raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")

    decision = "ALLOW" if allowed else "DENY"
    log_decision(agent_id, user_id, resource, action, decision)

    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by sandbox policy")

    # Simulated success — never real data, just proof the call was authorized
    return {
        "user": user_id,
        "resource": resource,
        "action": action,
        "status": "simulated success",
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)