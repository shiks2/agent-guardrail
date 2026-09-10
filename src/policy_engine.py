"""
Agent Guardrail — generalized policy engine.

Instead of one Python endpoint per resource, this exposes a single dynamic
route: /api/{resource}/{user_id}/{action}

The resource and action names are whatever you define in policy.json — no
code changes needed to model a new API. Point your agent at this instead
of production, and it gets a 200 or 403 back based on the synthetic user's
policy, with every decision logged to audit.jsonl.

Policy values must be JSON booleans. A quoted `"false"` is rejected at load time
rather than silently treated as truthy, and an invalid policy fails closed with a
503 instead of a 500.

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
import re
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

# Caller-supplied attribution is advisory; keep it bounded and printable.
MAX_AGENT_ID_LEN = 128
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

_audit_lock = threading.Lock()


class PolicyError(Exception):
    """policy.json is structurally invalid. Requests fail closed (503), never allow."""


def _require_bool(value: object, path: str) -> bool:
    """Accept only real JSON booleans. bool subclasses int, hence the exact check."""
    if type(value) is not bool:
        raise PolicyError(
            f"{path} must be a JSON boolean (true/false), got {type(value).__name__}={value!r}"
        )
    return value


def validate_policy(doc: object) -> dict:
    """Validate the whole document so a typo fails closed instead of failing open."""
    if not isinstance(doc, dict):
        raise PolicyError("policy root must be a JSON object")

    users = doc.get("synthetic_users")
    if not isinstance(users, dict) or not users:
        raise PolicyError('"synthetic_users" must be a non-empty JSON object')

    for user, resources in users.items():
        if not isinstance(resources, dict):
            raise PolicyError(f"synthetic_users[{user!r}] must be an object of resources")
        for resource, actions in resources.items():
            if not isinstance(actions, dict):
                raise PolicyError(
                    f"synthetic_users[{user!r}][{resource!r}] must be an object of actions"
                )
            for action, allowed in actions.items():
                _require_bool(allowed, f"synthetic_users[{user!r}][{resource!r}][{action!r}]")

    return doc


def load_policy() -> dict:
    """Reload and validate policy.json on every request so edits apply without a restart."""
    try:
        with open(POLICY_PATH) as f:
            doc = json.load(f)
    except FileNotFoundError as e:
        raise PolicyError(f"policy file not found: {POLICY_PATH}") from e
    except json.JSONDecodeError as e:
        raise PolicyError(f"policy file is not valid JSON: {e}") from e
    return validate_policy(doc)


def log_decision(
    agent_id: str,
    user_id: str,
    resource: str,
    action: str,
    decision: str,
    *,
    reason: str,
    method: str,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_id,
        "user": user_id,
        "resource": resource,
        "action": action,
        "method": method,
        "decision": decision,
        "reason": reason,
    }
    with _audit_lock:
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    print(f"{'✅ ALLOW' if decision == 'ALLOW' else '🚫 DENY'}: "
          f"agent={agent_id} user={user_id} resource={resource} action={action} "
          f"method={method} reason={reason}")


def check_permission(
    user_id: str, resource: str, action: str, policy: dict
) -> tuple[bool, dict | None, str]:
    """
    Returns (is_allowed, user_policy, reason).
    user_policy is None if the synthetic user doesn't exist in policy.json.
    Unknown resources/actions for a known user default to DENY (fail-closed).
    `reason` is a stable, machine-readable code for the audit log.
    """
    user_policy = policy["synthetic_users"].get(user_id)
    if user_policy is None:
        return False, None, "UNKNOWN_USER"
    resource_policy = user_policy.get(resource)
    if resource_policy is None:
        return False, user_policy, "UNKNOWN_RESOURCE"
    if action not in resource_policy:
        return False, user_policy, "UNKNOWN_ACTION"
    allowed = _require_bool(
        resource_policy[action], f"synthetic_users[{user_id!r}][{resource!r}][{action!r}]"
    )
    return allowed, user_policy, "POLICY_ALLOW" if allowed else "POLICY_DENY"


def clean_agent_id(request: Request) -> str:
    """Bound and sanitize caller-supplied attribution; prefer the X-Agent-Id header."""
    raw = request.headers.get("x-agent-id") or request.query_params.get("agent_id") or "unknown"
    return _CONTROL_CHARS.sub("", raw)[:MAX_AGENT_ID_LEN] or "unknown"


@app.api_route("/api/{resource}/{user_id}/{action}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def check_and_simulate(resource: str, user_id: str, action: str, request: Request):
    agent_id = clean_agent_id(request)
    method = request.method.upper()

    # A broken policy denies everything loudly instead of returning a bare 500.
    try:
        policy = load_policy()
        allowed, user_policy, reason = check_permission(user_id, resource, action, policy)
    except PolicyError as e:
        log_decision(
            agent_id, user_id, resource, action, "DENY",
            reason=f"POLICY_ERROR: {e}", method=method,
        )
        raise HTTPException(
            status_code=503, detail="Guardrail policy is invalid; see audit.jsonl"
        )

    decision = "ALLOW" if allowed else "DENY"
    # Log every outcome, including the unknown-user 404 below, before raising.
    log_decision(agent_id, user_id, resource, action, decision, reason=reason, method=method)

    if user_policy is None:
        raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")

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
    try:
        load_policy()
    except PolicyError as e:
        return {"status": "policy_error", "detail": str(e)}
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)