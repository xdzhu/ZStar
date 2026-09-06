#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$ROOT/../../.." && pwd)
exec python "$REPO/tools/shared_response/run_one_dimensional_example.py" --case "$ROOT" "$@"
