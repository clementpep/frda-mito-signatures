# Weekly watch log

One entry per weekly run: papers found by the protocol queries (`research/protocol.md`) over the
window stated, added to the corpus as `to_screen`. Relevance lines are taken from titles only;
screening (L-003) decides inclusion.

## W-2026-W44 (run 2026-10-26)
Window: FIRST_PDATE 2026-10-11 → 2026-10-26 (15 days, overlapping the previous week to cover
Europe PMC index lag, see FIX-watch-lag). Logs: `research/search-logs/2026-10-26-watch-w-2026-w44-*.json`.
Protocol queries (with `LANG:eng AND (SRC:MED OR SRC:PPR)`) return no preprints; a separate preprint
arm (same queries, `SRC:PPR` instead, no `LANG:eng`) is logged with the `-ppr` suffix.

| Id | Title | Found by | Relevance (from title) |
|---|---|---|---|
| MED:42878077 | Edited HSPCs rescue frataxin deficiency and inflammation-driven multisystemic pathology in Friedreich's ataxia mice. | Q2 | Mouse model, gene-edited cell intervention; RQ2 |
| MED:42887212 | Glial-specific mitochondrial failure and redox imbalance contribute to regional vulnerability in Friedreich's ataxia. | Q2 | Mitochondrial changes by cell type/region; RQ1 |
| MED:42909834 | Ataxia Therapeutics: A Comprehensive Overview of the Clinical Development Pipeline. | Q5a | Review of ataxia therapies; background for RQ2 |
| MED:42921272 | Neurodegenerative Diseases: Epidemiology, Risk Factors, Classification, Pathophysiology, Clinical Features, Diagnosis, and Therapeutic Strategies. | Q2, Q5a | General neurodegeneration review; likely out of scope, screening decides |
| PPR:PPR1338733 | Autonomic neurons are intrinsically hyperexcitable in a Friedreich ataxia iPSC model | Q1-ppr, Q5a-ppr | iPSC model, electrophysiology; RQ1 |
| PPR:PPR1344364 | Friedreich Ataxia iPSC-derived microglia display an interferon-responsive, antigen-presenting, and inflammasome-associated state with lysosomal biology and extracellular matrix abnormalities | Q1-ppr, Q2-ppr | iPSC microglia, expression-level states; RQ1 |

Hit counts (window above): MED arm Q1 0, Q2 3, Q3 0, Q5a 2, Q5b 0; preprint arm Q1 2, Q2 1, Q3 0, Q5a 1, Q5b 0.
6 unique records added (4 MED, 2 preprints). The two MED:42878077 / MED:42887212 records were
first indexed 2026-10-19 and are the ones the W-2026-W43 run (window to 2026-10-19) missed.
