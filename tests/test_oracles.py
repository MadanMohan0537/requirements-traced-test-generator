import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from casefoundry.generator import generate_suite
from casefoundry.models import TestCase
from casefoundry.oracles import assess_oracles, oracle_summary
from casefoundry.parser import parse_requirements
from casefoundry.review import ReviewQueue


def candidate(case_id: str, expected: str, confidence: float = 0.95) -> TestCase:
    return TestCase(
        case_id, "R1", "member", "upload-document", "boundary",
        {"action": "upload", "size": 1_000_001, "extension": "txt"},
        expected, "Uploads must not exceed 1,000,000 bytes.", confidence,
        "requirement-derived boundary rule",
    )


class OracleTests(unittest.TestCase):
    def test_high_confidence_conflict_is_held(self):
        assessments = assess_oracles([
            candidate("deny-oracle", "deny"),
            candidate("allow-oracle", "allow"),
        ])
        self.assertEqual({item.status for item in assessments}, {"conflict"})
        self.assertTrue(all(item.conflict_with for item in assessments))

    def test_low_confidence_and_missing_evidence_are_uncertain(self):
        weak = replace(candidate("weak", "deny", 0.4), evidence="")
        assessment = assess_oracles([weak])[0]
        self.assertEqual(assessment.status, "uncertain")
        self.assertIn("missing requirement evidence", assessment.reasons)

    def test_known_generated_oracles_are_ready(self):
        cases = generate_suite(parse_requirements("[R1] Upload policy"))
        summary = oracle_summary(assess_oracles(cases))
        self.assertEqual(summary["counts"]["ready"], len(cases))
        self.assertEqual(summary["held_for_adjudication"], 0)

    def test_unknown_domain_cases_require_review(self):
        cases = generate_suite(parse_requirements("[R9] Novel domain rule"))
        summary = oracle_summary(assess_oracles(cases))
        self.assertEqual(summary["counts"]["uncertain"], len(cases))

    def test_invalid_confidence_and_threshold_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_oracles([candidate("bad", "deny", float("nan"))])
        with self.assertRaises(ValueError):
            assess_oracles([], minimum_confidence=1.1)

    def test_queue_persists_evidence_and_requires_adjudication_reason(self):
        cases = [candidate("deny-oracle", "deny"), candidate("allow-oracle", "allow")]
        assessments = assess_oracles(cases)
        with tempfile.TemporaryDirectory() as tmp:
            queue = ReviewQueue(Path(tmp) / "review.db")
            self.assertEqual(queue.add_oracles(cases, assessments), 2)
            self.assertEqual(queue.oracle_counts()["conflict"], 2)
            with self.assertRaises(ValueError):
                queue.adjudicate_oracle("deny-oracle", "deny", "")
            queue.adjudicate_oracle(
                "deny-oracle", "deny", "R1 explicitly defines the maximum"
            )
            self.assertEqual(queue.oracle_counts()["adjudicated"], 1)

    def test_ready_oracle_cannot_be_adjudicated(self):
        case = candidate("ready", "deny")
        with tempfile.TemporaryDirectory() as tmp:
            queue = ReviewQueue(Path(tmp) / "review.db")
            queue.add_oracles([case], assess_oracles([case]))
            with self.assertRaises(ValueError):
                queue.adjudicate_oracle("ready", "deny", "unnecessary")


if __name__ == "__main__":
    unittest.main()
