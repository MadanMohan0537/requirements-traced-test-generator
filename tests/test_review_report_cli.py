import json
import tempfile
import unittest
from pathlib import Path

from casefoundry.cli import generate
from casefoundry.generator import generate_suite
from casefoundry.parser import parse_requirements
from casefoundry.report import build_report
from casefoundry.review import ReviewQueue


PRD = "\n".join(["[R1] Upload policy", "[R2] Ground answers", "[R3] Refuse unsupported", "[R4] Admin deletes", "[R5] Member cannot delete"])


class ReviewReportCliTests(unittest.TestCase):
    def test_coverage_has_no_thin_known_clause(self):
        requirements = parse_requirements(PRD)
        report = build_report(requirements, generate_suite(requirements))
        self.assertTrue(all(not row["thin"] for row in report["coverage"].values()))

    def test_review_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = ReviewQueue(Path(tmp) / "review.db")
            case = generate_suite(parse_requirements("[R1] Upload policy"))[0]
            self.assertEqual(queue.add([case]), 1)
            self.assertEqual(queue.add([case]), 0)
            queue.decide(case.id, "accepted", "valid boundary")
            self.assertEqual(queue.counts()["accepted"], 1)

    def test_invalid_review_state_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ReviewQueue(Path(tmp) / "review.db").decide("missing", "maybe")

    def test_end_to_end_cli_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prd = root / "prd.md"
            prd.write_text(PRD)
            report = generate(str(prd), str(root / "cases.json"), str(root / "coverage.json"), str(root / "reviews.db"))
            self.assertEqual(report["mutation"]["score"], 1.0)
            self.assertEqual(report["oracles"]["held_for_adjudication"], 0)
            self.assertEqual(len(json.loads((root / "cases.json").read_text())), report["cases"])
            self.assertEqual(report["queued_for_review"], report["cases"])
            self.assertEqual(report["queued_for_oracle_review"], report["cases"])


if __name__ == "__main__":
    unittest.main()

