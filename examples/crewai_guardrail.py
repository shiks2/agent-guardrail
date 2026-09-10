"""
Example: Role-Based Agent Guardrails for CrewAI / Multi-Agent Systems.

Demonstrates multi-agent attribution where each specialized agent (e.g. ReaderBot,
AdminBot) carries its identity and validates operations before execution.
"""

import sys
from pathlib import Path

# Add src to path for local runs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client import GuardrailClient


class GuardrailedRecordManager:
    """Multi-agent tool with role-based identity tracking."""

    def __init__(self, agent_role: str, guardrail_url: str = "http://127.0.0.1:8080"):
        self.agent_role = agent_role
        self.guardrail = GuardrailClient(base_url=guardrail_url, agent_id=agent_role)

    def delete_records(self, user_id: str) -> dict:
        """Attempt to delete user records with guardrail pre-check."""
        check = self.guardrail.check(
            user_id=user_id,
            resource="records",
            action="delete",
            method="DELETE",
        )

        if not check.allowed:
            return {
                "success": False,
                "agent": self.agent_role,
                "error": f"Access denied by guardrail policy ({check.detail})",
            }

        return {
            "success": True,
            "agent": self.agent_role,
            "message": f"Successfully deleted records for {user_id}",
        }


def main():
    print("Initializing Multi-Agent Guardrail Simulation...")

    # Agent 1: Customer Support Agent
    support_agent = GuardrailedRecordManager(agent_role="customer-support-bot")
    print("\n[Support Agent Attempt] Deleting records for 'alice':")
    response_1 = support_agent.delete_records(user_id="alice")
    print(f"Result: {response_1}")

    # Agent 2: Compliance Auditor
    auditor_agent = GuardrailedRecordManager(agent_role="compliance-auditor-bot")
    print("\n[Auditor Attempt] Deleting records for 'bob':")
    response_2 = auditor_agent.delete_records(user_id="bob")
    print(f"Result: {response_2}")


if __name__ == "__main__":
    main()
