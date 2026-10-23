from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TestCase:
    id: str
    requirement_id: str
    persona: str
    intent: str
    difficulty: str
    input: dict
    expected: str
    evidence: str
    oracle_confidence: float = 0.9
    oracle_basis: str = "deterministic-domain-rule"
    generator: str = "deterministic-grid-v1"

    def to_dict(self) -> dict:
        return asdict(self)


