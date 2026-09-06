#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$ROOT/../../.." && pwd)
if [[ "${1:-}" == --post-only ]]; then
    exec python "$REPO/examples/common/reproduce_unified_spectra.py" --case-dir "$ROOT"
fi
exec python "$REPO/tools/shared_response/run_one_dimensional_example.py" --case "$ROOT" "$@"
