#!/usr/bin/env bash
set -euo pipefail

case_dir=""
dim=""
work=""
dry_run=0
post_only=0
method=unified
while [[ $# -gt 0 ]]; do
    case "$1" in
        --case-dir) case_dir=${2:?missing value for --case-dir}; shift 2 ;;
        --dim) dim=${2:?missing value for --dim}; shift 2 ;;
        --work) work=${2:?missing value for --work}; shift 2 ;;
        --dry-run) dry_run=1; shift ;;
        --post-only) post_only=1; shift ;;
        --method) method=${2:?missing method}; shift 2 ;;
        -h|--help) echo 'Usage: run_spectra_case.sh --case-dir DIR --dim {0,1,2,3} [--method unified|mode] [--work DIR] [--dry-run] [--post-only]'; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ "$method" == unified || "$method" == mode ]] || { echo '--method must be unified or mode' >&2; exit 2; }
[[ -n "$case_dir" && -n "$dim" ]] || { echo 'Missing --case-dir or --dim' >&2; exit 2; }
case_dir=$(cd "$case_dir" && pwd)
if [[ "$post_only" == 1 ]]; then
    exec "${ZSTAR_PYTHON:-python}" "$case_dir/../../common/reproduce_unified_spectra.py" --case-dir "$case_dir"
fi
work=${work:-"$case_dir/work"}
if [[ "$work" != /* ]]; then work="$case_dir/$work"; fi

if [[ "$dry_run" -eq 1 ]]; then
    bash "$case_dir/../../common/run_abacus_case.sh" --case-dir "$case_dir" \
        --work "$work" --dim "$dim" --stage all --dry-run
    if [[ "$method" == unified ]]; then
        cat <<EOF
6. zstar spectra pre --response .
7. zstar spectra run
8. zstar spectra post
The existing displacement SCFs supply IR and nonresonant Raman; PYATB evaluates
the additional dielectric tensors from private electronic-matrix copies.
DRY RUN: no spectroscopy solver or post-processing command was started.
EOF
    else
        cat <<EOF
6. For dim > 0: zstar ir --qpoints qpoints.yaml --born BEC.dat \
     --dielectric BORN --dim $dim --outdir ir_spectrum
7. zstar raman prepare --stru STRU --qpoints qpoints.yaml --outdir raman
8. zstar raman run --raman-dir raman --reference 0.no-move \
     --qpoints qpoints.yaml --dim $dim
   For dim 0 this also writes molecular IR from the mode dipole derivatives.
DRY RUN: no spectroscopy solver or post-processing command was started.
EOF
    fi
    exit 0
fi

runtime=$("${ZSTAR_PYTHON:-python}" "$(dirname "${BASH_SOURCE[0]}")/runtime.py" "$case_dir")
mapfile -t runtime_values <<< "$runtime"
abacus_command=${runtime_values[0]}
pyatb_command=${runtime_values[1]}
export OMP_NUM_THREADS=${runtime_values[2]}

bash "$case_dir/../../common/run_abacus_case.sh" --case-dir "$case_dir" \
    --work "$work" --dim "$dim" --stage all
cd "$work"
if [[ "$method" == unified ]]; then
    [[ -f spectra/.zstar/spectra.json ]] || zstar spectra pre --response .
    zstar spectra run --abacus-command "$abacus_command" --pyatb-command "$pyatb_command" \
        --omp-threads "$OMP_NUM_THREADS"
    zstar spectra post
    echo "Unified IR/Raman spectra completed under $work/spectra"
    exit 0
fi
if [[ "$dim" != 0 ]]; then
    zstar ir --qpoints qpoints.yaml --born BEC.dat \
        --dielectric BORN --dim "$dim" --outdir ir_spectrum
fi
zstar raman prepare --stru STRU --qpoints qpoints.yaml --outdir raman
zstar raman run --raman-dir raman --reference 0.no-move \
    --qpoints qpoints.yaml --dim "$dim" \
    --abacus-command "$abacus_command" --pyatb-command "$pyatb_command"
echo "IR/Raman spectra completed under $work"
