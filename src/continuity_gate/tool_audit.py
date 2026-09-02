"""Audit a captured MCP ``tools/list`` response.

MCP annotations are hints, not enforcement. This module checks that a declared
read-only surface is internally consistent; it cannot prove the server code is
safe. Pair it with implementation tests or sandboxing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

WRITE_WORDS = {
    "add",
    "apply",
    "approve",
    "cancel",
    "continue",
    "create",
    "delete",
    "dispatch",
    "edit",
    "execute",
    "interrupt",
    "move",
    "post",
    "publish",
    "remove",
    "rename",
    "run",
    "send",
    "start",
    "submit",
    "update",
    "upload",
    "write",
}


@dataclass(slots=True)
class ToolAudit:
    valid: bool
    tool_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "tool_count": self.tool_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def is_write_like_name(name: str) -> bool:
    # MCP tool names are commonly snake_case, but custom servers also expose
    # kebab-case, dotted names, and camelCase. Normalize all four so a name
    # such as deleteRecord cannot bypass the consistency check.
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    words = {part.lower() for part in re.split(r"[^A-Za-z0-9]+", camel_split) if part}
    return bool(words & WRITE_WORDS)


def audit_tools(payload: Any, *, require_closed_world: bool = True) -> ToolAudit:
    errors: list[str] = []
    warnings: list[str] = []

    if isinstance(payload, dict):
        tools = payload.get("tools")
    else:
        tools = None
    if not isinstance(tools, list):
        return ToolAudit(False, 0, ["tools/list capture must contain a tools array"])

    names: set[str] = set()
    for index, tool in enumerate(tools):
        where = f"tools[{index}]"
        if not isinstance(tool, dict):
            errors.append(f"{where} must be an object")
            continue
        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{where}.name must be a non-empty string")
            continue
        if name in names:
            errors.append(f"duplicate tool name: {name}")
        names.add(name)
        if is_write_like_name(name):
            errors.append(f"read-only surface exposes a write-like tool name: {name}")

        annotations = tool.get("annotations")
        if not isinstance(annotations, dict):
            errors.append(f"{name}: annotations are missing")
            continue
        if annotations.get("readOnlyHint") is not True:
            errors.append(f"{name}: readOnlyHint must be true")
        if annotations.get("destructiveHint") is True:
            errors.append(f"{name}: destructiveHint cannot be true")
        if require_closed_world and annotations.get("openWorldHint") is not False:
            errors.append(
                f"{name}: openWorldHint must be false for this closed surface"
            )
        if "idempotentHint" in annotations:
            warnings.append(
                f"{name}: idempotentHint is not meaningful for a read-only tool"
            )

    if not tools:
        warnings.append("the captured surface exposes no tools")

    return ToolAudit(not errors, len(tools), errors, warnings)
