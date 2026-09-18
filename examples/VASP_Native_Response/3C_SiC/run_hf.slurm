#!/usr/bin/env bash
#SBATCH --job-name=zstar-native-SiC
#SBATCH --partition=hfacnormal01
#SBATCH --nodes=1
#SBATCH --ntasks=64
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
source /public/home/iai806/Software/VASP/env.sh 6.3.2
export PATH=/public/home/iai806/zstar-validation/vasp-native-20260918/venv/bin:$PATH
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
cd "$SLURM_SUBMIT_DIR"
bash run.sh
