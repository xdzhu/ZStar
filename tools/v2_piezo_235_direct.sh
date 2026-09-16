#!/usr/bin/env bash
# Direct single-node runner for 235.  This intentionally does not submit PBS.
set -u -o pipefail

ROOT="${1:?usage: $0 CASE_ROOT VALENCE_LIST}"
shift
# Accept either one quoted list ("20 6") or two shell words (20 6).  This
# makes nested gateway->compute-node SSH launchers immune to quote splitting.
VALENCE="${*:?usage: $0 CASE_ROOT VALENCE_LIST}"
NP="${ZSTAR_MPI_RANKS:-40}"
OMP="${ZSTAR_OMP_THREADS:-1}"
ABACUS="${ZSTAR_ABACUS:-/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus}"
MPI="${ZSTAR_MPI_LAUNCHER:-/home/zhuxd/intel/oneapi/mpi/2021.9.0/bin/mpirun}"
PYATB_INPUT="${ZSTAR_PYATB_INPUT:-/home/zhuxd/Software/anaconda3/envs/icu/bin/pyatb_input}"
PYTHON="${ZSTAR_PYTHON:-/home/zhuxd/Software/anaconda3/envs/icu/bin/python}"
ADAPTER="${ZSTAR_PYATB_ADAPTER:-$ROOT/pyatb_precision.py}"
export OMP_NUM_THREADS="$OMP" MKL_NUM_THREADS="$OMP" OPENBLAS_NUM_THREADS="$OMP"
export I_MPI_FABRICS="${I_MPI_FABRICS:-shm}"

input_value() {
    local input="$1" key="$2"
    awk -v wanted="$key" '
        /^[[:space:]]*($|#)/ { next }
        $1 == wanted { value=$2 }
        END { if (value != "") print value }
    ' "$input"
}

validate_symmetry_protocol() {
    local input="$1" stage="$2" symmetry_prec symmetry
    symmetry_prec=$(input_value "$input" symmetry_prec)
    test -n "$symmetry_prec" && awk -v s="$symmetry_prec" 'BEGIN { exit !(s == 1e-3) }' || {
        echo "v2 requires symmetry_prec=1e-3 in $input" >&2
        return 1
    }
    symmetry=$(input_value "$input" symmetry)
    case "$stage" in
        reference)
            test "$symmetry" = 1 || {
                echo "v2 reference requires symmetry=1 in $input" >&2
                return 1
            }
            ;;
        strain-*)
            test "$symmetry" = 0 || {
                echo "v2 perturbation requires symmetry=0 in $input" >&2
                return 1
            }
            ;;
    esac
}

validate_relax_protocol() {
    local input="$1" force_thr scf_thr relax_nmax
    force_thr=$(input_value "$input" force_thr_ev)
    scf_thr=$(input_value "$input" scf_thr)
    relax_nmax=$(input_value "$input" relax_nmax)
    test -n "$relax_nmax" && awk -v n="$relax_nmax" 'BEGIN { exit !(n >= 100 && n == int(n)) }' || {
        echo "invalid or missing relax_nmax in $input" >&2
        return 1
    }
    test -n "$force_thr" && awk -v f="$force_thr" 'BEGIN { exit !(f == 1e-4) }' || {
        echo "v2 fixed protocol requires force_thr_ev=1e-4 in $input" >&2
        return 1
    }
    test -n "$scf_thr" && awk -v s="$scf_thr" 'BEGIN { exit !(s == 1e-8) }' || {
        echo "v2 fixed protocol requires scf_thr=1e-8 in $input" >&2
        return 1
    }
}

stage_paths=()
if test -n "${ZSTAR_STAGE_IDS:-}"; then
    read -r -a requested_stages <<< "${ZSTAR_STAGE_IDS//,/ }"
    for stage in "${requested_stages[@]}"; do
        case "$stage" in
            reference|strain-*) stage_paths+=("$ROOT/$stage") ;;
            *) echo "invalid stage id in ZSTAR_STAGE_IDS: $stage" >&2; exit 2 ;;
        esac
    done
else
    shopt -s nullglob
    stage_paths=("$ROOT"/reference "$ROOT"/strain-*)
    shopt -u nullglob
fi
test "${#stage_paths[@]}" -gt 0 || { echo "no stages selected under $ROOT" >&2; exit 2; }

for d in "${stage_paths[@]}"; do
    test -d "$d" || continue
    stage=$(basename "$d")
    compat=""
    test -f "$d/INPUT" && test -f "$d/STRU" && test -f "$d/KPT" || { echo "missing inputs in $d" >&2; exit 2; }
    validate_symmetry_protocol "$d/INPUT" "$stage" || exit 3
    calculation=$(input_value "$d/INPUT" calculation)
    calculation=${calculation:-scf}
    case "$calculation" in
        relax|cell-relax) validate_relax_protocol "$d/INPUT" || exit 3 ;;
    esac
    if test ! -f "$d/.abacus_done_${NP}"; then
        start=$(date +%s)
        (cd "$d" && "$MPI" -np "$NP" "$ABACUS" > "abacus_${NP}mpi.log" 2>&1)
        rc=$?; end=$(date +%s)
        printf '{"stage":"%s","node":"%s","mpi":%s,"omp":%s,"returncode":%s,"elapsed_seconds":%s}\n' \
            "$stage" "$(hostname)" "$NP" "$OMP" "$rc" "$((end-start))" > "$d/runtime_abacus_${NP}mpi.json"
        test "$rc" -eq 0 || { echo "ABACUS failed: $stage" >&2; exit "$rc"; }
        case "$calculation" in
            relax|cell-relax)
                grep -qi 'relaxation is converged' "$d"/OUT.*/running_relax.log 2>/dev/null || {
                    echo "ionic relaxation did not converge: $stage" >&2
                    exit 4
                }
                ;;
            *)
                grep -qiE 'charge density convergence is achieved|calculation *finished' "$d"/OUT.*/running_*.log 2>/dev/null || {
                    echo "electronic calculation did not converge: $stage" >&2
                    exit 4
                }
                ;;
        esac
        touch "$d/.abacus_done_${NP}"
    else
        echo "SKIP ABACUS $stage"
    fi
    if test "$stage" != reference; then
        out=$(find "$d" -maxdepth 2 -type f -name STRU_ION_D -print -quit)
        test -n "$out" || { echo "relaxed structure missing for $stage" >&2; exit 5; }
        test -f "$d/STRU_INITIAL" || cp "$d/STRU" "$d/STRU_INITIAL"
        cp "$out" "$d/STRU"
        # PYATB's input generator expects running_scf.log even when the
        # preceding fixed-cell calculation was an ionic relaxation.
        if test -f "$d/OUT."*/running_relax.log; then
            compat=$(find "$d" -maxdepth 2 -type f -name running_relax.log -print -quit | sed 's/running_relax.log/running_scf.log/')
            cp "$(find "$d" -maxdepth 2 -type f -name running_relax.log -print -quit)" "$compat"
        fi
    fi
    test -f "$d/pyatb/Out/Polarization/zstar_precision.json" && { test -z "$compat" || rm -f "$compat"; echo "SKIP PYATB $stage"; continue; }
    test -d "$d/pyatb" && mv "$d/pyatb" "$d/pyatb.aborted" || true
    "$PYATB_INPUT" -i "$d" -o "$d/pyatb" --polar --valence "$VALENCE" > "$d/pyatb_input.log" 2>&1 || { test -z "$compat" || rm -f "$compat"; echo "PYATB input failed: $stage" >&2; exit 6; }
    start=$(date +%s)
    (cd "$d/pyatb" && "$MPI" -np "$NP" "$PYTHON" "$ADAPTER" > "pyatb_precision_${NP}mpi.log" 2>&1)
    rc=$?; end=$(date +%s)
    printf '{"stage":"%s","node":"%s","mpi":%s,"omp":%s,"returncode":%s,"elapsed_seconds":%s}\n' \
        "$stage" "$(hostname)" "$NP" "$OMP" "$rc" "$((end-start))" > "$d/runtime_pyatb_${NP}mpi.json"
    test -z "$compat" || rm -f "$compat"
    test "$rc" -eq 0 || { echo "PYATB failed: $stage" >&2; exit 7; }
    test -f "$d/pyatb/Out/Polarization/polarization.dat" && test -f "$d/pyatb/Out/Polarization/zstar_precision.json" || { echo "missing polarization output: $stage" >&2; exit 8; }
    touch "$d/.pyatb_done_${NP}"
    echo "DONE $stage"
done
echo "V2_PIEZO_CASE_COMPLETE root=$ROOT node=$(hostname) mpi=$NP omp=$OMP"
