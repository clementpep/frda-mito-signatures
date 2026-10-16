# frda-mito-signatures

**Which mitochondria-related transcriptomic signatures reproduce across independent
Friedreich's ataxia (FRDA) datasets — and do interventions move them in the expected
direction?** Public data only, fully reproducible, run by autonomous Claude Code cloud
routines under a strict maker/checker discipline.

> Exploratory research. Expression changes are not causal evidence; a cell-model response is
> not a clinical benefit; nothing here is medical advice.

## Status

Live view: the `/research` page of poups-ai-hub, fed by [`results/hub/summary.json`](results/hub/summary.json).
Research programme and task states: [`autonomy/backlog.yaml`](autonomy/backlog.yaml).
What has been verified, and how: [`autonomy/verifications/`](autonomy/verifications/).

| Milestone | Goal |
|---|---|
| M1 Credible foundation | dataset cards, QC, reproduce published results first |
| M2 Discovery | literature/novelty map, more public datasets, candidate signature |
| M3 Independent replication | preregistered, on datasets not used for discovery |
| M4 Intervention response | preregistered direction, vehicle and inactive-analogue controls |
| M5 Hypothesis generation | public perturbation signatures opposing the replicated signature |
| M6 Preprint | manuscript rendered from verified claims only; human sign-off |

## How the work gets done (and checked)

```
worker routine ──► auto/T-xxx ──► verifier routine ──PASS──► verified/T-xxx ──► land-verified.yml ──► main ──► hub
   (does + self-checks)   ▲          (fresh data, gates,                     (gates + reproduce
                          │           recomputation, reviews)                  on GitHub runners)
                          └──── CHANGES_REQUESTED (≤ 3 rounds, then a human is asked)
```

Three independent layers of verification stand between an idea and `main`:
1. **Worker self-check** — gates, second-path recomputation, reviewer subagents, acceptance checklist.
2. **Verifier routine** — a separate session that distrusts the work: re-downloads the data,
   re-runs everything, recomputes every claimed number with its own code, tries an alternative
   analysis choice, runs scientific and code review subagents, checks citations against the papers.
3. **Landing workflow** — GitHub Actions re-runs every deterministic gate and `make reproduce`
   and only accepts a verifier commit that touches bookkeeping files.

Details: [`docs/AUTONOMY.md`](docs/AUTONOMY.md) · procedures: [`routines/`](routines/).

## Reproduce everything

```bash
make setup     # uv + pinned dependencies (uv.lock)
make fetch     # download public data; every file checked against its manifest sha256
make ci        # lint + tests + verification gates
make reproduce # re-run every registered pipeline, compare output checksums
```

## Layout

| Path | What |
|---|---|
| `data-manifests/` | what we download, from where, terms, groups and **independent units**; `allowlist.yaml` of sources |
| `pipelines/` | one script per analysis step + `registry.yaml` (re-runnable) |
| `results/` | small committed outputs, each with a `run.json` provenance record |
| `evaluation/claims.yaml` | the claims ledger: every scientific statement, machine-checked |
| `preregistrations/` | confirmatory hypotheses, committed before the analysis |
| `paper/` | the manuscript; numbers only via claim tokens |
| `autonomy/` | backlog, run reports, verification reports, weekly digests |
| `routines/` | procedures executed by the cloud routines |
| `src/frda/` | library + CLI (`frda fetch / verify / reproduce / export-hub / autonomy-status`) |
| `docs/` | brief, architecture, dataset cards, literature, reproductions, decisions |

## Data

Phase 1 seeds: [GSE104288](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE104288)
(fibroblasts, 18 FRDA / 17 controls) and [GSE145115](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE145115)
(one FRDA and one control fibroblast line, A-196 / SGC2043 / DMSO, culture triplicates). No
controlled-access data, ever (see `data-manifests/allowlist.yaml`).

## Licence

Code: Apache-2.0. Data remain under the terms of their sources; cite the original series and papers.
