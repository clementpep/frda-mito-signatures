# CLAUDE.md

Guidance for Claude Code (interactive sessions and cloud routines) in this repository.

## What this is

An open, reproducible research project on Friedreich's ataxia (FRDA): mitochondria-related
transcriptomic signatures from **public data only**, aiming at an open **preprint** with
preregistered, independently replicated findings. Most of the work is done by three cloud
routines (`routines/`); a human owner steers through the backlog and signs off on publication.

Read before working: `docs/PROJECT_BRIEF.md` (scope), `routines/procedures.md` (rules P0–P8),
`docs/AUTONOMY.md` (the loop), `research/PLAN.md` (the thesis plan: phases, effort tracks,
how ideas are arbitrated), `autonomy/backlog.yaml` (what to do next).

## Commands

```bash
export PATH="$HOME/.local/bin:$PATH"
make setup          # uv sync --frozen (deps pinned in uv.lock)
make fetch          # download manifest files, verify sha256
make ci             # lint + test + verify (gates)
uv run --frozen frda verify --require-data   # gates, failing if data is absent
make reproduce      # re-run registered pipelines, compare output hashes
make hub            # regenerate results/hub/summary.json (do it before every commit)
make status         # auto/* and verified/* branch states
uv run --frozen frda task T-004              # print one task
uv run --frozen frda research-status         # phase, budgets, corpus, ideas
uv run --frozen frda lit-search "<q>" --save slug --task L-002   # Europe PMC, logged
uv run --frozen frda lit-add MED:29125828 --task L-002            # corpus (resolved ids only)
uv run --frozen frda lit-verify               # papers exist, card quotes verbatim (online)
```

## Non-negotiable rules

1. **Never invent data, values, citations or sample labels.** Can't obtain it → say so.
2. Public data only, from `data-manifests/allowlist.yaml` sources, via manifests with sha256.
3. Statistics on **independent units** (donors / cell lines), never on culture replicates.
   GSE145115 has one FRDA line and one control line: everything there is exploratory.
4. No causal, clinical or therapeutic wording in claims (enforced by the `claims` gate).
5. Reproduce published results (M1) before any "new" claim (enforced).
6. Confirmatory analyses are preregistered in `preregistrations/` and committed first (enforced).
7. Never weaken a gate, test or tolerance to get green. Fix the work, or escalate.
8. Nothing reaches `main` except through `verified/*` + `land-verified.yml`. Interactive
   sessions follow the same branch protocol unless the owner says otherwise.

## Conventions

- Python ≥ 3.12, ruff (line 100), pytest. Library code in `src/frda/`, analysis in `pipelines/`.
- Pipelines: `pipelines/pNNN_slug.py --out DIR`, data via `frda.io`, outputs via
  `frda.provenance.write_json` + `write_run`, registered in `pipelines/registry.yaml`.
- Every scientific statement is a claim in `evaluation/claims.yaml`; docs, hub and manuscript
  render from claims. The manuscript uses tokens (`paper/README.md`).
- Commits: `work(T-xxx): …` (worker), `verify(T-xxx): PASS|CHANGES_REQUESTED|NEEDS_HUMAN — …`
  (verifier), `land(T-xxx): …` (landing workflow).
- Repository content is in English (open science); routine final messages may be in French.

## Hub integration

`results/hub/summary.json` (contract: `docs/HUB_CONTRACT.md`, `schema_version`) is read by
poups-ai-hub's `/research` page from the public raw GitHub URL. Changing its shape = bump
`SCHEMA_VERSION` in `src/frda/hub.py` and update the hub's zod schema.
