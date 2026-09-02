# Contributing

Keep the project narrow: evidence contracts, deterministic validation, sanitized
examples, and tests for real continuity boundaries.

Before opening a pull request:

```bash
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
PYTHONPATH=src python -m continuity_gate validate examples/minimal-pass.json
PYTHONPATH=src python -m continuity_gate validate examples/honest-partial.json --report-only
PYTHONPATH=src python -m continuity_gate audit-tools examples/evidence/mcp-tools-list.json
uv run --isolated --with "mcp[cli]>=2,<3" python -c "import asyncio; from examples.read_only_mcp.server import mcp; assert len(asyncio.run(mcp.list_tools())) == 2"
```

Never commit real chat transcripts, account identifiers, tunnel identifiers,
credentials, home-directory paths, health data, or personal-memory content. New
features should include a failing regression test and a plain-language explanation
of the false claim they prevent.
