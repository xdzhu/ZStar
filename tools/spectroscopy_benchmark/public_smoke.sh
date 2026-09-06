#!/usr/bin/env bash
set -euo pipefail
source /home/zhuxd/intel/oneapi/setvars.sh >/dev/null 2>&1
export PATH=/home/zhuxd/Software/anaconda3/envs/icu_copy/bin:$PATH
export PYTHONPATH=/home/zhuxd/abacus/agent-runs/20260906-unified-spectroscopy/public-code
export OMP_NUM_THREADS=40 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
root=/home/zhuxd/abacus/agent-runs/20260906-unified-spectroscopy/CH4/public_workflow
source_root=/home/zhuxd/abacus/agent-runs/20260904-molecular-relaxed-efficiency/CH4/unified
if [[ ! -f "$root/.zstar/spectra.json" ]]; then
    python -m zstar spectra pre --response "$source_root" --root "$root"
fi
python -m zstar spectra run --root "$root" \
    --abacus-command 'mpirun -np 1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus' \
    --pyatb-command 'env OMP_NUM_THREADS=1 mpirun -np 40 pyatb' --omp-threads 40
python -m zstar spectra post --root "$root"
python -m zstar spectra stat --root "$root"
