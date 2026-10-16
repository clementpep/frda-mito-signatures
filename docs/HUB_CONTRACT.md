# Hub contract — results/hub/summary.json

Read by poups-ai-hub (`GET /api/research/frda` → page `/research`) from
`https://raw.githubusercontent.com/clementpep/frda-mito-signatures/main/results/hub/summary.json`.
Written by `frda export-hub` (`src/frda/hub.py`), refreshed on every landing.

Rules:
- `schema_version` is an integer. Additive changes (new optional fields) keep it; any rename,
  removal or type change bumps it, and the hub's zod schema (`server/schemas/research.js`) must
  accept the new version before it lands on main here.
- Only verified state is published: the file on `main` reflects what passed landing.
- No raw data, no identifiers: titles, counts, statuses, statements, links.

```jsonc
{
  "schema_version": 1,
  "generated_at": "2026-10-16T17:00:00+00:00",
  "commit": "<sha>",
  "project": { "id", "title", "subtitle", "questions": [str], "target", "disclaimer", "repo_url" },
  "progress": { "total", "done", "in_review", "ready", "changes_requested", "blocked", "needs_human", "proposed" },
  "milestones": [ { "id", "title", "goal", "status": "todo|in_progress|done", "tasks_done", "tasks_total" } ],
  "tasks": [ { "id", "title", "milestone", "status", "kind" } ],
  "claims": [ { "id", "statement", "status": "reproduced|refuted|new|not_demonstrated",
                "evidence_level": "exploratory|single_dataset|replicated|preregistered_confirmed",
                "datasets": [str], "limitations": [str], "verified": bool,
                "source": { "pmid", "doi", "location" } | null } ],
  "verifications": [ { "task", "date", "verdict": "PASS|CHANGES_REQUESTED|NEEDS_HUMAN",
                       "summary", "attempt", "acceptance_met", "report_url" } ],
  "datasets": [ { "id", "title", "tissue_or_model", "assay", "url",
                  "groups": [ { "name", "independent_units", "unit", "samples" } ] } ]
}
```
