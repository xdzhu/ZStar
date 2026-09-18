#!/usr/bin/env bash
# Reference-only ionic relaxation on one explicitly selected 235 compute node.
set -u -o pipefail
ROOT="${1:?usage: $0 REFERENCE_ROOT}"
NP="${ZSTAR_MPI_RANKS:-40}"
OMP="${ZSTAR_OMP_THREADS:-1}"
ABACUS="${ZSTAR_ABACUS:-/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus}"
MPI="${ZSTAR_MPI_LAUNCHER:-/home/zhuxd/intel/oneapi/mpi/2021.9.0/bin/mpirun}"
export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"
export I_MPI_FABRICS="${I_MPI_FABRICS:-shm}"
cd "$ROOT"
# One stage directory maps to one ABACUS executable.  A second launcher writing
# to the same OUT.* tree invalidates the calculation, so fail closed instead of
# letting two 40-rank runs overlap.
lock_dir=".zstar-relax-${NP}mpi.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "ERROR: active ZStar relaxation lock: $ROOT/$lock_dir" >&2
    echo "Resolve the existing run before launching another copy in this directory." >&2
    exit 10
fi
cleanup_lock() { rmdir "$lock_dir" 2>/dev/null || true; }
trap cleanup_lock EXIT INT TERM
relax_log=$(find OUT.* -maxdepth 1 -type f \( -name 'running_cell-relax.log' -o -name 'running_relax.log' \) -print -quit 2>/dev/null || true)
relaxed_stru=$(find OUT.* -maxdepth 1 -type f -name STRU_ION_D -print -quit 2>/dev/null || true)
if test -n "$relax_log" && test -n "$relaxed_stru" && grep -qi 'relaxation is converged' "$relax_log"; then
    printf '%s\n' "{\"node\":\"$(hostname)\",\"mpi\":$NP,\"omp\":$OMP,\"returncode\":0,\"elapsed_seconds\":0,\"reused_converged_output\":true}" > "runtime_relax_${NP}mpi.json"
    echo "REUSE_CONVERGED_REFERENCE_RELAX node=$(hostname) mpi=$NP omp=$OMP"
else
    start=$(date +%s)
    "$MPI" -np "$NP" "$ABACUS" > "abacus_relax_${NP}mpi.log" 2>&1
    rc=$?
    end=$(date +%s)
    printf '%s\n' "{\"node\":\"$(hostname)\",\"mpi\":$NP,\"omp\":$OMP,\"returncode\":$rc,\"elapsed_seconds\":$((end-start))}" > "runtime_relax_${NP}mpi.json"
    test "$rc" -eq 0 || exit "$rc"
    relax_log=$(find OUT.* -maxdepth 1 -type f \( -name 'running_cell-relax.log' -o -name 'running_relax.log' \) -print -quit 2>/dev/null || true)
    relaxed_stru=$(find OUT.* -maxdepth 1 -type f -name STRU_ION_D -print -quit 2>/dev/null || true)
fi
test -n "$relax_log" && grep -qi 'relaxation is converged' "$relax_log" || exit 2
test -n "$relaxed_stru" || exit 3
echo "REFERENCE_RELAX_COMPLETE node=$(hostname) mpi=$NP omp=$OMP"
