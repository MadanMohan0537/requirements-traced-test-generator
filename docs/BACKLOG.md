# Rigorous feature backlog

P1 mutation adequacy and P2 oracle uncertainty routing are implemented. Everything else below is planned and ordered by decision value rather than visual polish.

| Priority | Feature | Concrete user problem | Intended behavior | Dependencies | Success test | Risks and tradeoffs |
|---|---|---|---|---|---|---|
| P1 shipped | Mutation adequacy score | Authors cannot tell whether generated tests detect defects | Seed deterministic faults; report kills, survivors, and case-to-fault matrix | Executable domain adapter, frozen fixture | At equal budget, grid cases kill more frozen mutations than happy-path-only cases | Artificial faults may be unrealistic; add incident-derived defects |
| P2 shipped | Oracle uncertainty queue | Generated expected answers can be confidently wrong | Separate requirement evidence, expected behavior, oracle basis, and confidence; hold weak and contradictory oracles for adjudication | Evidence-bearing case model, SQLite queue | Frozen opposing 0.95-confidence oracles are both held; known-domain control oracles are ready | Exact-input matching misses semantic conflicts; confidence is not calibration |
| P2 | PRD-diff impact regeneration | A small requirement edit forces noisy full regeneration | Fingerprint clauses; regenerate and retire only impacted descendants | Versioned PRDs, stable lineage | Editing R3 changes only R3-linked cases and the audit explains every delta | Cross-clause dependencies may be missed |
| P2 | Incident-derived mutation importer | Toy faults overstate real-world adequacy | Convert redacted historical defects into replayable domain mutations | Incident taxonomy, privacy review | Held-out incident mutations distinguish the grid from a random equal-budget suite | Historical incidents are selective and can leak sensitive detail |
| P3 | Diversity budget optimizer | Case count grows faster than review capacity | Select a budgeted set maximizing clause, persona, difficulty, and lexical diversity | Similarity model, review budget | Same mutation score with at least 30% fewer reviewed cases | Optimization may remove rare but valuable cases |
| P3 | Cross-clause contradiction witness | Individual clauses look covered although their expectations conflict | Produce one concrete input where two clauses demand incompatible outcomes | Clause relation graph, reviewed oracle | Every seeded contradiction yields a reviewer-confirmed witness | Semantic conflicts can be approximate |
| P3 | Reviewer-disagreement audit | One reviewer can silently define the golden set | Blind duplicate a sample; report agreement by clause and difficulty | Reviewer identity, assignment | Seeded ambiguous cases show lower agreement and reach adjudication | Duplicate review increases cost |
| P3 | Generator blind-spot split | Generator and app may share model-family blind spots | Compare deterministic, alternate-model, and hand-written hostile sources separately | Optional local models, source labels | Each source is scored on frozen mutations and held-out incidents | More generators add noise, compute, and licensing concerns |
| P4 | Safe executable exporter | Teams need tests in their framework, not JSON | Export reviewed cases to pytest with strict schema and sandbox boundaries | Accepted-only view, template versioning | Generated tests run in a clean container without arbitrary-code escape | Generated code is a security surface |

## Next slice

Build PRD-diff impact regeneration next. A clause fingerprint and stable lineage
should retire and regenerate only descendants of changed requirements, with an
audit artifact explaining every retained, added, and retired case.


