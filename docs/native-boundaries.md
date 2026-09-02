# Native boundaries

“One assistant” is a user-experience statement. It is not evidence that every
surface shares the same transcript, memory, tools, permissions, runtime, or
freshness.

Record each boundary explicitly:

| Boundary | Question to answer |
| --- | --- |
| Identity | Does the same name and voice apply on each intended surface? |
| History | Can this surface actually see the earlier conversation? |
| Memory | Which stored facts are available here, and with what scope? |
| Tools | Which tools can this surface call right now? |
| Permissions | Does the current account, workspace, and client authorize them? |
| Host | What stops working when the private machine sleeps or goes offline? |
| Delivery | Did the intended device receive the result or notification? |

Account synchronization is not local execution. A connected desktop service is
not a phone receipt. A conversation appearing on two clients is not proof that a
private plugin ran on both. A model saying “done” is not an external delivery
receipt.

The safest architecture usually keeps native product surfaces as the frontstage,
keeps private context read-only by default, and introduces a write-capable bridge
only for a concrete journey that cannot be completed natively. A write bridge is
an execution authority, not a memory feature; give it a separate threat model,
approval policy, and release gate.

## A native ChatGPT-to-Codex handoff

As of September 2026, OpenAI's Codex Projects documentation says ordinary
ChatGPT chats do not appear in the Codex sidebar, but **New chat** can open an
existing ChatGPT chat and add it to a Codex chat. This is the narrow native path
to carry a phone-synced conversation into local work without copy-paste. Treat
the resulting Codex chat as a new execution transcript; do not relabel it as one
shared history.

Codex Remote is a different path: it controls chats on a connected host and stops
when that host sleeps, loses its network, or closes Codex. It is useful as an
engineering control surface, not evidence that an ordinary mobile chat gained
local files or tools.

For current product behavior, consult the official documentation at the time you
run the test. Product support changes faster than this repository; the real
client path remains the acceptance authority. The exact sources used for this
version are listed in [references.md](references.md).
