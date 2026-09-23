#!/bin/bash
#PBS -j oe
set -euo pipefail

case_dir=${ZSTAR_PBS_CASE:?ZSTAR_PBS_CASE is required}
log="$case_dir/pbs-${PBS_JOBID:-manual}.log"
exec >"$log" 2>&1
trap 'status=$?; echo "FAILED at line $LINENO (exit $status)"; exit $status' ERR
echo "Started $(date -Iseconds) on $(hostname) with ${PBS_NP:-unknown} allocated cores"
if [[ -f /etc/profile.d/modules.sh ]]; then
    source /etc/profile.d/modules.sh
fi
if [[ -n "${ZSTAR_ENV_DIR:-}" ]]; then
    export PATH="$ZSTAR_ENV_DIR/bin:$PATH"
fi
module load intelmpi/2018.1.163
export OMP_NUM_THREADS=${ZSTAR_OMP_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}

ranks=${PBS_NP:-28}
abacus_command=${ZSTAR_ABACUS_COMMAND:-"mpirun -np $ranks abacus"}
pyatb_command=${ZSTAR_PYATB_COMMAND:-pyatb}

cd "$case_dir"
bash run.sh --omp-threads "$OMP_NUM_THREADS" \
    --abacus-command "$abacus_command" --pyatb-command "$pyatb_command"
python analyze.py
echo "Finished $(date -Iseconds)"
