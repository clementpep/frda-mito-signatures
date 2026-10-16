# Routine `frda-watch` — weekly watch, digest and supervision

The weekly run has two parts on one branch: the watch (steps 0–5 below), then the supervision
(`routines/supervisor.md`, S1–S6), then the hand-over (step 6).

Read `routines/procedures.md` first. Task id for this run: `W-<ISO year>-W<ISO week>`
(e.g. `W-2026-W43`), branch `auto/<that id>`.

## STEP 0 — P0 sync, P1 setup

If `origin/auto/W-<this week>` already exists, stop: `💤 frda-watch — already ran this week`.

```bash
W="W-$(date -u +%G)-W$(date -u +%V)"; git checkout -b "auto/$W" origin/main
```

## STEP 1 — Upstream drift

```bash
uv run --frozen frda fetch --force
```
A checksum mismatch means a public file changed upstream. Do NOT update the manifest: add a
`FIX-<date>-drift-<GSE>` task (`status: ready`, priority 1, kind data) to the backlog describing
the mismatch, and flag it first in the digest.

## STEP 2 — New public datasets

NCBI E-utilities (allowlisted, ≤ 3 requests/s), since the date of the previous digest:
`esearch.fcgi?db=gds&term=(friedreich ataxia OR frataxin OR FXN) AND gse[ETYP]&mindate=<last>&maxdate=<today>&datetype=pdat`
then `esummary`. For each new series not already in `data-manifests/` or `candidates.yaml`: add
it to `data-manifests/candidates.yaml` with what the summary states (no guessing) and the date.

## STEP 3 — New literature and novelty risk

Run the protocol queries of `research/protocol.md` restricted to the last 8 days
(`frda lit-search "<query> AND FIRST_PDATE:[<date-8d> TO <today>]" --save watch-<W>-<rq> --task <W>`),
then `frda lit-add <new ids> --task <W> --found-by <log-stem>` (they enter as `to_screen`; screening
is a literature task). Append to `docs/literature/watch-log.md`: id, title, one-line relevance. For any paper
that overlaps a current claim or a candidate question (`docs/literature/landscape.md`), write a
**novelty alert** in the digest: which claim, what overlaps, consequence (cite it, differentiate,
or drop).

## STEP 4 — Backlog proposals

New work suggested by steps 1–3 is added to `autonomy/backlog.yaml` as `status: proposed` (never
`ready`), with goal and acceptance criteria. The verifier decides whether it becomes `ready`.

## STEP 5 — Weekly digest

`autonomy/digests/<W>.md`:
- landed on main this week (`git log --since='7 days ago' --oneline origin/main`), by task;
- verification verdicts of the week (from `autonomy/verifications/`), attempts, open NEEDS_HUMAN;
- claims added / changed, by status (reproduced / refuted / new / not_demonstrated);
- drift, new datasets, novelty alerts;
- milestone progress and the next 3 tasks the worker will take.
Numbers and links only; no hype.

## STEP 5b — Supervision

Execute `routines/supervisor.md` S1–S6 now, on this branch.

## STEP 6 — Commit, push, final message

```bash
make hub && uv run --frozen frda verify --require-data
git add -A && git commit -m "work($W): weekly watch, digest and supervision"
bash scripts/push-branch.sh HEAD "auto/$W"
```
Final message: `✅ frda-watch — <W>: <n> papers, <n> datasets, <n> alerts; RD-xxx: <one line>`
(or `⚠️ NEEDS HUMAN — <the pivot question>` when the supervision asks for a pivot; mention the
monthly report when one was written).
