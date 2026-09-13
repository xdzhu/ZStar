#!/usr/bin/env bash
set -euo pipefail

# Submit the native Slurm driver without hand-counting array indices.  This
# prevents a frame-list tail from being silently omitted during recovery.
ROOT="${1:?usage: $0 BATCH_ROOT STAGE_LIST [THROTTLE]}"
STAGE_LIST="${2:?usage: $0 BATCH_ROOT STAGE_LIST [THROTTLE]}"
THROTTLE="${3:-4}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[[ -d "$ROOT" ]] || { echo "missing BATCH_ROOT: $ROOT" >&2; exit 2; }
[[ -s "$STAGE_LIST" ]] || { echo "missing or empty STAGE_LIST: $STAGE_LIST" >&2; exit 2; }
COUNT="$(awk 'NF {n++} END {print n+0}' "$STAGE_LIST")"
(( COUNT > 0 )) || { echo "STAGE_LIST has no stages" >&2; exit 2; }
(( THROTTLE > 0 )) || { echo "THROTTLE must be positive" >&2; exit 2; }

cd "$ROOT"
sbatch \
  --array="0-$((COUNT - 1))%${THROTTLE}" \
  --exclude="j10r2n12" \
  --export="ALL,BATCH_ROOT=$ROOT,STAGE_LIST=$STAGE_LIST,I_MPI_FABRICS=ofi,PYATB_MP=0.08,PYATB_MPI_NTASKS=32,OMP_NUM_THREADS=1,MKL_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1,NUMEXPR_NUM_THREADS=1,MKL_DYNAMIC=FALSE" \
  "$SCRIPT_DIR/wuzhen_bec_array.slurm"
