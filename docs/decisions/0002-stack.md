# ADR 0002 — Python stack, uv, normalised matrices

Date: 2026-10-16 · Status: accepted

- Python 3.13 with numpy/pandas/scipy/statsmodels; pinned by `uv.lock`; `uv sync --frozen` in
  routines and CI so every run uses the same versions. No R in the cloud image: if a method needs
  R/Bioconductor (e.g. limma), a task must first justify it and add it reproducibly.
- The seed GEO series only publish **normalised** matrices (no raw integer counts): count models
  (DESeq2/edgeR) cannot be refitted as published. Reproductions document this gap; analyses use
  methods valid on normalised, log-transformed data, at the independent-unit level.
- Pydantic schemas for every state file (manifests, claims, backlog, reports, preregistrations):
  an agent cannot write a malformed record without a gate failing.
