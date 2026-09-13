#!/usr/bin/env bash
# One non-exclusive 32 MPI x 1 OMP Slurm job for a complete v2 piezo case.
set -u -o pipefail

ROOT="${1:?usage: $0 CASE_ROOT VALENCE_LIST}"
shift
# Accept either one quoted list ("3 5") or two shell words (3 5), which is
# useful when sbatch is invoked through a gateway shell.
VALENCE="${*:?usage: $0 CASE_ROOT VALENCE_LIST}"
NP="${ZSTAR_MPI_RANKS:-32}"
OMP="${ZSTAR_OMP_THREADS:-1}"
ABACUS_ENV="${ZSTAR_ABACUS_ENV:-/public/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh}"
PYATB_ENV="${ZSTAR_PYATB_ENV:-/public/home/iai806/apprepo/pyatb/v1.1.2-mpi4py/scripts/env.sh}"
ADAPTER="${ZSTAR_PYATB_ADAPTER:-$ROOT/pyatb_precision.py}"

export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"

run_abacus() {
    local d="$1"; local stage="$2"; local start end rc
    # The environment scripts use module purge, so source it before every
    # ABACUS invocation after a PYATB invocation.
    source "$ABACUS_ENV"
    export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"
    start=$(date +%s)
    (cd "$d" && mpirun -np "$NP" abacus > "abacus_${NP}mpi.log" 2>&1)
    rc=$?
    end=$(date +%s)
    printf '{"stage":"%s","node":"%s","mpi":%s,"omp":%s,"returncode":%s,"elapsed_seconds":%s}\n' \
        "$stage" "$(hostname)" "$NP" "$OMP" "$rc" "$((end-start))" > "$d/runtime_abacus_${NP}mpi.json"
    return "$rc"
}

run_pyatb() {
    local d="$1"; local stage="$2"; local start end rc
    # The conda-pack activation script references optional variables without
    # ${var:-}; temporarily relax nounset while activating the environment.
    set +u
    source "$PYATB_ENV"
    set -u
    export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"
    command -v pyatb_input >/dev/null || { echo "pyatb_input not found after sourcing $PYATB_ENV" >&2; return 20; }
    start=$(date +%s)
    (cd "$d" && pyatb_input -i . -o pyatb --polar --valence "$VALENCE" > pyatb_input.log 2>&1) || return $?
    (cd "$d/pyatb" && mpirun -np "$NP" python "$ADAPTER" > "pyatb_precision_${NP}mpi.log" 2>&1)
    rc=$?
    end=$(date +%s)
    printf '{"stage":"%s","node":"%s","mpi":%s,"omp":%s,"returncode":%s,"elapsed_seconds":%s}\n' \
        "$stage" "$(hostname)" "$NP" "$OMP" "$rc" "$((end-start))" > "$d/runtime_pyatb_${NP}mpi.json"
    return "$rc"
}

for d in "$ROOT"/reference "$ROOT"/strain-*; do
    test -d "$d" || continue
    stage=$(basename "$d")
    compat=""
    if test ! -f "$d/.abacus_done_${NP}"; then
        test -f "$d/INPUT" && test -f "$d/STRU" && test -f "$d/KPT" || { echo "missing inputs in $d" >&2; exit 2; }
        echo "START ABACUS $stage node=$(hostname) mpi=$NP omp=$OMP"
        run_abacus "$d" "$stage" || { echo "ABACUS failed: $stage" >&2; exit 3; }
        if ! grep -qiE 'charge density convergence is achieved|relaxation is converged|calculation *finished' "$d"/OUT.*/running_*.log 2>/dev/null; then
            echo "ABACUS has no convergence marker: $stage" >&2; exit 4
        fi
        touch "$d/.abacus_done_${NP}"
    else
        echo "SKIP ABACUS $stage"
    fi
    if test "$stage" != reference; then
        out=$(find "$d" -maxdepth 2 -type f -name STRU_ION_D -print -quit)
        test -n "$out" || { echo "relaxed structure missing for $stage" >&2; exit 5; }
        test -f "$d/STRU_INITIAL" || cp "$d/STRU" "$d/STRU_INITIAL"
        cp "$out" "$d/STRU"
        if test -f "$d/OUT."*/running_relax.log; then
            relax_log=$(find "$d" -maxdepth 2 -type f -name running_relax.log -print -quit)
            compat="$(dirname "$relax_log")/running_scf.log"
            cp "$relax_log" "$compat"
        fi
    fi
    if test -f "$d/pyatb/Out/Polarization/zstar_precision.json"; then
        test -z "$compat" || rm -f "$compat"
        echo "SKIP PYATB $stage"
        continue
    fi
    rm -rf "$d/pyatb.aborted" 2>/dev/null || true
    test -d "$d/pyatb" && mv "$d/pyatb" "$d/pyatb.aborted" || true
    echo "START PYATB $stage node=$(hostname) mpi=$NP omp=$OMP"
    run_pyatb "$d" "$stage"; rc=$?
    test -z "$compat" || rm -f "$compat"
    test "$rc" -eq 0 || { echo "PYATB failed: $stage" >&2; exit 6; }
    test -f "$d/pyatb/Out/Polarization/polarization.dat" || { echo "missing polarization output: $stage" >&2; exit 7; }
    test -f "$d/pyatb/Out/Polarization/zstar_precision.json" || { echo "missing precision audit: $stage" >&2; exit 8; }
    touch "$d/.pyatb_done_${NP}"
    echo "DONE $stage"
done
echo "V2_PIEZO_CASE_COMPLETE root=$ROOT node=$(hostname) mpi=$NP omp=$OMP"
