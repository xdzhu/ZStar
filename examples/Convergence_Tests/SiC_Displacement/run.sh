#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
template="$here/run"
root=${ZSTAR_CONVERGENCE_ROOT:-"$here/work"}
displacements=(0.005 0.010 0.015 0.020 0.025 0.030)

for displacement in "${displacements[@]}"; do
    label=${displacement/./p}
    work="$root/d${label}"
    if [[ ! -d "$work" ]]; then
        mkdir -p "$work"
        cp -a "$template/." "$work/"
    fi
    cd "$work"
    if [[ ! -f shared_response.json ]]; then
        zstar bec pre --stru STRU --input INPUT --dim 3 \
            --displacement "$displacement"
    fi
    zstar bec run --no-electronic-dielectric "$@"
    zstar bec stat
    if [[ " $* " != *" --dry-run "* ]]; then
        zstar bec post
    fi
done
