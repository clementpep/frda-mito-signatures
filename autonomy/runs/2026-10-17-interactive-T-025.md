# Run report — T-025 (interactive session, 2026-10-17)

Owner request: "il faut que ce travail ait du sens, donc analyser proprement des examens faits sur
des patients pour aider la commu scientifique ! Pas juste faire des hypothèses théoriques."

## What was checked live (GEO E-utilities and acc.cgi, Europe PMC; not saved as artifacts here)
- Human FRDA series in GEO (esearch db=gds, "friedreich ataxia OR friedreich's ataxia OR
  frataxin", gse, Homo sapiens): 35 series; patient-derived ones with clinical annotations include
  GSE102008, GSE30933, GSE243874, GSE226646, GSE105052, GSE200907.
- GSE102008 GSM characteristics: 733 samples, GPL10558, status Patient 411 / Carrier 228 /
  Control 94, one GSM per pidn, site CHOP 568 / UCLA 165; onset and duration 407, gaa1 376, gaa2
  357, functional stage 334. Series pubmed_id 29790959 = Nachun et al. 2018, Hum Mol Genet
  (Europe PMC). Series matrix 82 MB, non-normalised supplementary file 400 MB.
- These figures are written in RD-002 and the T-026/T-008 notes as facts to re-derive and save
  as artifacts by those tasks, not as results.

## Changes
- RD-002 (pivot, owner decision): patients first.
- PLAN.md research question, project.yaml hub questions, protocol RQ5, brief addendum.
- Backlog: M1/M3 wording; T-026–T-030 added; T-008, T-010 re-scoped; T-003 priority 2; L-001 note.

## Checks
`make ci` 191 passed, verify PASS; `frda autonomy-status`: next worker task L-001.

## Attempt 2 (after autonomy/verifications/T-025-ae89fbd.md, CHANGES_REQUESTED, 3 blocking)

Owner's session (this one) fixed the supervision-owned files, as the report asks; RD-002 now quotes
the owner's request and says who wrote the record.

Re-read of the full text (Europe PMC PMC6097013, fullTextXML, 2026-10-17), quotes checked:
- B1: the "27-gene panel" is in the GEO series summary only; the paper's "27 genes" is the
  mitochondrial translation module. RD-002 says so; T-027 targets come from the paper (DE counts
  829 / 1078 / 182 with their global FDR, a mitochondrial module enrichment, a progression or
  GAA1 association if reported).
- B2: the paper's mitochondrial modules (respiratory chain complex, 20 genes, log BF = 1.89;
  mitochondrial translation, 27 genes, log BF = 4.44) are recorded in RD-002 as prior evidence;
  T-010, T-029 and T-030 require a comparison or novelty check against them.
- B3: paper Table 1 (739 subjects: 418 / 228 / 93; 2 of 95 controls excluded for low blood
  frataxin) vs GEO (733 GSM: 411 / 228 / 94; 1299 run): T-026, T-027 and T-028 must reconcile or
  report the gap, and the frataxin exclusion is stated as not applicable from GEO.
- Non-blocking items written into the tasks directly (see FIX-T025 note). Dropping
  `depends_on: [T-006]` from T-008 is intended: a dataset census does not need the gap analysis,
  and the patient line needs it early.
- Wording aligned: the probe is not saved as an artifact here; T-026 and T-008 re-derive and save it.
