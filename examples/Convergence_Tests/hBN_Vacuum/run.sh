#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
template="$here/run"
root=${ZSTAR_CONVERGENCE_ROOT:-"$here/work"}
heights=(15 20 30 40)

for height in "${heights[@]}"; do
    work="$root/Lz${height}"
    if [[ ! -d "$work" ]]; then
        mkdir -p "$work"
        cp -a "$template/." "$work/"
        python "$here/set_vacuum.py" "$work/STRU" "$height"
    fi
    python "$here/set_vacuum.py" "$work/STRU" "$height" --check
    cd "$work"
    if [[ ! -f shared_response.json ]]; then
        zstar bec pre --stru STRU --input INPUT --dim 2
    fi
    zstar bec run --no-electronic-dielectric "$@"
    zstar bec stat
    if [[ " $* " != *" --dry-run "* ]]; then
        zstar bec post
    fi
done
