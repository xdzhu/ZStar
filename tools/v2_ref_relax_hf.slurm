#!/usr/bin/env bash
# Reference-only ionic relaxation before a relaxed-ion v2 strain ensemble.
set -u -o pipefail
ROOT="${1:?usage: $0 REFERENCE_ROOT}"
NP="${ZSTAR_MPI_RANKS:-32}"
OMP="${ZSTAR_OMP_THREADS:-1}"
PROFILE="${ZSTAR_V2_CONVERGENCE_PROFILE:-production}"
ENV_SCRIPT="${ZSTAR_ABACUS_ENV:-/public/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh}"

case "$PROFILE" in
    production|verification) MAX_FORCE=1e-4; MAX_STRESS=0.5; MAX_SCF=1e-8 ;;
    *) echo "unknown ZSTAR_V2_CONVERGENCE_PROFILE=$PROFILE (production|verification)" >&2; exit 2 ;;
esac
PROFILE_MARKER="$ROOT/convergence_profile.txt"
test -f "$PROFILE_MARKER" || { echo "missing v2 convergence_profile.txt in $ROOT" >&2; exit 2; }
EXPECTED_PROFILE=$(tr -d '[:space:]' < "$PROFILE_MARKER")
test "$EXPECTED_PROFILE" = "$PROFILE" || {
    echo "input profile $EXPECTED_PROFILE does not match ZSTAR_V2_CONVERGENCE_PROFILE=$PROFILE" >&2; exit 2;
}

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
awk -v x="$(input_value "$INPUT" force_thr_ev)" -v limit="$MAX_FORCE" 'BEGIN { exit !(x == limit) }' || {
    echo "v2 $PROFILE reference requires force_thr_ev=$MAX_FORCE" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" stress_thr)" -v limit="$MAX_STRESS" 'BEGIN { exit !(x == limit) }' || {
    echo "v2 $PROFILE reference requires stress_thr=$MAX_STRESS kbar" >&2; exit 2;
}
awk -v x="$(input_value "$INPUT" scf_thr)" -v limit="$MAX_SCF" 'BEGIN { exit !(x == limit) }' || {
    echo "v2 $PROFILE reference requires scf_thr=$MAX_SCF" >&2; exit 2;
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
reference_log=$(find OUT.* -maxdepth 1 -type f \( -name 'running_cell-relax.log' -o -name 'running_relax.log' \) -print -quit)
test -n "$reference_log" || {
    echo "reference relaxation log is missing (expected running_cell-relax.log)" >&2
    exit 2
}
grep -qi 'relaxation is converged' "$reference_log" || {
    echo "reference relaxation did not reach a convergence marker" >&2
    exit 2
}
test -f OUT.*/STRU_ION_D || {
    echo "reference relaxation did not emit STRU_ION_D" >&2
    exit 3
}
echo "REFERENCE_RELAX_COMPLETE profile=$PROFILE node=$(hostname) mpi=$NP omp=$OMP"
