# Literature review protocol (written by task L-001, 2026-10-18; frozen once L-001 has landed)

Like a preregistration, the protocol is written before searching. Once L-001 has landed, changes are
amendments appended at the bottom with date and reason; earlier text is not edited.

## Review questions
- RQ1. What is known about transcriptomic changes in FRDA (patient cells, iPSC-derived cells,
  animal models, tissues), and which of them involve mitochondrial functions?
- RQ2. Which interventions have published molecular (transcriptomic or mitochondrial) readouts in
  FRDA models, and what moved?
- RQ3. Which public datasets exist, what were they used for, and what has not been done with them?
- RQ5. Which molecular measurements in patients (blood, plasma, muscle, other accessible
  tissues) have been studied as FRDA biomarkers, and how did they relate to clinical measures
  (FARS/mFARS, SARA, functional stage, GAA repeat length, age at onset, disease duration,
  cardiomyopathy, diabetes)? Patient-derived evidence is prioritised (RD-002).
- RQ4. Which methods are appropriate for cross-dataset meta-analysis and gene-set testing on
  normalised matrices with few independent units?

## Sources
Europe PMC (includes PubMed and preprints), via `frda lit-search`; search logs saved under
`research/search-logs/`. Citation chasing (references and cited-by of core papers) allowed and logged.

## Queries
Written and size-tested on 2026-10-18 (task L-001) with `frda lit-search "<query>" --max 1 --show 0`
(no search log saved, nothing added to the corpus: the real searches, with saved logs, are L-002).
Europe PMC returns slightly different counts as its index grows: the counts below are the
size estimate at freezing, not an acceptance threshold for L-002.

Shared building blocks (written out in full in each query below, so each is copy-pasteable):
- `FR` = `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN)`.
  `Friedreich*` is required: the exact phrase `"Friedreich"` misses "Friedreich's" (checked: it
  missed Nachun et al. 2018, MED:29790959, which `Friedreich*` finds).
- `Y` = `PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)`
  (PubMed-indexed records and preprints; the year range is narrowed to a window when a query is split).

| Id | Question | Query | Hits (2026-10-18) |
|---|---|---|---|
| Q1 | RQ1 | `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN) AND (TITLE_ABS:transcript* OR TITLE_ABS:"RNA-seq" OR TITLE_ABS:"RNA sequencing" OR TITLE_ABS:"gene expression" OR TITLE_ABS:microarray OR TITLE_ABS:"differentially expressed") AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 370 |
| Q2 | RQ2 | `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN) AND ((TITLE_ABS:transcript* OR TITLE_ABS:"RNA-seq" OR TITLE_ABS:"RNA sequencing" OR TITLE_ABS:"gene expression" OR TITLE_ABS:microarray OR TITLE_ABS:"differentially expressed") OR TITLE_ABS:mitochondri*) AND (TITLE_ABS:treat* OR TITLE_ABS:compound* OR TITLE_ABS:HDAC OR TITLE_ABS:inhibitor* OR TITLE_ABS:therap* OR TITLE_ABS:drug* OR TITLE_ABS:omaveloxolone OR TITLE_ABS:nicotinamide OR TITLE_ABS:"gene therapy") AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 634 |
| Q3 | RQ3 | `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN) AND (TITLE_ABS:GSE* OR TITLE_ABS:"Gene Expression Omnibus" OR TITLE_ABS:"publicly available" OR TITLE_ABS:"public data*" OR TITLE_ABS:reanaly* OR TITLE_ABS:re-analy* OR TITLE_ABS:meta-analys* OR TITLE_ABS:dataset*) AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 32 |
| Q4 | RQ4 | `(TITLE_ABS:"gene set" OR TITLE_ABS:"gene-set" OR TITLE_ABS:"pathway analysis") AND (TITLE_ABS:"small sample*" OR TITLE_ABS:"few samples" OR TITLE_ABS:meta-analys* OR TITLE_ABS:"batch effect*" OR TITLE_ABS:pseudoreplication OR TITLE_ABS:"sample size") AND (TITLE_ABS:transcript* OR TITLE_ABS:"RNA-seq" OR TITLE_ABS:microarray) AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 149 |
| Q5a | RQ5 (blood-type fluids) | `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN) AND (TITLE_ABS:biomarker* OR TITLE_ABS:blood OR TITLE_ABS:plasma OR TITLE_ABS:serum OR TITLE_ABS:PBMC* OR TITLE_ABS:miRNA* OR TITLE_ABS:microRNA*) AND (TITLE_ABS:FARS OR TITLE_ABS:mFARS OR TITLE_ABS:SARA OR TITLE_ABS:GAA OR TITLE_ABS:clinical OR TITLE_ABS:"disease duration" OR TITLE_ABS:"age at onset" OR TITLE_ABS:cardiomyopathy OR TITLE_ABS:patients) AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 299 |
| Q5b | RQ5 (other accessible tissues, imaging) | `(TITLE_ABS:Friedreich* OR TITLE_ABS:FRDA OR TITLE_ABS:frataxin OR TITLE_ABS:FXN) AND (TITLE_ABS:muscle OR TITLE_ABS:biops* OR TITLE_ABS:"cerebrospinal fluid" OR TITLE_ABS:saliva OR TITLE_ABS:buccal OR TITLE_ABS:neurofilament OR TITLE_ABS:MRI OR TITLE_ABS:imaging) AND (TITLE_ABS:FARS OR TITLE_ABS:mFARS OR TITLE_ABS:SARA OR TITLE_ABS:GAA OR TITLE_ABS:clinical OR TITLE_ABS:"disease duration" OR TITLE_ABS:"age at onset" OR TITLE_ABS:cardiomyopathy OR TITLE_ABS:patients) AND PUB_YEAR:[2005 TO 2026] AND LANG:eng AND (SRC:MED OR SRC:PPR)` | 293 |

`CL` (clinical-measure block, written out in full inside Q5a/Q5b) = `(TITLE_ABS:FARS OR TITLE_ABS:mFARS OR TITLE_ABS:SARA OR TITLE_ABS:GAA OR TITLE_ABS:clinical OR TITLE_ABS:"disease duration" OR TITLE_ABS:"age at onset" OR TITLE_ABS:cardiomyopathy OR TITLE_ABS:patients)`.

Known scope limits, accepted before searching (not result-driven): Q5 has no term for diabetes,
functional stage, lymphocytes, leukocytes, fibroblasts, proteomics or metabolomics (a probe
with those terms adds further, partly overlapping hits; not logged); Q1 has no `RNAseq`, `single-cell` or
`expression profil*`. Papers of these kinds are expected to be reached by Q1/Q5 on other terms and by
citation chasing; an amendment may add terms after L-002 if the recall check against core papers shows a gap. RQ5 has two
queries (Q5a, Q5b) so that each stays readable; RQ4 is the only query without `FR`, because
methods papers are rarely FRDA-specific; its hits are screened only for method relevance.

### Splitting rule
A search is screenable when each run screens at most 150 records (cap below). A query with more
than 150 hits is therefore executed in the following **year windows** (the query text is unchanged
except `PUB_YEAR:[2005 TO 2026]` is replaced by the window); each window is its own search log in
L-002 and its records are screened newest window first:

| Query | Windows (hits on 2026-10-18) |
|---|---|
| Q1 (370) | 2024–2026 (56), 2021–2023 (65), 2017–2020 (71), 2012–2016 (98), 2005–2011 (80) |
| Q2 (634) | 2024–2026 (109), 2021–2023 (108), 2017–2020 (129), 2012–2016 (150), 2005–2011 (138) |
| Q5a (299) | 2024–2026 (71), 2021–2023 (49), 2017–2020 (65), 2005–2016 (114) |
| Q5b (293) | 2024–2026 (60), 2021–2023 (50), 2017–2020 (70), 2005–2016 (113) |
| Q3 (32), Q4 (149) | not split |

Windows are sized at the freezing date; a window that grows above 150 is screened over two
runs (task split, criteria unchanged). Total before deduplication: 1,777 hits; the queries
overlap (e.g. the three seed papers are each found by 1–5 queries), so the deduplicated corpus
will be smaller. Pre-2005 records (65 FRDA transcript hits) are outside the date range and enter
only through citation chasing (below) when a core paper cites them.

### Citation chasing
Allowed and logged (`frda lit-citations`, saved logs) for relevance-3 papers and dataset papers;
resolved ids are screened like search hits, with the same criteria.

### Seeds
Added explicitly in L-002 with `found_by: seed`, outside the queries: MED:29125828 (Napierala 2017),
MED:33028632 (Vilema-Enríquez 2020), the Maddock et al. 2026 preprint (Europe PMC id resolved in
L-002), and MED:29790959 (Nachun 2018, the source paper of GSE102008, RD-002) — the last was
verified to exist in Europe PMC on 2026-10-18 and is found by Q1 and Q5a anyway.

## Eligibility
Applied at title/abstract screening; each decision cites the criterion code in `screen_reason`.

Inclusion
- I1. Primary research, preprint, or dataset/resource paper reporting original molecular data
  (transcriptome, proteome, miRNA, mitochondrial function or biomarker measurement) in FRDA or
  frataxin-deficient systems — or, for RQ5, patient-derived measurements related to clinical
  measures.
- I2. Reviews and meta-analyses of FRDA molecular or biomarker data: eligible as background and
  for citation chasing; capped at relevance 2 (their primary studies carry the evidence).
- I3. Methods papers (Q4 only) on gene-set testing, batch handling or cross-dataset meta-analysis
  with few independent units, when the method is applicable to normalised expression matrices.
- I4. Models: human patient cells and tissues; iPSC-derived and other cell models; mouse and other
  animal models (e.g. YG8R, KIKO, conditional knockouts); non-mammalian models are eligible but
  capped at relevance 2.
- I5. English; published 2005–2026 (older records only via citation chasing).

Exclusion (first matching reason is recorded)
- E1. No FRDA or frataxin-deficiency link (except Q4 methods papers).
- E2. No molecular, omics or biomarker measurement (e.g. purely clinical-trial efficacy, imaging
  without a molecular or clinical-biomarker link, rehabilitation, quality of life) — unless it reports a
  patient biomarker related to a clinical measure (RQ5).
- E3. Case report of one or two patients without a transcriptomic or biomarker readout.
- E4. Editorial, comment, letter without data, conference abstract without data, retraction notice.
- E5. Not in English or outside 2005–2026 and not reached through citation chasing.
- E6. Duplicate of another record (same DOI, or preprint whose published version is in the corpus —
  keep the published version, note the preprint id).

Controlled-access data, identifiable data and data under terms that forbid processing with an AI
assistant are never ingested from a paper, whatever its relevance (P5.2).

### Relevance scale (0–3)
- 0 — Excluded by an E-criterion or unrelated.
- 1 — Context only: FRDA molecular or biomarker topic, but no reusable data, result or method for
  this project (background, narrow single-gene studies, non-mammalian models).
- 2 — Informs the project: transcriptomic or mitochondrial findings in FRDA models or patients,
  intervention readouts, other patient biomarkers, applicable methods.
- 3 — Core: reports or re-uses a public FRDA dataset (GSE104288, GSE145115, GSE102008, other
  patient cohorts), reports a mitochondrial signature or module in FRDA, or directly bears on a
  registered claim or task; a patient-cohort study relating molecular measures to clinical measures
  (functional stage, GAA length, onset, duration) also scores 3 (RD-002). The seed papers are added
  with `found_by: seed` but are scored by these criteria like any record.

## Screening
Title/abstract screening of every hit; each decision recorded in `research/corpus.yaml`
(`status`, `screen_reason`, `relevance` 0–3, `topics`). Counts kept in `research/screening.md`
(PRISMA-style flow). One screener per run; the verifier re-screens a random sample of 10
decisions. Per-run cap: **150 records screened**. Criteria are not edited while screening; a
needed change is an amendment below.

## Reading
Priority rule, in this order:
1. relevance 3, then relevance 2;
2. within a relevance level, **patient-derived evidence first** (RD-002: blood, PBMC, muscle,
   plasma/serum cohorts with clinical measures; such cohorts reach relevance 3, see scale), then dataset papers, then animal and cell-model
   papers;
3. then the more recent paper first, ties broken by smaller PMID/PPR id.

One card per paper (`research/cards/_TEMPLATE.md`), quotes verbatim with location;
`source_text: abstract_only` when the full text is not open access. Reviews (capped at relevance 2) may be read in the first batch when they are the most
cited background of the core papers; this is the one exception to rule 1, and L-004 names them.
Per-run cap: **6 cards**
(as `routines/playbooks/literature.md`). Relevance 1 papers are not read.

## Synthesis
`research/synthesis/` — themed chapters; every statement cites `[@SRC:ID]` of a read paper.

## Amendments

### A1 — 2026-10-28 — preprints are in scope (owner decision)
Reason: `LANG:eng` removes every Europe PMC preprint record, so the `SRC:PPR` part of `Y` retrieves
nothing (L-002 run: 49 preprint hits for 2024–2026 without `LANG:eng`, 0 with it; non-blocking
finding of verification L-002-bd88fc5 and question 2 of the October report, both on branches
`auto/L-002` and `auto/W-2026-W44` at the time).
Decided by the owner on 2026-10-28, before any screening (L-003 not started).
Change (L-002 landed on 2026-10-30 without it; the preprint arm is task L-002b, before screening
L-003; confirmed by the owner in RD-003):
- each query Qx above is also run as a **preprint arm** `Qx-ppr`: the same text with
  `LANG:eng AND (SRC:MED OR SRC:PPR)` replaced by `SRC:PPR`, same year windows; its search log is
  saved separately (slug suffix `-ppr`). The PubMed arm (query text above) is unchanged;
- preprint-arm hits enter the corpus as for any query (`frda lit-add`, `to_screen`, `kind: preprint`);
- screening criteria are unchanged: I5/E5 (English) are applied at screening, E6 keeps the
  published version when both exist; cards and synthesis say "preprint, not peer-reviewed";
- the weekly watch (`routines/watch.md` STEP 3) runs both arms.
