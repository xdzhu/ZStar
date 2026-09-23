#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
queue=${ZSTAR_PBS_QUEUE:-gold5120}
ppn=${ZSTAR_PBS_PPN:-28}
qsub -V -q "$queue" -l "nodes=1:ppn=$ppn" -N zstar-sic-disp \
    -v ZSTAR_PBS_CASE="$here" "$here/pbs_job.sh"
