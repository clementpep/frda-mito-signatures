#!/usr/bin/env bash
# P1 — environment for a routine or CI run: uv, pinned deps (uv.lock), data
# downloaded and checked against manifest sha256. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "routine-setup: installing uv"
  python3 -m pip install --quiet --user uv 2>/dev/null \
    || python3 -m pip install --quiet --break-system-packages uv
fi
uv --version
uv sync --frozen --extra dev --quiet
uv run --frozen frda fetch
echo "routine-setup: OK (remember: export PATH=\"\$HOME/.local/bin:\$PATH\" in later shells)"
