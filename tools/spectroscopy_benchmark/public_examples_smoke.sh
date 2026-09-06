#!/usr/bin/env bash
set -euo pipefail
export PATH=/home/zhuxd/Software/anaconda3/envs/icu_copy/bin:$PATH
export PYTHONPATH=/home/zhuxd/abacus/agent-runs/20260906-unified-spectroscopy/public-code
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
root=/home/zhuxd/abacus/agent-runs/20260906-unified-spectroscopy/public-examples
for case in Bulk_HfO2 2D_MoS2 Nanowire_Sb2S3 Molecule_CH4; do
    bash "$root/examples/IR_Raman_Spectra/$case/run.sh" --post-only
done
