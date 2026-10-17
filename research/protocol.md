# Literature review protocol (draft — finalised and frozen by task L-001)

Like a preregistration, the protocol is written before searching. Once L-001 lands, changes are
amendments appended at the bottom with date and reason; earlier text is not edited.

## Review questions
- RQ1. What is known about transcriptomic changes in FRDA (patient cells, iPSC-derived cells,
  animal models, tissues), and which of them involve mitochondrial functions?
- RQ2. Which interventions have published molecular (transcriptomic or mitochondrial) readouts in
  FRDA models, and what moved?
- RQ3. Which public datasets exist, what were they used for, and what has not been done with them?
- RQ4. Which methods are appropriate for cross-dataset meta-analysis and gene-set testing on
  normalised matrices with few independent units?

## Sources
Europe PMC (includes PubMed and preprints), via `frda lit-search`; search logs saved under
`research/search-logs/`. Citation chasing (references of core papers) allowed and logged.

## Queries
To be written in L-001 (one per RQ), tested for size, and frozen.

## Eligibility
To be written in L-001: inclusion / exclusion criteria (language, years, article types, models).

## Screening
Title/abstract screening of every hit; each decision recorded in `research/corpus.yaml`
(`status`, `screen_reason`, `relevance` 0–3, `topics`). Counts kept in `research/screening.md`
(PRISMA-style flow).

## Reading
Priority: relevance 3, then 2. One card per paper (`research/cards/_TEMPLATE.md`), quotes verbatim
with location; `source_text: abstract_only` when the full text is not open access.

## Synthesis
`research/synthesis/` — themed chapters; every statement cites `[@SRC:ID]` of a read paper.

## Amendments
