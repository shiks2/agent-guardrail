"""
Example: Integrating Agent Guardrail with LangChain Tool Calling.

This example shows how to wrap LangChain tools with GuardrailClient so that
agent tool executions are pre-evaluated against policy.json before touching data.
"""

import sys
from pathlib import Path

# Add src to path for local runs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client import GuardrailClient


class GuardrailedEmailTool:
    """A simulated LangChain tool that checks permissions prior to execution."""

    name = "read_user_emails"
    description = "Read email messages for a given user account."

    def __init__(self, guardrail_url: str = "http://127.0.0.1:8080", agent_id: str = "langchain-agent"):
        self.guardrail = GuardrailClient(base_url=guardrail_url, agent_id=agent_id)

    def run(self, user_id: str) -> str:
        """Executes the tool with guardrail enforcement."""
        # 1. Evaluate permission boundary against the guardrail server
        check = self.guardrail.check(user_id=user_id, resource="emails", action="read", method="GET")

        # 2. If denied or user not found, return boundary denial message to the agent loop
        if not check.allowed:
            return f"TOOL_PERMISSION_DENIED: Agent is not authorized to read emails for user '{user_id}'. Reason: {check.detail}"

        # 3. If allowed, simulate safe execution
        return f"SUCCESS: Retrieved 3 emails for user '{user_id}'."


def main():
    print("Initializing LangChain Tool Guardrail Example...")
    tool = GuardrailedEmailTool(agent_id="langchain-assistant-v1")

    # Example 1: Authorized User (Alice)
    print("\n[Agent Action] Querying emails for user 'alice':")
    result_alice = tool.run(user_id="alice")
    print(f"Tool Output: {result_alice}")

    # Example 2: Unauthorized User (Bob)
    print("\n[Agent Action] Querying emails for user 'bob':")
    result_bob = tool.run(user_id="bob")
    print(f"Tool Output: {result_bob}")


if __name__ == "__main__":
    main()
