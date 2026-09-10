"""
Command-line interface for Agent Guardrail.
Provides audit trail reporting and CI validation.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def parse_audit_file(path: Path | str) -> list[dict]:
    """Parse JSON Lines from audit.jsonl file."""
    file_path = Path(path)
    if not file_path.exists():
        return []
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def analyze_audit_records(records: list[dict]) -> dict:
    """Compute summary metrics and breakdown tables from audit records."""
    total = len(records)
    decisions = Counter(r.get("decision", "UNKNOWN") for r in records)
    reasons = Counter(r.get("reason", "UNKNOWN") for r in records)
    agents = Counter(r.get("agent", "unknown") for r in records)
    denials = [r for r in records if r.get("decision") == "DENY"]

    denial_breakdown = Counter(
        (
            r.get("agent", "unknown"),
            r.get("user", "unknown"),
            r.get("resource", "unknown"),
            r.get("action", "unknown"),
            r.get("method", "GET"),
            r.get("reason", "UNKNOWN"),
        )
        for r in denials
    )

    return {
        "total_requests": total,
        "allowed": decisions.get("ALLOW", 0),
        "denied": decisions.get("DENY", 0),
        "reasons": dict(reasons),
        "agents": dict(agents),
        "unauthorized_attempts": [
            {
                "agent": item[0],
                "user": item[1],
                "resource": item[2],
                "action": item[3],
                "method": item[4],
                "reason": item[5],
                "count": count,
            }
            for item, count in denial_breakdown.most_common()
        ],
    }


def format_text_report(stats: dict) -> str:
    """Format audit statistics into a clean text summary."""
    lines = [
        "==================================================",
        "           AGENT GUARDRAIL AUDIT REPORT           ",
        "==================================================",
        f"Total Requests Evaluated: {stats['total_requests']}",
        f"  - Allowed: {stats['allowed']}",
        f"  - Denied:  {stats['denied']}",
        "",
        "Decisions by Reason Code:",
    ]
    for reason, count in stats.get("reasons", {}).items():
        lines.append(f"  * {reason}: {count}")

    lines.append("")
    lines.append("Activity by Agent:")
    for agent, count in stats.get("agents", {}).items():
        lines.append(f"  * {agent}: {count} requests")

    unauthorized = stats.get("unauthorized_attempts", [])
    if unauthorized:
        lines.append("")
        lines.append("Unauthorized Attempts Breakdown:")
        lines.append(f"{'AGENT':<15} {'USER':<10} {'RESOURCE':<12} {'ACTION':<10} {'METHOD':<8} {'COUNT':<6} REASON")
        lines.append("-" * 80)
        for item in unauthorized:
            lines.append(
                f"{item['agent']:<15} {item['user']:<10} {item['resource']:<12} "
                f"{item['action']:<10} {item['method']:<8} {item['count']:<6} {item['reason']}"
            )
    else:
        lines.append("")
        lines.append("No unauthorized attempts recorded.")

    lines.append("==================================================")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guardrail", description="Agent Guardrail CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    report_parser = subparsers.add_parser("report", help="Analyze audit log and generate summary")
    report_parser.add_argument(
        "--audit",
        type=str,
        default="src/audit.jsonl",
        help="Path to audit.jsonl file (default: src/audit.jsonl)",
    )
    report_parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format",
    )
    report_parser.add_argument(
        "--fail-on-deny",
        action="store_true",
        help="Exit with non-zero code if any unauthorized (DENY) attempts exist",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "report":
        records = parse_audit_file(args.audit)
        stats = analyze_audit_records(records)

        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(format_text_report(stats))

        if args.fail_on_deny and stats["denied"] > 0:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
