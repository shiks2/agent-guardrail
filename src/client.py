"""
Python Client SDK for Agent Guardrail powered by httpx.
"""

from dataclasses import dataclass
from typing import Any
import httpx


@dataclass
class GuardrailResponse:
    """Represents the outcome of a permission check against Agent Guardrail."""
    status_code: int
    allowed: bool
    user: str | None = None
    resource: str | None = None
    action: str | None = None
    detail: str | None = None
    raw: dict[str, Any] | None = None


class GuardrailClient:
    """Client for evaluating permissions against Agent Guardrail."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        agent_id: str = "default-agent",
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-Agent-Id": agent_id},
        )

    def check(
        self,
        user_id: str,
        resource: str,
        action: str,
        method: str = "GET",
    ) -> GuardrailResponse:
        """Evaluate permission for an action on a resource for a user."""
        try:
            r = self.client.request(method.upper(), f"/api/{resource}/{user_id}/{action}")
            data = r.json() if r.content else {}
            return GuardrailResponse(
                status_code=r.status_code,
                allowed=r.is_success,
                user=data.get("user", user_id),
                resource=data.get("resource", resource),
                action=data.get("action", action),
                detail=data.get("status") if r.is_success else data.get("detail", r.text),
                raw=data,
            )
        except httpx.HTTPError as e:
            return GuardrailResponse(
                status_code=0,
                allowed=False,
                user=user_id,
                resource=resource,
                action=action,
                detail=f"Connection failed: {e}",
                raw={},
            )

    def assert_allowed(
        self,
        user_id: str,
        resource: str,
        action: str,
        method: str = "GET",
    ) -> GuardrailResponse:
        """Check permission and raise AssertionError if the action is not allowed."""
        res = self.check(user_id, resource, action, method=method)
        if not res.allowed:
            raise AssertionError(
                f"Expected ALLOW for {user_id} -> {resource}:{action} ({method}), "
                f"got {res.status_code} ({res.detail})"
            )
        return res

    def assert_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        method: str = "GET",
    ) -> GuardrailResponse:
        """Check permission and raise AssertionError if the action is allowed."""
        res = self.check(user_id, resource, action, method=method)
        if res.allowed:
            raise AssertionError(
                f"Expected DENY for {user_id} -> {resource}:{action} ({method}), "
                f"got {res.status_code} ALLOW"
            )
        return res
