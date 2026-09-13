#!/usr/bin/env bash
# Reference-only ionic relaxation before a relaxed-ion v2 strain ensemble.
set -u -o pipefail
ROOT="${1:?usage: $0 REFERENCE_ROOT}"
NP="${ZSTAR_MPI_RANKS:-32}"
OMP="${ZSTAR_OMP_THREADS:-1}"
ENV_SCRIPT="${ZSTAR_ABACUS_ENV:-/public/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh}"
set +u
source "$ENV_SCRIPT"
set -u
export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"
cd "$ROOT"
start=$(date +%s)
mpirun -np "$NP" abacus > "abacus_relax_${NP}mpi.log" 2>&1
rc=$?
end=$(date +%s)
printf '%s\n' "{\"node\":\"$(hostname)\",\"mpi\":$NP,\"omp\":$OMP,\"returncode\":$rc,\"elapsed_seconds\":$((end-start))}" > "runtime_relax_${NP}mpi.json"
test "$rc" -eq 0 || exit "$rc"
grep -qiE 'relaxation is converged|calculation *finished' OUT.*/running_relax.log || {
    echo "reference relaxation did not reach a convergence marker" >&2
    exit 2
}
test -f OUT.*/STRU_ION_D || {
    echo "reference relaxation did not emit STRU_ION_D" >&2
    exit 3
}
echo "REFERENCE_RELAX_COMPLETE node=$(hostname) mpi=$NP omp=$OMP"
