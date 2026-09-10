"""
Agent Guardrail — generalized policy engine.

Instead of one Python endpoint per resource, this exposes a single dynamic
route: /api/{resource}/{user_id}/{action}

The resource and action names are whatever you define in policy.json — no
code changes needed to model a new API. Point your agent at this instead
of production, and it gets a 200 or 403 back based on the synthetic user's
policy, with every decision logged to audit.jsonl.

Policy values must be JSON booleans. A quoted "false" is rejected at load time
rather than silently treated as truthy, and an invalid policy fails closed with a
503 instead of a 500.

Example calls:
    GET    /api/emails/alice/read     -> 200 (allowed)
    GET    /api/emails/bob/read       -> 403 (denied)
    DELETE /api/emails/alice/delete   -> 403 (denied)
    GET    /api/emails/charlie/read   -> 404 (no such synthetic user)
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from policy import (
    DEFAULT_POLICY_PATH,
    DEFAULT_ACTION_METHODS,
    HTTP_VERBS,
    PolicyError,
    action_methods_for,
    require_bool,
    validate_policy,
    load_policy as _load_policy,
)
from audit import (
    DEFAULT_AUDIT_LOG_PATH,
    MAX_AGENT_ID_LEN,
    clean_agent_id,
    log_decision as _log_decision,
)
from engine import check_permission

# Module-level paths for direct access and test monkeypatching
POLICY_PATH: Path = DEFAULT_POLICY_PATH
AUDIT_LOG_PATH: Path = DEFAULT_AUDIT_LOG_PATH
HOST = os.getenv("AGENT_GUARDRAIL_HOST", "127.0.0.1")
PORT = int(os.getenv("AGENT_GUARDRAIL_PORT", 8080))


def load_policy(path: Path | str | None = None) -> dict:
    return _load_policy(path or POLICY_PATH)


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
    _log_decision(
        agent_id,
        user_id,
        resource,
        action,
        decision,
        reason=reason,
        method=method,
        audit_log_path=AUDIT_LOG_PATH,
    )


app = FastAPI(title="Agent Guardrail")

cors_origins_env = os.getenv("AGENT_GUARDRAIL_CORS_ORIGINS")
allowed_origins = (
    [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    if cors_origins_env
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PolicyError)
async def policy_error_handler(request: Request, exc: PolicyError):
    agent_id = clean_agent_id(request)
    method = request.method.upper()
    log_decision(
        agent_id,
        "unknown",
        "unknown",
        "unknown",
        "DENY",
        reason=f"POLICY_ERROR: {exc}",
        method=method,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": f"Guardrail policy is invalid; see audit.jsonl ({exc})"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    P0-4 safety net: No decision path may produce an unhandled, unaudited 500.
    Every unexpected exception is audited with INTERNAL_ERROR before returning 500.
    """
    agent_id = clean_agent_id(request)
    method = request.method.upper()
    log_decision(
        agent_id,
        "unknown",
        "unknown",
        "unknown",
        "DENY",
        reason=f"INTERNAL_ERROR: {exc}",
        method=method,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error; see audit.jsonl"},
    )


@app.api_route("/api/{resource}/{user_id}/{action}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def check_and_simulate(resource: str, user_id: str, action: str, request: Request):
    agent_id = clean_agent_id(request)
    method = request.method.upper()

    try:
        policy = load_policy()
        allowed, user_policy, reason = check_permission(
            user_id, resource, action, policy, method=method
        )
    except PolicyError as e:
        log_decision(
            agent_id,
            user_id,
            resource,
            action,
            "DENY",
            reason=f"POLICY_ERROR: {e}",
            method=method,
        )
        raise HTTPException(
            status_code=503, detail="Guardrail policy is invalid; see audit.jsonl"
        )

    decision = "ALLOW" if allowed else "DENY"
    # Log every outcome, including unknown-user 404, before raising.
    log_decision(agent_id, user_id, resource, action, decision, reason=reason, method=method)

    if user_policy is None:
        raise HTTPException(status_code=404, detail=f"No such synthetic user: {user_id}")

    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by sandbox policy")

    return {
        "user": user_id,
        "resource": resource,
        "action": action,
        "status": "simulated success",
    }


@app.get("/healthz")
def healthz():
    try:
        load_policy()
    except PolicyError as e:
        return {"status": "policy_error", "detail": str(e)}
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)