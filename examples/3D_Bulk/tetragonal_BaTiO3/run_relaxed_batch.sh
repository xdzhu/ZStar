#!/usr/bin/env bash
# Experimental v2 runner for fixed-cell ABACUS ionic relaxations.
#
# The runner deliberately lives next to the research fixture rather than in
# the stable CLI.  It uses an atomic per-stage directory lock so two launchers
# cannot write the same ABACUS directory concurrently.
set -u -o pipefail

CASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ZSTAR_V2_RUN_ROOT:-$CASE_ROOT/run}"
ABACUS="${ZSTAR_ABACUS:-abacus}"
MPI="${ZSTAR_MPI_LAUNCHER:-mpirun}"
MPI_RANKS="${ZSTAR_MPI_RANKS:-40}"
OMP_THREADS="${ZSTAR_OMP_THREADS:-1}"

export OMP_NUM_THREADS="$OMP_THREADS"
export MKL_NUM_THREADS="$OMP_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_THREADS"
export I_MPI_PIN="${I_MPI_PIN:-1}"

timestamp() { date --iso-8601=seconds; }

stage_lock() {
    local directory="$1"
    local lock="$directory/.zstar-stage.lock"
    if mkdir "$lock" 2>/dev/null; then
        printf '%s\n' "$$" > "$lock/pid"
        printf '%s\n' "$(hostname)" > "$lock/host"
        printf '%s\n' "$(timestamp)" > "$lock/started"
        return 0
    fi

    local old_pid=""
    if [[ -f "$lock/pid" ]]; then
        old_pid="$(cat "$lock/pid" 2>/dev/null || true)"
    fi
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
        echo "skip active stage lock=$lock pid=$old_pid"
        return 1
    fi

    # A killed launcher can leave a stale lock.  Move it aside for audit; the
    # atomic rename prevents a second launcher from deleting a fresh lock.
    local stale="${lock}.stale-$(date +%Y%m%d-%H%M%S)-$$"
    if ! mv "$lock" "$stale" 2>/dev/null; then
        echo "stage lock changed while inspecting: $lock" >&2
        return 1
    fi
    if ! mkdir "$lock" 2>/dev/null; then
        echo "could not recreate stage lock: $lock" >&2
        return 1
    fi
    printf '%s\n' "$$" > "$lock/pid"
    printf '%s\n' "$(hostname)" > "$lock/host"
    printf '%s\n' "$(timestamp)" > "$lock/started"
    return 0
}

stage_unlock() {
    local directory="$1"
    local lock="$directory/.zstar-stage.lock"
    rm -f "$directory/.running40" "$lock/pid" "$lock/host" "$lock/started"
    rmdir "$lock" 2>/dev/null || true
}

run_stage() {
    local stage="$1"
    local directory="$ROOT/$stage"
    if [[ ! -d "$directory" ]]; then
        echo "missing stage: $directory" >&2
        return 2
    fi
    if [[ -f "$directory/.done40" ]]; then
        echo "skip completed $stage"
        return 0
    fi
    if ! stage_lock "$directory"; then
        # Another launcher owns the stage, or a concurrent launcher won the
        # stale-lock race.  Never start a second MPI job in that directory.
        return 0
    fi

    for required in INPUT STRU KPT; do
        if [[ ! -f "$directory/$required" ]]; then
            echo "missing $required in $directory" >&2
            stage_unlock "$directory"
            return 2
        fi
    done

    echo "$(timestamp) START $stage" | tee "$directory/status_40mpi.log"
    printf '%s\n' "$$" > "$directory/.running40"
    local start end rc
    start="$(date +%s)"
    (
        cd "$directory" || exit 2
        "$MPI" -np "$MPI_RANKS" "$ABACUS" > abacus_40mpi.log 2>&1
    )
    rc=$?
    end="$(date +%s)"
    printf 'node=%s mpi=%s openmp=%s stage=%s exit_code=%s elapsed_seconds=%s start_epoch=%s end_epoch=%s\n' \
        "$(hostname)" "$MPI_RANKS" "$OMP_THREADS" "$stage" "$rc" "$((end-start))" "$start" "$end" \
        > "$directory/runtime_40mpi.txt"

    if [[ "$rc" -ne 0 ]]; then
        echo "$(timestamp) FAIL $stage exit_code=$rc" | tee -a "$directory/status_40mpi.log" "$directory/failed_40mpi.log"
        stage_unlock "$directory"
        return "$rc"
    fi

    local relax_log=""
    for candidate in "$directory/OUT.POLAR/running_relax.log" "$directory/OUT.POLAR/running_cell-relax.log"; do
        if [[ -f "$candidate" ]]; then
            relax_log="$candidate"
            break
        fi
    done
    if [[ ! -f "$directory/OUT.POLAR/STRU_ION_D" ]] || [[ -z "$relax_log" ]] || \
       ! grep -q "Relaxation is converged" "$relax_log"; then
        echo "$(timestamp) FAIL $stage ionic relaxation not converged" | tee -a "$directory/status_40mpi.log" "$directory/failed_40mpi.log"
        stage_unlock "$directory"
        return 3
    fi

    touch "$directory/.done40"
    echo "$(timestamp) DONE $stage" | tee -a "$directory/status_40mpi.log"
    stage_unlock "$directory"
}

if [[ "$#" -eq 0 ]]; then
    echo "usage: $0 STAGE [STAGE ...]" >&2
    exit 2
fi
for stage in "$@"; do
    run_stage "$stage" || exit $?
done
