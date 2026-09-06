#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
exec python "$repo/tools/shared_response/run_one_dimensional_example.py" --case "$here" --stage response "$@"
