from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from continuity_gate.tool_audit import audit_tools  # noqa: E402
from continuity_gate.validator import validate_manifest  # noqa: E402


AS_OF = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def load_example(name: str = "minimal-pass.json") -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def validate(payload: dict):
    return validate_manifest(payload, root=ROOT / "examples", as_of=AS_OF)


class GateValidationTests(unittest.TestCase):
    def test_complete_live_manifest_is_ready(self) -> None:
        report = validate(load_example())
        self.assertTrue(report.valid, report.errors)
        self.assertTrue(report.ready)
        self.assertEqual(report.score, 100.0)

    def test_honest_partial_manifest_is_valid_but_blocked(self) -> None:
        report = validate(load_example("honest-partial.json"))
        self.assertTrue(report.valid, report.errors)
        self.assertFalse(report.ready)
        self.assertEqual(report.score, 30.0)
        self.assertIn("mobile_chat_continuity", " ".join(report.warnings))

    def test_partial_journey_requires_evidence(self) -> None:
        payload = load_example("honest-partial.json")
        payload["journeys"][1]["evidence"] = []
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("partial journey has no evidence", " ".join(report.errors))

    def test_declared_ready_cannot_override_computed_gate(self) -> None:
        payload = load_example("honest-partial.json")
        payload["release"]["declared_ready"] = True
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("disagrees with computed", " ".join(report.errors))

    def test_supported_claim_requires_every_journey_to_pass(self) -> None:
        payload = load_example("honest-partial.json")
        payload["claims"][1]["status"] = "supported"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("unpassed required journey", " ".join(report.errors))

    def test_critical_pass_requires_live_evidence(self) -> None:
        payload = load_example()
        item = payload["journeys"][0]
        item.pop("required_evidence_kind")
        item["evidence"][0]["kind"] = "synthetic"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("critical pass requires live evidence", " ".join(report.errors))

    def test_surface_specific_evidence_kind_is_enforced(self) -> None:
        payload = load_example()
        payload["journeys"][1]["evidence"][0]["kind"] = "live_desktop"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("lacks required live_device", " ".join(report.errors))

    def test_shared_name_requires_explicit_capability_boundary(self) -> None:
        payload = load_example()
        payload["system"]["identity"]["capability_sharing_is_not_implied"] = False
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("capability_sharing_is_not_implied", " ".join(report.errors))

    def test_claimed_shared_history_needs_evidence_claim(self) -> None:
        payload = load_example()
        payload["system"]["identity"]["shared_history"] = True
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("shared_history=true", " ".join(report.errors))

    def test_private_absolute_path_is_rejected(self) -> None:
        payload = load_example()
        payload["system"]["name"] = "/" + "Users/example/private-project"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("macOS user path", " ".join(report.errors))

    def test_secret_like_token_is_rejected(self) -> None:
        payload = load_example()
        payload["system"]["name"] = "sk" + "_exampletoken123456"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("secret-like token", " ".join(report.errors))

    def test_parent_traversal_artifact_is_rejected(self) -> None:
        payload = load_example()
        payload["journeys"][0]["evidence"][0]["artifact"] = "../private.json"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("unsafe evidence artifact", " ".join(report.errors))

    def test_missing_artifact_is_rejected(self) -> None:
        payload = load_example()
        payload["journeys"][0]["evidence"][0]["artifact"] = "evidence/missing.json"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("does not exist", " ".join(report.errors))

    def test_stale_evidence_is_rejected_when_freshness_is_declared(self) -> None:
        payload = load_example()
        payload["journeys"][0]["fresh_for_days"] = 0.01
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("evidence is stale", " ".join(report.errors))

    def test_future_evidence_is_rejected(self) -> None:
        payload = load_example()
        payload["journeys"][0]["evidence"][0]["observed_at"] = "2027-01-01T00:00:00Z"
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("timestamp is in the future", " ".join(report.errors))

    def test_duplicate_journey_id_is_rejected(self) -> None:
        payload = load_example()
        payload["journeys"].append(copy.deepcopy(payload["journeys"][0]))
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("duplicate journey id", " ".join(report.errors))

    def test_read_only_surface_requires_zero_write_tools(self) -> None:
        payload = load_example()
        payload["tool_surfaces"][0]["write_tool_count"] = 1
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("write_tool_count=0", " ".join(report.errors))

    def test_read_only_surface_rejects_write_like_name(self) -> None:
        payload = load_example()
        payload["tool_surfaces"][0]["tool_names"].append("send_result")
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("write-like tool", " ".join(report.errors))

    def test_write_capable_surface_warns_without_approval(self) -> None:
        payload = load_example()
        payload["tool_surfaces"] = [
            {"name": "executor", "mode": "write_capable", "tool_names": ["run_task"]}
        ]
        report = validate(payload)
        self.assertTrue(report.valid, report.errors)
        self.assertIn("approval_required=true", " ".join(report.warnings))

    def test_release_requires_at_least_one_claim(self) -> None:
        payload = load_example()
        payload["release"]["required_claims"] = []
        payload["release"]["declared_ready"] = False
        report = validate(payload)
        self.assertFalse(report.valid)
        self.assertIn("non-empty string array", " ".join(report.errors))

    def test_invalid_json_shape_does_not_crash(self) -> None:
        report = validate_manifest([], root=ROOT, as_of=AS_OF)
        self.assertFalse(report.valid)
        self.assertEqual(report.score, 0.0)

    def test_manifest_can_be_validated_from_a_copied_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target / "evidence").mkdir()
            source = ROOT / "examples" / "evidence"
            for item in source.iterdir():
                (target / "evidence" / item.name).write_bytes(item.read_bytes())
            report = validate_manifest(load_example(), root=target, as_of=AS_OF)
            self.assertTrue(report.ready, report.errors)


class ToolAuditTests(unittest.TestCase):
    def test_read_only_capture_passes(self) -> None:
        payload = json.loads(
            (ROOT / "examples/evidence/mcp-tools-list.json").read_text(encoding="utf-8")
        )
        report = audit_tools(payload)
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(report.tool_count, 4)

    def test_bad_capture_reports_annotations_and_write_name(self) -> None:
        payload = json.loads(
            (ROOT / "tests/fixtures/tools-bad.json").read_text(encoding="utf-8")
        )
        report = audit_tools(payload)
        self.assertFalse(report.valid)
        joined = " ".join(report.errors)
        self.assertIn("readOnlyHint", joined)
        self.assertIn("delete_record", joined)
        self.assertIn("destructiveHint", joined)

    def test_camel_case_write_name_is_rejected(self) -> None:
        payload = {
            "tools": [
                {
                    "name": "deleteRecord",
                    "annotations": {"readOnlyHint": True, "openWorldHint": False},
                }
            ]
        }
        report = audit_tools(payload)
        self.assertFalse(report.valid)
        self.assertIn("deleteRecord", " ".join(report.errors))

    def test_missing_tools_array_is_rejected(self) -> None:
        report = audit_tools({})
        self.assertFalse(report.valid)
        self.assertIn("tools array", report.errors[0])


if __name__ == "__main__":
    unittest.main()
