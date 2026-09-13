#!/usr/bin/env bash
# Research-only remote runner.  Invoke from a node with a private run root and
# an explicit stage list; it never submits to PBS and never changes v1 state.
set -u -o pipefail

ROOT="${1:?usage: $0 ROOT STAGE...}"
shift
ABACUS="${ZSTAR_ABACUS:-/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus}"
MPI="${ZSTAR_MPI_LAUNCHER:-/home/zhuxd/intel/oneapi/mpi/2021.9.0/bin/mpirun}"
NP="${ZSTAR_MPI_RANKS:-40}"
export OMP_NUM_THREADS="${ZSTAR_OMP_THREADS:-1}"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export I_MPI_FABRICS="${I_MPI_FABRICS:-shm:dapl}"

for stage in "$@"; do
    d="$ROOT/$stage"
    test -d "$d" || { echo "missing stage $d" >&2; exit 2; }
    if test -f "$d/.done40"; then
        echo "SKIP $stage"
        continue
    fi
    test -f "$d/INPUT" && test -f "$d/STRU" && test -f "$d/KPT" || {
        echo "missing input in $d" >&2; exit 2;
    }
    start=$(date +%s)
    printf 'START node=%s stage=%s mpi=%s omp=%s epoch=%s\n' "$(hostname)" "$stage" "$NP" "$OMP_NUM_THREADS" "$start" > "$d/status_40mpi.log"
    (cd "$d" && "$MPI" -np "$NP" "$ABACUS" > abacus_40mpi.log 2>&1)
    rc=$?
    end=$(date +%s)
    printf '{"node":"%s","stage":"%s","mpi":%s,"omp":%s,"returncode":%s,"elapsed_seconds":%s,"start_epoch":%s,"end_epoch":%s}\n' \
        "$(hostname)" "$stage" "$NP" "$OMP_NUM_THREADS" "$rc" "$((end-start))" "$start" "$end" > "$d/runtime_40mpi.json"
    if test "$rc" -ne 0; then
        echo "FAIL $stage rc=$rc" | tee -a "$d/status_40mpi.log"
        exit "$rc"
    fi
    if grep -qi 'calculation  *finished' "$d"/OUT.*/running_*.log 2>/dev/null || \
       grep -qi 'charge density convergence is achieved' "$d"/OUT.*/running_*.log 2>/dev/null; then
        touch "$d/.done40"
        echo "DONE $stage" | tee -a "$d/status_40mpi.log"
    else
        echo "FAIL $stage: no convergence marker" | tee -a "$d/status_40mpi.log"
        exit 3
    fi
done
