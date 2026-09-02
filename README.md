# GPT Native Continuity Gate

[![CI](https://github.com/27ive/gpt-native-continuity-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/27ive/gpt-native-continuity-gate/actions/workflows/ci.yml)

A small, dependency-free release gate for a common personal-AI failure: saying
“it works everywhere” when only a script, one desktop chat, or an account setting
was tested.

This repository does **not** build another assistant, memory store, message bus,
or ChatGPT-to-Codex bridge. It checks the claims around systems that already use
native ChatGPT/Codex surfaces, MCP tools, private context, voice, mobile clients,
scheduled work, and notifications.

## What it catches

- a shared assistant name being mistaken for shared history, memory, tools, or permissions;
- “mobile works” backed only by documentation or account sync, not a physical-device round trip;
- “voice works” backed by text tests;
- “read-only MCP” backed only by `readOnlyHint`, with no implementation test;
- a passing score that hides one failed critical journey;
- stale, missing, absolute-path, or secret-bearing evidence artifacts;
- a hand-edited `declared_ready: true` that disagrees with the computed gate.

## Quick start

Python 3.10+ is enough. No runtime dependencies are required.

```bash
PYTHONPATH=src python -m continuity_gate validate examples/minimal-pass.json
PYTHONPATH=src python -m continuity_gate validate examples/honest-partial.json --report-only
PYTHONPATH=src python -m continuity_gate audit-tools examples/evidence/mcp-tools-list.json
python -m unittest discover -s tests -v
```

Expected results:

```text
READY — score 100.0
BLOCKED — score 30.0
```

Install the command if you prefer:

```bash
python -m pip install .
continuity-gate validate path/to/your-manifest.json
```

Exit codes are designed for CI:

- `0`: valid and ready;
- `1`: valid but honestly blocked;
- `2`: invalid or internally contradictory.

Use `--report-only` when publishing a known-blocked candidate report without
failing the surrounding documentation job.

## The manifest in one minute

The gate has four pieces:

1. `system.identity` states which capabilities are and are not actually shared.
2. `journeys` records weighted real-user paths and their evidence.
3. `claims` can be `supported` only when every required journey passed.
4. `release` combines a score threshold with hard critical-journey and claim gates.

A critical pass needs live evidence. A journey can additionally require
`live_device`, `live_desktop`, or `live_service`, so a desktop test cannot satisfy
a phone or voice claim. Partial evidence receives half score for visibility but
never satisfies a claim.

Start from [the honest blocked example](examples/honest-partial.json), replace the
sanitized receipts with your own, and promote one journey at a time. The JSON
Schema is at [schemas/continuity-gate-v1.schema.json](schemas/continuity-gate-v1.schema.json).

## Read-only MCP check

Capture the server's `tools/list` result and run:

```bash
continuity-gate audit-tools tools-list.json
```

The audit rejects missing `readOnlyHint`, destructive hints, open-world tools on a
closed private surface, duplicate names, and obvious write-like tool names. It is
only a consistency check. The MCP specification treats annotations as untrusted
hints, so real enforcement still belongs in credentials, mounts, code, and
before/after behavior tests. See the deliberately small
[read-only MCP example](examples/read_only_mcp/README.md).

## Why this is narrow

There are already capable open-source bridges that let ChatGPT start or supervise
local coding agents. Rebuilding that control plane would add another privileged
runtime. This project instead makes the less glamorous boundary testable:

> Native continuity is the set of user journeys you can reproduce, not the set of
> surfaces that share a logo or account.

The method and evidence ladder are in [docs/method.md](docs/method.md). Product
boundaries are in [docs/native-boundaries.md](docs/native-boundaries.md), the
security model is in [docs/threat-model.md](docs/threat-model.md), and current
primary technical sources are in [docs/references.md](docs/references.md).

## Status

`0.1.0` is an intentionally small public alpha. The validator is deterministic,
standard-library only, covered by unit tests, and safe to run offline. It does not
connect to an account, inspect a private archive, or certify that an MCP server is
secure.

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and
[SECURITY.md](SECURITY.md).

## License

MIT
