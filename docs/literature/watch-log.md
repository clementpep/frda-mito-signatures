# Weekly literature watch log

Appended by the weekly watch. One row per new paper: id, title, one-line relevance.

## W-2026-W43 (2026-10-11 → 2026-10-19)
Scope: MED records only, English only (the protocol queries carry `LANG:eng AND (SRC:MED OR SRC:PPR)`, which
removes preprints; see FIX-L002c). Q4 (methods) is not FRDA-specific and is not part of the watch.

Original run 2026-10-19 (`research/search-logs/2026-10-19-watch-w-2026-w43-q*.json`): 0 hits on Q1, Q2, Q3, Q5a, Q5b.
**Corrected 2026-10-31** (same queries, same window, re-run after Europe PMC indexing lag;
`research/search-logs/2026-10-31-watch-w-2026-w43-rerun-q*.json`): Q2 returns 2, the others 0.
Both were first indexed on 2026-10-19, the run day, after the original query ran.

| id | title | relevance | corpus |
|---|---|---|---|
| MED:42878077 | Edited HSPCs rescue frataxin deficiency and inflammation-driven multisystemic pathology in Friedreich's ataxia mice. | FRDA mouse model, gene-edited haematopoietic cells; therapy-oriented, background for L-003 | added, `to_screen` |
| MED:42887212 | Glial-specific mitochondrial failure and redox imbalance contribute to regional vulnerability in Friedreich's ataxia. | mitochondrial/redox biology by cell type in FRDA; background for the mitochondrial signature question | added, `to_screen` |

Preprint arm, without `LANG:eng` (`*-rerun-nolang-q*.json`), not added pending FIX-L002c:
| id | title | relevance |
|---|---|---|
| PPR:PPR1338733 | Autonomic neurons are intrinsically hyperexcitable in a Friedreich ataxia iPSC model | iPSC neurons; hit by Q1 and Q5a |
| PPR:PPR1344364 | Friedreich Ataxia iPSC-derived microglia display an interferon-responsive, antigen-presenting phenotype | iPSC microglia; hit by Q1 and Q2 |

Relevance lines are from titles and the query hit, not from a reading of the full text. Novelty: no overlap with a
claim or lead (no claim, no idea, empty synthesis). Window note: 2026-10-11 → 2026-10-19 spans 9 calendar days.
Sanity check: the same query shape with a wider window (`FIRST_PDATE:[2026-09-01 TO 2026-10-19]`, FRDA terms
only) returned 21 hits on 2026-10-19 and 24 on 2026-10-20: the lag is visible there too.
No saved log exists for the GEO query (count 0, `db=gds`, FRDA/frataxin/FXN, GSE, 2026-10-11 → 2026-10-19; checked
independently by the verifier on 2026-10-20).

## W-2026-W45 (FIRST_PDATE 2026-10-24 -> 2026-11-02, 10-day window overlapping last week for index lag)
Both arms run: protocol arm (`LANG:eng AND (SRC:MED OR SRC:PPR)`) and preprint arm (`SRC:PPR`, amendment A1), Q1, Q2, Q3, Q5a, Q5b
(`research/search-logs/2026-11-02-watch-w-2026-w45-*.json`). Hits: Q1 1, Q2 2, Q5b 1, others 0; preprint arm 0 on all five.
Q4 (methods) is not FRDA-specific and is not part of the watch. Papers added as `to_screen` (corpus 1279 -> 1283):
| id | title | relevance |
|---|---|---|
| MED:42966307 | The Fe-S cluster assembly NFS1-ISD11-FH subcomplex is involved in heme biosynthesis in plants. | Fe-S assembly, frataxin homolog in plants; hit by Q1; background |
| MED:42966764 | In vivo frataxin expression of a triplex purified minicircle. | FXN expression approach; hit by Q2; therapy-oriented background |
| MED:42956153 | Stimulated protein degradation to promote mitochondrial function and neuronal survival. | mitochondrial function; hit by Q2; background |
| MED:42949167 | Intrinsic Activity Reductions and Cerebello-Cortical Diaschisis-Like Mechanism in Friedreich Ataxia: An fALFF Resting-State fMRI Study. | patient imaging; hit by Q5b; RQ5 background |

Relevance lines are from titles and the query hit, not from a reading of the full text. Papers seen by the W-2026-W44 run
(branch `auto/W-2026-W44`, not on main when this run started) are not repeated here; the window start 2026-10-24 does not reach back to them in full.
Novelty: no overlap with a claim or lead (no claim, no idea, empty synthesis).

