# ADR 0001 — Autonomous maker/checker loop on git, no direct push to main

Date: 2026-10-16 · Status: accepted

## Context
The owner wants research to progress autonomously through Claude Code cloud routines, with
systematic verification ("verification doubles or triples quality"), and later a preprint.
Cloud sandboxes may refuse direct pushes to `main` (observed on ai-trading-agent), routines have
no `gh` CLI, and a routine session can stop at any time.

## Decision
- Separate maker (worker routine), checker (verifier routine) and lander (GitHub Actions).
- All state in git; branch names and commit subjects are the protocol (`frda autonomy-status`).
- Deterministic gates in code (`frda verify`), mandatory for everyone; agentic review on top.
- Landing only through `verified/*` + `land-verified.yml`, which re-runs the gates and refuses a
  verifier commit touching anything but bookkeeping.
- WIP limit 1 to avoid merge conflicts and to always build on verified work.

## Consequences
- Throughput ≈ one task per day at best; quality over speed. Raise `wip_limit` when tasks get
  independent (e.g. literature vs analysis).
- A verifier can still be wrong: layered checks + human sign-off before publication.
- The hub only shows verified state.
