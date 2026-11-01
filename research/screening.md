# Screening flow (PRISMA-style)

Maintained by literature tasks. Counts must match `research/corpus.yaml`.

| Step | n |
|---|---|
| Records identified (all search logs, deduplicated) | 1277 |
| Excluded at title/abstract | 0 |
| To read | 0 |
| Read (cards) | 0 |

(`to_screen` = 1277; L-003 screens them.)

## Identification, per search log (L-002, 2026-10-19)

Queries executed verbatim from `research/protocol.md` (only the `PUB_YEAR` window changes).
"New" = added to the corpus by this search (first finder, in execution order, after the 4 seeds);
"already" = already in the corpus from an earlier search or seed, or merged by DOI.

| Search log | Hits | Retrieved | New | Already |
|---|---|---|---|---|
| q1-2005-2011 | 80 | 80 | 80 | 0 |
| q1-2012-2016 | 98 | 98 | 98 | 0 |
| q1-2017-2020 | 71 | 71 | 69 | 2 |
| q1-2021-2023 | 65 | 65 | 65 | 0 |
| q1-2024-2026 | 56 | 56 | 56 | 0 |
| q2-2005-2011 | 138 | 138 | 95 | 43 |
| q2-2012-2016 | 150 | 150 | 88 | 62 |
| q2-2017-2020 | 129 | 129 | 83 | 46 |
| q2-2021-2023 | 108 | 108 | 61 | 47 |
| q2-2024-2026 | 109 | 109 | 70 | 39 |
| q3 | 32 | 32 | 18 | 14 |
| q4 | 149 | 149 | 149 | 0 |
| q5a-2005-2016 | 114 | 114 | 77 | 37 |
| q5a-2017-2020 | 65 | 65 | 45 | 20 |
| q5a-2021-2023 | 49 | 49 | 30 | 19 |
| q5a-2024-2026 | 71 | 71 | 50 | 21 |
| q5b-2005-2016 | 113 | 113 | 55 | 58 |
| q5b-2017-2020 | 70 | 70 | 39 | 31 |
| q5b-2021-2023 | 50 | 50 | 23 | 27 |
| q5b-2024-2026 | 60 | 60 | 22 | 38 |

Total retrieved before deduplication: 1777 (equal to the 1,777 announced in the protocol);
corpus after deduplication: 1277 = 4 seeds + 1273 found by queries.
Seeds: MED:29125828, MED:33028632, PPR:PPR1219382 (Maddock et al. 2026 preprint, id resolved by an
Europe PMC author/year search), MED:29790959. Three of the four are also retrieved by queries
(PPR:PPR1219382 is retrieved by none of the 20 searches; MED:33028632 only by Q5a, not by Q2 or Q1).
One retrieved record was not added as its own entry: MED:17235301 (Q2 2005-2011) shares its DOI
(10.1038/sj.mt.6300021) with MED:28182935, already in the corpus — merged by `lit-add`'s DOI rule.

Note: `found_by` in the corpus records only the first search (in execution order) that returned a
paper; overlap between searches is in the search logs themselves (e.g. MED:29125828 is returned by
5 searches). 10 records have no DOI, so the DOI-merge rule cannot dedupe them: L-003 checks
preprint/published pairs among them under E6.

Recall defect found while reviewing (not patched here, the protocol is frozen): every query carries
`LANG:eng`, and Europe PMC preprint records have no language field, so the `SRC:PPR` arm of
Q1–Q5b returns 0 records. Re-query on 2026-10-19: `SRC:PPR AND (Friedreich* OR frataxin) AND
PUB_YEAR:[2024 TO 2026]` = 49 hits; the same with `AND LANG:eng` = 0. The corpus therefore holds
no preprint except the Maddock seed (PPR:PPR1219382, a systematic review and meta-analysis: not
primary data). A protocol amendment (drop `LANG:eng` for `SRC:PPR`, or run a preprint arm) is needed
before L-003 treats the search as complete.
