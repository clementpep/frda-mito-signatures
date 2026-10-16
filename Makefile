# One entry point per verb. Every routine and the CI call these targets, so
# a contributor and an agent run exactly the same checks.
.PHONY: setup fetch lint test verify reproduce ci hub status

UV ?= uv
RUN = $(UV) run --frozen

setup:            ## install pinned deps (uv.lock) into .venv
	$(UV) sync --frozen --extra dev

fetch:            ## download every manifest file and verify its sha256
	$(RUN) frda fetch

lint:
	$(RUN) ruff check src tests pipelines scripts
	$(RUN) ruff format --check src tests pipelines scripts

test:
	$(RUN) pytest

verify:           ## deterministic verification gates (fails on any FAIL)
	$(RUN) frda verify

reproduce:        ## re-run every registered pipeline from raw data, compare output hashes
	$(RUN) frda reproduce

hub:              ## regenerate results/hub/summary.json (contract: docs/HUB_CONTRACT.md)
	$(RUN) frda export-hub

status:           ## state of the autonomy loop (branches awaiting verification, etc.)
	$(RUN) frda autonomy-status

ci: lint test verify
