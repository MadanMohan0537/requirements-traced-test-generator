"""Privacy-gated, data-only incident mutations and equal-budget adequacy checks."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import random

from .models import TestCase
from .mutations import toy_app


ALLOWED_TRIGGER_FIELDS = {"action", "extension", "size", "role", "has_source"}
ALLOWED_RESULTS = {"allow", "deny", "grounded", "refuse", "manual-review"}
SOURCE_TYPES = {"redacted-historical-defect", "synthetic-incident-analogue"}


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _text(value: object, label: str, limit: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} must be nonempty text up to {limit} characters")
    return value.strip()


def validate_incident_bundle(bundle: dict, cases: list[TestCase]) -> dict:
    required = {"schema_version", "provenance", "privacy_review", "experiment", "incidents"}
    if not isinstance(bundle, dict) or set(bundle) != required:
        raise ValueError("incident bundle has unsupported or missing fields")
    if bundle["schema_version"] != 1:
        raise ValueError("incident bundle schema_version must be 1")
    _text(bundle["provenance"], "provenance", 1000)
    review = bundle["privacy_review"]
    review_keys = {"reviewed", "contains_real_user_data", "reviewer", "reviewed_at", "notes"}
    if not isinstance(review, dict) or set(review) != review_keys:
        raise ValueError("privacy_review has unsupported or missing fields")
    if review["reviewed"] is not True or review["contains_real_user_data"] is not False:
        raise ValueError("privacy review must confirm review and absence of real user data")
    _text(review["reviewer"], "privacy reviewer", 200)
    _text(review["notes"], "privacy notes", 1000)
    try:
        reviewed_at = datetime.fromisoformat(
            _text(review["reviewed_at"], "reviewed_at").replace("Z", "+00:00"))
        if reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must include a timezone")
    except ValueError as exc:
        raise ValueError("reviewed_at must be ISO-8601") from exc
    experiment = bundle["experiment"]
    if not isinstance(experiment, dict) or set(experiment) != {"budget", "random_seed", "minimum_kill_gain"}:
        raise ValueError("experiment requires budget, random_seed and minimum_kill_gain")
    for key in ("budget", "random_seed", "minimum_kill_gain"):
        value = experiment[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be an integer")
    if experiment["budget"] < 1 or experiment["minimum_kill_gain"] < 0:
        raise ValueError("budget must be positive and minimum_kill_gain nonnegative")
    if experiment["budget"] > len(cases):
        raise ValueError("experiment budget exceeds available cases")

    requirement_ids = {case.requirement_id for case in cases}
    incidents, seen = bundle["incidents"], set()
    incident_keys = {"id", "requirement_id", "summary", "source_type", "trigger",
                     "expected", "observed", "redaction_notes"}
    if not isinstance(incidents, list) or not incidents:
        raise ValueError("incidents must be a nonempty list")
    for incident in incidents:
        if not isinstance(incident, dict) or set(incident) != incident_keys:
            raise ValueError("incident has unsupported or missing fields")
        incident_id = _text(incident["id"], "incident id", 100)
        if incident_id in seen:
            raise ValueError("incident IDs must be unique")
        seen.add(incident_id)
        if incident["requirement_id"] not in requirement_ids:
            raise ValueError("incident requirement_id must exist in the PRD suite")
        _text(incident["summary"], "incident summary")
        _text(incident["redaction_notes"], "redaction notes", 1000)
        if incident["source_type"] not in SOURCE_TYPES:
            raise ValueError("unsupported incident source_type")
        trigger = incident["trigger"]
        if (not isinstance(trigger, dict) or not trigger
                or not set(trigger) <= ALLOWED_TRIGGER_FIELDS):
            raise ValueError("incident trigger contains unsupported or no fields")
        for key, value in trigger.items():
            if key == "size" and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("trigger size must be a nonnegative integer")
            if key == "has_source" and not isinstance(value, bool):
                raise ValueError("trigger has_source must be boolean")
            if key not in {"size", "has_source"}:
                _text(value, f"trigger {key}", 100)
        if incident["expected"] not in ALLOWED_RESULTS or incident["observed"] not in ALLOWED_RESULTS:
            raise ValueError("incident expected/observed result is unsupported")
        if incident["expected"] == incident["observed"]:
            raise ValueError("incident expected and observed results must differ")
    return bundle


def _matches(payload: dict, trigger: dict) -> bool:
    return all(payload.get(key) == value for key, value in trigger.items())


def _score(cases: list[TestCase], incidents: list[dict]) -> dict:
    matrix, survivors = {}, []
    for incident in incidents:
        killers = [case.id for case in cases
                   if case.expected == incident["expected"]
                   and toy_app(case.input) == incident["expected"]
                   and _matches(case.input, incident["trigger"])]
        matrix[incident["id"]] = killers
        if not killers:
            survivors.append(incident["id"])
    killed = len(incidents) - len(survivors)
    return {"selected_case_ids": [case.id for case in cases], "cases": len(cases),
            "killed": killed, "total": len(incidents),
            "score": killed / len(incidents), "survivors": survivors, "matrix": matrix}


def _diverse_grid(cases: list[TestCase], budget: int) -> list[TestCase]:
    rank = {"hostile": 0, "boundary": 1, "happy": 2}
    groups = defaultdict(list)
    for case in cases:
        groups[case.requirement_id].append(case)
    for group in groups.values():
        group.sort(key=lambda case: (rank.get(case.difficulty, 99), case.id))
    selected = []
    depth = 0
    while len(selected) < budget:
        progressed = False
        for requirement_id in sorted(groups):
            if depth < len(groups[requirement_id]):
                selected.append(groups[requirement_id][depth])
                progressed = True
                if len(selected) == budget:
                    break
        if not progressed:
            break
        depth += 1
    return selected


def incident_adequacy(cases: list[TestCase], bundle: dict) -> dict:
    """Compare a requirement-balanced grid with seeded random cases at equal budget."""
    validate_incident_bundle(bundle, cases)
    config = bundle["experiment"]
    budget = config["budget"]
    grid_cases = _diverse_grid(cases, budget)
    random_cases = random.Random(config["random_seed"]).sample(cases, budget)
    grid, random_result = (_score(grid_cases, bundle["incidents"]),
                           _score(random_cases, bundle["incidents"]))
    gain = grid["killed"] - random_result["killed"]
    source_counts = dict(sorted(Counter(item["source_type"] for item in bundle["incidents"]).items()))
    result = {
        "schema_version": 1,
        "bundle_sha256": _digest(bundle),
        "suite_sha256": _digest([case.to_dict() for case in cases]),
        "privacy_review": bundle["privacy_review"],
        "source_counts": source_counts,
        "budget": budget,
        "random_seed": config["random_seed"],
        "minimum_kill_gain": config["minimum_kill_gain"],
        "grid": grid,
        "random": random_result,
        "kill_gain": gain,
        "accepted": gain >= config["minimum_kill_gain"],
        "limitations": [
            "Privacy review is a documented assertion, not automated sensitive-data detection.",
            "Structured trigger matching replays a defect signature; it does not model arbitrary code faults.",
            "One seeded random allocation is descriptive and historical incidents are selective evidence.",
        ],
    }
    result["audit_sha256"] = _digest(result)
    return result
