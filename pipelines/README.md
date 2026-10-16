# Pipelines

One script per analysis step: `pipelines/pNNN_<slug>.py --out DIR`.

Rules (enforced by gates or by the verifier):
- Read data only through `frda.io.load_matrix` and groups only through the manifest.
- Write outputs with `frda.provenance.write_json` (sorted keys, 6 significant digits → reruns hash equal),
  then call `frda.provenance.write_run(...)` last.
- Deterministic: fixed seeds, no network calls except through `frda.acquire`, no wall-clock in outputs.
- Register the pipeline in `registry.yaml`; commit its outputs under `results/<P-id>-<slug>/`.
- Small outputs only (< 2 MB per file); large intermediates stay out of git.

See `pipelines/p000_example.py` for the skeleton.
