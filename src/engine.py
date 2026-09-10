"""
Core policy permission evaluation engine.
"""

from policy import require_bool, action_methods_for


def check_permission(
    user_id: str, resource: str, action: str, policy: dict, *, method: str = "GET"
) -> tuple[bool, dict | None, str]:
    """
    Evaluates policy permission for a given user, resource, and action.
    Returns (is_allowed, user_policy, reason).
    
    Reason codes:
    - POLICY_ALLOW: Request permitted by policy and method matches.
    - POLICY_DENY: Action exists for user/resource but boolean value is False.
    - UNKNOWN_USER: User not found in synthetic_users.
    - UNKNOWN_RESOURCE: Resource not found in user's permissions.
    - UNKNOWN_ACTION: Action not found in resource's permissions.
    - UNBOUND_ACTION: Action is not bound to any HTTP method.
    - METHOD_MISMATCH: HTTP method does not match allowed methods for this action.
    """
    user_policy = policy.get("synthetic_users", {}).get(user_id)
    if user_policy is None:
        return False, None, "UNKNOWN_USER"
    resource_policy = user_policy.get(resource)
    if resource_policy is None:
        return False, user_policy, "UNKNOWN_RESOURCE"
    if action not in resource_policy:
        return False, user_policy, "UNKNOWN_ACTION"
    allowed = require_bool(
        resource_policy[action], f"synthetic_users[{user_id!r}][{resource!r}][{action!r}]"
    )
    if not allowed:
        return False, user_policy, "POLICY_DENY"

    # Enforce method-action binding (P0-3 / F2)
    valid_methods = action_methods_for(action, policy)
    if valid_methods is None:
        return False, user_policy, "UNBOUND_ACTION"
    if method.upper() not in valid_methods:
        return False, user_policy, "METHOD_MISMATCH"

    return True, user_policy, "POLICY_ALLOW"
