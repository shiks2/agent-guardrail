"""
CI Evaluation Recipe: Automated Agent Boundary Conformance Testing.

This test recipe illustrates how CI pipelines run AI agents against Agent Guardrail
to verify that agent tool executions strictly adhere to permission policies.
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

import client
from policy_test_utils import audit, env, set_policy  # noqa: F401


class SimulatedAIAgent:
    """A simulated autonomous agent that attempts operations based on prompt instructions."""

    def __init__(self, agent_id: str, test_client):
        self.agent_id = agent_id
        self.test_client = test_client

    def execute_task(self, user: str, resource: str, action: str, method: str = "GET"):
        """Execute task by querying the guardrail endpoint."""
        return self.test_client.get(
            f"/api/{resource}/{user}/{action}",
            headers={"X-Agent-Id": self.agent_id},
        )


def test_agent_authorized_workflow(env):
    """Scenario 1: Agent performs a legitimate operation within granted boundaries."""
    agent = SimulatedAIAgent(agent_id="doc-analyzer", test_client=env.client)

    # Alice has permission to read calendar
    response = agent.execute_task(user="alice", resource="calendar", action="read")
    assert response.status_code == 200
    assert response.json()["status"] == "simulated success"

    # Verify audit record
    last_log = audit(env)[-1]
    assert last_log["agent"] == "doc-analyzer"
    assert last_log["decision"] == "ALLOW"
    assert last_log["reason"] == "POLICY_ALLOW"


def test_agent_unauthorized_boundary_rejection(env):
    """Scenario 2: Agent attempts an unauthorized boundary crossing."""
    agent = SimulatedAIAgent(agent_id="rogue-assistant", test_client=env.client)

    # Bob is NOT permitted to read emails
    response = agent.execute_task(user="bob", resource="emails", action="read")
    assert response.status_code == 403

    # Verify audit trail captures attempted violation
    last_log = audit(env)[-1]
    assert last_log["agent"] == "rogue-assistant"
    assert last_log["decision"] == "DENY"
    assert last_log["reason"] == "POLICY_DENY"


def test_agent_unknown_user_probing_detected(env):
    """Scenario 3: Agent probes for non-existent users; guardrail catches and audits."""
    agent = SimulatedAIAgent(agent_id="directory-scanner", test_client=env.client)

    response = agent.execute_task(user="eve_unknown", resource="records", action="read")
    assert response.status_code == 404

    # Verify audit trail captures the probe
    last_log = audit(env)[-1]
    assert last_log["agent"] == "directory-scanner"
    assert last_log["decision"] == "DENY"
    assert last_log["reason"] == "UNKNOWN_USER"
