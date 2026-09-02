"""Validate a continuity-gate evidence manifest using only the standard library."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .tool_audit import is_write_like_name

SCHEMA = "gpt-native-continuity-gate/v1"
JOURNEY_STATUSES = {"passed", "partial", "failed", "pending", "not_applicable"}
CLAIM_STATUSES = {"supported", "partial", "unsupported", "not_claimed"}
EVIDENCE_KINDS = {
    "live_device",
    "live_desktop",
    "live_service",
    "synthetic",
    "document",
    "self_report",
}
LIVE_KINDS = {"live_device", "live_desktop", "live_service"}
STATUS_CREDIT = {"passed": 1.0, "partial": 0.5}
PRIVATE_PATTERNS = {
    "macOS user path": re.compile(r"/Users/[^/\s]+/"),
    "Windows user path": re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
    "secret-like token": re.compile(
        r"\b(?:sk|gh[opusr]|xox[baprs]|AKIA|tunnel)_[A-Za-z0-9_-]{8,}\b"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


@dataclass(slots=True)
class GateReport:
    valid: bool
    ready: bool
    score: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    journeys: dict[str, str] = field(default_factory=dict)
    claims: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "gpt-native-continuity-gate/report-v1",
            "valid": self.valid,
            "ready": self.ready,
            "score": self.score,
            "errors": self.errors,
            "warnings": self.warnings,
            "journeys": self.journeys,
            "claims": self.claims,
        }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _scan_public_safety(manifest: Any) -> list[str]:
    serialized = json.dumps(manifest, ensure_ascii=False)
    return [
        label
        for label, pattern in PRIVATE_PATTERNS.items()
        if pattern.search(serialized)
    ]


def _require_object(value: Any, where: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{where} must be an object")
        return {}
    return value


def _validate_identity(
    system: dict[str, Any], claims: dict[str, str], errors: list[str]
) -> None:
    identity = _require_object(system.get("identity"), "system.identity", errors)
    shared_name = identity.get("shared_name_across_surfaces")
    if not isinstance(shared_name, bool):
        errors.append("system.identity.shared_name_across_surfaces must be boolean")
    if (
        shared_name is True
        and identity.get("capability_sharing_is_not_implied") is not True
    ):
        errors.append("a shared name requires capability_sharing_is_not_implied=true")

    for capability in ("history", "memory", "tools", "permissions"):
        key = f"shared_{capability}"
        value = identity.get(key)
        if not isinstance(value, bool):
            errors.append(f"system.identity.{key} must be boolean")
        elif value is True and claims.get(key) != "supported":
            errors.append(f"{key}=true requires a supported claim with the same id")


def _validate_tool_surfaces(
    surfaces: Any, root: Path, errors: list[str], warnings: list[str]
) -> None:
    if not isinstance(surfaces, list):
        errors.append("tool_surfaces must be an array")
        return
    seen: set[str] = set()
    for index, raw in enumerate(surfaces):
        surface = _require_object(raw, f"tool_surfaces[{index}]", errors)
        name = surface.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"tool_surfaces[{index}].name must be a non-empty string")
            continue
        if name in seen:
            errors.append(f"duplicate tool surface: {name}")
        seen.add(name)
        mode = surface.get("mode")
        if mode not in {"read_only", "write_capable"}:
            errors.append(f"{name}: mode must be read_only or write_capable")
            continue
        tool_names = surface.get("tool_names")
        if (
            not isinstance(tool_names, list)
            or not tool_names
            or not all(isinstance(item, str) and item for item in tool_names)
        ):
            errors.append(f"{name}: tool_names must be a non-empty string array")
            continue
        if len(set(tool_names)) != len(tool_names):
            errors.append(f"{name}: tool_names contain duplicates")

        if mode == "read_only":
            if surface.get("write_tool_count") != 0:
                errors.append(
                    f"{name}: read_only surface must declare write_tool_count=0"
                )
            if surface.get("annotations_verified") is not True:
                errors.append(f"{name}: read-only annotations were not verified")
            if surface.get("implementation_verified") is not True:
                errors.append(f"{name}: implementation behavior was not verified")
            for tool_name in tool_names:
                if is_write_like_name(tool_name):
                    errors.append(
                        f"{name}: write-like tool appears on a read-only surface: {tool_name}"
                    )
            artifacts = surface.get("enforcement_artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                errors.append(f"{name}: enforcement_artifacts must not be empty")
            else:
                for artifact in artifacts:
                    if not _safe_relative_path(artifact):
                        errors.append(
                            f"{name}: unsafe enforcement artifact path: {artifact!r}"
                        )
                    elif not (root / artifact).is_file():
                        errors.append(
                            f"{name}: enforcement artifact does not exist: {artifact}"
                        )
        elif surface.get("approval_required") is not True:
            warnings.append(
                f"{name}: write-capable surface does not declare approval_required=true"
            )


def _validate_journeys(
    raw_journeys: Any,
    root: Path,
    now: datetime,
    errors: list[str],
    warnings: list[str],
) -> tuple[dict[str, dict[str, Any]], float]:
    if not isinstance(raw_journeys, list) or not raw_journeys:
        errors.append("journeys must be a non-empty array")
        return {}, 0.0

    journeys: dict[str, dict[str, Any]] = {}
    earned = 0.0
    total = 0.0
    for index, raw in enumerate(raw_journeys):
        journey = _require_object(raw, f"journeys[{index}]", errors)
        identifier = journey.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"journeys[{index}].id must be a non-empty string")
            continue
        if identifier in journeys:
            errors.append(f"duplicate journey id: {identifier}")
            continue
        journeys[identifier] = journey

        status = journey.get("status")
        if status not in JOURNEY_STATUSES:
            errors.append(f"{identifier}: invalid journey status {status!r}")
            continue
        critical = journey.get("critical")
        if not isinstance(critical, bool):
            errors.append(f"{identifier}: critical must be boolean")
        elif status == "not_applicable" and critical:
            errors.append(f"{identifier}: a critical journey cannot be not_applicable")
        weight = journey.get("weight")
        if not _is_number(weight) or not 0 < float(weight) <= 100:
            errors.append(f"{identifier}: weight must be in (0, 100]")
            continue
        if status != "not_applicable":
            total += float(weight)
            earned += float(weight) * STATUS_CREDIT.get(status, 0.0)

        evidence = journey.get("evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{identifier}: evidence must be an array")
            evidence = []
        if status in {"passed", "partial"} and not evidence:
            errors.append(f"{identifier}: {status} journey has no evidence")

        kinds: set[str] = set()
        for evidence_index, raw_item in enumerate(evidence):
            item = _require_object(
                raw_item, f"{identifier}.evidence[{evidence_index}]", errors
            )
            kind = item.get("kind")
            if kind not in EVIDENCE_KINDS:
                errors.append(f"{identifier}: invalid evidence kind {kind!r}")
            else:
                kinds.add(kind)
            observed_at = _parse_time(item.get("observed_at"))
            if observed_at is None:
                errors.append(f"{identifier}: evidence observed_at must be ISO-8601")
            elif observed_at > now:
                errors.append(f"{identifier}: evidence timestamp is in the future")
            else:
                fresh_for_days = journey.get("fresh_for_days")
                if fresh_for_days is not None:
                    if not _is_number(fresh_for_days) or float(fresh_for_days) <= 0:
                        errors.append(f"{identifier}: fresh_for_days must be positive")
                    elif (now - observed_at).total_seconds() > float(
                        fresh_for_days
                    ) * 86400:
                        errors.append(f"{identifier}: passed evidence is stale")
            artifact = item.get("artifact")
            if not _safe_relative_path(artifact):
                errors.append(
                    f"{identifier}: unsafe evidence artifact path: {artifact!r}"
                )
            elif not (root / artifact).is_file():
                errors.append(
                    f"{identifier}: evidence artifact does not exist: {artifact}"
                )
            assertions = item.get("assertions")
            if (
                not isinstance(assertions, list)
                or not assertions
                or not all(
                    isinstance(assertion, str) and assertion for assertion in assertions
                )
            ):
                errors.append(
                    f"{identifier}: evidence assertions must be a non-empty string array"
                )

        required_kind = journey.get("required_evidence_kind")
        if required_kind is not None and required_kind not in EVIDENCE_KINDS:
            errors.append(
                f"{identifier}: unknown required_evidence_kind {required_kind!r}"
            )
        elif status == "passed" and required_kind and required_kind not in kinds:
            errors.append(
                f"{identifier}: passed journey lacks required {required_kind} evidence"
            )
        if (
            status == "passed"
            and journey.get("critical") is True
            and not (kinds & LIVE_KINDS)
        ):
            errors.append(f"{identifier}: critical pass requires live evidence")
        if status == "partial":
            warnings.append(
                f"{identifier}: partial evidence receives half credit but cannot satisfy a claim"
            )

    score = 0.0 if total == 0 else round(100.0 * earned / total, 1)
    return journeys, score


def _validate_claims(
    raw_claims: Any,
    journeys: dict[str, dict[str, Any]],
    errors: list[str],
    warnings: list[str],
) -> dict[str, str]:
    if not isinstance(raw_claims, list):
        errors.append("claims must be an array")
        return {}
    claims: dict[str, str] = {}
    for index, raw in enumerate(raw_claims):
        claim = _require_object(raw, f"claims[{index}]", errors)
        identifier = claim.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"claims[{index}].id must be a non-empty string")
            continue
        if identifier in claims:
            errors.append(f"duplicate claim id: {identifier}")
            continue
        status = claim.get("status")
        if status not in CLAIM_STATUSES:
            errors.append(f"{identifier}: invalid claim status {status!r}")
            continue
        claims[identifier] = status
        required = claim.get("requires")
        if (
            not isinstance(required, list)
            or not required
            or not all(isinstance(item, str) and item for item in required)
        ):
            errors.append(
                f"{identifier}: requires must be a non-empty journey id array"
            )
            continue
        if len(set(required)) != len(required):
            errors.append(f"{identifier}: requires contains duplicate journey ids")
        missing = [item for item in required if item not in journeys]
        if missing:
            errors.append(
                f"{identifier}: unknown required journeys: {', '.join(missing)}"
            )
            continue
        required_statuses = [journeys[item].get("status") for item in required]
        all_passed = all(item == "passed" for item in required_statuses)
        any_evidence = any(item in {"passed", "partial"} for item in required_statuses)
        if status == "supported" and not all_passed:
            errors.append(
                f"{identifier}: supported claim has an unpassed required journey"
            )
        elif status == "partial" and not any_evidence:
            errors.append(
                f"{identifier}: partial claim has no passed or partial journey"
            )
        elif status in {"unsupported", "not_claimed"} and all_passed:
            warnings.append(
                f"{identifier}: all evidence passed but the claim is {status}"
            )
    return claims


def _critical_failures(journeys: Iterable[dict[str, Any]]) -> list[str]:
    return [
        str(journey.get("id"))
        for journey in journeys
        if journey.get("critical") is True and journey.get("status") != "passed"
    ]


def validate_manifest(
    manifest: Any,
    *,
    root: Path,
    as_of: datetime | None = None,
) -> GateReport:
    errors: list[str] = []
    warnings: list[str] = []
    now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)

    if not isinstance(manifest, dict):
        return GateReport(False, False, 0.0, ["manifest must be a JSON object"])
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA!r}")
    if manifest.get("public_safe") is not True:
        errors.append("public_safe must be true")
    for match in _scan_public_safety(manifest):
        errors.append(f"manifest contains a prohibited {match}")

    system = _require_object(manifest.get("system"), "system", errors)
    if not isinstance(system.get("name"), str) or not system.get("name"):
        errors.append("system.name must be a non-empty string")

    journeys, score = _validate_journeys(
        manifest.get("journeys"), root, now, errors, warnings
    )
    claims = _validate_claims(manifest.get("claims"), journeys, errors, warnings)
    _validate_identity(system, claims, errors)
    _validate_tool_surfaces(manifest.get("tool_surfaces"), root, errors, warnings)

    release = _require_object(manifest.get("release"), "release", errors)
    minimum_score = release.get("minimum_score")
    if not _is_number(minimum_score) or not 0 <= float(minimum_score) <= 100:
        errors.append("release.minimum_score must be in [0, 100]")
        minimum_score = 100
    required_claims = release.get("required_claims")
    if (
        not isinstance(required_claims, list)
        or not required_claims
        or not all(isinstance(item, str) and item for item in required_claims)
    ):
        errors.append("release.required_claims must be a non-empty string array")
        required_claims = []
    unknown_claims = [item for item in required_claims if item not in claims]
    if unknown_claims:
        errors.append(f"release references unknown claims: {', '.join(unknown_claims)}")
    unsupported_claims = [
        item for item in required_claims if claims.get(item) != "supported"
    ]
    critical = _critical_failures(journeys.values())

    computed_ready = (
        not errors
        and score >= float(minimum_score)
        and not unsupported_claims
        and not critical
    )
    declared_ready = release.get("declared_ready")
    if not isinstance(declared_ready, bool):
        errors.append("release.declared_ready must be boolean")
    elif declared_ready != computed_ready:
        errors.append(
            f"release.declared_ready={declared_ready} disagrees with computed ready={computed_ready}"
        )

    if unsupported_claims:
        warnings.append(
            "required claims not supported: " + ", ".join(unsupported_claims)
        )
    if critical:
        warnings.append("critical journeys not passed: " + ", ".join(critical))
    if score < float(minimum_score):
        warnings.append(
            f"score {score:.1f} is below release threshold {float(minimum_score):.1f}"
        )

    valid = not errors
    return GateReport(
        valid=valid,
        ready=computed_ready and valid,
        score=score,
        errors=errors,
        warnings=warnings,
        journeys={key: str(value.get("status")) for key, value in journeys.items()},
        claims=claims,
    )
