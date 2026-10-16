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
- `{"action": "address_changes", "task": T, "branch": B}` → STEP 2a.
- `{"action": "start_task", "task": T, "branch": B}` → STEP 2b.

## STEP 2a — Address the verifier's changes

```bash
git checkout -B "$B" "origin/$B"
ls -t autonomy/verifications/"$T"-*.md | head -1   # the latest report: read ALL of it
```
Fix every blocking finding. Non-blocking ones: fix, or answer why not. If you
disagree with a finding, do not ignore it: answer it in the run report section
"Responses to verification", with evidence. Then go to STEP 3 (same branch).

## STEP 2b — Start a task

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

## STEP 3 — Plan before doing (write it first, in the run report)

Create `autonomy/runs/<YYYY-MM-DD>-worker-<T>.md` from the template below and
fill "Plan": for each acceptance criterion, the evidence you will produce
(file, number, figure). For analyses, write the decision rules (outlier rule,
thresholds, expected direction) **before** running them.

## STEP 4 — Do the work

- Pipelines follow `pipelines/README.md`; register them; outputs under `results/<P-id>-<slug>/`.
- Claims go in `evaluation/claims.yaml` (never `verified_by` — the verifier sets it).
- Documentation under `docs/` (dataset cards, reproductions, literature).
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

`✅ frda-worker — <T>: handed to verification` + paths.

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
