"""
Policy loading, validation, and action-method resolution.
"""

import json
from pathlib import Path

DEFAULT_POLICY_PATH = Path(__file__).parent / "policy.json"

DEFAULT_ACTION_METHODS: dict[str, set[str]] = {
    "read": {"GET", "HEAD"},
    "write": {"POST", "PUT", "PATCH"},
    "delete": {"DELETE"},
}
HTTP_VERBS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


class PolicyError(Exception):
    """policy.json is structurally invalid. Requests fail closed (503), never allow."""


def require_bool(value: object, path: str) -> bool:
    """Accept only real JSON booleans. bool subclasses int, hence the exact type check."""
    if type(value) is not bool:
        raise PolicyError(
            f"{path} must be a JSON boolean (true/false), got {type(value).__name__}={value!r}"
        )
    return value


def action_methods_for(action: str, policy: dict) -> set[str] | None:
    """
    Resolve allowed HTTP methods for an action:
    1. Explicit custom mapping in policy["action_methods"]
    2. Built-in standard action mapping (read -> GET/HEAD, write -> POST/PUT/PATCH, delete -> DELETE)
    3. Zero-config fallback: if action name is itself a valid HTTP verb (e.g. "get", "post", "delete")
    """
    custom = policy.get("action_methods")
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
    """Validate the policy document so any typo fails closed instead of failing open."""
    if not isinstance(doc, dict):
        raise PolicyError("policy root must be a JSON object")

    users = doc.get("synthetic_users")
    if not isinstance(users, dict) or not users:
        raise PolicyError('"synthetic_users" must be a non-empty JSON object')

    for user, resources in users.items():
        if not isinstance(resources, dict):
            raise PolicyError(f"synthetic_users[{user!r}] must be an object of resources")
        for resource, actions in resources.items():
            if not isinstance(actions, dict):
                raise PolicyError(
                    f"synthetic_users[{user!r}][{resource!r}] must be an object of actions"
                )
            for action, allowed in actions.items():
                require_bool(allowed, f"synthetic_users[{user!r}][{resource!r}][{action!r}]")

    action_methods = doc.get("action_methods")
    if action_methods is not None:
        if not isinstance(action_methods, dict):
            raise PolicyError('"action_methods" must be a JSON object')
        for act, methods in action_methods.items():
            if not isinstance(methods, (list, str)):
                raise PolicyError(f"action_methods[{act!r}] must be a list of HTTP verbs or a string")

    return doc


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict:
    """Reload and validate policy.json on every request so edits apply without a restart."""
    try:
        with open(path) as f:
            doc = json.load(f)
    except FileNotFoundError as e:
        raise PolicyError(f"policy file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise PolicyError(f"policy file is not valid JSON: {e}") from e
    return validate_policy(doc)
