# Preregistrations

A confirmatory analysis is declared here **before** it runs, in its own commit.
Git history is the timestamp; the `preregistration` gate checks that:

- the file `PR-NNN-<slug>.md` has a valid front matter (see `src/frda/prereg.py`),
- it was committed in an ancestor of the commit that introduced the confirmatory `run.json`,
- it was never edited afterwards (an amendment is a new file with `amends: PR-NNN`).

Template:

```markdown
---
id: PR-001
task: T-011
title: Replication of the GSE104288 mitochondrial signature in independent datasets
hypotheses:
  - H1: ...
primary_outcome: ...
expected_direction: ...
analysis_plan: ...
decision_rule: ...
created: 2026-10-20
---
Free-text rationale, power considerations, datasets in scope and why.
```
