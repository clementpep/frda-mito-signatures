---
paper: MED:00000000
read_date: 2026-10-20
read_by: L-004
source_text: full_text            # or abstract_only (non open-access)
question: What the paper asks, in one sentence.
model_system: e.g. primary fibroblasts from FRDA patients and controls
independent_units: e.g. 18 FRDA / 17 controls (donors)
methods: e.g. RNA-seq, DESeq2, FDR < 0.05, |log2FC| > 1
findings:
  - statement: Our one-sentence paraphrase.
    quote: "Exact sentence(s) copied from the paper (word sequence checked by `frda lit-verify`)."
    location: Results, Fig. 2B
limitations:
  - What limits the conclusions (n, design, confounders, model relevance).
datasets: [GSE104288]
relevance_to: [Q1]
leads: []                         # I-xxx ideas this paper suggests (add them as seed in ideas.yaml)
---
## Notes
Free notes: how this paper relates to others in the corpus, what it does not show, what we could test.
