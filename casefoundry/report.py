from collections import Counter

from .models import Requirement, TestCase
from .mutations import mutation_score
from .oracles import assess_oracles, oracle_summary


def build_report(requirements: list[Requirement], cases: list[TestCase]) -> dict:
    counts = Counter(case.requirement_id for case in cases)
    mutation = mutation_score(cases)
    oracles = oracle_summary(assess_oracles(cases))
    return {
        "requirements": len(requirements),
        "cases": len(cases),
        "coverage": {r.id: {"cases": counts[r.id], "thin": counts[r.id] < 3} for r in requirements},
        "difficulty": dict(Counter(case.difficulty for case in cases)),
        "oracles": oracles,
        "mutation": {
            "killed": mutation.killed,
            "total": mutation.total,
            "score": mutation.score,
            "survivors": list(mutation.survivors),
            "matrix": mutation.matrix,
        },
    }


