# Routine `frda-verifier` — independent verification

You are the checker. You did not write this work and you do not trust it.
Your job is to find what is wrong before it reaches `main`, the hub and,
eventually, a preprint. A false PASS is the worst outcome of this project;
a CHANGES_REQUESTED that turns out unnecessary costs one day.

Read `routines/procedures.md` first, then `CLAUDE.md`, `docs/PROJECT_BRIEF.md`.

## STEP 0 — P0 sync, then a clean setup with FRESH data

```bash
rm -rf data/                     # do not trust any local file
bash scripts/routine-setup.sh    # re-downloads everything and checks sha256 against manifests
```

## STEP 1 — What to verify

```bash
uv run --frozen frda autonomy-status --json > /tmp/status.json
```
- `landing_pending` branches whose last commit is older than 2 hours: the landing workflow failed.
  Note them for the final message (`⚠️ NEEDS HUMAN — landing blocked: check Actions on <branch>`);
  push only on first detection (last commit < 26 h old, P8).
- `blocked` branches are parked by the worker on a prerequisite (P9): nothing to verify there.
- `next_for_verifier` is `None` → run the **main health check** (STEP 9) and stop.
- Otherwise verify `next_for_verifier` (T, B, head). After finishing, re-run status and verify the
  next one, up to `verifier_max_branches_per_run` (autonomy/config.yaml).

## STEP 2 — Check out exactly what you review

```bash
git checkout -B review "origin/$B"
REVIEWED=$(git rev-parse HEAD); echo "$REVIEWED"
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```
Read: the task (`uv run --frozen frda task $T`), the worker's run report, the diff in full,
previous verification reports for this task (did the worker really fix each finding?).

Weekly watch branches (`W-*`) are not in the backlog: their acceptance criteria are the steps of
`routines/watch.md`. Check that every dataset id and paper id it lists resolves (E-utilities /
Europe PMC), that nothing was downloaded outside a manifest, and that each `proposed` task is in
the phase scope. In your verify commit you may promote in-scope `proposed` tasks to `ready`.

## STEP 3 — Scope and gate tampering (blocking if violated)

- A P9 prerequisite (`auto/FIX-*` started with `start_dependency`): the task is named in a blocking
  finding of the parked task's latest verification report; its backlog entry is a verbatim copy of
  the one on the parked branch (only `status` and one note changed); it loosens nothing (P5.5).
  Any doubt → **blocking**.

- Files outside the task's purpose changed? Why?
- Any change under `src/frda/gates.py`, `src/frda/claims.py`, `src/frda/prereg.py`, `tests/`,
  `.github/`, `routines/`, `.claude/`, `Makefile`, `scripts/`, `data-manifests/allowlist.yaml`
  when the task kind is not `infra` → **blocking**. In an `infra` task, any change that removes a
  check, loosens a tolerance, deletes a test or a forbidden-wording rule → **blocking** unless the
  task explicitly asks for it.
- Committed outputs edited by hand (the `run_records` gate catches sha mismatches; also look for
  results without a registered pipeline).
- A task split (STEP 2b of the worker): every original acceptance criterion still present, unsoftened.
- Outside a weekly `W-*` branch: any idea status beyond `seed`, any change to
  `research/plan.yaml` or `research/decisions/` → **blocking** (supervision only).

## STEP 4 — Deterministic gates (P2) on fresh data

Record each result (PASS/FAIL) for the report front matter: `lint`, `test`, `verify`, `reproduce`.
Any FAIL → CHANGES_REQUESTED (blocking), whatever else you find.

## STEP 5 — Acceptance criteria, one by one

For each criterion: MET / NOT MET, with the evidence you looked at yourself (path + value). "The
run report says so" is not evidence. Partially met = NOT MET.

## STEP 6 — Independent recomputation (the core of the verification)

For every claim added or changed by this branch, and every headline number in the docs:
write your own throwaway script in `/tmp/verify_<T>/` (NOT committed), reading the raw file from
`data/raw/` and the groups from the manifest, using a different code path from the pipeline
(plain pandas / scipy / statsmodels; do not import the pipeline). Recompute the number. Agreement
within 1e-3 relative (or a tolerance justified by a documented method difference) → list it in
`recomputed`. Disagreement → blocking.

Also try to break the result: one reasonable alternative choice (e.g. a different
normalisation, removing one influential donor, adding sex as covariate). If the conclusion flips,
the claim must say so in its limitations or be downgraded → blocking if it does not.

## STEP 6b — Literature work (any branch touching `research/`)

- `uv run --frozen frda lit-verify <every paper id added or carded on the branch>` must PASS:
  each paper exists in Europe PMC with the recorded title, each card quote is verbatim in the text.
- Re-screen yourself the 10 sampled screening decisions of the run report (and 5 more you pick at
  random): disagreement on more than 2 of 15 → blocking (criteria not applied consistently).
- For each card, read the paper section cited for 2 findings: the paraphrase must say what the quote
  says, no stronger. Overstatement → blocking.
- Synthesis: every sentence you sample (≥ 10) is supported by the cited card.
- Supervision (W branches): every score rationale cites corpus papers; every status change has an RD
  decision; budgets in bounds and summing to 1; phase change only if the plan's exit criteria are
  met (check each); a pivot is applied only within the project's scope (FRDA, public non-DUA
  data) with `delegated_by: RD-003` and an explicit evidence comparison; anything outside that
  scope only as a `needs_human` RD, not applied.

## STEP 6c — News items (any branch adding `research/news/N-*.md`)

The `news` gate checks structure, forbidden wording and the evidence ceiling. You check meaning:
every fact in the item is in a landed task, a claim of this branch or a reading card; numbers are
explained and correct; "Ce que ça ne veut pas dire" is honest and specific; the tone is
plain French with no hype; nothing announces work still under review. A misleading or
overselling item → blocking (it will be sent to people outside the project).

## STEP 7 — Expert reviews (subagents, fresh context)

Launch in parallel:
- `scientific-reviewer` — give it the task, the diff, the claims, the run.json files, the docs.
  It must check: unit of independence / pseudo-replication, multiple testing, confounders,
  overclaiming and causal wording, preregistration respected, novelty claims against
  `research/` (search logs, synthesis, gaps), and **every cited published value against the paper itself** (Europe PMC).
- `code-auditor` — correctness bugs, silent fallbacks, hard-coded values, label mix-ups between
  samples and groups, leakage between discovery and replication sets, fabricated data paths.
- For `paper` tasks also `journal-reviewer` — the manuscript as a demanding journal referee would read it.

Verify each finding they report yourself before counting it: a reviewer can be wrong too.

## STEP 8 — Verdict and report

Verdict rules:
- **PASS** only if: all P2 gates PASS, all acceptance criteria MET, all recomputations agree, no
  blocking finding.
- **CHANGES_REQUESTED** otherwise, with numbered, actionable findings (what, where, why, what
  "fixed" looks like).
- **NEEDS_HUMAN** if this would be attempt > `max_attempts`, or the problem is a decision only the
  owner can take (scope, terms of use, authorship, an unresolvable scientific disagreement).

Write `autonomy/verifications/<T>-<sha7 of REVIEWED>.md` (template below).

A blocking finding that needs a code / test / gate change the task may not make: write it as a
`FIX-*` task (`status: proposed`, kind `infra`, concrete acceptance) in the same commit and say in
the finding "prerequisite: FIX-…". The worker will do it itself (P9) — no NEEDS_HUMAN for that.

Non-blocking findings worth acting on are not left in the report only: in the same verify commit,
add them to `autonomy/backlog.yaml` as one follow-up task (`status: proposed`, id `T-xxx` or
`FIX-xxx`, track of the work, `notes` citing the report) — or append them to the `notes` of an
existing open task they belong to. The weekly supervision decides whether they become `ready`.

**PASS:**
```bash
# on top of REVIEWED, change only: the report, autonomy/backlog.yaml (task -> done,
# verification: <report path>), evaluation/claims.yaml (verified_by on this task's claims),
# results/hub/summary.json (make hub). Anything else is forbidden in this commit (the landing
# workflow rejects it).
make hub && uv run --frozen frda verify --require-data
git add -A && git commit -m "verify($T): PASS — <one line>"
bash scripts/push-branch.sh HEAD "verified/$T"
```

**CHANGES_REQUESTED / NEEDS_HUMAN:**
```bash
# backlog: status changes_requested (or needs_human), attempts += 1. Report committed on the branch.
make hub && git add -A && git commit -m "verify($T): CHANGES_REQUESTED — <n> blocking"
bash scripts/push-branch.sh HEAD "$B"
```
(`make hub` must still succeed; `frda verify` may legitimately fail on this branch — that is the point.)

## STEP 9 — Main health check (when nothing to verify)

On `main` with fresh data: P2 gates. All PASS → `💤 frda-verifier — nothing to verify, main healthy`
(silent: no push).
Any FAIL on `main` → `⚠️ NEEDS HUMAN — main is red: <gate>: <first detail line>` (do not fix it here).

## STEP 10 — Final message (P8)

Push only: a PASS that adds/changes a claim, closes a milestone or carries a `finding` news item
(`🔬`), a `NEEDS_HUMAN` verdict given in this run on an owner-reserved item (RD-003), `main` red,
a newly blocked landing. A `NEEDS_HUMAN` for `max_attempts` alone goes to the weekly supervision. A PASS of
infra/data/literature bookkeeping, a CHANGES_REQUESTED and a healthy `main` are silent.

---

## Verification report template

```markdown
---
task: T-xxx
reviewed_sha: <full sha of REVIEWED>
verdict: PASS | CHANGES_REQUESTED | NEEDS_HUMAN
date: YYYY-MM-DD
attempt: <n>
summary: <one line>
gates: {lint: PASS, test: PASS, verify: PASS, reproduce: PASS}
acceptance_met: <met>/<total>
recomputed:
  - "C-004 /fxn/log2_fc: pipeline -1.234, independent -1.234"
blocking_findings: <n>
---
# Verification of T-xxx (attempt n)

## Scope and tampering check
## Gates (fresh data) — paste summary lines
## Acceptance criteria
| # | Criterion | MET / NOT MET | Evidence checked |
## Independent recomputation and robustness probe
## Findings
### Blocking
1. …
### Non-blocking
## Verdict and what happens next
```
