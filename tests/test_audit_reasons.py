"""
L2 regression tests: every decision — including the unknown-user 404 — is written to
audit.jsonl with a machine-readable reason, and the HTTP method is recorded.

Run: pytest tests/test_audit_reasons.py
"""

from policy_test_utils import audit, env, set_policy  # noqa: F401


def test_unknown_user_is_audited_before_404(env):
    r = env.client.get("/api/emails/ghost/read", params={"agent_id": "probe"})
    assert r.status_code == 404
    line = audit(env)[-1]
    assert (line["decision"], line["reason"], line["agent"]) == ("DENY", "UNKNOWN_USER", "probe")


def test_unknown_resource_and_action_reasons(env):
    env.client.get("/api/nuclear/alice/launch")
    env.client.get("/api/emails/alice/launch")
    assert [line["reason"] for line in audit(env)] == ["UNKNOWN_RESOURCE", "UNKNOWN_ACTION"]


def test_policy_deny_and_allow_reasons(env):
    env.client.get("/api/emails/bob/read")
    env.client.get("/api/emails/alice/read")
    assert [line["reason"] for line in audit(env)] == ["POLICY_DENY", "POLICY_ALLOW"]
    assert [line["decision"] for line in audit(env)] == ["DENY", "ALLOW"]


def test_policy_error_is_audited_with_reason(env):
    set_policy(env, {"synthetic_users": {"alice": {"emails": {"read": "false"}}}})
    env.client.get("/api/emails/alice/read")
    line = audit(env)[-1]
    assert line["decision"] == "DENY"
    assert line["reason"].startswith("POLICY_ERROR")


def test_one_audit_line_per_request(env):
    for _ in range(5):
        env.client.get("/api/emails/alice/read")
    assert len(audit(env)) == 5


def test_method_is_recorded_without_changing_the_decision(env):
    """
    Decision semantics are intentionally unchanged: the action lives in the path and the
    HTTP method is still not part of the check. The log now tells the truth about it.
    """
    r = env.client.delete("/api/emails/alice/read", params={"agent_id": "x"})
    assert r.status_code == 200  # preserved behavior, not a silent break
    line = audit(env)[-1]
    assert line["method"] == "DELETE"
    assert line["action"] == "read"
    assert line["decision"] == "ALLOW"
