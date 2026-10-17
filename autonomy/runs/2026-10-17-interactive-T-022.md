---
routine: interactive (owner session)
task: T-022
date: 2026-10-17
branch: auto/T-022
---
# T-022 — Wider sources

Requested by the owner: assess the GitHub list public-apis for this project, then integrate what
is useful (owner set the OPENALEX_API_KEY environment secret).

## Assessment (summary)
public-apis is a directory; ~15 entries are relevant. Probed live from the routine environment:
OpenAlex (works with the key: 49 works cite MED:29125828), Semantic Scholar (works, licence
agreement to assess), Crossref and Unpaywall (CC-BY of Napierala 2017 confirmed), MyGene.info
(FXN → ENSG00000165060), Open Targets (FRDA = MONDO_0100339), ENA (raw reads: 157.5 GB for
GSE104288, 62 GB for GSE145115 — too large for a session). Outside the list, recount3 hosts
raw gene coverage sums for GSE104288 (SRP118922, 35 runs, 63,856 genes); none for GSE145115.
Only OpenAlex's terms could be read and quoted now (CC0, openalex-docs README); the others go to
T-023 (terms first, then allowlist). KEGG avoided (redistribution limits).

## What was done
- allowlist: openalex (terms quoted).
- `frda.literature.citations` + `frda lit-citations` (cited-by with cursor paging; references in
  batches of 50); works resolved to Europe PMC ids by PMID, else DOI search; unresolved listed;
  key from the environment, `mailto` set, key redacted from errors.
- Manifests: `column_map`, `comment_prefix`; `frda.io.read_manifest_file` used by `load_matrix`
  and the data_integrity gate (messages now prefixed by file name).
- verifier.md: non-blocking findings → proposed follow-up task; procedures P5.7 secrets;
  playbook: citation chasing section and commands.
- T-021 follow-ups: literal U+E000 in source neutralised; lit-verify scope stated (docstring,
  card template).
- Backlog: T-022 (this), T-023 (terms + recount3 manifest), note on T-004.

## Self-verification
- `make ci` PASS (80 tests), `make reproduce` PASS.
- Online in a scratch copy: `lit-citations MED:29125828 --direction cited-by` → 49 works,
  44 resolved, 5 unresolved; `--direction references` → 65 works, 65 resolved; no key in logs.
