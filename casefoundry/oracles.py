"""Evidence-first oracle screening and contradiction detection."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .models import TestCase


ORACLE_STATUSES = ("ready", "uncertain", "conflict")


@dataclass(frozen=True)
class OracleAssessment:
    case_id: str
    status: str
    reasons: tuple[str, ...]
    conflict_with: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "reasons": list(self.reasons),
            "conflict_with": list(self.conflict_with),
        }


def _behavior_key(case: TestCase) -> str:
    """Match cases that exercise the same behavior, independent of dict order."""
    payload = json.dumps(case.input, sort_keys=True, separators=(",", ":"))
    return f"{case.intent}|{payload}"


def assess_oracles(
    cases: list[TestCase], minimum_confidence: float = 0.75
) -> list[OracleAssessment]:
    """Classify oracle candidates without treating confidence as calibration.

    Confidence is only a routing signal. Conflicting expected behavior always
    wins and requires adjudication, even when every candidate is high-confidence.
    """
    if not 0 <= minimum_confidence <= 1 or not math.isfinite(minimum_confidence):
        raise ValueError("minimum_confidence must be finite and between 0 and 1")
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case ids must be unique")

    groups: dict[str, list[TestCase]] = {}
    for case in cases:
        if not math.isfinite(case.oracle_confidence) or not 0 <= case.oracle_confidence <= 1:
            raise ValueError(f"invalid oracle confidence for {case.id}")
        groups.setdefault(_behavior_key(case), []).append(case)

    conflicts: dict[str, tuple[str, ...]] = {}
    for group in groups.values():
        executable = {case.expected for case in group if case.expected != "manual-review"}
        if len(executable) > 1:
            for case in group:
                conflicts[case.id] = tuple(sorted(other.id for other in group if other.id != case.id))

    results: list[OracleAssessment] = []
    for case in cases:
        reasons: list[str] = []
        if case.id in conflicts:
            results.append(OracleAssessment(
                case.id, "conflict", ("expected behavior conflicts for the same input",),
                conflicts[case.id],
            ))
            continue
        if not case.evidence.strip():
            reasons.append("missing requirement evidence")
        if not case.oracle_basis.strip():
            reasons.append("missing oracle basis")
        if case.expected == "manual-review":
            reasons.append("no executable expected behavior")
        if case.oracle_confidence < minimum_confidence:
            reasons.append(
                f"confidence {case.oracle_confidence:.2f} below routing threshold "
                f"{minimum_confidence:.2f}"
            )
        results.append(OracleAssessment(
            case.id, "uncertain" if reasons else "ready", tuple(reasons)
        ))
    return results


def oracle_summary(assessments: list[OracleAssessment]) -> dict:
    counts = {status: 0 for status in ORACLE_STATUSES}
    for assessment in assessments:
        counts[assessment.status] += 1
    total = len(assessments)
    return {
        "total": total,
        "counts": counts,
        "ready_rate": counts["ready"] / total if total else 0.0,
        "held_for_adjudication": counts["uncertain"] + counts["conflict"],
        "assessments": [item.to_dict() for item in assessments],
    }
