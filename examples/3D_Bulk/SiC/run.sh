#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)

with_spectra=0
dry_run=0
bec_args=()
for argument in "$@"; do
    case "$argument" in
        --with-spectra)
            with_spectra=1
            ;;
        --dry-run)
            dry_run=1
            bec_args+=("$argument")
            ;;
        -h|--help)
            cat <<'EOF'
Usage: bash run.sh [--with-spectra] [ZSTAR BEC RUN OPTIONS]

  --with-spectra  Continue from Unified BEC/Gamma results to IR and Raman.
  --dry-run       Prepare and inspect the workflow without starting a solver.

Calculator paths and MPI/OMP settings are read from `zstar config`.
EOF
            exit 0
            ;;
        *)
            bec_args+=("$argument")
            ;;
    esac
done

bash "$here/../../Benchmarks/run_case.sh" "$here" 3 "${bec_args[@]}"

if [[ $with_spectra -eq 0 ]]; then
    exit 0
fi
if [[ $dry_run -eq 1 ]]; then
    echo "Spectroscopy plan: Unified response -> IR -> Raman"
    echo "Run again without --dry-run to generate spectra under work/spectra/."
    exit 0
fi

work=${ZSTAR_WORK:-"$here/work"}
cd "$work"
if [[ ! -f spectra/.zstar/spectra.json ]]; then
    zstar spectra pre --root spectra --response .
fi
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra

echo "BEC and Gamma outputs: $work"
echo "IR and Raman outputs:  $work/spectra"
