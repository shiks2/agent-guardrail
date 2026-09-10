"""
L3 regression tests: caller-supplied agent attribution is bounded and printable.

audit.jsonl's `agent` field is the answer to "which agent did this?", but it is
entirely caller-controlled. At minimum it must not be unbounded or contain raw
control characters.

Run: pytest tests/test_agent_id.py
"""

from policy_test_utils import audit, env  # noqa: F401

import policy_engine


def test_default_is_unknown(env):
    env.client.get("/api/emails/alice/read")
    assert audit(env)[-1]["agent"] == "unknown"


def test_long_agent_id_is_truncated(env):
    env.client.get("/api/emails/alice/read", params={"agent_id": "X" * 5000})
    assert len(audit(env)[-1]["agent"]) == policy_engine.MAX_AGENT_ID_LEN


def test_control_characters_are_stripped(env):
    env.client.get("/api/emails/alice/read", params={"agent_id": "a\nb\tc"})
    assert audit(env)[-1]["agent"] == "abc"


def test_empty_agent_id_falls_back_to_unknown(env):
    env.client.get("/api/emails/alice/read", params={"agent_id": ""})
    assert audit(env)[-1]["agent"] == "unknown"


def test_x_agent_id_header_is_honored(env):
    env.client.get("/api/emails/alice/read", headers={"X-Agent-Id": "header-bot"})
    assert audit(env)[-1]["agent"] == "header-bot"
