# Routine `frda-worker` — do one research task, and check it yourself

You are the maker. Your work will be verified by an independent session that
re-downloads the data, re-runs everything and tries to falsify your claims.
Work so that it finds nothing: small scope, explicit evidence, honest limits.

Read `routines/procedures.md` first. Then `CLAUDE.md`, `docs/PROJECT_BRIEF.md`,
`autonomy/project.yaml`.

## STEP 0 — P0 sync, P1 setup

## STEP 1 — What to do

```bash
uv run --frozen frda autonomy-status --json > /tmp/status.json
python3 -c "import json;print(json.load(open('/tmp/status.json'))['next_for_worker'])"
```
- `None` → final message `💤 frda-worker — nothing to do (<WIP full | no ready task | waiting for verification>)`. Stop. No commit.
- `{"action": "address_changes", "task": T, "branch": B}` → STEP 2a
  (with `"merge_main": true`: the prerequisite it was parked on has landed → STEP 2a, first bullet).
- `{"action": "start_dependency", "task": F, "branch": B, "for": T, "source_branch": S}` → STEP 2c.
- `{"action": "start_task", "task": T, "branch": B}` → STEP 2b.

## STEP 2a — Address the verifier's changes

```bash
git checkout -B "$B" "origin/$B"
ls -t autonomy/verifications/"$T"-*.md | head -1   # the latest report: read ALL of it
```
- Always `git merge --no-edit origin/main` first (a branch cut before a tooling fix lands with
  its own old code: W-2026-W43 could not land on 2026-10-31 because of it); conflicts in
  `results/hub/summary.json` → take main's and `make hub`.
- `merge_main: true`, or a blocking finding names a `FIX-*` prerequisite that is already `done`
  on main → the merge above brings it (the prerequisite's fix is on
  main). In `autonomy/backlog.yaml` keep main's entry for the prerequisite (`done`). Then re-read
  `research/protocol.md` "Amendments": an amendment dated after the branch was cut applies to
  this task's re-hand-over (say how in the run report).

Fix every blocking finding. Non-blocking ones: fix, or answer why not. If you
disagree with a finding, do not ignore it: answer it in the run report section
"Responses to verification", with evidence. Then go to STEP 3 (same branch).

**A blocking finding you may not fix on this branch** (it needs `src/`, `tests/`… outside an
`infra` task, P5.4/P5.5) **and that names a `FIX-*` prerequisite** in the report → do not stop and
do not notify (P9). Park the branch and continue:
```bash
git commit --allow-empty -m "blocked($T): needs <FIX-ID>"
bash scripts/push-branch.sh HEAD "$B"
uv run --frozen frda autonomy-status --json > /tmp/status.json   # then back to STEP 1, once
```
No `FIX-*` named, or the fix is a scientific / scope decision → `⚠️ NEEDS HUMAN` as before (P8:
notified only if this decision is new).

## STEP 2b — Start a task

`next_for_worker.why` says why this task was chosen (effort track most behind its budget). Copy it
into the run report. Track `literature` → follow `routines/playbooks/literature.md`.

```bash
git checkout -b "$B" origin/main
uv run --frozen frda task "$T"
```
Read the task, its dependencies' outputs and reports. In `autonomy/backlog.yaml`
set this task's `status: in_review` (only this task).

Size check: if the task cannot be completed and self-verified within this run,
split it. Do the first coherent part; in the backlog, replace the task by
`<T>a` / `<T>b` … with the original acceptance criteria distributed so that
**none is dropped or softened**, and explain the split in the run report. The
verifier checks the split.

## STEP 2c — Do a prerequisite fix (P9)

```bash
git checkout -b "$B" origin/main
git show "origin/$S:autonomy/backlog.yaml"            # the verifier's FIX entry, on the parked branch
ls -t $(git ls-tree -r --name-only "origin/$S" autonomy/verifications | grep "/$T-") | head -1
```
Check, before anything: the latest verification report of `T` names `F` in a **blocking** finding;
`F` is `kind: infra` or `data`; its acceptance does not ask to loosen a gate, test, tolerance or
wording rule. Any check fails → `⚠️ NEEDS HUMAN — F: promote it?` (notified once) and stop.
Otherwise copy the `F` entry **verbatim** into this branch's `autonomy/backlog.yaml`, change only
`status: proposed` → `in_review`, add a note `auto-promoted by the worker (P9) to unblock T`. Then
STEP 3 as for any task; the run report says it is a P9 prerequisite and for which task.

## STEP 3 — Plan before doing (write it first, in the run report)

Create `autonomy/runs/<YYYY-MM-DD>-worker-<T>.md` from the template below and
fill "Plan": for each acceptance criterion, the evidence you will produce
(file, number, figure). For analyses, write the decision rules (outlier rule,
thresholds, expected direction) **before** running them.

## STEP 4 — Do the work

- Pipelines follow `pipelines/README.md`; register them; outputs under `results/<P-id>-<slug>/`.
- Claims go in `evaluation/claims.yaml` (never `verified_by` — the verifier sets it).
- Documentation under `docs/` (dataset cards, reproductions); research memory under `research/`
  (corpus, cards, synthesis). You may add ideas with `status: seed` only; scoring, status changes,
  budgets and phases belong to the weekly supervision (`routines/supervisor.md`).
- Literature and published values: Europe PMC REST API (allowlisted), quoted verbatim with location.
- Respect P5 and P6. You may not touch `src/frda/gates.py`, `src/frda/claims.py`
  (rules), `tests/`, `.github/`, `routines/`, `.claude/`, `Makefile`, `scripts/` unless the task
  kind is `infra`; adding a new test for your own code is welcome.

## STEP 5 — Self-verification (mandatory, before any push)

1. P2 gates. Fix until all pass. Never by weakening a check (P5.5).
2. Recompute each headline number of this task a second way (a different code path: e.g. plain
   pandas/scipy in a scratch script under /tmp, not committed) and compare. Record both values in
   the run report.
3. Launch the `scientific-reviewer` subagent on your diff
   (`git diff origin/main...HEAD`), giving it the task and the claims you added. Launch the
   `code-auditor` subagent on the same diff. Fix every blocking finding; list the others with your
   answer in the run report.
4. Re-read each acceptance criterion and mark MET / NOT MET with the evidence path. If one is NOT
   MET and cannot be met, say so — do not hand over a branch pretending otherwise.

## STEP 5b — News for non-specialists

If this task adds or changes claims, or closes a milestone, write one news item
`research/news/N-<YYYYMMDD>-<slug>.md` from `_TEMPLATE.md`, following `research/news/STYLE.md`
(plain French, every number explained, honest "Ce que ça ne veut pas dire"; for a `finding`,
cite the claims and an evidence level no stronger than the weakest of them). It is announced on
Telegram only after landing. No news for routine infrastructure or data-wrangling steps.

## STEP 6 — Commit and push

```bash
make hub
uv run --frozen frda verify --require-data
git add -A
git commit -m "work($T): <what changed, ≤ 72 chars>"
bash scripts/push-branch.sh HEAD "$B"
```
The **last** commit of the branch must be the `work(...)` commit.

## STEP 7 — Final message (P8)

`✅ frda-worker — <T>: handed to verification` + paths (prefix with the `⏸️` line when a branch was
parked in this run). **No push notification** for a hand-over or a park (P8); push only a new
`NEEDS HUMAN` decision.

---

## Run report template

```markdown
---
routine: worker
task: T-xxx
date: YYYY-MM-DD
branch: auto/T-xxx
---
# T-xxx — <title>

## Plan (written before doing)
| Acceptance criterion | Planned evidence |
|---|---|

## What was done
- commands run, pipelines added, files changed (paths)

## Results (numbers, with the artifact path they come from)

## Self-verification
- Gates: lint ✅ test ✅ verify ✅ reproduce ✅ (paste summary lines)
- Second-path recomputation: <value A> vs <value B> (tolerance, script description)
- scientific-reviewer: <n blocking fixed>, other findings and answers
- code-auditor: idem
| Acceptance criterion | MET / NOT MET | Evidence |
|---|---|---|

## Limitations and open questions

## Responses to verification (STEP 2a only)
```
