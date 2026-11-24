import copy
import json
from pathlib import Path
import tempfile
import unittest

from casefoundry.cli import main
from casefoundry.generator import generate_suite
from casefoundry.incidents import incident_adequacy, validate_incident_bundle
from casefoundry.parser import parse_requirements

ROOT = Path(__file__).resolve().parents[1]
CASES = generate_suite(parse_requirements((ROOT/"data/sample-prd.md").read_text()))
BUNDLE = json.loads((ROOT/"data/sample-incidents.json").read_text())


class IncidentMutationTests(unittest.TestCase):
    def test_equal_budget_grid_beats_seeded_random_fixture(self):
        result = incident_adequacy(CASES, BUNDLE)
        self.assertEqual(result["grid"]["cases"], 4)
        self.assertEqual(result["random"]["cases"], 4)
        self.assertEqual(result["grid"]["killed"], 3)
        self.assertEqual(result["random"]["killed"], 2)
        self.assertEqual(result["kill_gain"], 1)
        self.assertTrue(result["accepted"])
        self.assertEqual(result, incident_adequacy(CASES, BUNDLE))

    def test_privacy_review_must_fail_closed(self):
        for field, value in (("reviewed", False), ("contains_real_user_data", True)):
            bundle = copy.deepcopy(BUNDLE)
            bundle["privacy_review"][field] = value
            with self.assertRaisesRegex(ValueError, "privacy"):
                validate_incident_bundle(bundle, CASES)

    def test_unknown_trigger_fields_and_requirements_are_rejected(self):
        bundle = copy.deepcopy(BUNDLE)
        bundle["incidents"][0]["trigger"]["raw_prompt"] = "private text"
        with self.assertRaisesRegex(ValueError, "trigger"):
            validate_incident_bundle(bundle, CASES)
        bundle = copy.deepcopy(BUNDLE)
        bundle["incidents"][0]["requirement_id"] = "R999"
        with self.assertRaisesRegex(ValueError, "requirement"):
            validate_incident_bundle(bundle, CASES)

    def test_duplicate_and_non_defect_incidents_are_rejected(self):
        bundle = copy.deepcopy(BUNDLE)
        bundle["incidents"].append(copy.deepcopy(bundle["incidents"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_incident_bundle(bundle, CASES)
        bundle = copy.deepcopy(BUNDLE)
        bundle["incidents"][0]["observed"] = bundle["incidents"][0]["expected"]
        with self.assertRaisesRegex(ValueError, "differ"):
            validate_incident_bundle(bundle, CASES)

    def test_predeclared_gain_controls_acceptance(self):
        bundle = copy.deepcopy(BUNDLE)
        bundle["experiment"]["minimum_kill_gain"] = 2
        self.assertFalse(incident_adequacy(CASES, bundle)["accepted"])

    def test_cli_writes_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"incident-audit.json"
            code = main(["incident-audit", str(ROOT/"data/sample-prd.md"),
                         "--incidents", str(ROOT/"data/sample-incidents.json"),
                         "--output", str(out)])
            self.assertEqual(code, 0)
            report = json.loads(out.read_text())
            self.assertTrue(report["audit_sha256"])
            self.assertEqual(report["source_counts"], {"synthetic-incident-analogue": 3})


if __name__ == "__main__":
    unittest.main()
