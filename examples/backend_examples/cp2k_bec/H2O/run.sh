#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec bash "$ROOT/../../../common/run_cp2k_bec_case.sh" --case-dir "$ROOT" "$@"
