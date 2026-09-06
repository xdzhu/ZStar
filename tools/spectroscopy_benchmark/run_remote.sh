#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
source /home/zhuxd/intel/oneapi/setvars.sh > "$root/$1.environment.log" 2>&1
export I_MPI_FABRICS=shm
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$root/code"
/home/zhuxd/Software/anaconda3/envs/icu_copy/bin/python -u \
  "$root/code/tools/spectroscopy_benchmark/run_optical_reuse.py" --root "$root" --case "$1"
