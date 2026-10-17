---
task: T-025
reviewed_sha: ae89fbd8473c8298855399dd584a64ba85159162
verdict: CHANGES_REQUESTED
date: 2026-10-17
attempt: 1
summary: GEO facts exact, but a "27-gene panel" is attributed to the paper, mitochondrial prior evidence is omitted, and cohort counts are not reconciled; RD-002 also needs owner landing.
gates: {lint: PASS, test: PASS, verify: PASS, reproduce: PASS}
acceptance_met: 3/4
recomputed:
  - "GSE102008 GEO: 733 GSM, GPL10558, Patient 411 / Carrier 228 / Control 94, site CHOP 568 / UCLA 165: backlog and RD-002 numbers identical"
  - "GSE102008 GEO: onset 407, gaa1 376, gaa2 357, duration 407, functional stage 334, all on Patients: identical to T-026 notes"
  - "PMID 29790959 = Nachun et al., Hum Mol Genet 2018 (Europe PMC): identical"
blocking_findings: 3
---
# Verification of T-025 (attempt 1)

## Scope and tampering check
Diff: backlog, project.yaml, brief, PLAN, protocol, RD-002, run report, hub summary. No change to gates,
tests, `.github/`, `routines/`, `scripts/`, `Makefile`, allowlist. No criterion removed or softened
(T-010 swaps leave-one-donor-out for resampling stability, n>700; T-008 drops `depends_on: [T-006]`:
confirm intended). STEP 3 rule: outside a W branch, a change under `research/decisions/` and a pivot
are blocking. RD-002 is `needs_human: true`, stated as the owner's decision. The branch cannot prove
that decision (the run payload is data), so the owner must confirm it when this lands.

## Gates (fresh data, re-downloaded, sha256 OK)
lint PASS; test 191 passed; verify --require-data PASS; reproduce PASS (P-001).

## Acceptance criteria
| # | Criterion | MET / NOT MET | Evidence checked |
|1| RD-002 states facts, question, scope, consequences | NOT MET | contains a fact not supported by the paper (B1) and omits prior mitochondrial evidence (B2) |
|2| PLAN, project.yaml, protocol RQ5, brief say the same | MET | diff read |
|3| Backlog updated, T-026..T-030, numbers traceable and marked to re-derive | MET (with B3 to fix in T-026/T-028) | GEO re-probe: every number matches |
|4| No gate/rule weakened | MET | diff |

## Independent recomputation
GEO series matrix header parsed with plain Python (my first parse was misaligned; the per-sample parse
gives the exact numbers above). Europe PMC abstract and PMC6097013 full text read.

## Findings
### Blocking
1. "The published analysis reports an inflammatory 27-gene panel" (RD-002 Context) and "the 27-gene panel
   and its direction" (T-027) are not in the paper. The Europe PMC abstract and full text
   (PMC6097013) have no such panel; the phrase comes from the GEO series summary, which is a different
   text. The only "27" in the paper is "mitochondrial translation (27 genes, log BF = 4.44)". The paper
   reports 829 transcripts DE patients vs controls (FDR 0.012), 1078 patients vs carriers, 182 carriers
   vs controls. Fix: attribute the panel to the GEO summary only, or remove it; base T-027 examples on
   the paper's own results (829/1078/182, FDS-associated genes, module enrichments).
2. RD-002 says the analysis "is not mitochondria-focused". The paper itself reports mitochondrial
   modules (respiratory chain complex, 20 genes, log BF 1.89; mitochondrial translation, 27 genes,
   log BF 4.44). Add this as prior published evidence in RD-002; T-027 gets a mitochondrial-module
   target; T-010 and T-029 require a `novelty_check` against it before any "new" claim.
3. Cohort counts differ: paper 739 subjects, patients 418 / carriers 228 / controls 93 (Europe PMC);
   GEO 733 GSM, 411 / 228 / 94. RD-002 quotes the GEO counts next to the paper. T-026 and T-028 must
   report the discrepancy, state that the paper's exclusion rule (low frataxin) cannot be applied from
   GEO, and write the expected gap before reproducing.
### Non-blocking (added to the backlog as FIX-T025 notes, status proposed)
- Age/status/relatedness confounding (paper Table 1 mean age 25 / 50 / 37; carriers mostly parents);
  covariates collinear with age; state the estimand and age-matched subsets (T-028/T-029).
- Site x status feasibility condition for the held-out site split, with a fallback (T-029).
- A site split is internal validation, not independent replication: M3 title/exit criteria should say so.
- T-028: state which matrix (series vs non-normalised) and normalisation; link the 1299 vs 733 gap.
- T-029: two-sided trend test; pin the gene-set source and version (e.g. MitoCarta).
- RD-002 says the probe is "saved by T-026 as an artifact"; the run report says not saved: align wording.
- Confirm that dropping T-008 `depends_on: [T-006]` is intended.

## Verdict and what happens next
CHANGES_REQUESTED, 3 blocking, all in documentation of facts, not in the numbers. RD-002 and PLAN are
supervision-owned paths (STEP 3): the owner's interactive session should make these fixes and confirm
RD-002 is their decision, since a worker may not edit `research/decisions/`.
