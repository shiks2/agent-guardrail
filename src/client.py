"""
Zero-dependency Python Client SDK for Agent Guardrail.
Provides a lightweight client to check permissions and assert boundary compliance.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


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
    """Client for querying Agent Guardrail mock server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        agent_id: str = "default-agent",
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.timeout = timeout

    def check(
        self,
        user_id: str,
        resource: str,
        action: str,
        method: str = "GET",
    ) -> GuardrailResponse:
        """
        Evaluate permission for an action on a resource for a user.
        Returns a GuardrailResponse object indicating whether the action is allowed.
        """
        url = f"{self.base_url}/api/{resource}/{user_id}/{action}"
        headers = {
            "X-Agent-Id": self.agent_id,
            "User-Agent": f"AgentGuardrailClient/{self.agent_id}",
        }
        req = urllib.request.Request(url, method=method.upper(), headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.status
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else {}
                return GuardrailResponse(
                    status_code=status_code,
                    allowed=True,
                    user=data.get("user", user_id),
                    resource=data.get("resource", resource),
                    action=data.get("action", action),
                    detail=data.get("status"),
                    raw=data,
                )
        except urllib.error.HTTPError as e:
            status_code = e.code
            body = e.read().decode("utf-8")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"detail": body}
            return GuardrailResponse(
                status_code=status_code,
                allowed=False,
                user=user_id,
                resource=resource,
                action=action,
                detail=data.get("detail", str(e)),
                raw=data,
            )
        except urllib.error.URLError as e:
            return GuardrailResponse(
                status_code=0,
                allowed=False,
                user=user_id,
                resource=resource,
                action=action,
                detail=f"Connection failed: {e.reason}",
                raw={},
            )

    def assert_allowed(
        self,
        user_id: str,
        resource: str,
        action: str,
        method: str = "GET",
    ) -> GuardrailResponse:
        """Check permission and raise AssertionError if the action is not allowed (status != 200)."""
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
        """Check permission and raise AssertionError if the action is allowed (status == 200)."""
        res = self.check(user_id, resource, action, method=method)
        if res.allowed:
            raise AssertionError(
                f"Expected DENY for {user_id} -> {resource}:{action} ({method}), "
                f"got {res.status_code} ALLOW"
            )
        return res
