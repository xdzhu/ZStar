#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/../../.." && pwd)"
PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
PYTHON_BIN="${PYTHON_BIN:-python3}"
ZSTAR=("$PYTHON_BIN" -m zstar)
DATA="$ROOT/results/sample_dataset/dataset.jsonl"
mkdir -p "$ROOT/results/validation" "$ROOT/results/selected_bec" "$ROOT/results/qnep_export"
"${ZSTAR[@]}" data inspect --input "$DATA" > "$ROOT/results/validation/inspect.json"
"${ZSTAR[@]}" data validate --input "$DATA" --report "$ROOT/results/validation/report.json"
"${ZSTAR[@]}" data select --input "$DATA" --output "$ROOT/results/selected_bec/selected.jsonl" --count 4 --seed 7 --temperature-bin 300 --temperature-bin 500 > "$ROOT/results/selected_bec/selection.json"
"${ZSTAR[@]}" data export --input "$ROOT/results/selected_bec/selected.jsonl" --output "$ROOT/results/qnep_export/train.xyz" > "$ROOT/results/qnep_export/export.json"
"${ZSTAR[@]}" qnep check --input "$ROOT/results/qnep_export/train.xyz" --audit-output "$ROOT/results/qnep_export/audit.json" > "$ROOT/results/qnep_export/check.txt"
echo "Level 1 complete: $ROOT/results/qnep_export/train.xyz"
