#!/usr/bin/env bash
# Push <local-ref> to origin/<remote-branch>, retrying only on network errors
# (2s, 4s, 8s, 16s). Refuses main and force pushes by construction.
set -euo pipefail
REF="${1:?local ref}"; BR="${2:?remote branch}"
case "$BR" in
  auto/*|verified/*) ;;
  *) echo "push-branch: refusing to push '$BR' (only auto/* and verified/*)" >&2; exit 2 ;;
esac
SHA=$(git rev-parse "$REF")
for delay in 0 2 4 8 16; do
  sleep "$delay"
  if git push origin "${SHA}:refs/heads/${BR}" 2>/tmp/push-branch.err; then
    echo "push-branch: ${BR} -> ${SHA:0:8}"; exit 0
  fi
  if ! grep -qiE "could not resolve|timed out|connection|reset|unexpected disconnect|RPC failed|HTTP 5|429" /tmp/push-branch.err; then
    cat /tmp/push-branch.err >&2; exit 1      # rejected (non-fast-forward, permission): no retry
  fi
  echo "push-branch: network error, retrying" >&2
done
cat /tmp/push-branch.err >&2; exit 1
