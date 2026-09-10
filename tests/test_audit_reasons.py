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


def test_method_mismatch_is_denied_and_audited(env):
    """
    F2 / P0-3 fix: Sending a DELETE request to a 'read' action is denied with METHOD_MISMATCH.
    """
    r = env.client.delete("/api/emails/alice/read", params={"agent_id": "x"})
    assert r.status_code == 403
    line = audit(env)[-1]
    assert line["method"] == "DELETE"
    assert line["action"] == "read"
    assert line["decision"] == "DENY"
    assert line["reason"] == "METHOD_MISMATCH"


def test_zero_config_verb_action(env):
    """Actions named after standard HTTP verbs bind automatically without config."""
    set_policy(
        env,
        {
            "synthetic_users": {
                "alice": {
                    "records": {"delete": True, "post": True}
                }
            }
        },
    )
    # DELETE on delete action -> allowed
    r1 = env.client.delete("/api/records/alice/delete")
    assert r1.status_code == 200
    assert audit(env)[-1]["reason"] == "POLICY_ALLOW"

    # GET on delete action -> method mismatch
    r2 = env.client.get("/api/records/alice/delete")
    assert r2.status_code == 403
    assert audit(env)[-1]["reason"] == "METHOD_MISMATCH"


def test_unbound_action_is_denied(env):
    """An action that is not in defaults and not an HTTP verb fails closed with UNBOUND_ACTION."""
    set_policy(
        env,
        {
            "synthetic_users": {
                "alice": {
                    "documents": {"approve": True}
                }
            }
        },
    )
    r = env.client.post("/api/documents/alice/approve")
    assert r.status_code == 403
    assert audit(env)[-1]["reason"] == "UNBOUND_ACTION"


def test_custom_action_methods_in_policy(env):
    """Custom action_methods declared in policy.json bind non-standard action names."""
    set_policy(
        env,
        {
            "action_methods": {
                "approve": ["POST"]
            },
            "synthetic_users": {
                "alice": {
                    "documents": {"approve": True}
                }
            }
        },
    )
    r_post = env.client.post("/api/documents/alice/approve")
    assert r_post.status_code == 200
    assert audit(env)[-1]["reason"] == "POLICY_ALLOW"

    r_get = env.client.get("/api/documents/alice/approve")
    assert r_get.status_code == 403
    assert audit(env)[-1]["reason"] == "METHOD_MISMATCH"

