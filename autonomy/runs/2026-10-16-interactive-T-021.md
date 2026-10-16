---
routine: interactive (owner session)
task: T-021
date: 2026-10-16
branch: auto/T-021
---
# T-021 — Research system

Built in an interactive session with the owner, handed to the verifier like any routine work
(CLAUDE.md rule 8).

## What was done
- `src/frda/research.py`: Paper/Corpus, CardMeta/Finding, Idea/Scores (rubric, priority), DecisionMeta;
  offline cross-reference checks (`problems`) and plan budget checks; `summary` for hub/supervisor.
- `src/frda/literature.py`: Europe PMC search (cursor paging, logs), add (ids resolved, DOI dedup),
  online verify (title match ≥ 0.9, quotes verbatim in full text or abstract, normalised).
- `src/frda/backlog.py`: `track`, `idea` fields; `pick_next` (budget deficit over recent window, FIX first);
  `recent_tracks` (by PASS report date). `autonomy.status` uses them and exposes `why`.
- New gate `research`; hub summary `research` block + `track` on tasks (additive, schema_version 1).
- `research/`: PLAN.md, plan.yaml (phases A–D, budgets), protocol.md (draft for L-001), corpus/ideas
  (empty), cards template, synthesis skeleton, RD-001, notebook/reports READMEs, screening.md.
- Routines: playbooks/literature.md, supervisor.md (run inside the weekly routine), verifier STEP 6b,
  worker/watch/procedures/README/CLAUDE.md/AUTONOMY.md updated.
- Backlog: L-001…L-009 (literature programme), T-006 → gap analysis, tracks on every task.

## Self-verification
- `make ci`: lint OK, 45 tests pass, verify PASS (paper SKIP). `make reproduce`: P-001 PASS.
- Online check in a scratch copy (not committed): `lit-search` RQ1-like query → 1389 hits (protocol
  must narrow: L-001); Maddock 2026 preprint found as PPR:PPR1219382; `lit-add MED:29125828
  MED:33028632` resolved metadata (PMC ids, OA). `lit-verify` on a card with one real full-text
  sentence and one invented sentence → only the invented one flagged.
- `frda autonomy-status` → next task L-001 (literature 60 % target / 0 % done).

## Gate/test changes (for the tampering check)
Only additions: new gate `gate_research`, new tests (`tests/test_research.py`). Two assertions in
`tests/test_backlog.py` that hard-coded the first ready task ids were generalised (the queue changed),
without weakening what they check (first task is ready; the next one respects dependencies).

## Not done in this session
- Reviewer subagents were not run by the maker here (interactive session); the verifier's
  STEP 7 reviews are therefore the first independent review of this diff.
