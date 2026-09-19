#!/usr/bin/env bash
set -euo pipefail

CASE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$CASE_DIR/../../.." && pwd)
WORK_ROOT="${ZSTAR_WORK_ROOT:-$CASE_DIR/work}"
ACTION="${1:-status}"
PYTHON="${ZSTAR_PYTHON:-python}"

case "$ACTION" in
  check)
    "$PYTHON" "$REPO_ROOT/tools/check_piezoelectric_example.py" "$CASE_DIR"
    ;;
  prepare)
    "$PYTHON" "$REPO_ROOT/tools/prepare_piezoelectric_case.py" --source "$CASE_DIR/run" \
      --output "$WORK_ROOT" --pp "$CASE_DIR/run" --orb "$CASE_DIR/run" \
      --profile production --amplitude 0.005 \
      --ion-relaxation relaxed-ion
    ;;
  run)
    bash "$REPO_ROOT/tools/run_piezoelectric_ensemble.sh" "$WORK_ROOT" 3 5
    ;;
  status)
    test -d "$WORK_ROOT" || { echo "not prepared: $WORK_ROOT"; exit 0; }
    find "$WORK_ROOT" -maxdepth 2 \( -name '.abacus_done_*' -o -name '.pyatb_done_*' \) -print | sort
    ;;
  collect)
    "$PYTHON" "$REPO_ROOT/tools/collect_piezoelectric_case.py" "$WORK_ROOT" \
      --output "$WORK_ROOT/results" --acoustic-gauge equal-weight
    ;;
  *) echo "usage: $0 {check|prepare|run|status|collect}" >&2; exit 2 ;;
esac
