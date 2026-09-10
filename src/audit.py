"""
Audit logging and agent ID attribution using standard library RotatingFileHandler.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import re
from pathlib import Path
from fastapi import Request

from models import AuditRecord

DEFAULT_AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"
DEFAULT_MAX_BYTES = int(os.getenv("AGENT_GUARDRAIL_AUDIT_MAX_BYTES", 10 * 1024 * 1024))
DEFAULT_BACKUP_COUNT = int(os.getenv("AGENT_GUARDRAIL_AUDIT_BACKUPS", 3))

MAX_AGENT_ID_LEN = 128
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def clean_agent_id(request: Request) -> str:
    """Bound and sanitize caller-supplied attribution; prefer the X-Agent-Id header."""
    raw = request.headers.get("x-agent-id") or request.query_params.get("agent_id") or "unknown"
    return _CONTROL_CHARS.sub("", raw)[:MAX_AGENT_ID_LEN] or "unknown"


def _get_audit_logger(log_path: Path | str, max_bytes: int, backup_count: int) -> logging.Logger:
    """Retrieve or configure a thread-safe RotatingFileHandler logger for the given path."""
    path_str = str(Path(log_path).resolve())
    logger_name = f"guardrail_audit_{path_str}_{max_bytes}_{backup_count}"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


def log_decision(
    agent_id: str,
    user_id: str,
    resource: str,
    action: str,
    decision: str,
    *,
    reason: str,
    method: str,
    audit_log_path: Path | str = DEFAULT_AUDIT_LOG_PATH,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Record an audit entry using RotatingFileHandler and log to console."""
    record = AuditRecord(
        agent=agent_id,
        user=user_id,
        resource=resource,
        action=action,
        method=method,
        decision=decision,
        reason=reason,
    )
    line = record.model_dump_json()
    logger = _get_audit_logger(audit_log_path, max_bytes, backup_count)
    logger.info(line)
    for handler in logger.handlers:
        handler.flush()

    print(f"[{decision}] agent={agent_id} user={user_id} resource={resource} action={action} "
          f"method={method} reason={reason}")
