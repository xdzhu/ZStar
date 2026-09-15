#!/usr/bin/env bash
set -euo pipefail

# Templates only: define paths to locally generated data and never embed a
# machine-specific absolute path in this example.
RAW_JSONL="${RAW_JSONL:?set RAW_JSONL}"
ANNOTATIONS_JSONL="${ANNOTATIONS_JSONL:?set ANNOTATIONS_JSONL}"
OUT_DIR="${OUT_DIR:-results/generated}"

mkdir -p "$OUT_DIR"
zstar qnep export --input "$RAW_JSONL" --annotations "$ANNOTATIONS_JSONL" \
  --output "$OUT_DIR/multiphase.xyz" --audit-output "$OUT_DIR/export.audit.json"
zstar qnep check --input "$OUT_DIR/multiphase.xyz"

# Example phase-stratified composition.  Run GPUMD/qNEP training separately.
# zstar qnep compose --base cubic_full.xyz --addition "$OUT_DIR/multiphase.xyz" \
#   --phases tetragonal orthorhombic rhombohedral --max-per-phase 108 \
#   --seed 20260915 --output "$OUT_DIR/cubic_plus_balanced.xyz"
