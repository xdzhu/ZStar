#!/usr/bin/env bash
set -euo pipefail

# Optional external stage. The normal `run/run.sh` remains CPU-only and does
# not require GPUMD. On a GPU host set GPUMD_ROOT to a GPUMD build directory,
# e.g. GPUMD_ROOT=/path/to/GPUMD/src, and choose an idle CUDA device.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${ROOT}/../../.." && pwd)"
GPUMD_ROOT="${GPUMD_ROOT:?Set GPUMD_ROOT to the directory containing nep and gpumd}"
GPU="${CUDA_VISIBLE_DEVICES:-0}"
SEED_DIR="${ROOT}/results/qnep_training/cubic_104_seed20260913"
DATASET="${ROOT}/results/qnep_export/train_qnep_249_sparse62.xyz"

PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" python "${ROOT}/run/prepare_qnep_training.py" \
  --input "${DATASET}" \
  --output-dir "${SEED_DIR}"
cp "${ROOT}/run/qnep_train_nep.in" "${SEED_DIR}/nep.in"
(cd "${SEED_DIR}" && CUDA_VISIBLE_DEVICES="${GPU}" "${GPUMD_ROOT}/nep" > train.log 2>&1)
PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" python "${ROOT}/run/evaluate_qnep_training.py" \
  --run-dir "${SEED_DIR}" \
  --output "${SEED_DIR}/metrics.json"

echo "qNEP training completed; use build_qnep_gpumd_phonon_inputs.py and GPUMD"
echo "compute_phonon/dump_xyz for the optional Level 2 phonon/NAC stage."
