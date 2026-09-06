#!/usr/bin/env bash
set -euo pipefail
root=${1:?acceptance workspace required}
source /home/zhuxd/intel/oneapi/setvars.sh >/dev/null 2>&1
unset PYTHONPATH
export PATH="$root/venv/bin:/home/zhuxd/Software/anaconda3/envs/icu_copy/bin:$PATH"
export OMP_NUM_THREADS=40 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export ABACUS_COMMAND='mpirun -np 1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'
export PYATB_COMMAND='env OMP_NUM_THREADS=1 mpirun -np 40 /home/zhuxd/Software/anaconda3/envs/icu_copy/bin/pyatb'
cd "$root"
python -c 'import zstar; print(zstar.__file__)'
zstar --version
for case in Bulk_HfO2 2D_MoS2 Nanowire_Sb2S3 Molecule_CH4; do
    (cd "examples/IR_Raman_Spectra/$case"; bash run.sh --dry-run; bash run.sh --post-only)
done
cd examples/IR_Raman_Spectra/Molecule_CH4
bash run.sh --work work-rc6
# Exercise the normal user restart, not a synthetic status-only check.
bash run.sh --work work-rc6
zstar spectra stat --root work-rc6/spectra
printf 'RELEASE_ACCEPTANCE_COMPLETE\n'
