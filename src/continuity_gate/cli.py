"""Command-line interface for the continuity gate."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .tool_audit import audit_tools
from .validator import GateReport, validate_manifest


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _render_report(report: GateReport) -> str:
    outcome = "READY" if report.ready else "BLOCKED"
    lines = [f"{outcome} — score {report.score:.1f}"]
    if report.errors:
        lines.append("Errors:")
        lines.extend(f"  - {item}" for item in report.errors)
    if report.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {item}" for item in report.warnings)
    return "\n".join(lines)


def _parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("--as-of must be ISO-8601") from error


def _validate(args: argparse.Namespace) -> int:
    path = args.manifest.resolve()
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        print(f"invalid manifest: {error}", file=sys.stderr)
        return 2
    report = validate_manifest(
        payload, root=path.parent, as_of=_parse_as_of(args.as_of)
    )
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(_render_report(report))
    if args.report_only:
        return 0
    if not report.valid:
        return 2
    return 0 if report.ready else 1


def _audit_tools(args: argparse.Namespace) -> int:
    try:
        payload = _load_json(args.capture)
    except (OSError, json.JSONDecodeError) as error:
        print(f"invalid tools/list capture: {error}", file=sys.stderr)
        return 2
    report = audit_tools(payload, require_closed_world=not args.allow_open_world)
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0 if report.valid else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="continuity-gate",
        description="Refuse cross-surface personal AI claims without matching evidence.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="validate an evidence manifest")
    validate.add_argument("manifest", type=Path)
    validate.add_argument(
        "--as-of", help="ISO-8601 clock for deterministic freshness tests"
    )
    validate.add_argument(
        "--json", action="store_true", help="emit a machine-readable report"
    )
    validate.add_argument(
        "--report-only",
        action="store_true",
        help="always exit zero after reporting (useful for honest blocked examples)",
    )
    validate.set_defaults(func=_validate)

    tools = subcommands.add_parser(
        "audit-tools", help="audit a captured MCP tools/list response"
    )
    tools.add_argument("capture", type=Path)
    tools.add_argument(
        "--allow-open-world",
        action="store_true",
        help="do not require openWorldHint=false",
    )
    tools.set_defaults(func=_audit_tools)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
