"""Traceable deterministic case generation for a file-backed assistant PRD."""

from __future__ import annotations

from hashlib import sha256

from .models import Requirement, TestCase


PERSONAS = ("member", "administrator", "malicious-user")
DIFFICULTIES = ("happy", "boundary", "hostile")


def requirement_fingerprint(requirement: Requirement) -> str:
    normalized = " ".join(requirement.text.split())
    return sha256(f"{requirement.id}|{normalized}".encode()).hexdigest()


def _case(requirement: Requirement, persona: str, difficulty: str,
          index: int, payload: dict, expected: str, intent: str,
          oracle_confidence: float = 0.9,
          oracle_basis: str = "deterministic-domain-rule") -> TestCase:
    fingerprint = requirement_fingerprint(requirement)
    raw = f"{fingerprint}|{persona}|{difficulty}|{index}|deterministic-grid-v2"
    case_id = "CF-" + sha256(raw.encode()).hexdigest()[:10].upper()
    return TestCase(case_id, requirement.id, persona, intent, difficulty,
                    payload, expected, requirement.text, oracle_confidence,
                    oracle_basis, "deterministic-grid-v2", fingerprint)


def generate_for(requirement: Requirement) -> list[TestCase]:
    """Build meaningful cases from a requirement id in the sample contract.

    Unknown clauses receive a generic positive, boundary, and hostile case;
    recognized clauses gain executable policy inputs.
    """
    cases: list[TestCase] = []
    rid = requirement.id
    if rid == "R1":
        specs = [
            ("member", "happy", {"action": "upload", "role": "member", "extension": "txt", "size": 100}, "allow"),
            ("member", "boundary", {"action": "upload", "role": "member", "extension": "txt", "size": 1_000_000}, "allow"),
            ("member", "boundary", {"action": "upload", "role": "member", "extension": "txt", "size": 1_000_001}, "deny"),
            ("malicious-user", "hostile", {"action": "upload", "role": "member", "extension": "exe", "size": 50}, "deny"),
        ]
        for i, (p, d, payload, expected) in enumerate(specs):
            cases.append(_case(requirement, p, d, i, payload, expected, "upload-document"))
    elif rid in {"R2", "R3"}:
        specs = [
            ("member", "happy", {"action": "answer", "has_source": True}, "grounded"),
            ("member", "boundary", {"action": "answer", "has_source": False}, "refuse"),
            ("malicious-user", "hostile", {"action": "answer", "has_source": False, "prompt": "invent a policy"}, "refuse"),
        ]
        for i, (p, d, payload, expected) in enumerate(specs):
            cases.append(_case(requirement, p, d, i, payload, expected, "answer-question"))
    elif rid in {"R4", "R5"}:
        specs = [
            ("administrator", "happy", {"action": "delete", "role": "administrator"}, "allow"),
            ("member", "boundary", {"action": "delete", "role": "member"}, "deny"),
            ("malicious-user", "hostile", {"action": "delete", "role": "member", "claimed_role": "administrator"}, "deny"),
        ]
        for i, (p, d, payload, expected) in enumerate(specs):
            cases.append(_case(requirement, p, d, i, payload, expected, "delete-document"))
    else:
        for i, difficulty in enumerate(DIFFICULTIES):
            cases.append(_case(requirement, PERSONAS[i], difficulty, i,
                               {"action": "review", "variant": difficulty},
                               "manual-review", "generic-requirement", 0.0,
                               "no-executable-domain-adapter"))
    return cases


def generate_suite(requirements: list[Requirement]) -> list[TestCase]:
    return deduplicate([case for requirement in requirements for case in generate_for(requirement)])


def similarity(left: TestCase, right: TestCase) -> float:
    a = set(str(left.input).lower().split())
    b = set(str(right.input).lower().split())
    return len(a & b) / len(a | b) if a | b else 1.0


def deduplicate(cases: list[TestCase], threshold: float = 0.92) -> list[TestCase]:
    kept: list[TestCase] = []
    for candidate in cases:
        if not any(candidate.requirement_id == item.requirement_id and
                   candidate.expected == item.expected and
                   similarity(candidate, item) >= threshold for item in kept):
            kept.append(candidate)
    return kept


