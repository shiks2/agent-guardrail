"""
Shared helpers for the guardrail test-suite.

Kept in a plain module rather than conftest.py so each test file states exactly
what it depends on.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import policy_engine  # noqa: E402

POLICY = {
    "synthetic_users": {
        "alice": {
            "emails": {"read": True, "delete": False},
            "records": {"read": True, "delete": False},
            "calendar": {"read": True, "write": True},
        },
        "bob": {
            "emails": {"read": False, "delete": False},
            "records": {"read": False, "delete": False},
            "calendar": {"read": True, "write": False},
        },
    }
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A TestClient wired to a throwaway policy.json and audit.jsonl."""
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(POLICY))
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(policy_engine, "POLICY_PATH", policy_path)
    monkeypatch.setattr(policy_engine, "AUDIT_LOG_PATH", audit_path)
    client = TestClient(policy_engine.app, raise_server_exceptions=False)
    return type("Env", (), {"client": client, "policy": policy_path, "audit": audit_path})


def audit(env):
    """Parsed audit.jsonl contents, oldest first."""
    if not env.audit.exists():
        return []
    return [json.loads(line) for line in env.audit.read_text().splitlines() if line.strip()]


def set_policy(env, doc):
    """Write a policy document; a str is written verbatim (for invalid-JSON tests)."""
    env.policy.write_text(doc if isinstance(doc, str) else json.dumps(doc))
