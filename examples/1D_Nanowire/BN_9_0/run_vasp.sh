#!/usr/bin/env bash
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
if [[ "${1:-}" == "--dry-run" ]]; then
  printf '%s\n' 'Fixed-geometry BN(9,0): PBE, 500 eV, 1x1x12, native DFPT BEC.' \
    'Set VASP_POTENTIAL_DIR to a licensed PAW-PBE-54 directory containing B/POTCAR and N/POTCAR.' \
    'Set VASP_COMMAND, e.g. mpirun -np 40 vasp_std (OMP_NUM_THREADS=1).' \
    "New inputs and results: $here/work-vasp; archived results are never overwritten."
  exit 0
fi
if [[ $# -ne 0 ]]; then
  printf '%s\n' 'Usage: bash run_vasp.sh [--dry-run]' >&2
  exit 2
fi
: "${VASP_POTENTIAL_DIR:?Set VASP_POTENTIAL_DIR to your licensed PAW-PBE-54 directory}"
export OMP_NUM_THREADS=1
exec python "$repo/tools/shared_response/bn9_vasp_validation.py" \
  --structure "$here/run/STRU" --potentials "$VASP_POTENTIAL_DIR" \
  --root "$here/work-vasp" --run --vasp-command "${VASP_COMMAND:-vasp_std}"
