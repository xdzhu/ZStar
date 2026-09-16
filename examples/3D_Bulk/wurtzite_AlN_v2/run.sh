#!/usr/bin/env bash
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$CASE_DIR/../../.." && pwd)
RUN_ROOT="$CASE_DIR/run/production"
ACTION=${1:-status}

require_file() {
    test -f "$1" || { echo "missing required file: $1" >&2; exit 2; }
}

verify_hash() {
    local file=$1 expected=$2 actual
    require_file "$file"
    actual=$(sha256sum "$file" | awk '{print $1}')
    test "$actual" = "$expected" || {
        echo "SHA-256 mismatch for $file" >&2
        echo "expected $expected" >&2
        echo "actual   $actual" >&2
        exit 2
    }
}

preflight() {
    command -v python >/dev/null || { echo "python is required" >&2; exit 2; }
    verify_hash "$CASE_DIR/pseudopotentials/Al.upf" 0674454d87460e8184c858c6628332728daa8f5c130dda89521593a240bc3da0
    verify_hash "$CASE_DIR/pseudopotentials/N.upf" 153a989f135fffe2e0f091bad0bbd724c0df5c12042ad3365f24feb0a426c529
    verify_hash "$CASE_DIR/orbitals/Al_gga_8au_100Ry_2s2p1d.orb" b4bed68f9596afcef0d25c3f4890d1a8293eb89262c73a13ac98ddeb43ff83ca
    verify_hash "$CASE_DIR/orbitals/N_gga_8au_100Ry_2s2p1d.orb" 2b4eec917686de180da0aecdabb6e25e24b5d980f9b25a14b37a024a14f95be3
}

case "$ACTION" in
    prepare)
        preflight
        if test -d "$RUN_ROOT" && test -n "$(find "$RUN_ROOT" -mindepth 1 -print -quit 2>/dev/null)"; then
            echo "run directory is not empty: $RUN_ROOT" >&2
            echo "keep it for restart, or move it aside explicitly before preparing again" >&2
            exit 2
        fi
        mkdir -p "$RUN_ROOT"
        python "$REPO_ROOT/tools/prepare_v2_piezo_case.py" \
            --source "$CASE_DIR/inputs" \
            --output "$RUN_ROOT" \
            --pseudopotential-dir "$CASE_DIR/pseudopotentials" \
            --orbital-dir "$CASE_DIR/orbitals" \
            --profile production \
            --amplitude 0.005 \
            --ion-relaxation relaxed-ion
        echo "prepared fixed production ensemble: $RUN_ROOT"
        ;;
    submit)
        command -v sbatch >/dev/null || { echo "submit requires HF Slurm (sbatch not found)" >&2; exit 2; }
        require_file "$RUN_ROOT/convergence_profile.txt"
        export ZSTAR_V2_CONVERGENCE_PROFILE=production
        export ZSTAR_MPI_RANKS=32
        export ZSTAR_OMP_THREADS=1
        export ZSTAR_PYATB_ADAPTER="$REPO_ROOT/zstar/pyatb_precision.py"
        sbatch --job-name=zv2-aln-prod --ntasks=32 --cpus-per-task=1 \
            --output="$RUN_ROOT/slurm-%j.out" --error="$RUN_ROOT/slurm-%j.err" \
            --export=ALL "$REPO_ROOT/tools/v2_piezo_hf.slurm" "$RUN_ROOT" "3 5"
        ;;
    status)
        if test ! -d "$RUN_ROOT"; then
            echo "not prepared: $RUN_ROOT"
            exit 0
        fi
        printf 'ABACUS complete: %s/13\n' "$(find "$RUN_ROOT" -name '.abacus_done_32' | wc -l)"
        printf 'PYATB complete:  %s/13\n' "$(find "$RUN_ROOT" -name '.pyatb_done_32' | wc -l)"
        find "$RUN_ROOT" -maxdepth 1 -name 'slurm-*.out' -o -name 'slurm-*.err' | sort
        ;;
    collect)
        require_file "$RUN_ROOT/reference/.pyatb_done_32"
        python "$REPO_ROOT/tools/collect_v2_piezo_case.py" "$RUN_ROOT" \
            --output "$RUN_ROOT/results" --symmetry-relative-tolerance 0.001 \
            --acoustic-gauge equal-weight
        ;;
    *)
        echo "usage: $0 {prepare|submit|status|collect}" >&2
        exit 2
        ;;
esac
