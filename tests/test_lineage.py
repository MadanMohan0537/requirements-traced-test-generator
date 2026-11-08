import copy
import json
from pathlib import Path
import tempfile
import unittest

from casefoundry.cli import generate, regenerate
from casefoundry.generator import generate_suite
from casefoundry.lineage import build_manifest, regenerate_impacted, validate_manifest
from casefoundry.parser import parse_requirements


BASE = "[R1] Upload text only.\n[R2] Ground every answer.\n[R3] Refuse unsupported answers."


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.requirements = parse_requirements(BASE)
        self.manifest = build_manifest(self.requirements, generate_suite(self.requirements))

    def test_manifest_is_deterministic_and_validated(self):
        self.assertEqual(self.manifest, build_manifest(self.requirements, generate_suite(self.requirements)))
        self.assertIs(validate_manifest(self.manifest), self.manifest)

    def test_edit_regenerates_only_changed_requirement(self):
        changed = parse_requirements(BASE.replace("Refuse unsupported answers.", "Refuse unsupported or ungrounded answers."))
        cases, manifest, audit, added = regenerate_impacted(self.manifest, changed)
        self.assertEqual(audit["regenerated_requirement_ids"], ["R3"])
        self.assertEqual(audit["counts"], {"retained": 7, "added": 3, "retired": 3})
        retained_before = {row["id"] for row in self.manifest["cases"] if row["requirement_id"] in {"R1", "R2"}}
        self.assertEqual(retained_before, set(audit["retained_case_ids"]))
        self.assertTrue(all(case.requirement_id == "R3" for case in added))
        validate_manifest(manifest)

    def test_added_and_removed_requirements_are_audited(self):
        new = parse_requirements("[R1] Upload text only.\n[R6] New policy.")
        _, _, audit, _ = regenerate_impacted(self.manifest, new)
        statuses = {row["requirement_id"]: row["status"] for row in audit["requirement_changes"]}
        self.assertEqual(statuses, {"R1": "unchanged", "R6": "added", "R2": "removed", "R3": "removed"})
        self.assertEqual(audit["regenerated_requirement_ids"], ["R6"])

    def test_reordering_requirements_retains_every_case(self):
        reordered = list(reversed(self.requirements))
        _, _, audit, added = regenerate_impacted(self.manifest, reordered)
        self.assertEqual(audit["counts"], {"retained": 10, "added": 0, "retired": 0})
        self.assertEqual(added, [])

    def test_tampered_manifest_and_lineage_are_rejected(self):
        for mutate in (
            lambda item: item["cases"][0].__setitem__("expected", "forged"),
            lambda item: item["requirements"][0].__setitem__("fingerprint", "forged"),
        ):
            item = copy.deepcopy(self.manifest)
            mutate(item)
            with self.assertRaises(ValueError):
                validate_manifest(item)

    def test_cli_writes_delta_and_queues_only_added_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root/"old.md"; old.write_text(BASE)
            new = root/"new.md"; new.write_text(BASE.replace("Refuse unsupported answers.", "Refuse unsupported or ungrounded answers."))
            generate(str(old), str(root/"old.json"), str(root/"coverage.json"),
                     str(root/"reviews.db"), str(root/"old.manifest.json"))
            audit = regenerate(str(new), str(root/"old.manifest.json"), str(root/"new.json"),
                               str(root/"new.manifest.json"), str(root/"audit.json"),
                               str(root/"new-reviews.db"))
            self.assertEqual(audit["counts"], {"retained": 7, "added": 3, "retired": 3})
            self.assertEqual(audit["queued_added_cases"], 3)
            self.assertEqual(audit["queued_added_oracles"], 3)
            self.assertEqual(json.loads((root/"audit.json").read_text()), audit)


if __name__ == "__main__":
    unittest.main()
