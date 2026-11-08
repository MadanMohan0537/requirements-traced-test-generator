# Architecture

## Boundary

CaseFoundry is a portfolio-scale offline tool. The CLI parses one PRD, creates versioned candidates, writes JSON reports, and seeds a local review database. It does not call a model or execute arbitrary generated code.

## Decisions

| Decision | Reason | Tradeoff |
|---|---|---|
| Explicit `[R#]` syntax | Makes traceability deterministic and testable | Requires authors to structure the source |
| Per-clause generation | Makes coverage gaps measurable | Cross-clause conflicts are not yet modeled |
| Structured inputs/expectations | Enables executable mutation tests | Needs a domain adapter for new products |
| Clause-bound SHA-256 IDs | Unchanged clauses retain cases while edited clauses receive new descendants | The v2 migration changes prior v1 IDs once |
| Jaccard dedupe | Zero-cost and explainable | Weak semantic recall |
| Human review before promotion | Prevents synthetic noise entering a golden set | Adds reviewer workload |
| Seeded mutation runner | Measures defect-detection ability | Synthetic defects can be unrealistic |
| Evidence-first oracle screen | A traceable case can still encode the wrong expected behavior | Exact-input conflict matching misses semantic contradictions |
| Confidence as routing only | Uncalibrated scores cannot prove correctness | More candidates require human adjudication |
| Signed-content manifest | Every candidate is bound to its clause fingerprint and suite digest | A digest is tamper evidence, not an identity signature |

## Artifact contracts

`cases.json` is an array of candidate cases. Each case carries requirement
evidence, expected behavior, oracle basis, and routing confidence.
`coverage.json` contains clause counts, difficulty counts, a mutation matrix,
and per-case oracle assessments. `reviews.db` stores the immutable candidate
payload plus ordinary review state and a separate `oracle_reviews` table for
ready, uncertain, conflicting, and adjudicated expectations.

`cases.manifest.json` contains normalized clause text, SHA-256 fingerprints, complete
candidate payloads, generator version, and a suite digest. `impact-audit.json` compares
the previous and current manifests, lists each clause as unchanged, changed, added, or
removed, and records exact retained, added, and retired case IDs. Only added cases are
seeded into a new review database; their oracle screen still compares against the full
current suite so conflicts with retained cases remain visible.

Oracle conflict detection canonicalizes structured input and combines it with
intent. Opposing expectations on the same behavior are held regardless of
confidence. Missing evidence, missing basis, manual expectations, and values
below the predeclared `0.75` routing threshold are uncertain.

## Production hardening

Add reviewed cross-clause dependency expansion, semantic contradiction detection,
domain-specific oracle adapters, calibrated semantic deduplication,
authenticated reviewer assignment, immutable audit events, and incremental
release signatures. Run generated code only inside a resource-limited
sandbox; this MVP deliberately avoids that risk.


