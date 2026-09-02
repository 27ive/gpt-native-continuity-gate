from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "examples/read_only_mcp/server.py"


class ReadOnlyExampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = ast.parse(SERVER.read_text(encoding="utf-8"))

    def test_exact_tool_surface(self) -> None:
        exported = []
        for node in self.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                call = decorator if isinstance(decorator, ast.Call) else None
                target = call.func if call else decorator
                if isinstance(target, ast.Attribute) and target.attr == "tool":
                    exported.append(node.name)
        self.assertEqual(exported, ["search_records", "read_record"])

    def test_no_obvious_write_or_process_primitive(self) -> None:
        forbidden = {
            "open",
            "remove",
            "rename",
            "replace",
            "rmdir",
            "mkdir",
            "unlink",
            "write",
            "write_bytes",
            "write_text",
            "popen",
            "run",
            "system",
        }
        calls = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id.lower())
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr.lower())
        # Ignore the guarded MCP server's own run() entrypoint. It starts the
        # protocol loop; it is not an exported tool implementation.
        tool_function_calls = []
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue
                    if isinstance(child.func, ast.Name):
                        tool_function_calls.append(child.func.id.lower())
                    elif isinstance(child.func, ast.Attribute):
                        tool_function_calls.append(child.func.attr.lower())
        self.assertFalse(set(tool_function_calls) & forbidden, calls)

    def test_fixture_is_literal_and_not_loaded_from_an_external_source(self) -> None:
        records_assignments = [
            node
            for node in self.tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "RECORDS"
                for target in node.targets
            )
        ]
        self.assertEqual(len(records_assignments), 1)
        self.assertIsInstance(records_assignments[0].value, ast.Dict)


if __name__ == "__main__":
    unittest.main()
