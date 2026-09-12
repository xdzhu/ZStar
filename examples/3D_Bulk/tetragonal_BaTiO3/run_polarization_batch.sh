#!/usr/bin/env bash
# Experimental one-run-per-geometry PYATB post-processing for the v2 fixture.
# A single PYATB polarization run evaluates all three lattice directions.
set -u -o pipefail

CASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ZSTAR_V2_RUN_ROOT:-$CASE_ROOT/run}"
PYATB_INPUT="${ZSTAR_PYATB_INPUT:-pyatb_input}"
MPI="${ZSTAR_MPI_LAUNCHER:-mpirun}"
PYTHON="${ZSTAR_PYTHON:-python}"
ADAPTER="${ZSTAR_PYATB_ADAPTER:-$CASE_ROOT/pyatb_precision.py}"
MPI_RANKS="${ZSTAR_MPI_RANKS:-40}"
OMP_THREADS="${ZSTAR_OMP_THREADS:-1}"
VALENCE="${ZSTAR_PYATB_VALENCE:-10 12 6}"

export OMP_NUM_THREADS="$OMP_THREADS"
export MKL_NUM_THREADS="$OMP_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_THREADS"
export I_MPI_PIN="${I_MPI_PIN:-1}"

timestamp() { date --iso-8601=seconds; }

LOCK_PATH=""
COMPAT_LOG_PATH=""
release_lock() {
    if [[ -n "$LOCK_PATH" ]]; then
        rm -f "$LOCK_PATH/pid" "$LOCK_PATH/host" "$LOCK_PATH/started"
        rmdir "$LOCK_PATH" 2>/dev/null || true
        LOCK_PATH=""
    fi
}
cleanup() {
    [[ -n "$COMPAT_LOG_PATH" ]] && rm -f "$COMPAT_LOG_PATH"
    COMPAT_LOG_PATH=""
    release_lock
}
trap cleanup EXIT
trap 'cleanup; exit 143' INT TERM

acquire_lock() {
    local directory="$1"
    local lock="$directory/.zstar-pyatb.lock"
    if mkdir "$lock" 2>/dev/null; then
        printf '%s\n' "$$" > "$lock/pid"
        printf '%s\n' "$(hostname)" > "$lock/host"
        printf '%s\n' "$(timestamp)" > "$lock/started"
        LOCK_PATH="$lock"
        return 0
    fi
    local old_pid=""
    [[ -f "$lock/pid" ]] && old_pid="$(cat "$lock/pid" 2>/dev/null || true)"
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
        echo "skip active PYATB lock=$lock pid=$old_pid"
        return 1
    fi
    local stale="${lock}.stale-$(date +%Y%m%d-%H%M%S)-$$"
    mv "$lock" "$stale" 2>/dev/null || return 1
    mkdir "$lock" 2>/dev/null || return 1
    printf '%s\n' "$$" > "$lock/pid"
    printf '%s\n' "$(hostname)" > "$lock/host"
    printf '%s\n' "$(timestamp)" > "$lock/started"
    LOCK_PATH="$lock"
    return 0
}

archive_old_outputs() {
    local directory="$1"
    local output="$directory/pyatb"
    local archive="$output/aborted-$(date +%Y%m%d-%H%M%S)-$$"
    local moved=0
    for item in Out Input STRU get_Energy.out; do
        if [[ -e "$output/$item" ]]; then
            [[ "$moved" -eq 0 ]] && { mkdir -p "$archive"; moved=1; }
            mv "$output/$item" "$archive/$item"
        fi
    done
}

run_stage() {
    local stage="$1"
    local directory="$ROOT/$stage"
    if [[ ! -d "$directory" ]]; then
        echo "missing stage: $directory" >&2
        return 2
    fi
    if [[ "$stage" == "reference" ]]; then
        [[ -f "$directory/.scf_done40" || -f "$directory/.done40" ]] || { echo "skip ABACUS-incomplete $stage"; return 0; }
    else
        [[ -f "$directory/.done40" ]] || { echo "skip ABACUS-incomplete $stage"; return 0; }
        [[ -f "$directory/OUT.POLAR/STRU_ION_D" ]] || { echo "skip missing final structure $stage"; return 0; }
        grep -qi "Relaxation is converged" "$directory/OUT.POLAR/running_relax.log" || { echo "skip ionic-incomplete $stage"; return 0; }
        if [[ ! -f "$directory/STRU_INITIAL" ]]; then
            cp "$directory/STRU" "$directory/STRU_INITIAL"
        fi
        cp "$directory/OUT.POLAR/STRU_ION_D" "$directory/STRU"
    fi
    [[ -f "$directory/.pyatb_done40" ]] && { echo "skip PYATB-completed $stage"; return 0; }
    acquire_lock "$directory" || return 0
    archive_old_outputs "$directory"

    # pyatb_input currently hard-codes OUT.*/running_scf.log.  Relaxation
    # output is named running_relax.log, so provide a temporary compatibility
    # copy and remove it before the stage is exposed to the v2 collector.
    if [[ "$stage" != "reference" ]]; then
        COMPAT_LOG_PATH="$directory/OUT.POLAR/running_scf.log"
        cp "$directory/OUT.POLAR/running_relax.log" "$COMPAT_LOG_PATH"
    fi
    "$PYATB_INPUT" -i "$directory" -o "$directory/pyatb" --polar --valence "$VALENCE" \
        > "$directory/pyatb_input_40mpi.log" 2>&1
    local rc=$?
    [[ -n "$COMPAT_LOG_PATH" ]] && { rm -f "$COMPAT_LOG_PATH"; COMPAT_LOG_PATH=""; }
    if [[ "$rc" -ne 0 ]]; then
        echo "pyatb_input failed for $stage rc=$rc" >&2
        release_lock
        return "$rc"
    fi

    cd "$directory/pyatb" || return 2
    "$MPI" -np "$MPI_RANKS" "$PYTHON" "$ADAPTER" > pyatb_precision_40mpi.log 2>&1
    rc=$?
    printf 'node=%s mpi=%s openmp=%s backend=pyatb_precision stage=%s exit_code=%s end=%s\n' \
        "$(hostname)" "$MPI_RANKS" "$OMP_THREADS" "$stage" "$rc" "$(timestamp)" \
        > ../runtime_pyatb_precision40.txt
    cd "$ROOT" || return 2
    if [[ "$rc" -eq 0 && -f "$directory/pyatb/Out/Polarization/polarization.dat" && \
          -f "$directory/pyatb/Out/Polarization/zstar_precision.json" ]]; then
        touch "$directory/.pyatb_done40"
        echo "$(timestamp) DONE $stage"
        release_lock
        return 0
    fi
    echo "PYATB output incomplete for $stage" >&2
    release_lock
    return 3
}

if [[ "$#" -eq 0 ]]; then
    echo "usage: $0 STAGE [STAGE ...]" >&2
    exit 2
fi
for stage in "$@"; do
    run_stage "$stage" || exit $?
done
