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
start=$(date +%s)
"$MPI" -np "$NP" "$ABACUS" > "abacus_relax_${NP}mpi.log" 2>&1
rc=$?
end=$(date +%s)
printf '%s\n' "{\"node\":\"$(hostname)\",\"mpi\":$NP,\"omp\":$OMP,\"returncode\":$rc,\"elapsed_seconds\":$((end-start))}" > "runtime_relax_${NP}mpi.json"
test "$rc" -eq 0 || exit "$rc"
grep -qiE 'relaxation is converged|calculation *finished' OUT.*/running_relax.log || exit 2
test -f OUT.*/STRU_ION_D || exit 3
echo "REFERENCE_RELAX_COMPLETE node=$(hostname) mpi=$NP omp=$OMP"
