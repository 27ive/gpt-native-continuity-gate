# Method

The gate separates four things that personal-AI projects often collapse into one:

1. **Product support** — documentation says a capability exists.
2. **Configuration** — the account or host shows the capability as enabled.
3. **Execution** — a service or model reports that a call ran.
4. **User-path acceptance** — the intended person completed the journey on the
   intended client and observed the intended result.

Only the fourth proves the user-facing claim. The first three are still useful as
supporting evidence, but they cannot be silently promoted.

## Evidence kinds

| Kind | What it can prove | What it cannot prove |
| --- | --- | --- |
| `document` | supported product behavior or a stated boundary | that your account or device works |
| `synthetic` | deterministic logic, parsing, routing, failure handling | a real client or notification path |
| `self_report` | useful diagnostic state | independent completion |
| `live_service` | a real backend, outage, recovery, or scheduled run | a phone UI or human voice experience |
| `live_desktop` | a real desktop interaction | a physical phone result |
| `live_device` | a physical mobile or voice journey | unrelated clients or later uptime |

Critical journeys require at least one live artifact. A journey can impose a more
specific kind through `required_evidence_kind`.

## Scoring and hard gates

Passed journeys receive full weight, partial journeys receive half, and failed or
pending journeys receive zero. The score is useful for seeing progress, but it is
not sufficient for release. Readiness also requires:

- every critical journey to pass;
- every claim listed in `release.required_claims` to be supported;
- every supported claim's required journeys to pass;
- the declared readiness value to equal the computed value;
- no structural, privacy, path, timestamp, or tool-surface errors.

This prevents an easy desktop test from numerically hiding a failed mobile,
offline, voice, or notification path.

## Freshness

Set `fresh_for_days` only where drift matters. The validator then rejects evidence
that is older than that journey allows. In deterministic tests, pass `--as-of` so
the result does not depend on the machine clock.

## A practical test order

1. Prove the smallest desktop read path.
2. Prove denied and missing-data behavior.
3. Prove the physical mobile path without retyping the answer.
4. Prove two human voice turns if voice is claimed.
5. Stop the private host and require a clear, non-fabricated failure.
6. Restart the host and prove automatic recovery through the real client.
7. Generate one real notification, receive it on the phone, and open the expected
   destination.
8. Only then mark the corresponding claims supported.
