# Rigorous feature backlog

P1 mutation adequacy, P2 oracle uncertainty routing, clause-scoped PRD-diff regeneration, and the incident mutation importer are implemented. Everything else below is planned and ordered by decision value rather than visual polish.

| Priority | Feature | Concrete user problem | Intended behavior | Dependencies | Success test | Risks and tradeoffs |
|---|---|---|---|---|---|---|
| P1 shipped | Mutation adequacy score | Authors cannot tell whether generated tests detect defects | Seed deterministic faults; report kills, survivors, and case-to-fault matrix | Executable domain adapter, frozen fixture | At equal budget, grid cases kill more frozen mutations than happy-path-only cases | Artificial faults may be unrealistic; add incident-derived defects |
| P2 shipped | Oracle uncertainty queue | Generated expected answers can be confidently wrong | Separate requirement evidence, expected behavior, oracle basis, and confidence; hold weak and contradictory oracles for adjudication | Evidence-bearing case model, SQLite queue | Frozen opposing 0.95-confidence oracles are both held; known-domain control oracles are ready | Exact-input matching misses semantic conflicts; confidence is not calibration |
| P2 shipped | PRD-diff impact regeneration | A small requirement edit forces noisy full regeneration | Fingerprint clauses; retain unchanged cases; regenerate and retire only impacted descendants; queue only additions | Versioned manifest, stable lineage, deterministic generator | Editing R3 changes only R3-linked cases; reorder changes none; audit explains every exact ID and rejects a modified manifest digest | Direct fingerprints miss cross-clause dependencies; digest is not an author signature; v1 IDs migrate once to v2 |
| P2 shipped | Incident-derived mutation importer | Toy faults overstate real-world adequacy | Import privacy-reviewed, data-only defect signatures; compare a requirement-balanced grid with seeded-random cases at equal budget | Incident taxonomy, privacy declaration, deterministic domain adapter | Synthetic fixture kills 3/3 signatures with the grid versus 2/3 at the same random budget; unsafe schemas fail closed | Historical incidents are selective; privacy is self-attested; narrow triggers miss general faults; one random draw is unstable |
| P3 | Diversity budget optimizer | Case count grows faster than review capacity | Select a budgeted set maximizing clause, persona, difficulty, and lexical diversity | Similarity model, review budget | Same mutation score with at least 30% fewer reviewed cases | Optimization may remove rare but valuable cases |
| P3 | Cross-clause contradiction witness | Individual clauses look covered although their expectations conflict | Produce one concrete input where two clauses demand incompatible outcomes | Clause relation graph, reviewed oracle | Every seeded contradiction yields a reviewer-confirmed witness | Semantic conflicts can be approximate |
| P3 | Reviewer-disagreement audit | One reviewer can silently define the golden set | Blind duplicate a sample; report agreement by clause and difficulty | Reviewer identity, assignment | Seeded ambiguous cases show lower agreement and reach adjudication | Duplicate review increases cost |
| P3 | Generator blind-spot split | Generator and app may share model-family blind spots | Compare deterministic, alternate-model, and hand-written hostile sources separately | Optional local models, source labels | Each source is scored on frozen mutations and held-out incidents | More generators add noise, compute, and licensing concerns |
| P4 | Safe executable exporter | Teams need tests in their framework, not JSON | Export reviewed cases to pytest with strict schema and sandbox boundaries | Accepted-only view, template versioning | Generated tests run in a clean container without arbitrary-code escape | Generated code is a security surface |

## Next slice

Build repeated-randomization uncertainty for incident adequacy next, then add a diversity
budget optimizer that tries to preserve kills with fewer reviewed cases.

## Further rigorous additions — planned

| Priority | Feature | Problem and behavior | Dependencies | Success test | Risks/tradeoffs |
|---|---|---|---|---|---|
| P2 | Dependency-aware diff expansion | A changed clause can affect tests owned by another unchanged clause | Store reviewed clause dependencies and expand the impacted set transitively | Seeded R2→R3 dependency regenerates both when R2 changes | Incorrect dependency graphs create noise or false retention |
| P2 | Incident privacy canary | A self-attested bundle may still contain sensitive text | Scan a frozen canary corpus and require independent review metadata before import | Seeded credential and identifier strings fail closed | Pattern scanning can miss context and create false confidence |
| P2 | Repeated random adequacy baseline | One random allocation can make the grid look better by chance | Evaluate many seeded allocations and report an empirical gain interval | Frozen incident bundle and suite | Null fixture does not claim a stable gain; strong fixture remains distinguishable | Repeated reuse can overfit the frozen incidents |
| P2 | Lineage signature and release attestation | A digest detects changes but not who approved a suite | Sign accepted manifest and audit digests through an external release workflow | Tampered or unsigned release artifacts fail verification | Key management and identity policy are out of scope locally |
| P3 | Review-state carry-forward policy | Retained cases may preserve approvals that no longer fit surrounding context | Require an explicit context-change review before carrying accepted state | A material related-clause change blocks silent approval reuse | More review work and dependency judgment |


