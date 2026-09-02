"""Tiny closed-world, read-only MCP example.

Run with:
    uv run --with "mcp[cli]>=2,<3" mcp run server.py

The in-memory records are fixtures. Replace the backend only after adding a
deterministic before/after test that proves every exported tool leaves it
unchanged. Annotations are hints; they are not the enforcement layer.
"""

from mcp.server import MCPServer
from mcp.types import ToolAnnotations


mcp = MCPServer("Read-only context example")

RECORDS = {
    "preference-1": "The user prefers concise status updates.",
    "boundary-1": "A shared assistant name does not imply shared tools or history.",
}

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)


@mcp.tool(title="Search records", annotations=READ_ONLY)
def search_records(query: str) -> list[str]:
    """Search the fixed fixture records and return matching record IDs."""
    needle = query.casefold()
    return [key for key, value in RECORDS.items() if needle in value.casefold()]


@mcp.tool(title="Read one record", annotations=READ_ONLY)
def read_record(record_id: str) -> str:
    """Read one fixture record by the ID returned from search_records."""
    return RECORDS.get(record_id, "No matching record.")


if __name__ == "__main__":
    mcp.run()
