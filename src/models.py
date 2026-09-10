"""
Domain models and schema definitions for Agent Guardrail using Pydantic.
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field, StrictBool, field_validator


class PolicyModel(BaseModel):
    """Declarative policy configuration model with strict boolean leaf validation."""

    action_methods: dict[str, list[str] | str] = Field(default_factory=dict)
    synthetic_users: dict[str, dict[str, dict[str, StrictBool]]]

    @field_validator("synthetic_users")
    @classmethod
    def validate_non_empty_users(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            raise ValueError('"synthetic_users" must be a non-empty object')
        return v


class AuditRecord(BaseModel):
    """Structured record for audit trail entries."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str = "unknown"
    user: str = "unknown"
    resource: str = "unknown"
    action: str = "unknown"
    method: str = "GET"
    decision: str = "DENY"
    reason: str = "UNKNOWN"
