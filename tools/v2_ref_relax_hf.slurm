#!/usr/bin/env bash
# Reference-only ionic relaxation before a relaxed-ion v2 strain ensemble.
set -u -o pipefail
ROOT="${1:?usage: $0 REFERENCE_ROOT}"
NP="${ZSTAR_MPI_RANKS:-32}"
OMP="${ZSTAR_OMP_THREADS:-1}"
ENV_SCRIPT="${ZSTAR_ABACUS_ENV:-/public/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh}"

input_value() {
    local input="$1" key="$2"
    awk -v wanted="$key" '
        /^[[:space:]]*($|#)/ { next }
        $1 == wanted { value=$2 }
        END { if (value != "") print value }
    ' "$input"
}

INPUT="$ROOT/INPUT"
test -f "$INPUT" || { echo "missing INPUT in $ROOT" >&2; exit 2; }
test "$(input_value "$INPUT" calculation)" = "cell-relax" || {
    echo "v2 reference requires calculation=cell-relax" >&2; exit 2;
}
test "$(input_value "$INPUT" symmetry)" = "1" || {
    echo "v2 reference requires symmetry=1" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" symmetry_prec)" 'BEGIN { exit !(x == 1e-3) }' || {
    echo "v2 reference requires symmetry_prec=1e-3" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" force_thr_ev)" 'BEGIN { exit !(x > 0 && x <= 1e-4) }' || {
    echo "v2 reference requires force_thr_ev<=1e-4" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" stress_thr)" 'BEGIN { exit !(x > 0 && x <= 0.1) }' || {
    echo "v2 reference requires stress_thr<=0.1 kbar" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" scf_thr)" 'BEGIN { exit !(x > 0 && x <= 1e-10) }' || {
    echo "v2 reference requires scf_thr<=1e-10" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" relax_nmax)" 'BEGIN { exit !(x >= 100 && x == int(x)) }' || {
    echo "v2 reference requires integer relax_nmax>=100" >&2; exit 2;
}
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
grep -qi 'relaxation is converged' OUT.*/running_relax.log || {
    echo "reference relaxation did not reach a convergence marker" >&2
    exit 2
}
test -f OUT.*/STRU_ION_D || {
    echo "reference relaxation did not emit STRU_ION_D" >&2
    exit 3
}
echo "REFERENCE_RELAX_COMPLETE node=$(hostname) mpi=$NP omp=$OMP"
