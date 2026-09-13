#!/usr/bin/env bash
#SBATCH --job-name=zstar-bto-c50
#SBATCH --partition=wzacnormal
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --cpus-per-task=1
#SBATCH --array=0-49%4
# These nodes have produced reproducible Intel-MPI/Slurm failures for this
# workload; keep them out of the force-label array.
#SBATCH --exclude=j10r2n12,j11r2n24,j11r2n37
#SBATCH --output=slurm-%A_%a.out
#SBATCH --error=slurm-%A_%a.out

set -euo pipefail
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MKL_DYNAMIC=FALSE

ROOT=${BATCH_ROOT:?set BATCH_ROOT to the uploaded cubic50 input root}
FRAME_LIST=${FRAME_LIST:-$ROOT/frame_ids.txt}
if [[ ! -s "$FRAME_LIST" ]]; then
  echo "missing or empty FRAME_LIST: $FRAME_LIST" >&2
  echo "Refusing to auto-discover frame-* directories; this prevents rerunning archived phonon frames." >&2
  exit 2
fi
FRAME_NAME=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$FRAME_LIST")
if [[ "$FRAME_NAME" != frame-* ]]; then
  FRAME_NAME="frame-$FRAME_NAME"
fi
# Existing phonon equilibrium/displacement labels must be reused, not
# recalculated by this supplementary-force array.  Requiring an explicit
# supp_* entry makes accidental duplicate phonon submissions fail before
# ABACUS starts.
if [[ "$FRAME_NAME" == frame-phonon_* ]]; then
  echo "refusing archived phonon frame $FRAME_NAME; reuse its existing DFT label" >&2
  exit 2
fi
FRAME_ROOT="$ROOT/$FRAME_NAME"
[[ -d "$FRAME_ROOT" ]] || { echo "missing frame: $FRAME_ROOT" >&2; exit 2; }

source "$HOME/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh"
for asset in "$ROOT/assets"/*; do
  ln -sfn "$asset" "$FRAME_ROOT/$(basename "$asset")"
done
cd "$FRAME_ROOT"

if [[ -s OUT.SCF/running_scf.log ]] && grep -q 'FINAL_ETOT_IS' OUT.SCF/running_scf.log; then
  echo "[SKIP] $FRAME_NAME already has FINAL_ETOT_IS"
  exit 0
fi

echo "[START] frame=$FRAME_NAME host=$(hostname) date=$(date -Is) np=${SLURM_NTASKS:-32} omp=$OMP_NUM_THREADS"
mpirun -np "${SLURM_NTASKS:-32}" abacus > abacus.stdout 2>&1
echo "[DONE] frame=$FRAME_NAME host=$(hostname) date=$(date -Is)"
