"""
Unit tests for the zero-dependency Python Client SDK (GuardrailClient).
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import client
from policy_test_utils import audit, env, set_policy  # noqa: F401


def test_client_check_allow(env):
    c = client.GuardrailClient(agent_id="test-client")
    # Using TestClient custom transport / monkeypatching or testing via client logic
    # Since GuardrailClient uses urllib.request, let's test both directly via URL or with a test client wrapper
    res = env.client.get("/api/emails/alice/read", headers={"X-Agent-Id": c.agent_id})
    assert res.status_code == 200
    assert audit(env)[-1]["agent"] == "test-client"
    assert audit(env)[-1]["decision"] == "ALLOW"


def test_client_response_dataclass():
    resp_allow = client.GuardrailResponse(
        status_code=200,
        allowed=True,
        user="alice",
        resource="emails",
        action="read",
        detail="simulated success",
        raw={"user": "alice", "status": "simulated success"},
    )
    assert resp_allow.allowed is True
    assert resp_allow.status_code == 200

    resp_deny = client.GuardrailResponse(
        status_code=403,
        allowed=False,
        user="bob",
        resource="emails",
        action="read",
        detail="Access denied by sandbox policy",
        raw={"detail": "Access denied by sandbox policy"},
    )
    assert resp_deny.allowed is False
    assert resp_deny.status_code == 403


def test_client_assertion_helpers(monkeypatch):
    c = client.GuardrailClient(agent_id="eval-bot")

    # Mock check returning allow
    monkeypatch.setattr(
        c,
        "check",
        lambda user, resource, action, method="GET": client.GuardrailResponse(
            status_code=200, allowed=True, user=user, resource=resource, action=action
        ),
    )
    res = c.assert_allowed("alice", "emails", "read")
    assert res.allowed is True

    with pytest.raises(AssertionError) as exc_info:
        c.assert_denied("alice", "emails", "read")
    assert "Expected DENY" in str(exc_info.value)

    # Mock check returning deny
    monkeypatch.setattr(
        c,
        "check",
        lambda user, resource, action, method="GET": client.GuardrailResponse(
            status_code=403, allowed=False, user=user, resource=resource, action=action, detail="Denied"
        ),
    )
    res = c.assert_denied("bob", "emails", "read")
    assert res.allowed is False

    with pytest.raises(AssertionError) as exc_info:
        c.assert_allowed("bob", "emails", "read")
    assert "Expected ALLOW" in str(exc_info.value)
