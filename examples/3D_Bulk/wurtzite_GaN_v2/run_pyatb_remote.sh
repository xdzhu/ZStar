#!/usr/bin/env bash
# One PYATB Berry calculation per completed geometry; all a/b/c directions are
# emitted by that single run.  Research-only, no PBS submission.
set -u -o pipefail

ROOT="${1:?usage: $0 ROOT [STAGE ...]}"
shift
PYATB_INPUT="${ZSTAR_PYATB_INPUT:-/home/zhuxd/Software/anaconda3/envs/icu/bin/pyatb_input}"
PYTHON="${ZSTAR_PYTHON:-/home/zhuxd/Software/anaconda3/envs/icu/bin/python}"
MPI="${ZSTAR_MPI_LAUNCHER:-/home/zhuxd/intel/oneapi/mpi/2021.9.0/bin/mpirun}"
NP="${ZSTAR_MPI_RANKS:-40}"
ADAPTER="${ZSTAR_PYATB_ADAPTER:-$(dirname "$0")/pyatb_precision.py}"
VALENCE="${ZSTAR_PYATB_VALENCE:-13 5}"
export OMP_NUM_THREADS="${ZSTAR_OMP_THREADS:-1}"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export I_MPI_FABRICS="${I_MPI_FABRICS:-shm:dapl}"

if test "$#" -eq 0; then
    set -- reference strain-*
fi
for stage in "$@"; do
    d="$ROOT/$stage"
    test -d "$d" || { echo "missing stage $d" >&2; exit 2; }
    test -f "$d/.done40" || { echo "skip ABACUS-incomplete $stage"; continue; }
    if test "$stage" != reference; then
        test -f "$d/OUT.GAN/STRU_ION_D" || { echo "missing relaxed structure $stage" >&2; exit 3; }
        test -f "$d/STRU_INITIAL" || cp "$d/STRU" "$d/STRU_INITIAL"
        cp "$d/OUT.GAN/STRU_ION_D" "$d/STRU"
        compat="$d/OUT.GAN/running_scf.log"
        cp "$d/OUT.GAN/running_relax.log" "$compat"
    else
        compat=""
    fi
    if test -f "$d/pyatb/Out/Polarization/zstar_precision.json"; then
        test -z "$compat" || rm -f "$compat"
        echo "SKIP PYATB $stage"
        continue
    fi
    if test -d "$d/pyatb"; then
        mv "$d/pyatb" "$d/pyatb.aborted-$(date +%Y%m%d-%H%M%S)"
    fi
    "$PYATB_INPUT" -i "$d" -o "$d/pyatb" --polar --valence "$VALENCE" > "$d/pyatb_input.log" 2>&1 || {
        test -z "$compat" || rm -f "$compat"; echo "PYATB input failed $stage" >&2; exit 4;
    }
    (cd "$d/pyatb" && "$MPI" -np "$NP" "$PYTHON" "$ADAPTER" > pyatb_precision40.log 2>&1)
    rc=$?
    test -z "$compat" || rm -f "$compat"
    if test "$rc" -ne 0 || ! test -f "$d/pyatb/Out/Polarization/polarization.dat" || ! test -f "$d/pyatb/Out/Polarization/zstar_precision.json"; then
        echo "PYATB failed or incomplete $stage rc=$rc" >&2
        exit 5
    fi
    touch "$d/.pyatb_done40"
    echo "DONE PYATB $stage"
done
