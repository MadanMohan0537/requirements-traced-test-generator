# Architecture

## Boundary

CaseFoundry is a portfolio-scale offline tool. The CLI parses one PRD, creates versioned candidates, writes JSON reports, and seeds a local review database. It does not call a model or execute arbitrary generated code.

## Decisions

| Decision | Reason | Tradeoff |
|---|---|---|
| Explicit `[R#]` syntax | Makes traceability deterministic and testable | Requires authors to structure the source |
| Per-clause generation | Makes coverage gaps measurable | Cross-clause conflicts are not yet modeled |
| Structured inputs/expectations | Enables executable mutation tests | Needs a domain adapter for new products |
| Stable SHA-256 IDs | Replays do not create duplicate review work | Meaningful edits should bump generator version |
| Jaccard dedupe | Zero-cost and explainable | Weak semantic recall |
| Human review before promotion | Prevents synthetic noise entering a golden set | Adds reviewer workload |
| Seeded mutation runner | Measures defect-detection ability | Synthetic defects can be unrealistic |
| Evidence-first oracle screen | A traceable case can still encode the wrong expected behavior | Exact-input conflict matching misses semantic contradictions |
| Confidence as routing only | Uncalibrated scores cannot prove correctness | More candidates require human adjudication |

## Artifact contracts

`cases.json` is an array of candidate cases. Each case carries requirement
evidence, expected behavior, oracle basis, and routing confidence.
`coverage.json` contains clause counts, difficulty counts, a mutation matrix,
and per-case oracle assessments. `reviews.db` stores the immutable candidate
payload plus ordinary review state and a separate `oracle_reviews` table for
ready, uncertain, conflicting, and adjudicated expectations.

Oracle conflict detection canonicalizes structured input and combines it with
intent. Opposing expectations on the same behavior are held regardless of
confidence. Missing evidence, missing basis, manual expectations, and values
below the predeclared `0.75` routing threshold are uncertain.

## Production hardening

Add versioned PRD snapshots, semantic and cross-clause contradiction detection,
domain-specific oracle adapters, calibrated semantic deduplication,
authenticated reviewer assignment, immutable audit events, and incremental
regeneration from PRD diffs. Run generated code only inside a resource-limited
sandbox; this MVP deliberately avoids that risk.


