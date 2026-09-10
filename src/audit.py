"""
Audit logging, log rotation, and agent ID attribution.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from fastapi import Request

DEFAULT_AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"
DEFAULT_MAX_BYTES = int(os.getenv("AGENT_GUARDRAIL_AUDIT_MAX_BYTES", 10 * 1024 * 1024))
DEFAULT_BACKUP_COUNT = int(os.getenv("AGENT_GUARDRAIL_AUDIT_BACKUPS", 3))

MAX_AGENT_ID_LEN = 128
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_audit_lock = threading.Lock()


def rotate_log_file(log_path: Path, max_bytes: int, backup_count: int) -> None:
    """Rotates log_path if file size exceeds max_bytes, keeping up to backup_count backups."""
    if max_bytes <= 0 or not log_path.exists():
        return
    try:
        if log_path.stat().st_size < max_bytes:
            return
    except OSError:
        return

    for i in range(backup_count - 1, 0, -1):
        src = Path(f"{log_path}.{i}")
        dst = Path(f"{log_path}.{i + 1}")
        if src.exists():
            try:
                src.replace(dst)
            except OSError:
                pass
    if backup_count > 0:
        target = Path(f"{log_path}.1")
        try:
            log_path.replace(target)
        except OSError:
            pass


def clean_agent_id(request: Request) -> str:
    """Bound and sanitize caller-supplied attribution; prefer the X-Agent-Id header."""
    raw = request.headers.get("x-agent-id") or request.query_params.get("agent_id") or "unknown"
    return _CONTROL_CHARS.sub("", raw)[:MAX_AGENT_ID_LEN] or "unknown"


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
    """Write an immutable audit entry to audit.jsonl under thread lock and log to console."""
    path = Path(audit_log_path)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_id,
        "user": user_id,
        "resource": resource,
        "action": action,
        "method": method,
        "decision": decision,
        "reason": reason,
    }
    with _audit_lock:
        rotate_log_file(path, max_bytes, backup_count)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    print(f"[{decision}] agent={agent_id} user={user_id} resource={resource} action={action} "
          f"method={method} reason={reason}")
