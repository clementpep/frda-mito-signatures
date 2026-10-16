# Autonomy and verification

Goal: research that advances every day without anyone at the keyboard, at a quality level
that survives peer review. The design rests on one idea: **the agent that does the work never
decides that the work is good.**

## Actors

| Actor | Runs | Can push | Decides |
|---|---|---|---|
| `frda-worker` routine | daily 02:47 Paris | `auto/<TASK>` | how to do a task |
| `frda-verifier` routine | daily 06:53 Paris | `auto/<TASK>` (changes), `verified/<TASK>` (PASS) | whether a task is done |
| `frda-watch` routine | Monday 07:41 Paris | `auto/W-YYYY-Www` | what is new outside (data, papers, novelty risk) |
| `land-verified.yml` | on push `verified/**` | `main` | whether the deterministic bar is met on clean runners |
| Owner (human) | any time | `main` | scope, `needs_human` decisions, authorship, submission |

State lives **only in git**: backlog and statuses in `autonomy/backlog.yaml`, work in branches,
evidence in `autonomy/runs/` and `autonomy/verifications/`. Any routine can crash at any point
without corrupting anything; the next run re-derives the situation with `frda autonomy-status`.

## Working like a PhD (research memory and arbitration)

`research/PLAN.md` is the thesis plan. The routines keep a research memory in `research/`: literature
corpus (every paper screened, with reasons), reading cards with verbatim quotes, a cited
state-of-the-art synthesis, a registry of research leads scored on a fixed rubric, and dated
research decisions. Effort is arbitrated between tracks (`literature`, `main`, `exploration`,
`writing`) by budgets set per phase in `research/plan.yaml`: the worker always takes the track
most behind its budget (`frda.backlog.pick_next`). The weekly supervision (the thesis director,
`routines/supervisor.md`) writes the lab notebook, scores and arbitrates leads, moves budgets and
phases, grooms the backlog, and reports monthly to the owner. Pivots are the owner's call.

## Task lifecycle

```
ready ──worker──► in_review (auto/T) ──verifier──► PASS ──► verified/T ──land──► done (main)
                        ▲                    │
                        └─ changes_requested ┘   attempt > 3 → needs_human (push notification)
proposed (watch) ──verifier──► ready
```
WIP limit 1 (`autonomy/config.yaml`): one task in flight, so branches never conflict and every
task builds on verified work.

## Verification layers

| # | Layer | Who | What it catches |
|---|---|---|---|
| 1 | Plan-before-do | worker | moving goalposts: decision rules written before results |
| 2 | Deterministic gates (`frda verify`) | everyone | schema errors, data outside allowlist, checksum drift, edited outputs, claims failing their checks, causal wording, "new" before reproduction, low-n not labelled exploratory, preregistration after results, stale hub |
| 3 | Re-execution (`make reproduce`) | worker, verifier, CI | non-determinism, results not produced by committed code |
| 4 | Self-review subagents | worker | obvious scientific and code errors, before handover |
| 5 | Fresh-data re-run | verifier | dependence on local state, upstream changes |
| 6 | Independent recomputation | verifier | pipeline bugs (second implementation, different code path) |
| 7 | Robustness probe | verifier | conclusions that flip under one reasonable alternative choice |
| 8 | Independent reviewers (`scientific-reviewer`, `code-auditor`, `journal-reviewer`) | verifier | pseudo-replication, confounding, overclaiming, wrong citations, label mix-ups, leakage |
| 9 | Gate-tampering check | verifier | "fixing" a red check by weakening it |
| 9b | Literature audit (`frda lit-verify`) + re-screening sample | verifier | invented papers, invented or altered quotes, inconsistent screening, synthesis stronger than its sources |
| 10 | Landing guard | GitHub Actions | self-approval, code sneaked into the verify commit, red gates on clean runners |
| 11 | Human sign-off | owner | anything published under a name |

## Publication track (why the extra rules)

Aiming for a preprint changes the bar from "useful" to "defensible":
- **Preregistration in git** (`preregistrations/`): a confirmatory result is only one whose
  hypothesis, direction and decision rule were committed before the run (checked by the gate,
  using commit ancestry as the timestamp).
- **Discovery / replication separation**: the signature is frozen on the discovery set, then
  tested on datasets never used to build it (M2 → M3).
- **Novelty discipline**: `research/` (synthesis, gap analysis, search logs) + weekly watch. A claim is `new` only
  with a novelty-check log; the weekly watch raises *novelty alerts* when a paper overlaps.
- **Numbers by construction**: the manuscript cannot contain a hand-typed statistic; it renders
  values from verified claim artifacts.
- **Negative results are results**: a failed replication is reported as `not_demonstrated`.
- **Humans for accountability**: authorship, an FRDA expert co-author, submission (T-019).

## Failure modes and what happens

| Situation | Effect |
|---|---|
| Worker run dies mid-task | no push → task still `ready` on main; next run restarts it |
| Verifier finds problems | `CHANGES_REQUESTED` commit on `auto/T`; next worker run addresses it |
| 3 rejected attempts | `NEEDS_HUMAN`; push notification with the question |
| Landing workflow fails (conflict, red gate) | `verified/T` stays; the verifier flags it next morning |
| Upstream GEO file changes | `frda fetch` refuses it; watch opens a `FIX-…-drift` task |
| `main` red (should never happen) | verifier health check notifies; nothing else lands until fixed |

## Owner's controls

- Pause/resume a routine in claude.ai → Routines. Change cadence there.
- Re-prioritise: edit `priority`/`status` in `autonomy/backlog.yaml` on main.
- Answer a `needs_human`: write the decision in the task's `notes`, set `status: ready`.
- Follow along: poups-ai-hub `/research`, weekly digests in `autonomy/digests/`.
