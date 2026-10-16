#!/usr/bin/env bash
# SessionStart hook: in Claude Code cloud sessions, install pinned deps so that
# `make test` / `make verify` work immediately. Data is fetched on demand (make fetch).
set -uo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/..}" || exit 0
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null 2>&1 || python3 -m pip install --quiet --user uv >/dev/null 2>&1
uv sync --frozen --extra dev --quiet >/dev/null 2>&1 && echo "frda: deps ready (uv sync)" || echo "frda: uv sync failed — run scripts/routine-setup.sh"
exit 0
