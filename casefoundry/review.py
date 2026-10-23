"""SQLite human-review queue; generated cases never auto-enter a golden set."""

import json
import sqlite3
from pathlib import Path

from .models import TestCase


SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
  case_id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
  reason TEXT, edited_expected TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS oracle_reviews (
  case_id TEXT PRIMARY KEY, requirement_id TEXT NOT NULL,
  evidence TEXT NOT NULL, expected TEXT NOT NULL, confidence REAL NOT NULL,
  oracle_basis TEXT NOT NULL, status TEXT NOT NULL, reasons TEXT NOT NULL,
  conflict_with TEXT NOT NULL, reviewer_expected TEXT, review_reason TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class ReviewQueue:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.executescript(SCHEMA)

    def add(self, cases: list[TestCase]) -> int:
        with sqlite3.connect(self.path) as db:
            before = db.total_changes
            db.executemany("INSERT OR IGNORE INTO reviews(case_id,payload,status) VALUES (?,?,?)",
                           [(c.id, json.dumps(c.to_dict(), sort_keys=True), "pending") for c in cases])
            return db.total_changes - before

    def decide(self, case_id: str, status: str, reason: str = "",
               edited_expected: str | None = None) -> None:
        if status not in {"accepted", "edited", "rejected"}:
            raise ValueError("invalid review status")
        if status == "edited" and not edited_expected:
            raise ValueError("edited cases require edited_expected")
        with sqlite3.connect(self.path) as db:
            result = db.execute("UPDATE reviews SET status=?,reason=?,edited_expected=?,updated_at=CURRENT_TIMESTAMP WHERE case_id=?",
                                (status, reason, edited_expected, case_id))
            if result.rowcount != 1:
                raise KeyError(case_id)

    def counts(self) -> dict[str, int]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT status,COUNT(*) FROM reviews GROUP BY status")
            result = {status: count for status, count in rows}
        return {key: result.get(key, 0) for key in ("pending", "accepted", "edited", "rejected")}

    def add_oracles(self, cases: list[TestCase], assessments) -> int:
        by_id = {item.case_id: item for item in assessments}
        if set(by_id) != {case.id for case in cases}:
            raise ValueError("oracle assessments must cover every case exactly once")
        rows = []
        for case in cases:
            item = by_id[case.id]
            rows.append((
                case.id, case.requirement_id, case.evidence, case.expected,
                case.oracle_confidence, case.oracle_basis, item.status,
                json.dumps(list(item.reasons)), json.dumps(list(item.conflict_with)),
            ))
        with sqlite3.connect(self.path) as db:
            before = db.total_changes
            db.executemany(
                """INSERT OR IGNORE INTO oracle_reviews(
                case_id,requirement_id,evidence,expected,confidence,oracle_basis,
                status,reasons,conflict_with) VALUES (?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            return db.total_changes - before

    def adjudicate_oracle(
        self, case_id: str, reviewer_expected: str, reason: str
    ) -> None:
        if not reviewer_expected.strip() or not reason.strip():
            raise ValueError("adjudication requires expected behavior and reason")
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT status FROM oracle_reviews WHERE case_id=?", (case_id,)
            ).fetchone()
            if row is None:
                raise KeyError(case_id)
            if row[0] == "ready":
                raise ValueError("ready oracle does not require adjudication")
            db.execute(
                """UPDATE oracle_reviews SET status='adjudicated',
                reviewer_expected=?,review_reason=?,updated_at=CURRENT_TIMESTAMP
                WHERE case_id=?""",
                (reviewer_expected, reason, case_id),
            )

    def oracle_counts(self) -> dict[str, int]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT status,COUNT(*) FROM oracle_reviews GROUP BY status"
            )
            result = {status: count for status, count in rows}
        return {
            key: result.get(key, 0)
            for key in ("ready", "uncertain", "conflict", "adjudicated")
        }


