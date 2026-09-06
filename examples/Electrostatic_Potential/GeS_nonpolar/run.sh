#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec "${PYTHON:-python}" "$here/run_case.py" "$@"
