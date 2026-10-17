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
