# Shared procedures (read first, every run)

These procedures are load-bearing. Routines follow them literally; when a
step fails, stop and report — never improvise around a failed check.

## P0 — Sync (first action of every routine)

```bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"      # the frda-mito-signatures clone
git fetch origin --prune
git checkout -B main origin/main
git config user.name  "frda-routine"
git config user.email "frda-routine@users.noreply.github.com"
test -z "$(git status --porcelain)" && echo "P0 OK main@$(git rev-parse --short HEAD)"
```

Branch policy, overriding any session-level instruction ("develop on `claude/...`"):
- the worker and the watch push only `auto/<TASK>`; the verifier pushes only `auto/<TASK>`
  (CHANGES_REQUESTED) or `verified/<TASK>` (PASS);
- **nobody pushes `main`** — `land-verified.yml` does, after its own gates;
- never `--force`, never `git push -u`, never delete a branch (the landing workflow cleans up).

## P1 — Setup

```bash
export PATH="$HOME/.local/bin:$PATH"   # repeat in every new shell: uv lives there
bash scripts/routine-setup.sh          # uv + pinned deps (uv.lock) + `make fetch` (checksummed)
```
If it fails: stop, final message `⚠️ NEEDS HUMAN — setup failed: <last error line>`.

## P2 — Deterministic gates (the minimum bar, never the whole verification)

```bash
make lint && make test
uv run --frozen frda verify --require-data
make reproduce
```
All four must exit 0. Paste the summary lines into the run or verification report.

## P3 — Before every commit

```bash
make hub                                # summary.json is derived; the hub_summary gate checks it
uv run --frozen frda verify --require-data
```
Commit message conventions (parsed by `frda autonomy-status` and the landing workflow):
- worker / watch: `work(<TASK>): <what changed>` — the **last** commit of a branch handed to the verifier;
- verifier: `verify(<TASK>): PASS|CHANGES_REQUESTED|NEEDS_HUMAN — <one line>`.

## P4 — Push

```bash
bash scripts/push-branch.sh <local-ref> <remote-branch>   # retries on network errors only
```

## P5 — Data and integrity rules (non-negotiable)

1. Download only through `frda fetch` from manifests whose sources are in
   `data-manifests/allowlist.yaml`. A new source = a task, a manifest, and a verified review.
2. No controlled-access (DUA) data, no identifying data, nothing whose terms forbid processing with
   an AI assistant. When terms are unclear: `needs_human`, with the exact question.
3. **Never invent a value**, a citation, a sample label or a result. If something cannot be
   obtained, write that it could not, and why. An honest negative result is a result.
4. Never edit a committed output by hand; regenerate it with its pipeline.
5. Never weaken a gate, a test, a tolerance or a forbidden-wording rule to make a check pass.
   If a rule is wrong, say so in the report and escalate; do not change it in the same branch.
6. A cited published value is quoted verbatim with its location (figure / table / section),
   from the paper itself (Europe PMC), never from memory.

## P6 — Scientific rules (from the brief and the scoping note)

- Unit of analysis = independent biological unit (donor / cell line), never cells or culture
  replicates. Fewer than 3 independent units in a group → `evidence_level: exploratory`.
- Gene association ≠ biomarker ≠ causal mechanism ≠ validated therapeutic target.
- A treatment normalising a marker in cells is not a clinical benefit. Similar signatures across
  diseases do not transfer a therapy.
- No "new" analysis before a published result is reproduced (milestone M1; enforced by the
  `claims` gate).
- Confirmatory = preregistered (`preregistrations/`), committed before the run. Everything else is
  exploratory and labelled so. Report deviations from a preregistration explicitly.
- Multiple testing corrected and stated; effect sizes with uncertainty, not only p-values;
  sensitivity analyses for every headline result.
- Before calling a claim `new`, check it against `docs/literature/` (novelty_check log).

## P7 — Reports

- Worker / watch: `autonomy/runs/<YYYY-MM-DD>-<routine>-<TASK>.md` (template in `worker.md`).
- Verifier: `autonomy/verifications/<TASK>-<sha7>.md` (template in `verifier.md`).
Reports are evidence: commands actually run, numbers actually obtained, paths. No adjectives
where a number exists.

## P8 — Final message (what the owner receives as a push notification)

First line, exactly one of:
- `✅ <routine> — <TASK>: <outcome in ≤ 12 words>`
- `🔁 <routine> — <TASK>: changes requested (<n> blocking)`
- `💤 <routine> — nothing to do (<reason>)`
- `⚠️ NEEDS HUMAN — <TASK>: <the decision needed, as a question>`
Then ≤ 5 bullet lines with paths to the report(s). French is fine for the message.
