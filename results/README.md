# results

`results/<P-id>-<slug>/` — outputs of registered pipelines, each with `run.json` (code commit,
input checksums, parameters, package versions, output checksums). Never edit by hand: the
`run_records` gate detects it. `results/hub/summary.json` is the export for poups-ai-hub.
