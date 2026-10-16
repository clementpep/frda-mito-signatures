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

## Responses to verification (attempt 1 → 2)

### Blocking — all fixed, each with a regression test
1. `tests/test_backlog.py`: the tautology is gone. `next_ready()` must equal the minimum
   (priority, id) among ready tasks whose dependencies are done; the exclusion test asserts non-None,
   dependencies done, and that excluding every dependency-free task yields `None`.
2. `literature.verify`: explicit ids absent from the corpus are problems; an empty target list is a
   problem ("no paper to verify"). Online: `frda lit-verify MED:99999999` → FAIL.
3. Degenerate quotes: `Finding` requires ≥ 20 letters/digits; `verify` re-checks after normalisation
   (`quote_is_substantive`).
4. Full-text cards: the recorded pmcid must equal the pmcid Europe PMC returns for the paper; only the
   `<body>` of the article is searched (front matter and references excluded). Tested offline; online the
   real Introduction sentence still passes and the invented one fails.
5. `pick_next`: tracks with budget ≤ 0 (or absent) only run when no funded track has a ready task (reason
   says so); deterministic tie-break (deficit, priority, track name). Tests for both.
6. `recent_tracks(window <= 0)` → `[]`; `research.problems` requires `budget_window` integer ≥ 1.

### Non-blocking
1. Fixed: stale T-006/landscape references (backlog M2 exit criterion and T-010 acceptance, watch.md,
   procedures.md P6, AUTONOMY.md, docs/literature/README.md, scientific-reviewer and journal-reviewer
   agents, verifier STEP 7). `T-010` now depends on `T-006`.
2. Partly fixed: the `research` gate requires `needs_human: true` on `kind: pivot` decisions. Owner
   acknowledgement for phases C/D or the first active idea stays a procedure rule (monthly report): the
   owner asked for autonomy; a pivot is the line that needs them.
3. Fixed: `track_floor: {main: 0.2}` in plan.yaml, enforced by the gate.
4. Not fixed here: protocol freezing is procedural (L-001 lands the protocol before L-002 can start, via
   depends_on; amendments section). A hash gate would add little over the dependency + verifier check.
5. Fixed: `fetch_record` matches source and id; `known_doi` updated within a batch; duplicate card/RD
   files raise. WIP excluding `W-` is intentional (weekly runs must not be blocked by task WIP).
6. Documented in `frda.literature` docstring (metadata and article texts, not checksummed datasets).
7. Still true; this attempt was not reviewed by subagents in the interactive session either.

Checks: `make ci` PASS (53 tests), `make reproduce` PASS.

## Responses to verification (attempt 2 → 3)

### Blocking
1. Markup false-PASS — fixed at the root: `normalise` no longer strips anything that looks like a tag.
   Markup is removed on the **source side only** (`markup_to_text`: XML parse of `<body>` with inline
   elements glued and block elements separated; regex fallback limited to real tags, so "p < 0.05 and
   q > 0.1" survives). A quote containing markup is rejected ("copy the text only"). Tests:
   `test_bracketed_invented_span_fails`, `test_literal_angle_brackets_in_source_are_kept`. Online on
   MED:29125828: real sentence PASS; same sentence with "<prove a cure>" inserted → FAIL.
2. Window test — rewritten with two PASS reports: window 10 → both tracks in order, 1 → latest, 0 → [],
   `True` → []. Mutation check: with the guard replaced by `if False:` the test fails; restored.

### Non-blocking
1. Fixed: shares are computed among budgeted tracks only (`test_unbudgeted_tracks_do_not_dilute_shares`).
2. Kept as is: the floor is a constraint on the budget the supervisor sets (gate); `pick_next` then honours
   the budget. Order inside `main` is the task priority (M1 tasks are priority 1–3).
3. Deferred: richer `novelty_check` content belongs to the claims schema (claims.py rule change → its own
   task, reviewed as such).
4. Deferred: `lit-verify` stays online-only by design (gates are offline); the verifier records it in STEP 6b.
   `abstract_only` cards are honest about their source; the synthesis may weigh them.
5. Fixed: supervisor S5 forbids editing acceptance/depends_on of existing tasks (replace + RD instead).
6. Fixed: `bool` rejected as window in gate and `recent_tracks`; `autonomy.status` falls back to 10 on an
   invalid window instead of crashing. Same-day ordering by id is acceptable (dates are days).
7. Fixed: slugs sanitised; logs never overwritten (`-2`, `-3`…); network errors reported as problems.
8. Fixed: PLAN.md wording (committee; "shifted … association only").

Checks: `make ci` PASS (57 tests), `make reproduce` PASS.
