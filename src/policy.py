"""
Policy loading, parsing, and action-method resolution.
Leverages Pydantic PolicyModel for declarative validation.
"""

import json
from pathlib import Path
from pydantic import ValidationError

from models import PolicyModel

DEFAULT_POLICY_PATH = Path(__file__).parent / "policy.json"

DEFAULT_ACTION_METHODS: dict[str, set[str]] = {
    "read": {"GET", "HEAD"},
    "write": {"POST", "PUT", "PATCH"},
    "delete": {"DELETE"},
}
HTTP_VERBS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


class PolicyError(Exception):
    """Raised when policy.json is structurally invalid or unparseable."""


def action_methods_for(action: str, policy: dict | PolicyModel) -> set[str] | None:
    """
    Resolve allowed HTTP methods for an action:
    1. Custom mapping in policy["action_methods"]
    2. Built-in mapping (read -> GET/HEAD, write -> POST/PUT/PATCH, delete -> DELETE)
    3. Zero-config fallback: if action name is a standard HTTP verb
    """
    custom = policy.get("action_methods") if isinstance(policy, dict) else policy.action_methods
    if isinstance(custom, dict) and action in custom:
        methods = custom[action]
        if isinstance(methods, list):
            return {m.upper() for m in methods if isinstance(m, str)}
        if isinstance(methods, str):
            return {methods.upper()}
    if action in DEFAULT_ACTION_METHODS:
        return DEFAULT_ACTION_METHODS[action]
    if action.upper() in HTTP_VERBS:
        return {action.upper()}
    return None


def validate_policy(doc: object) -> dict:
    """Validate policy using Pydantic StrictBool schema; raises PolicyError on failure."""
    if not isinstance(doc, dict):
        raise PolicyError("policy root must be a JSON object")
    try:
        model = PolicyModel.model_validate(doc)
        return model.model_dump()
    except (ValidationError, ValueError, TypeError) as e:
        raise PolicyError(f"invalid policy structure: {e}") from e


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict:
    """Reload and validate policy.json on every request so edits apply without a restart."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError as e:
        raise PolicyError(f"policy file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise PolicyError(f"policy file is not valid JSON: {e}") from e
    return validate_policy(doc)
