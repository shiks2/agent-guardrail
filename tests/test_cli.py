"""
Tests for audit log rotation and the guardrail report CLI.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import audit
import cli


def test_log_rotation(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    max_bytes = 150  # small threshold to trigger rotation quickly

    # Write 5 entries
    for i in range(5):
        audit.log_decision(
            f"agent-{i}",
            "alice",
            "emails",
            "read",
            "ALLOW",
            reason="POLICY_ALLOW",
            method="GET",
            audit_log_path=log_file,
            max_bytes=max_bytes,
            backup_count=2,
        )

    # Verify primary log exists
    assert log_file.exists()
    # Verify backup .1 exists
    backup_1 = Path(f"{log_file}.1")
    assert backup_1.exists()


def test_cli_report_text(tmp_path, capsys):
    log_file = tmp_path / "audit.jsonl"
    records = [
        {
            "timestamp": "2026-09-10T12:00:00Z",
            "agent": "test-bot",
            "user": "alice",
            "resource": "emails",
            "action": "read",
            "method": "GET",
            "decision": "ALLOW",
            "reason": "POLICY_ALLOW",
        },
        {
            "timestamp": "2026-09-10T12:01:00Z",
            "agent": "test-bot",
            "user": "alice",
            "resource": "emails",
            "action": "delete",
            "method": "DELETE",
            "decision": "DENY",
            "reason": "POLICY_DENY",
        },
    ]
    with open(log_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    exit_code = cli.main(["report", "--audit", str(log_file)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "AGENT GUARDRAIL AUDIT REPORT" in captured.out
    assert "Total Requests Evaluated: 2" in captured.out
    assert "Allowed: 1" in captured.out
    assert "Denied:  1" in captured.out
    assert "POLICY_DENY" in captured.out


def test_cli_report_json(tmp_path, capsys):
    log_file = tmp_path / "audit.jsonl"
    records = [
        {
            "timestamp": "2026-09-10T12:00:00Z",
            "agent": "crawler",
            "user": "bob",
            "resource": "records",
            "action": "read",
            "method": "GET",
            "decision": "DENY",
            "reason": "UNKNOWN_USER",
        }
    ]
    with open(log_file, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    exit_code = cli.main(["report", "--audit", str(log_file), "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_requests"] == 1
    assert data["denied"] == 1
    assert len(data["unauthorized_attempts"]) == 1
    assert data["unauthorized_attempts"][0]["reason"] == "UNKNOWN_USER"


def test_cli_fail_on_deny(tmp_path):
    log_file = tmp_path / "audit.jsonl"
    record = {
        "timestamp": "2026-09-10T12:00:00Z",
        "agent": "bad-bot",
        "user": "alice",
        "resource": "emails",
        "action": "delete",
        "method": "DELETE",
        "decision": "DENY",
        "reason": "POLICY_DENY",
    }
    with open(log_file, "w") as f:
        f.write(json.dumps(record) + "\n")

    exit_code = cli.main(["report", "--audit", str(log_file), "--fail-on-deny"])
    assert exit_code == 1


def test_cli_empty_log(tmp_path, capsys):
    empty_log = tmp_path / "nonexistent.jsonl"
    exit_code = cli.main(["report", "--audit", str(empty_log)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Total Requests Evaluated: 0" in captured.out
