# Security policy

Please do not open a public issue for a vulnerability that could expose private
data or credentials. Use GitHub's private vulnerability reporting for this
repository when available.

The validator runs offline and makes no network calls. It reads only the manifest
and the relative evidence paths named by that manifest. Do not use it as a sandbox
for untrusted Python code; it validates JSON and does not execute evidence files.

The read-only MCP example is educational, not a security boundary. Tool annotations
are hints. Enforce read-only behavior with source permissions, code, isolation, and
tests.
