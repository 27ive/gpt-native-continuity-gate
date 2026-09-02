# Threat model

The gate is designed for public, sanitized evidence manifests. It assumes the
underlying personal-AI system may touch private context and that its client may
combine several tools in one session.

## Protected assets

- private archives, memory, health data, messages, and local files;
- API keys, tunnel identifiers, workspace identifiers, and account metadata;
- the difference between current state and historical context;
- the user's ability to understand whether a result was delivered or merely queued.

## Main failure modes

1. **Overclaiming:** a setting, synthetic test, or self-report is presented as a
   completed user journey.
2. **Capability confusion:** a shared identity is treated as shared history,
   memory, tools, or permissions.
3. **Read-only theater:** MCP annotations say read-only while the implementation
   can still write or exfiltrate.
4. **Stale truth:** old archive content is used as if it described current state.
5. **Evidence leakage:** public manifests contain absolute paths, credentials,
   raw private records, or stable account identifiers.
6. **Score laundering:** many easy passes hide one failed critical boundary.

## Controls in this repository

- evidence-kind requirements and critical hard gates;
- claim-to-journey dependency checks;
- readiness recomputation instead of trusting a hand-edited flag;
- relative, existing artifact paths only;
- basic absolute-path and secret-pattern rejection;
- consistency checks for closed, read-only MCP surfaces;
- no network calls and no account access in the validator.

## What this does not guarantee

Static metadata cannot prove that a tool is safe. MCP annotations are explicitly
hints, and a malicious or buggy server can lie. Use read-only source credentials,
filesystem mounts, network policy, sandboxing, code review, and deterministic
before/after tests as the enforcement layer.

The privacy scan is intentionally conservative and incomplete. Run a dedicated
secret scanner and manually inspect every public commit before publishing real
evidence.
