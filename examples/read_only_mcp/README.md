# Read-only MCP example

This is deliberately small: two tools over a fixed in-memory mapping, using the
current stable v2 line of the official MCP Python SDK.

```bash
uv run --with "mcp[cli]>=2,<3" mcp run server.py
```

Both tools declare `read_only_hint=True` and `open_world_hint=False`. Those are
useful client hints, not a security guarantee. A real deployment should also:

1. mount the source read-only or expose a backend account with read-only rights;
2. keep write functions out of the server process;
3. hash fixtures before and after every tool in a deterministic test;
4. test denied paths and missing records;
5. capture `tools/list` and run `continuity-gate audit-tools` on it.
