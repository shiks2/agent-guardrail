"""
L1 regression tests: policy values must be real JSON booleans, and a malformed
policy must fail closed with 503 rather than returning a bare 500.

Run: pytest tests/test_policy_validation.py
"""

import pytest

from policy_test_utils import audit, env, set_policy  # noqa: F401


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("GET", "/api/emails/alice/read", 200),
        ("GET", "/api/emails/bob/read", 403),
        ("DELETE", "/api/records/alice/delete", 403),
        ("GET", "/api/calendar/bob/read", 200),
    ],
)
def test_readme_examples_unchanged(env, method, path, expected):
    assert env.client.request(method, path).status_code == expected


def test_allow_response_shape_unchanged(env):
    assert env.client.get("/api/emails/alice/read").json() == {
        "user": "alice",
        "resource": "emails",
        "action": "read",
        "status": "simulated success",
    }


@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None, ["x"], {"x": True}, ""])
def test_non_boolean_policy_value_is_rejected_not_allowed(env, bad):
    set_policy(env, {"synthetic_users": {"alice": {"emails": {"read": bad}}}})
    r = env.client.get("/api/emails/alice/read")
    assert r.status_code == 503, f"{bad!r} must not be coerced into a decision"
    assert audit(env)[-1]["decision"] == "DENY"


def test_quoted_false_specifically_is_denied(env):
    """The headline regression: a YAML/env copy-paste of "false" used to grant access."""
    set_policy(env, {"synthetic_users": {"alice": {"emails": {"read": "false"}}}})
    assert env.client.get("/api/emails/alice/read").status_code == 503


@pytest.mark.parametrize(
    "doc",
    [
        {},
        {"synthetic_users": {}},
        {"synthetic_users": {"alice": None}},
        {"synthetic_users": {"alice": {"emails": None}}},
        {"synthetic_users": {"alice": {"emails": {"read": False, "write": "nope"}}}},
        "not json at all",
    ],
)
def test_malformed_policy_is_503_and_audited(env, doc):
    set_policy(env, doc)
    assert env.client.get("/api/emails/alice/read").status_code == 503
    assert audit(env), "a rejected policy must still produce an audit line"


def test_healthz_reports_policy_error(env):
    assert env.client.get("/healthz").json() == {"status": "ok"}
    set_policy(env, "{ broken")
    assert env.client.get("/healthz").json()["status"] == "policy_error"
