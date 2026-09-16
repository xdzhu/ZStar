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
PROFILE="${ZSTAR_V2_CONVERGENCE_PROFILE:-production}"
ABACUS_ENV="${ZSTAR_ABACUS_ENV:-/public/home/iai806/apprepo/abacus/v3.10.0LTS-intelmpi2025/scripts/env.sh}"
PYATB_ENV="${ZSTAR_PYATB_ENV:-/public/home/iai806/apprepo/pyatb/v1.1.2-mpi4py/scripts/env.sh}"
ADAPTER="${ZSTAR_PYATB_ADAPTER:-$ROOT/pyatb_precision.py}"

export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"

case "$PROFILE" in
    production) MAX_SCF=1e-8; MAX_RELAX_FORCE=1e-4 ;;
    verification) MAX_SCF=1e-10; MAX_RELAX_FORCE=1e-6 ;;
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

require_leq() {
    local input="$1" key="$2" limit="$3"
    local value
    value=$(input_value "$input" "$key")
    awk -v x="$value" -v limit="$limit" 'BEGIN { exit !(x > 0 && x <= limit) }' || {
        echo "v2 HF runner requires $key<=$limit in $input" >&2
        return 1
    }
}

validate_stage_input() {
    local input="$1" stage="$2" calculation symmetry
    symmetry=$(input_value "$input" symmetry)
    awk -v x="$(input_value "$input" symmetry_prec)" 'BEGIN { exit !(x == 1e-3) }' || {
        echo "v2 HF runner requires symmetry_prec=1e-3 in $input" >&2; return 1;
    }
    calculation=$(input_value "$input" calculation)
    calculation=${calculation:-scf}
    case "$stage" in
        reference)
            test "$symmetry" = "1" || { echo "v2 reference requires symmetry=1" >&2; return 1; }
            require_leq "$input" scf_thr "$MAX_SCF" || return 1
            case "$calculation" in
                scf) ;;
                relax)
                    require_leq "$input" force_thr_ev "$MAX_RELAX_FORCE" || return 1
                    awk -v x="$(input_value "$input" relax_nmax)" 'BEGIN { exit !(x >= 100 && x == int(x)) }' || {
                        echo "v2 relaxed response reference requires integer relax_nmax>=100" >&2; return 1;
                    }
                    ;;
                *) echo "unsupported v2 response reference calculation=$calculation in $input" >&2; return 1 ;;
            esac
            ;;
        strain-*)
            test "$symmetry" = "0" || { echo "v2 perturbations require symmetry=0" >&2; return 1; }
            case "$calculation" in
                scf) require_leq "$input" scf_thr "$MAX_SCF" || return 1 ;;
                relax)
                    require_leq "$input" force_thr_ev "$MAX_RELAX_FORCE" || return 1
                    require_leq "$input" scf_thr "$MAX_SCF" || return 1
                    awk -v x="$(input_value "$input" relax_nmax)" 'BEGIN { exit !(x >= 100 && x == int(x)) }' || {
                        echo "v2 relaxed perturbations require integer relax_nmax>=100" >&2; return 1;
                    }
                    ;;
                *) echo "unsupported v2 response calculation=$calculation in $input" >&2; return 1 ;;
            esac
            ;;
    esac
}

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
    test -f "$d/INPUT" && test -f "$d/STRU" && test -f "$d/KPT" || { echo "missing inputs in $d" >&2; exit 2; }
    validate_stage_input "$d/INPUT" "$stage" || exit 2
    calculation=$(input_value "$d/INPUT" calculation)
    calculation=${calculation:-scf}
    if test ! -f "$d/.abacus_done_${NP}"; then
        echo "START ABACUS $stage node=$(hostname) mpi=$NP omp=$OMP"
        run_abacus "$d" "$stage" || { echo "ABACUS failed: $stage" >&2; exit 3; }
        case "$calculation" in
            relax) grep -qi 'relaxation is converged' "$d"/OUT.*/running_relax.log 2>/dev/null || { echo "ionic relaxation did not converge: $stage" >&2; exit 4; } ;;
            scf) grep -qiE 'charge density convergence is achieved|calculation *finished' "$d"/OUT.*/running_scf.log 2>/dev/null || { echo "electronic calculation did not converge: $stage" >&2; exit 4; } ;;
        esac
        touch "$d/.abacus_done_${NP}"
    else
        echo "SKIP ABACUS $stage"
    fi
    if test "$calculation" = relax; then
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
echo "V2_PIEZO_CASE_COMPLETE root=$ROOT profile=$PROFILE node=$(hostname) mpi=$NP omp=$OMP"
