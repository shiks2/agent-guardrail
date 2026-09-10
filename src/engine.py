"""
Core authorization decision engine.
Evaluates permissions against validated policy configuration and HTTP methods.
"""

from policy import action_methods_for


def check_permission(
    user_id: str, resource: str, action: str, policy: dict, *, method: str = "GET"
) -> tuple[bool, dict | None, str]:
    """
    Evaluates policy permission for a given user, resource, and action.
    Returns (is_allowed, user_policy, reason).
    """
    users = policy.get("synthetic_users", {})
    user_policy = users.get(user_id)
    if user_policy is None:
        return False, None, "UNKNOWN_USER"

    resource_policy = user_policy.get(resource)
    if resource_policy is None:
        return False, user_policy, "UNKNOWN_RESOURCE"

    if action not in resource_policy:
        return False, user_policy, "UNKNOWN_ACTION"

    if not resource_policy[action]:
        return False, user_policy, "POLICY_DENY"

    # Enforce method-action binding (P0-3 / F2)
    valid_methods = action_methods_for(action, policy)
    if valid_methods is None:
        return False, user_policy, "UNBOUND_ACTION"
    if method.upper() not in valid_methods:
        return False, user_policy, "METHOD_MISMATCH"

    return True, user_policy, "POLICY_ALLOW"
