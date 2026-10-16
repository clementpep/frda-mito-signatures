# Thesis plan

This project is run like a PhD, by autonomous routines, with the owner as thesis director's
director: they steer, the routines work and check each other.

## The research question (phase 1)

1. Which mitochondria-related transcriptomic signatures reproduce across independent FRDA datasets?
2. Do interventions (starting with A-196 in GSE145115) move these signatures in the expected direction?

The question can be refined by the weekly supervision (decision `kind: arbitration`). Changing it
— another disease, another mechanism, another data type — is a **pivot**: decided by the owner
(`needs_human: true`).

## How a working week looks

| Day | Who | What |
|---|---|---|
| every night | worker | one task, chosen by `pick_next`: the effort track most behind its budget |
| every morning | verifier | independent verification of the night's work; quotes checked against the papers |
| Monday | watch + supervision | new data and papers → corpus; lab notebook; ideas scored; budgets and priorities arbitrated; monthly report to the owner |

## Effort tracks and budgets

| Track | What it covers |
|---|---|
| `literature` | protocol, searches, screening, reading cards, synthesis, gap analysis |
| `main` | the active line: data, QC, reproductions, analyses of the main question |
| `exploration` | short, bounded scoping studies of candidate ideas (≤ 2 tasks each) |
| `writing` | manuscript, figures, outreach brief |
| `infra` | tooling; outside the budget, picked when nothing budgeted is ready |

Budgets per phase are in `research/plan.yaml`. The supervisor can move them within
`budget_bounds`, recording why in an RD decision. `FIX-*` tasks (data drift, broken main) always
go first.

## Phases

- **A — State of the art and credible foundation** (now): bibliography like a first-year PhD
  student — explicit review protocol, reproducible searches, screening with reasons, reading cards
  with verbatim quotes, a cited synthesis; in parallel the M1 reproductions. Output: chapter 1
  (state of the art) and a list of seed ideas grounded in papers and public data.
- **B — Research question and leads**: ideas scored on a fixed rubric, novelty-checked, one chosen
  as the main line, others parked or explored briefly.
- **C — Contribution**: preregistered analyses (M3–M5).
- **D — Writing**: manuscript from verified claims, internal review, owner sign-off.

Phase transitions are proposed by the supervision when the exit criteria in `plan.yaml` are met,
recorded as an RD decision (`kind: phase`) and announced to the owner in the monthly report.

## How leads are found and arbitrated

1. **Sources of leads** — every reading card can propose leads (`leads:`); the gap analysis of
   the synthesis; contradictions between papers; datasets nobody analysed for a question; the
   weekly watch (new paper or dataset).
2. **Seed** — anyone (worker, supervisor) can add an idea with `status: seed`: a question, the papers
   behind it, the public data that could test it.
3. **Scoring** (supervision only) — fixed rubric 1–5: novelty (against the corpus, never from
   memory), feasibility with public data, value for FRDA research, cost (5 = cheap), risk (5 = safe).
   Priority = 0.30·novelty + 0.25·feasibility + 0.25·value + 0.10·cost + 0.10·risk.
4. **Gates** — `candidate` requires scores, a novelty check and `publishable_if` (why a negative
   result would still be worth reporting). `active` is limited to `max_active_ideas`.
5. **Decision** — every status change beyond `seed` cites an RD decision with its rationale; ideas
   are parked, not deleted, so the reasoning stays auditable.

## What the owner sees

- `/research` on poups-ai-hub: phase, budgets, corpus progress, ideas and their status.
- `research/reports/YYYY-MM.md`: monthly progress report with explicit questions.
- Push notifications: `⚠️ NEEDS HUMAN` (pivot, terms of use, three failed verifications).
