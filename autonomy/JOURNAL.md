# Autonomy journal

There is no shared append-only log (it would conflict between branches). The history is:
- `git log --first-parent main` — one `land(T-xxx)` merge per verified task;
- `autonomy/runs/` — one report per worker/watch run;
- `autonomy/verifications/` — one report per verification;
- `autonomy/digests/` — weekly summaries.

2026-10-16 — bootstrap: repository, gates, routines and research backlog created in an
interactive session with the owner.
